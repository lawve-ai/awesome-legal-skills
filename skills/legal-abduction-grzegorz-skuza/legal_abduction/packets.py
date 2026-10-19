"""Model task packets (H steps): identical protocol for `host` and `none`.

The script never calls a model or the network. It emits `task_packet.json` plus a
`proposal.template.json` skeleton; a host model or a human fills the proposal and
`ingest-proposal` validates it (see proposals.py). The cache key covers the case,
task type, schema/prompt/model versions, the analysis hash and the hash of every
object in the packet; `lang` is deliberately excluded so a language change never
re-triggers model work for existing content. A packet that exceeds `max_chars` is
refused, never truncated. Production `prepare` for hypotheses and matrix needs a
budget hook (provided by the review budget calculator, LA-012); without it the
call fails instead of letting packets through silently.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from .profile import load_profile, analysis_hash, require_ready
from .repository import Repository, SCHEMA_DIR
from .runtime import EXIT_POLICY, EXIT_USAGE, LaError, atomic_write, canonical_json, sha256_obj
from .validation import admit, load_registry

TASK_TYPES = ("claims", "hypotheses", "altcause", "matrix", "tests", "event_time")
BUDGET_REQUIRED = frozenset({"hypotheses", "matrix"})
SCHEMA_VERSION = 1
MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")

BudgetHook = Callable[[str, int, int], bool]


def output_schema_id(task_type: str) -> str:
    return f"la:schema/task_{task_type}/v{2 if task_type == 'tests' else 1}"


def make_object(obj_type: str, obj_id: str, content: dict[str, Any]) -> dict[str, Any]:
    return {"type": obj_type, "id": obj_id, "hash": sha256_obj(content), "content": content}


def compute_cache_key(case_id: str, task_type: str, prompt_version: str, model_id: str, analysis_hash_: str,
                      items: list[dict[str, Any]]) -> str:
    return sha256_obj({
        "case_id": case_id, "task_type": task_type, "schema_version": SCHEMA_VERSION,
        "output_schema_id": output_schema_id(task_type), "prompt_version": prompt_version, "model_id": model_id,
        "analysis_hash": analysis_hash_,
        "objects": sorted([[i["type"], i["id"], i["hash"]] for i in items]),
    })


def prune_passages(passages: list[dict[str, Any]], representative_docs: set[str] | None,
                   out_of_scope_ids: set[str] | None = None) -> list[dict[str, Any]]:
    """Drop out-of-scope passages and copies (only family representatives are packed)."""
    out = []
    for p in passages:
        if out_of_scope_ids and p["id"] in out_of_scope_ids:
            continue
        if representative_docs is not None and p["document_id"] not in representative_docs:
            continue
        out.append(p)
    return out


def build_packet(case_id: str, task_type: str, objects: list[dict[str, Any]], *, model_id: str, prompt_version: str,
                 lang: str, analysis_hash_: str, max_chars: int | None = None) -> dict[str, Any]:
    if task_type not in TASK_TYPES:
        raise LaError("E_UNKNOWN_TASK", "Unknown task type.", "Nieznany typ zadania.", EXIT_USAGE)
    if not MODEL_ID_RE.match(model_id):
        raise LaError("E_BAD_CONFIG", "model_id has an invalid format.", "Nieprawidłowy format model_id.", EXIT_USAGE)
    items = [{"type": o["type"], "id": o["id"], "hash": sha256_obj(o["content"]), "content": o["content"]}
             for o in objects]
    key = compute_cache_key(case_id, task_type, prompt_version, model_id, analysis_hash_, items)
    packet = {"case_id": case_id, "packet_id": f"pkt-{key[:16]}", "task_type": task_type,
              "schema_version": SCHEMA_VERSION, "prompt_version": prompt_version, "lang": lang, "model_id": model_id,
              "analysis_hash": analysis_hash_, "output_schema_id": output_schema_id(task_type), "cache_key": key,
              "items": sorted(items, key=lambda i: (i["type"], i["id"]))}
    size = len(canonical_json(packet).decode("utf-8"))
    if max_chars is not None and size > max_chars:
        raise LaError("E_PACKET_TOO_LARGE", "Packet exceeds packet.max_chars; narrow the scope (no truncation).",
                      "Pakiet przekracza packet.max_chars; zawęź zakres (bez ucinania).", EXIT_USAGE,
                      {"size": str(size), "limit": str(max_chars)})
    return packet


def verify_packet(packet: dict[str, Any], registry: dict[str, Any] | None = None) -> None:
    """Schema, per-object hashes and cache key must all be self-consistent."""
    reg = registry or load_registry(SCHEMA_DIR)
    admit(packet, "la:schema/packet/v1", reg)
    for i in packet["items"]:
        if i["hash"] != sha256_obj(i["content"]):
            raise LaError("E_PACKET_TAMPERED", "Packet object hash mismatch.", "Niezgodność hasza obiektu pakietu.",
                          EXIT_USAGE, {"id": i["id"]})
    want = compute_cache_key(packet["case_id"], packet["task_type"], packet["prompt_version"], packet["model_id"],
                             packet["analysis_hash"], packet["items"])
    if want != packet["cache_key"] or packet["output_schema_id"] != output_schema_id(packet["task_type"]):
        raise LaError("E_PACKET_TAMPERED", "Packet cache key mismatch.", "Niezgodność klucza cache pakietu.", EXIT_USAGE)


def prepare(case_dir: Path | str, task_type: str, objects: list[dict[str, Any]], *, model_id: str = "none",
            prompt_version: str | None = None, max_chars: int | None = None, budget_hook: BudgetHook | None = None,
            synthetic: bool = False) -> dict[str, Any]:
    """Emit a packet for the case. `synthetic=True` skips the budget hook (tests/fixtures only)."""
    root = Path(case_dir)
    gate = require_ready(root, "prepare", touches_corpus=True)
    profile = load_profile(root)
    packet = build_packet(profile["case_id"], task_type, objects, model_id=model_id,
                          prompt_version=prompt_version or f"{task_type}-1", lang=profile["lang"],
                          analysis_hash_=analysis_hash(profile), max_chars=max_chars)
    chars = len(canonical_json(packet).decode("utf-8"))
    if task_type in BUDGET_REQUIRED and not synthetic:
        if budget_hook is None:
            raise LaError("E_BUDGET_HOOK_REQUIRED", "A review-budget hook is required before packing this task "
                          "(calculator arrives with LA-012).", "Przed pakowaniem tego zadania wymagany jest hook "
                          "budżetu recenzji (kalkulator: LA-012).", EXIT_POLICY)
        if budget_hook(task_type, chars, len(packet["items"])) is not True:
            raise LaError("E_BUDGET_REFUSED", "The review budget does not allow this packet.",
                          "Budżet recenzji nie pozwala na ten pakiet.", EXIT_POLICY)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        cached = [(i, s) for i, s in repo.proposal_ids_for_cache_key(packet["cache_key"]) if s != "auto_rejected"]
    finally:
        repo.close()
    if cached:
        return {"ok": True, "cache_hit": True, "packet_id": packet["packet_id"], "cache_key": packet["cache_key"],
                "proposals": sorted(i for i, _ in cached), "mode": gate["mode"]}
    base = f"packets/{packet['packet_id']}"
    atomic_write(root, f"{base}/task_packet.json", canonical_json(packet) + b"\n")
    atomic_write(root, f"{base}/proposal.template.json", canonical_json({"items": []}) + b"\n")
    return {"ok": True, "cache_hit": False, "packet_id": packet["packet_id"], "cache_key": packet["cache_key"],
            "path": f"{base}/task_packet.json", "chars": chars, "mode": gate["mode"]}
