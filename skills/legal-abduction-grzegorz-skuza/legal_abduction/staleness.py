"""Dependency edges, vertical invalidation and "to be reassessed" state (LA-018, R16).

Approval writes provenance edges to the step, the reviewer and the proposal, but not the
data dependencies between records. `ensure_edges` materialises them as idempotent
`wasDerivedFrom` rows (X depends on Y) for provenance. `invalidate` walks the *current*
dependencies (`dependency_edges`) and appends `<record> wasInvalidatedBy step:<event>` edges:
nothing is updated or deleted, old records stay history. A record stays *stale*
("do ponownej oceny") until a reviewed `reassessment` value record clears the event, or — for
assessments — until a newer assessment supersedes it. Reports and the comparison must not
treat stale records as current basis.

Precise propagation (fact-change extension). An event has an *impact* on each record it reaches:

content   the record's content may change (re-extraction, displaced representative, a manually
          invalidated record, an assumption): everything derived from that content is reached
standing  the record's content is unchanged but its evidential standing is in question (a
          withdrawn/changed/reinstated fact, an observation whose claim was withdrawn)

Edges are typed by the record types they join:

derived    passage<-document, claim<-passage, observation<-claim, hypothesis<-assumption:
           carry content as content and standing as standing
judged     assessment<-observation/hypothesis/passage, test<-hypothesis: carry content only
           (a judgment about unchanged content stays valid when only standing moves)
reliance   hypothesis<-observation where the hypothesis's *current* cell is supports/conflicts:
           any impact on the observation becomes standing impact on the explanation; a neutral
           cell does not make the explanation rest on the fact
scope      observation set<-observation, hypothesis<-set: traversed only from a set root

So a withdrawn observation flags only the explanations that rely on it; its cells become void
(see facts.py), and neither unrelated hypotheses nor the rest of the matrix are flagged.
Each flagged record keeps its impact and the dependency path from the root.
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from . import facts, packets
from .profile import load_profile
from .repository import ReadRepository, Repository
from .runtime import EXIT_POLICY, EXIT_USAGE, LaError, sha256_hex, sha256_obj

DECISIONS = ("reaffirmed", "replaced")
IMPACTS = ("content", "standing")
NON_NEUTRAL = ("supports", "conflicts")
DERIVED = {("psg", "doc"), ("doc", "doc"), ("clm", "psg"), ("obs", "clm"), ("hyp", "asm")}
JUDGED = {("ass", "obs"), ("ass", "hyp"), ("ass", "psg"), ("tst", "hyp")}
SCOPE = {("set", "obs"), ("hyp", "set")}


def _err(code: str, en: str, pl: str, ids: dict[str, str] | None = None) -> LaError:
    return LaError(code, en, pl, EXIT_USAGE, ids)


def _assumption_owner(asm_id: str) -> str | None:
    base = asm_id.split(":", 1)[1]
    head, sep, tail = base.rpartition("-")
    return f"hyp:{head}" if sep and tail.isdigit() else None


def dependency_edges(rd: ReadRepository) -> list[tuple[str, str, str]]:
    """(dependent, 'wasDerivedFrom', dependency) for every data dependency between current records."""
    edges: set[tuple[str, str, str]] = set()

    def dep(a: str, b: str) -> None:
        edges.add((a, "wasDerivedFrom", b))
    for p in rd.frozen_rows("passages"):
        dep(p["id"], p["document_id"])
    for d in rd.frozen_rows("documents"):
        if d["kind"] == "derived":
            dep(d["id"], d["derived_from"])
    for c in rd.approved_rows("claims"):
        dep(c["id"], c["passage_id"])
    for o in rd.approved_rows("observations"):
        for c in o["claim_ids"]:
            dep(o["id"], c)
    for s in rd.approved_rows("observation_sets"):
        for o in s["observation_ids"]:
            dep(s["id"], o)
    hyps = {h["id"] for h in rd.approved_rows("hypotheses")}
    for h in rd.approved_rows("hypotheses"):
        dep(h["id"], h["scope_id"])
    for a in rd.approved_rows("assumptions"):
        owner = _assumption_owner(a["id"])
        if owner in hyps:
            dep(owner, a["id"])
    for a in rd.current_assessments():
        dep(a["id"], a["observation_id"])
        dep(a["id"], a["hypothesis_id"])
        for p in a["basis_passage_ids"]:
            dep(a["id"], p)
        if a["relation"] in NON_NEUTRAL and a["hypothesis_id"] in hyps:
            dep(a["hypothesis_id"], a["observation_id"])  # reliance: the explanation rests on this fact
    for t in rd.approved_rows("tests"):
        for o in t["outcomes"]:
            for h in o["impact"]:
                dep(t["id"], h)
    return sorted(edges)


def edge_kind(dependent: str, dependency: str) -> str:
    pair = (dependent.split(":", 1)[0], dependency.split(":", 1)[0])
    if pair == ("hyp", "obs"):
        return "reliance"
    if pair in DERIVED:
        return "derived"
    if pair in JUDGED:
        return "judged"
    if pair in SCOPE:
        return "scope"
    return "derived"  # unknown pairs keep the conservative pre-extension behaviour


def _carry(kind: str, impact: str, from_root_set: bool) -> str | None:
    """Impact that crosses an edge of `kind` given the dependency's impact (None: stops here)."""
    if kind == "derived":
        return impact
    if kind == "judged":
        return "content" if impact == "content" else None
    if kind == "reliance":
        return "standing"
    if kind == "scope":
        return "content" if from_root_set and impact == "content" else None
    return impact


