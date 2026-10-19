"""Which earlier judgments need revisiting, and why (fact-change extension of R16).

`build` turns the open invalidation edges (staleness.stale_records) into a reviewer-facing list:
for each stale record its prior content (what was judged), the event(s) that flagged it with the
reason and — when the event came from `update withdraw|change|reinstate` — the fact change, the
impact (content/standing) and the dependency path from the changed fact. It also lists the *void*
cells (cells on withdrawn/changed observations, which stop counting and need no decision) and,
per scope, the comparison state and the replacement pairs still `not_assessed`.

`write_template` writes a reassessment skeleton for the human: decisions stay empty and are never
filled by the agent; `update reassess` imports only the entries the human decided.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import compare, facts, staleness
from .profile import load_profile
from .repository import ReadRepository
from .runtime import EXIT_USAGE, LaError, canonical_json, sha256_obj

HINTS = {  # what the reviewer decides, by record type and impact
    ("hyp", "standing"): "explanation_rests_on_changed_fact",
    ("hyp", "content"): "explanation_content_changed",
    ("obs", "standing"): "observation_basis_changed",
    ("obs", "content"): "observation_content_changed",
    ("ass", "content"): "cell_rejudge",
    ("tst", "content"): "test_rebuild",
    ("clm", "content"): "claim_recheck",
    ("set", "content"): "scope_recheck",
}


def _short(text: str, n: int = 160) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _index(rd: ReadRepository) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for t in ("claims", "observations", "observation_sets", "hypotheses", "assumptions", "tests"):
        for r in rd.approved_rows(t):
            idx[r["id"]] = r
    for a in rd.current_assessments():
        idx[a["id"]] = a
    for t in ("passages", "documents"):
        for r in rd.frozen_rows(t):
            idx[r["id"]] = r
    return idx


def prior(rid: str, idx: dict[str, dict[str, Any]], cells: list[dict[str, Any]], excluded: set[str]) -> dict[str, Any]:
    """What was judged before: the record's own content, in short form."""
    r = idx.get(rid)
    kind = rid.split(":", 1)[0]
    if r is None:
        return {}
    if kind == "ass":
        return {"observation_id": r["observation_id"], "hypothesis_id": r["hypothesis_id"], "relation": r["relation"],
                "reason": _short(r["reason"]),
                "observation": _short(idx.get(r["observation_id"], {}).get("description", "")),
                "hypothesis": _short(idx.get(r["hypothesis_id"], {}).get("mechanism", ""))}
    if kind == "hyp":
        rests = sorted(([c["observation_id"], c["relation"], c["observation_id"] in excluded] for c in cells
                        if c["hypothesis_id"] == rid and c["relation"] in staleness.NON_NEUTRAL))
        return {"mechanism": _short(r["mechanism"]), "kind": r["kind"], "scope_id": r["scope_id"],
                "rests_on": [{"observation_id": o, "relation": rel, "excluded": ex} for o, rel, ex in rests]}
    if kind == "obs":
        return {"description": _short(r["description"]), "claim_ids": r["claim_ids"],
                "withdrawn_claims": sorted(c for c in r["claim_ids"] if c in excluded),
                "remaining_claims": sorted(c for c in r["claim_ids"] if c not in excluded)}
    if kind == "clm":
        return {"proposition": _short(r["proposition"]), "quote": _short(r["quote"])}
    if kind == "tst":
        return {"question": _short(r["question"])}
    if kind == "set":
        return {"rationale": _short(r["rationale"]), "observations": len(r["observation_ids"])}
    if kind == "asm":
        return {"statement": _short(r["statement"]), "basis": _short(r.get("basis") or "")}
    return {"id": rid}


