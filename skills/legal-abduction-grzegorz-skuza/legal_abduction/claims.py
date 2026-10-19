"""Claims: segmentation for `claims prepare` and guarded ingest for `claims ingest`.

Both reuse the shared packet/proposal protocol. Guard flags are computed here
(any model-supplied `guard_flags` is overwritten), stored with the queued proposal
and mapped to a triage class; a flagged proposal still needs individual review and
is never approved by this module.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import families, guards, packets, proposals
from .repository import Repository
from .runtime import EXIT_USAGE, LaError

_BOUND = re.compile(r"(?<=[.!?…])\s+(?=[\"„“«A-ZĄĆĘŁŃÓŚŹŻ0-9])")


def segment(text: str) -> list[dict[str, Any]]:
    """Sentence-like segments as literal slices with code-point offsets."""
    segs, pos = [], 0
    for m in _BOUND.finditer(text):
        segs.append((pos, m.start()))
        pos = m.end()
    segs.append((pos, len(text)))
    return [{"start": a, "end": b, "text": text[a:b]} for a, b in segs if text[a:b].strip()]


def claim_objects(case_dir: Path | str, case_id: str) -> list[dict[str, Any]]:
    """Packet objects for passages of family representatives (copies are not packed)."""
    repo = Repository(Path(case_dir) / "case.db", case_id)
    try:
        cur = families.current_memberships(repo)
        if not cur:
            raise LaError("E_FAMILIES_REQUIRED", "Run `families` before preparing claims.",
                          "Przed przygotowaniem twierdzeń uruchom `families`.", EXIT_USAGE)
        reps = set(families.representatives({d: (m["family_id"], m["basis"]) for d, m in cur.items()}).values())
        original_of = {b["id"]: b.get("derived_from") or b["id"] for b, _ in repo.frozen_bodies("documents")}
        out = []
        for p, _ in repo.frozen_bodies("passages"):
            if original_of.get(p["document_id"]) not in reps or not p["text"].strip() or "needs_text" in p["quality_flags"]:
                continue
            out.append(packets.make_object("passage", p["id"], {
                "document_id": p["document_id"], "locator": p["locator"], "quality_flags": p["quality_flags"],
                "segments": segment(p["text"])}))
        return sorted(out, key=lambda o: o["id"])
    finally:
        repo.close()


def prepare_claims(case_dir: Path | str, **kw: Any) -> dict[str, Any]:
    profile = packets.load_profile(case_dir)
    return packets.prepare(case_dir, "claims", claim_objects(case_dir, profile["case_id"]), **kw)


def _enrich(task: str, payload: dict[str, Any], known: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    items = []
    for item in payload["items"]:
        if guards.status_violation(item):
            return payload, "E_STATUS_TOO_HIGH"
        flags = guards.check_claim(item, known["passages"].get(item["passage_id"]),
                                   known["passage_flags"].get(item["passage_id"], []))
        items.append({**item, "guard_flags": flags})
    return {"items": items}, None


def ingest_claims(case_dir: Path | str, packet: dict[str, Any], payload: Any) -> dict[str, Any]:
    if packet.get("task_type") != "claims":
        raise LaError("E_UNKNOWN_TASK", "This is not a claims packet.", "To nie jest pakiet twierdzeń.", EXIT_USAGE)
    r = proposals.ingest_proposal(case_dir, packet, payload, enrich=_enrich)
    if r["state"] == "pending":
        r["triage"] = [guards.triage_class(i["guard_flags"]) for i in r["payload"]["items"]]
    return r
