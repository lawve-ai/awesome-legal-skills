"""Deterministic source families (R5): identical bytes and EML threads.

Documents are grouped with a union-find over (a) the SHA-256 of the original and
(b) the message ids named in each EML (`Message-ID`, `In-Reply-To`, `References`).
Two replies to the same absent parent share a family; a duplicated Message-ID on
different bytes also joins them and is reported as a warning. Cycles cannot loop
(union-find). The family id is `fam:` + the smallest member document id suffix, so
adding a copy keeps it stable. Memberships are separate immutable rows; a change
adds a new row that `supersedes` the previous one, and nothing is updated in place.
Near-duplicates and model-based common-origin detection are out of scope (P1).
"""
from __future__ import annotations

import email
import email.policy
import re
from pathlib import Path
from typing import Any

from .extract import _sha256_file
from .ingest import _doc_filename
from .repository import Repository
from .runtime import EXIT_INTEGRITY, EXIT_USAGE, LaError, sha256_obj

MAX_REFS = 1000
_MSGID = re.compile(r"<[^<>\s]{1,998}>")
# Relation words of pipeline step 10 (PRD); the closed enum itself stays open (T-ENUM).
SUPPORTS, CONFLICTS = "supports", "conflicts"


class _UF:
    def __init__(self) -> None:
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)  # deterministic root


def _ids(value: Any) -> list[str]:
    return _MSGID.findall(str(value)) if value is not None else []


def eml_ids(data: bytes) -> tuple[str | None, list[str], bool]:
    """(own Message-ID, referenced ids, truncated)."""
    msg = email.message_from_bytes(data, policy=email.policy.default)
    own = _ids(msg["Message-ID"])
    refs = _ids(msg["In-Reply-To"]) + _ids(msg["References"])
    truncated = len(refs) > MAX_REFS
    return (own[0] if own else None), sorted(set(refs[:MAX_REFS])), truncated


def compute_assignment(docs: list[dict[str, Any]], eml: dict[str, tuple[str | None, list[str], bool]]
                       ) -> tuple[dict[str, tuple[str, str]], list[dict[str, str]]]:
    """Pure grouping. Returns ({doc_id: (family_id, basis)}, warnings)."""
    uf = _UF()
    warnings: list[dict[str, str]] = []
    by_sha: dict[str, str] = {}
    for d in sorted(docs, key=lambda d: d["id"]):
        uf.find(d["id"])
        first = by_sha.setdefault(d["sha256"], d["id"])
        if first != d["id"]:
            uf.union(first, d["id"])
    owners: dict[str, list[str]] = {}
    for d in sorted(docs, key=lambda d: d["id"]):
        if d["id"] not in eml:
            continue
        own, refs, truncated = eml[d["id"]]
        if truncated:
            warnings.append({"code": "header_truncated", "document_id": d["id"]})
        nodes = ([own] if own else []) + refs
        for n in nodes:
            uf.union(d["id"], "msg:" + n)
        if own:
            owners.setdefault(own, []).append(d["id"])
    sha_of0 = {d["id"]: d["sha256"] for d in docs}
    for mid, ids in sorted(owners.items()):
        if len({sha_of0[i] for i in ids}) > 1:
            warnings.append({"code": "duplicate_message_id", "message_id": mid})
    members: dict[str, list[str]] = {}
    for d in docs:
        members.setdefault(uf.find(d["id"]), []).append(d["id"])
    sha_of = {d["id"]: d["sha256"] for d in docs}
    out: dict[str, tuple[str, str]] = {}
    for ids in members.values():
        fam = "fam:" + min(ids).split(":", 1)[1]
        mixed = len({sha_of[i] for i in ids}) > 1  # members with different bytes can only be joined by headers
        for i in ids:
            out[i] = (fam, "email_headers" if mixed and i in eml else "bytes")
    return out, warnings


def representatives(assignment: dict[str, tuple[str, str]]) -> dict[str, str]:
    """Deterministic packing representative: smallest document id of each family."""
    reps: dict[str, str] = {}
    for doc_id, (fam, _) in sorted(assignment.items()):
        reps.setdefault(fam, doc_id)
    return reps


def _mid(body: dict[str, Any]) -> str:
    return sha256_obj(body)[:32]


def current_memberships(repo: Repository) -> dict[str, dict[str, Any]]:
    rows = [b for b, _ in repo.frozen_bodies("family_memberships")]
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    return {r["document_id"]: r for r in rows if _mid(r) not in superseded}