def walk(rd: ReadRepository, roots: list[str], impact: str = "content",
         void: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """record id -> {"impact", "path"} for roots and everything their change reaches (current edges).

    Content outranks standing: a record reached both ways is content-impacted and keeps the path
    of the content route. Cycle-safe: a record is re-expanded only when its impact upgrades.
    """
    if impact not in IMPACTS:
        raise ValueError(impact)
    dependents: dict[str, list[str]] = {}
    for a, _, b in dependency_edges(rd):
        dependents.setdefault(b, []).append(a)
    rank = {"standing": 0, "content": 1}
    # records already out of the basis are neither flagged nor walked through; a dry run passes the
    # void set as it would be after the change
    void = _void_ids(rd) if void is None else void
    out: dict[str, dict[str, Any]] = {r: {"impact": impact, "path": [r]} for r in sorted(set(roots))}
    queue = deque(sorted(out))
    while queue:
        node = queue.popleft()
        cur = out[node]
        from_root_set = node.startswith("set:") and cur["path"] == [node]
        for dep in sorted(dependents.get(node, [])):
            if dep in void:
                continue
            kind = edge_kind(dep, node)
            nxt = _carry(kind, cur["impact"], from_root_set)
            if nxt is None:
                continue
            old = out.get(dep)
            if old is None or rank[nxt] > rank[old["impact"]]:
                out[dep] = {"impact": nxt, "path": [*cur["path"], dep], "via": kind}
                queue.append(dep)
    return dict(sorted(out.items()))


def downstream(rd: ReadRepository, roots: list[str], impact: str = "content") -> list[str]:
    """Roots plus everything their change reaches under the typed rules above."""
    return sorted(walk(rd, roots, impact))


def known_ids(rd: ReadRepository) -> set[str]:
    ids = {r["id"] for t in ("passages", "documents") for r in rd.frozen_rows(t)}
    for t in ("claims", "observations", "observation_sets", "hypotheses", "assumptions", "tests"):
        ids |= {r["id"] for r in rd.approved_rows(t)}
    return ids | {a["id"] for a in rd.current_assessments()}


def _latest_run(rd: ReadRepository) -> str:
    return rd.runs()[-1]["id"]


def ensure_edges(case_dir: Path | str) -> int:
    """Insert the missing dependency edges (append-only, idempotent); returns how many were new."""
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        rd = repo.reader()
        wanted = dependency_edges(rd)
        have = {(a, p, b) for a, p, b in rd.prov_edges("wasDerivedFrom")}
        missing = [e for e in wanted if e not in have]
        if not missing:
            return 0
        step = f"deps:{sha256_obj(missing)[:16]}"
        repo.add_step(step, _latest_run(rd), "dependency-edges", "software:la.py")
        repo.add_prov_edges(missing, step)
        return len(missing)
    finally:
        repo.close()


def invalidations(rd: ReadRepository) -> list[dict[str, Any]]:
    return [r for r in rd.frozen_rows("value_records") if r.get("kind") == "invalidation"]


def invalidate(case_dir: Path | str, roots: list[str], reason: str, *, flag_roots: bool, auto: bool = False,
               if_new: bool = False, impact: str = "content", cause: str | None = None) -> dict[str, Any]:
    """Flag what the change of `roots` reaches as to-be-reassessed. Never updates a protected row.

    `impact` is the kind of change at the roots (see module doc); `cause` links a fact_change record.
    Records that are void (withdrawn/changed facts and cells on withdrawn observations) are never flagged.
    """
    root = Path(case_dir)
    if not roots or not str(reason or "").strip():
        raise _err("E_INVALIDATION_INPUT", "At least one record id and a reason are required.",
                   "Wymagany jest co najmniej jeden identyfikator rekordu i uzasadnienie.")
    if impact not in IMPACTS:
        raise _err("E_INVALIDATION_INPUT", "impact must be content or standing.", "impact: content albo standing.")
    ensure_edges(root)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        rd = repo.reader()
        unknown = sorted(set(roots) - known_ids(rd))
        if unknown:
            raise _err("E_UNKNOWN_ID", "A root record is unknown.", "Rekord źródłowy jest nieznany.",
                       {"id": unknown[0]})
        roots = sorted(set(roots))
        prior = invalidations(rd)
        if if_new and any(p["roots"] == roots and p["reason"] == reason for p in prior):
            return {"ok": True, "event": None, "roots": roots, "flagged": [], "flagged_by_type": {},
                    "already_recorded": True}
        reached = walk(rd, roots, impact)
        void = _void_ids(rd)
        flagged = [i for i in reached if (flag_roots or i not in set(roots)) and i not in void]
        n = len(prior)
        event = sha256_obj([roots, reason, n])[:16]
        step = f"invalidate:{event}"
        repo.add_step(step, _latest_run(rd), "invalidate", "software:la.py")
        repo.add_prov_edges([(i, "wasInvalidatedBy", f"step:{step}") for i in flagged], step)
        details = {i: {"impact": reached[i]["impact"], "path": reached[i]["path"]} for i in flagged}
        repo.add_frozen_many("value_records", [{
            "id": f"inv:{event}", "kind": "invalidation", "roots": roots, "reason": reason, "flag_roots": flag_roots,
            "auto": auto, "impact": impact, "cause": cause, "flagged": flagged, "details": details,
            "downstream_total": len(reached)}], step)
        by_prefix: dict[str, int] = {}
        for i in flagged:
            by_prefix[i.split(":", 1)[0]] = by_prefix.get(i.split(":", 1)[0], 0) + 1
        return {"ok": True, "event": event, "roots": roots, "impact": impact, "flagged": flagged,
                "flagged_by_type": dict(sorted(by_prefix.items())), "downstream_total": len(reached)}
    finally:
        repo.close()


def _cleared_edges(rd: ReadRepository) -> set[str]:
    return {e for r in rd.frozen_rows("value_records") if r.get("kind") == "reassessment" for e in r["edge_ids"]}


def _void_ids(rd: ReadRepository) -> set[str]:
    """Withdrawn/changed facts and the cells on withdrawn/changed observations: out of the basis, not stale."""
    return facts.excluded_ids(rd) | {a["id"] for a in facts.void_assessments(rd)}


def stale_records(rd: ReadRepository) -> dict[str, list[str]]:
    """record id -> open invalidation edge ids ("do ponownej oceny"); void records are not stale."""
    cleared = _cleared_edges(rd)
    superseded = rd.superseded_ids("assessments")
    void = _void_ids(rd)
    out: dict[str, list[str]] = {}
    for subject, _, obj in rd.prov_edges("wasInvalidatedBy"):
        edge = f"{subject}|wasInvalidatedBy|{obj}"
        if edge in cleared or subject in superseded or subject in void:
            continue
        out.setdefault(subject, []).append(edge)
    return {k: sorted(v) for k, v in sorted(out.items())}


def marker_object(rd: ReadRepository, ids: list[str]) -> dict[str, Any] | None:
    """Packet object that changes the cache key whenever packet inputs are stale (None when none are)."""
    stale = stale_records(rd)
    hit = sorted(i for i in set(ids) if i in stale)
    if not hit:
        return None
    return packets.make_object("stale", "stale", {"ids": hit, "events": sorted(e for i in hit for e in stale[i])})


def assert_no_stale(case_dir: Path | str) -> None:
    root = Path(case_dir)
    profile = load_profile(root)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        stale = stale_records(rd)
    finally:
        rd.close()
    if stale:
        raise LaError("E_STALE_RECORDS", "Records are marked for reassessment; they cannot be the basis of a report.",
                      "Rekordy czekają na ponowną ocenę; nie mogą być podstawą raportu.", EXIT_POLICY,
                      {"count": str(len(stale)), "first": next(iter(stale))})


def reassess(case_dir: Path | str, file_path: Path | str) -> dict[str, Any]:
    """Reviewer decision file: each listed stale record is reaffirmed or replaced (individual class I)."""
    from .review import evidence_class_for
    root = Path(case_dir)
    raw = Path(file_path).read_bytes()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise _err("E_REASSESS_FILE", "The reassessment file is not valid JSON.",
                   "Plik ponownej oceny nie jest poprawnym JSON.") from e
    profile = load_profile(root)
    if isinstance(doc, dict) and isinstance(doc.get("reassessments"), list):  # template entries left null are skipped
        doc["reassessments"] = [r for r in doc["reassessments"] if not (isinstance(r, dict) and r.get("decision") is None)]
    if (not isinstance(doc, dict) or doc.get("case_id") != profile["case_id"]
            or not isinstance(doc.get("reassessments"), list) or not doc["reassessments"]):
        raise _err("E_REASSESS_FILE", "The reassessment file does not belong to this case or is empty.",
                   "Plik ponownej oceny nie należy do tej sprawy albo jest pusty.")
    reviewer = str(doc.get("reviewer") or "").strip()
    if not reviewer:
        raise _err("E_REASSESS_FILE", "The reassessment file must name the reviewer.",
                   "Plik ponownej oceny musi wskazywać recenzenta.")
    evidence = evidence_class_for(root, file_path)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        rd = repo.reader()
        stale = stale_records(rd)
        recs = []
        for r in doc["reassessments"]:
            rid = r.get("record_id") if isinstance(r, dict) else None
            if rid not in stale:
                raise _err("E_NOT_STALE", "The record is not waiting for reassessment.",
                           "Rekord nie oczekuje na ponowną ocenę.", {"id": str(rid)})
            if r.get("decision") not in DECISIONS or not str(r.get("reason") or "").strip():
                raise _err("E_REASSESS_DECISION", "A decision (reaffirmed|replaced) and a reason are required.",
                           "Wymagana jest decyzja (reaffirmed|replaced) i uzasadnienie.", {"id": rid})
            body = {"kind": "reassessment", "record_id": rid, "edge_ids": stale[rid], "decision": r["decision"],
                    "reason": str(r["reason"]).strip(), "reviewer": reviewer, "evidence_class": evidence,
                    "triage": "I", "mode": "individual"}
            recs.append({"id": "rea:" + sha256_obj(body)[:20], **body})
        step = f"reassess:{sha256_hex(raw)[:16]}"
        repo.add_step(step, _latest_run(rd), "reassess", "none")
        repo.add_frozen_many("value_records", recs, step)
    finally:
        repo.close()
    return {"ok": True, "cleared": len(recs), "evidence_class": evidence}
