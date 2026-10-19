"""Proposal queue ingest (R7): validate a model/human proposal and queue it.

A proposal only ever lands in the append-only `proposals` queue. A technical
failure (schema, unknown id, quote that is not a literal Passage slice) stores the
proposal and a review with decision `auto_rejected` and a code, never an approved
record. `auto_rejected` is a technical rejection, not human review; its
`evidence_class` is `auto_technical` (T-ENUM keeps the real class set open).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .packets import TASK_TYPES, output_schema_id, verify_packet
from .profile import load_profile
from .repository import SCHEMA_DIR, Repository
from .runtime import EXIT_USAGE, LaError, sha256_obj
from .validation import load_registry, validate

AUTO_REJECTED = "auto_rejected"


def _known(repo: Repository, profile: dict[str, Any]) -> dict[str, Any]:
    reader = repo.reader()
    passages = {b["id"]: b["text"] for b, _ in repo.frozen_bodies("passages")}
    passage_flags = {b["id"]: b["quality_flags"] for b, _ in repo.frozen_bodies("passages")}
    ids = {t: {r["id"] for r in reader.approved_rows(t)}
           for t in ("observation_sets", "observations", "hypotheses", "perspectives")}
    ids["perspectives"] |= {p["id"] for p in profile["perspectives"]}
    from . import facts
    sets = {s["id"]: facts.effective_observation_ids(reader, s)
            for s in reader.approved_rows("observation_sets")}
    return {"passages": passages, "passage_flags": passage_flags, **ids,
            "documents": {b["id"] for b, _ in repo.frozen_bodies("documents")},
            "passage_documents": {b["id"]: b["document_id"] for b, _ in repo.frozen_bodies("passages")},
            "scope_observations": sets,
            "hypothesis_scopes": {h["id"]: h["scope_id"] for h in reader.approved_rows("hypotheses")}}


def check_item(task: str, item: dict[str, Any], known: dict[str, Any]) -> str | None:
    """First reference/quote problem of one item, or None."""
    def miss(kind: str, value: str) -> str | None:
        return None if value in known[kind] else "E_UNKNOWN_ID"
    if task == "claims":
        if item["passage_id"] not in known["passages"]:
            return "E_UNKNOWN_ID"
        text = known["passages"][item["passage_id"]]
        if not (0 <= item["start"] < item["end"] <= len(text)) or text[item["start"]:item["end"]] != item["quote"]:
            return "E_QUOTE_MISMATCH"
    elif task in ("hypotheses", "altcause"):
        for r in (miss("observation_sets", item["scope_id"]), *[miss("perspectives", b) for b in item["burdens"]],
                  miss("hypotheses", item["alternative_to"]) if task == "altcause" else None):
            if r:
                return r
    elif task == "matrix":
        for r in (miss("observations", item["observation_id"]), miss("hypotheses", item["hypothesis_id"]),
                  *[None if p in known["passages"] else "E_UNKNOWN_ID" for p in item["basis_passage_ids"]]):
            if r:
                return r
    elif task == "tests":
        for o in item["outcomes"]:
            for h in o["impact"]:
                if h not in known["hypotheses"]:
                    return "E_UNKNOWN_ID"
        # Also used by generic ingest-proposal and corrected human review items.
        # No entry path may skip the document/action contract.
        from .test_plan import validate_action_item, validate_test_item
        scope_hyps = sorted(h for h, scope in known["hypothesis_scopes"].items()
                            if scope == item["scope_id"])
        return validate_action_item(item, known) or validate_test_item(item, scope_hyps)
    elif task == "event_time":
        return miss("observations", item["observation_id"])
    return None


def validate_payload(task: str, payload: dict[str, Any], known: dict[str, Any],
                     registry: dict[str, Any]) -> str | None:
    errs = validate(payload, registry[output_schema_id(task)], registry)
    if errs:
        return "E_SCHEMA"
    for item in payload["items"]:
        code = check_item(task, item, known)
        if code:
            return code
    return None


def ingest_proposal(case_dir: Path | str, packet: dict[str, Any], payload: Any,
                    enrich: Callable[[str, dict[str, Any], dict[str, Any]], tuple[dict[str, Any], str | None]] | None = None
                    ) -> dict[str, Any]:
    """Queue `payload` for `packet`; returns {proposal_id, state, code}. Never approves.

    `enrich(task, payload, known)` may add computed fields (guard flags) or return a technical
    rejection code; it runs only after schema and reference checks passed.
    """
    root = Path(case_dir)
    profile = load_profile(root)
    registry = load_registry(SCHEMA_DIR)
    verify_packet(packet, registry)
    if packet["case_id"] != profile["case_id"]:
        raise LaError("E_FOREIGN_CASE", "The packet belongs to another case.", "Pakiet należy do innej sprawy.",
                      EXIT_USAGE)
    if not isinstance(payload, dict):
        raise LaError("E_PAYLOAD_NOT_OBJECT", "A proposal must be a JSON object.", "Propozycja musi być obiektem JSON.",
                      EXIT_USAGE)
    task = packet["task_type"]
    if task not in TASK_TYPES:
        raise LaError("E_UNKNOWN_TASK", "Unknown task type.", "Nieznany typ zadania.", EXIT_USAGE)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        known = _known(repo, profile)
        code = validate_payload(task, payload, known, registry)
        stored = payload
        if code is None and enrich is not None:
            stored, code = enrich(task, payload, known)
            if code is not None:
                stored = payload  # a rejected proposal is stored exactly as received
        pid = "prop:" + sha256_obj({"cache_key": packet["cache_key"], "payload": stored})[:24]
        run = repo.reader().runs()[-1]
        model = packet["model_id"]
        step_id = f"propose:{pid[5:]}"
        repo.add_step(step_id, run["id"], "ingest-proposal", "none" if model == "none" else f"model:{model}")
        repo.add_proposal({"id": pid, "task_type": task, "cache_key": packet["cache_key"], "payload_json": stored},
                          step_id)
        if code:
            repo.record_review({"case_id": profile["case_id"], "id": f"rev:auto-{pid[5:]}", "item_id": pid,
                                "decision": AUTO_REJECTED, "reviewer": "software:la.py", "reason": code,
                                "evidence_class": "auto_technical", "review_file_sha256": sha256_obj(stored),
                                "batch_id": "auto", "sampled": False}, step_id)
        state = repo.proposal_state()[pid]
    finally:
        repo.close()
    return {"ok": True, "proposal_id": pid, "state": state, "code": code, "payload": stored}