def compute_families(case_dir: Path | str, case_id: str) -> dict[str, Any]:
    root = Path(case_dir)
    repo = Repository(root / "case.db", case_id)
    try:
        docs = [b for b, _ in repo.frozen_bodies("documents") if b["kind"] == "original"]
        if not docs:
            raise LaError("E_NO_CORPUS", "No frozen documents; run ingest first.",
                          "Brak zamrożonych dokumentów; najpierw uruchom ingest.", EXIT_USAGE)
        eml: dict[str, tuple[str | None, list[str], bool]] = {}
        for d in docs:
            if d["mime"] != "message/rfc822":
                continue
            f = root / "corpus" / _doc_filename(d["id"])
            if _sha256_file(f) != d["sha256"]:
                raise LaError("E_CORPUS_TAMPERED", "A frozen copy no longer matches its SHA-256.",
                              "Zamrożona kopia nie zgadza się już z SHA-256.", EXIT_INTEGRITY, {"document_id": d["id"]})
            eml[d["id"]] = eml_ids(f.read_bytes())
        assignment, warnings = compute_assignment(docs, eml)
        current = current_memberships(repo)
        run = repo.reader().runs()[-1]
        step_id = f"families:{run['id']}:{sha256_obj(sorted(assignment.items()))[:12]}"
        repo.add_step(step_id, run["id"], "families", "software:la.py")
        new_rows = []
        for doc_id, (fam, basis) in sorted(assignment.items()):
            cur = current.get(doc_id)
            if cur is not None and (cur["family_id"], cur["basis"]) == (fam, basis):
                continue
            row = {"case_id": case_id, "document_id": doc_id, "family_id": fam, "basis": basis}
            if cur is not None:
                row["supersedes"] = _mid(cur)
            new_rows.append(row)
        repo.add_frozen_many("family_memberships", new_rows, step_id)
        repo.add_prov_edges([e for r in new_rows for e in (
            (f"mem:{_mid(r)}", "wasGeneratedBy", f"step:{step_id}"),
            (f"mem:{_mid(r)}", "wasDerivedFrom", r["document_id"]))], step_id)
        families = {fam for fam, _ in assignment.values()}
        return {"ok": True, "documents": len(docs), "families": len(families), "new_memberships": len(new_rows),
                "warnings": warnings, "representatives": representatives(assignment)}
    finally:
        repo.close()


# --- aggregation shared with comparison (LA-016) -------------------------------------

def document_family_map(repo: Repository) -> dict[str, str]:
    """Current family of every document; derived documents inherit from their original."""
    fam = {d: m["family_id"] for d, m in current_memberships(repo).items()}
    for b, _ in repo.frozen_bodies("documents"):
        if b["kind"] == "derived" and b["derived_from"] in fam:
            fam[b["id"]] = fam[b["derived_from"]]
    return fam


def document_family_map_from_rows(membership_rows: list[dict[str, Any]], document_rows: list[dict[str, Any]]) -> dict[str, str]:
    """Same as `document_family_map` for callers holding plain rows (read-only repository)."""
    superseded = {r["supersedes"] for r in membership_rows if r.get("supersedes")}
    fam = {r["document_id"]: r["family_id"] for r in membership_rows if _mid(r) not in superseded}
    for d in document_rows:
        if d["kind"] == "derived" and d["derived_from"] in fam:
            fam[d["id"]] = fam[d["derived_from"]]
    return fam


def aggregate_by_family(assessments: list[dict[str, Any]], passage_document: dict[str, str],
                        doc_family: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Per hypothesis: each family counts at most once for support and once for conflict.

    Support and conflict are independent, so one family may appear in both. `neutral`
    and unknown relations contribute nothing; assessments whose basis passages resolve
    to no family are counted as `unattributed`, never silently dropped.
    """
    out: dict[str, dict[str, Any]] = {}
    for a in sorted(assessments, key=lambda a: a["id"]):
        h = out.setdefault(a["hypothesis_id"], {"support": set(), "conflict": set(), "unattributed": 0})
        if a["relation"] not in (SUPPORTS, CONFLICTS):
            continue
        fams = {doc_family[passage_document[p]] for p in a.get("basis_passage_ids", [])
                if p in passage_document and passage_document[p] in doc_family}
        if not fams:
            h["unattributed"] += 1
            continue
        h["support" if a["relation"] == SUPPORTS else "conflict"].update(fams)
    return {hid: {"supports": len(v["support"]), "conflicts": len(v["conflict"]),
                  "support_families": sorted(v["support"]), "conflict_families": sorted(v["conflict"]),
                  "unattributed": v["unattributed"]} for hid, v in sorted(out.items())}