def build(rd: ReadRepository, scope_id: str | None = None) -> dict[str, Any]:
    stale = staleness.stale_records(rd)
    inv = {f"step:invalidate:{r['id'].split(':', 1)[1]}": r for r in staleness.invalidations(rd)}
    changes = {r["id"]: r for r in facts.fact_changes(rd)}
    state = facts.states(rd)
    excluded = set(state)
    idx = _index(rd)
    cells = rd.current_assessments()
    sets = {s["id"]: s for s in rd.approved_rows("observation_sets")}
    hyps = rd.approved_rows("hypotheses")
    scopes = [scope_id] if scope_id else sorted({h["scope_id"] for h in hyps} | set(sets))
    if scope_id and scope_id not in sets:
        raise LaError("E_SCOPE_UNKNOWN", "No approved ObservationSet with this id.",
                      "Brak zatwierdzonego ObservationSet o tym id.", EXIT_USAGE, {"scope_id": scope_id})
    in_scope: set[str] | None = None
    if scope_id:
        s = sets[scope_id]
        scope_hyps = {h["id"] for h in hyps if h["scope_id"] == scope_id}
        scope_obs = set(s["observation_ids"]) | set(facts.effective_observation_ids(rd, s, state))
        scope_claims = {c for o in scope_obs if o in idx for c in idx[o].get("claim_ids", [])}
        scope_cells = {c["id"] for c in cells if c["hypothesis_id"] in scope_hyps}
        scope_tests = {t["id"] for t in rd.approved_rows("tests")
                       if any(set(o["impact"]) & scope_hyps for o in t["outcomes"])}
        in_scope = scope_hyps | scope_obs | scope_claims | scope_cells | scope_tests | {scope_id}
    items = []
    for rid, edges in stale.items():
        if in_scope is not None and rid not in in_scope:
            continue
        triggers = []
        for e in edges:
            r = inv.get(e.split("|", 2)[2])
            if r is None:
                continue
            det = (r.get("details") or {}).get(rid, {})
            imp = det.get("impact", "content")  # pre-extension events carry no details: they were content walks
            t = {"event": r["id"], "reason": r["reason"], "roots": r["roots"], "auto": r["auto"], "impact": imp,
                 "path": det.get("path")}
            ch = changes.get(r.get("cause") or "")
            if ch:
                t["fact_change"] = {k: ch[k] for k in ("id", "fact_id", "change", "replacement_id", "reason",
                                                       "recorded_by", "evidence_class")}
            triggers.append(t)
        kind = rid.split(":", 1)[0]
        impact = "content" if not triggers or any(t["impact"] == "content" for t in triggers) else "standing"
        items.append({"id": rid, "type": kind, "impact": impact, "hint": HINTS.get((kind, impact), "reassess"),
                      "prior": prior(rid, idx, cells, excluded), "triggers": triggers, "edge_ids": edges})
    void = [a for a in facts.void_assessments(rd) if in_scope is None or a["hypothesis_id"] in in_scope]
    void_out = [{"id": a["id"], "observation_id": a["observation_id"], "hypothesis_id": a["hypothesis_id"],
                 "relation": a["relation"], "fact_change": state[a["observation_id"]]["id"]} for a in void]
    comparisons = []
    for s in scopes:
        if s not in sets:
            continue
        c = compare.compare_scope(rd, s)
        new_obs = sorted(set(c["observation_ids"]) - set(sets[s]["observation_ids"]))
        comparisons.append({"scope_id": s, "status": c["status"], "leader": c["leader"],
                            "provisional_leader": c["provisional_leader"],
                            "reasons": [r["code"] for r in c["underdetermined_reasons"]],
                            "fact_changes": c["fact_changes"], "replacement_observations": new_obs,
                            "replacement_pairs_not_assessed": [m for m in c["missing_assessments"]
                                                               if m["observation_id"] in new_obs]})
    facts_out = [{"fact_id": k, "change": v["change"], "replacement_id": facts.resolve(state, k), "reason": v["reason"],
                  "event": v["id"], "evidence_class": v["evidence_class"]} for k, v in state.items()
                 if in_scope is None or k in in_scope]
    by_type: dict[str, int] = {}
    for i in items:
        by_type[i["type"]] = by_type.get(i["type"], 0) + 1
    return {"ok": True, "scope_id": scope_id, "to_revisit": len(items), "to_revisit_by_type": dict(sorted(by_type.items())),
            "items": items, "void_assessments": void_out, "changed_facts": facts_out, "comparisons": comparisons}


def compact(result: dict[str, Any]) -> list[dict[str, Any]]:
    """One line per judgment for `update run`: id, type, hint and what triggered it."""
    out = []
    for i in result["items"]:
        out.append({"id": i["id"], "type": i["type"], "impact": i["impact"], "hint": i["hint"],
                    "because": [({"fact_id": t["fact_change"]["fact_id"], "change": t["fact_change"]["change"]}
                                 if "fact_change" in t else {"roots": t["roots"]}) | {"reason": t["reason"]}
                                for t in i["triggers"]]})
    return out


def run(case_dir: Path | str, scope_id: str | None = None, template: str | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        result = build(rd, scope_id)
    finally:
        rd.close()
    if template is not None:
        result["template"] = write_template(root, profile["case_id"], result, template or None)
    return result


def write_template(root: Path, case_id: str, result: dict[str, Any], out: str | None) -> str:
    """Reassessment skeleton: decisions empty for the human. Never overwrites an existing file."""
    doc = {"format": 1, "case_id": case_id, "reviewer": "",
           "note": "Fill decision (reaffirmed|replaced) and reason for the records you decide; leave the rest null. "
                   "Uzupełnij decision (reaffirmed|replaced) i reason dla rozstrzyganych rekordów; resztę zostaw jako null.",
           "reassessments": [{"record_id": i["id"], "decision": None, "reason": "", "hint": i["hint"], "prior": i["prior"],
                              "because": [t["reason"] for t in i["triggers"]]} for i in result["items"]]}
    data = canonical_json(doc) + b"\n"
    if out is None:
        target = root / "review" / f"reassess-{sha256_obj(doc)[:16]}.json"
    else:
        target = Path(out)  # like `review export --out`: as given (relative to the working directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target, "xb") as fh:
            fh.write(data)
    except FileExistsError as e:
        raise LaError("E_OUT_EXISTS", "The output file already exists; it is never overwritten.",
                      "Plik wyjściowy już istnieje; nigdy nie jest nadpisywany.", EXIT_USAGE) from e
    return str(target)

