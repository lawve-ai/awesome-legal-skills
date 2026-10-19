"""Audit-only rejection snapshots. Never part of the approved evidential basis.

Only the review writer may read proposals. Reports use the chained snapshots in
value_records and the existing reviews, through the unchanged ReadRepository.
Legacy rejections acquire a snapshot on review export, without a new decision.
"""
from __future__ import annotations

from typing import Any

from .repository import ReadRepository, Repository
from .runtime import EXIT_INTEGRITY, LaError, sha256_obj

KIND = "rejection_snapshot"


def _error(review_id: str) -> LaError:
    return LaError("E_REVIEW_HISTORY_INTEGRITY", "Rejection history does not match its reviewed version.",
                   "Historia odrzucenia nie odpowiada ocenionej wersji.", EXIT_INTEGRITY,
                   {"review_id": review_id})


def capture(repo: Repository, step_id: str) -> int:
    """Append missing snapshots from stored versions; never import history from a user's file."""
    records = [b for b, _ in repo.frozen_bodies("value_records")]
    captured = {b["review_id"] for b in records if b.get("kind") == KIND}
    rejected = [r for r in repo.review_rows() if r["decision"] == "rejected" and r["id"] not in captured]
    if not rejected:
        return 0
    proposals = {pid: (task, payload) for pid, task, payload in repo.proposals_rows()}
    passages = {p["id"]: p for p, _ in repo.frozen_bodies("passages")}
    documents = {d["id"]: d for d, _ in repo.frozen_bodies("documents")}
    snapshots = []
    for r in rejected:
        pid, sep, index = r["item_id"].rpartition("#")
        if not sep or not index.isdigit() or pid not in proposals:
            continue  # legacy/incomplete: remain visibly missing, never invent content
        task, payload = proposals[pid]
        items = payload.get("items", [])
        if int(index) >= len(items) or not isinstance(items[int(index)], dict):
            continue
        item = items[int(index)]
        digest = sha256_obj({"task": task, "item": item})
        if r.get("item_hash") and r["item_hash"] != digest:
            raise _error(r["id"])
        source_ids = set(item.get("basis_passage_ids", []))
        if task == "claims":
            source_ids.add(item["passage_id"])
        if task == "tests":
            source_ids.update(item.get("document", {}).get("basis_passage_ids", []))
        sources = []
        for source_id in sorted(source_ids):
            p = passages.get(source_id)
            d = documents.get(p["document_id"]) if p else None
            if p is None or d is None:
                sources.append({"passage_id": source_id, "status": "source_missing"})
                continue
            original = documents.get(d.get("derived_from")) if d["kind"] == "derived" else d
            source = {"passage_id": source_id, "status": "available", "locator": p["locator"],
                      "document": d, "original_document": original,
                      "text": p["text"], "text_sha256": p["text_sha256"]}
            if task == "claims":
                if p["text"][item["start"]:item["end"]] != item["quote"]:
                    raise _error(r["id"])
                source.update({k: item[k] for k in ("quote", "start", "end")})
            sources.append(source)
        snapshots.append({"id": f"rej-snapshot:{r['id']}", "kind": KIND,
                          "review_id": r["id"], "item_id": r["item_id"], "task_type": task,
                          "item_hash": digest, "proposed": item, "sources": sources,
                          "binding": "review_item_hash" if r.get("item_hash") else "legacy_unbound",
                          "audit_only": True})
    repo.add_frozen_many("value_records", snapshots, step_id)
    return len(snapshots)


def read(rd: ReadRepository) -> dict[str, Any]:
    """Read chronological audit history without querying the proposals queue."""
    records = rd.frozen_rows("value_records")
    snapshots = {}
    for b in records:
        if b.get("kind") == KIND:
            if b["review_id"] in snapshots:
                raise _error(b["review_id"])
            snapshots[b["review_id"]] = b
    imports = {b["sha256"]: b for b in records if b.get("kind") == "review_file"}
    entries = []
    reviews = rd.review_rows()
    for r in reviews:
        if r["decision"] != "rejected":
            continue  # auto_technical is not a human rejection
        snapshot = snapshots.get(r["id"])
        if snapshot:
            digest = sha256_obj({"task": snapshot["task_type"], "item": snapshot["proposed"]})
            if (snapshot["item_id"] != r["item_id"] or snapshot["item_hash"] != digest
                    or (r.get("item_hash") and r["item_hash"] != digest)
                    or snapshot.get("audit_only") is not True):
                raise _error(r["id"])
        entry = {"review_id": r["id"], "item_id": r["item_id"], "decision": r["decision"],
                 "reason": r.get("reason"), "reason_status": "recorded" if r.get("reason") else "missing",
                 "reviewer": r["reviewer"], "evidence_class": r["evidence_class"],
                 "review_file_sha256": r["review_file_sha256"],
                 "imported_at": imports.get(r["review_file_sha256"], {}).get("imported_at"),
                 "decision_time": None, "snapshot_status": "available" if snapshot else "snapshot_missing",
                 "later_reviews": [{k: later.get(k) for k in ("id", "item_id", "item_hash", "decision", "reason",
                                     "reviewer", "evidence_class", "review_file_sha256", "reconsiders_review_id")}
                                   for later in reviews if later.get("reconsiders_review_id") == r["id"]],
                 "snapshot": snapshot, "audit_only": True}
        entries.append(entry)
    return {"format": 1, "scope": "case_wide", "audit_only": True,
            "decision_time_note": "not recorded; imported_at is software import time, not decision time",
            "rejections": entries,
            "complete": all(e["snapshot_status"] == "available" and e["reason_status"] == "recorded"
                            and e["snapshot"]["binding"] == "review_item_hash"
                            and all(s["status"] == "available" for s in e["snapshot"]["sources"])
                            for e in entries)}
