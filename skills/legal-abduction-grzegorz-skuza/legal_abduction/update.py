"""Incremental update after new material (LA-018, R16, pipeline step 16).

`update` re-does only what the change touches and never rewrites history:

horizontal rules  new documents -> families relative to the existing ones (a displaced family
                  representative is a vertical root), claim packets only for new Passages of
                  representatives (instrumented), new observations/hypotheses -> new
                  `not_assessed` pairs (counted), every empty SearchRecord re-run against the
                  new corpus (a hit ends `not_found`), R11 re-check, comparison and LOO;
vertical rules    superseded extraction, a displaced representative or an explicitly named record
                  -> recursive CTE over `prov_edges`, everything downstream gets
                  `wasInvalidatedBy` and stays "to be reassessed" (see staleness.py).

The reference point is the latest `analysis_baseline` value record (documents already handled).
Without one, documents that already have approved claims count as handled, everything else is
new. A baseline is written only after all stages finished, so an interrupted update recomputes
the same delta; every counter is derived from stored state, never from "what this call did", so
a resumed run returns the same result as an uninterrupted one.

`semantic_view` canonicalises the current approved set of one scope into content keys (ids,
Runs and chain heads excluded) so a delta analysis can be compared with a from-scratch one.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from . import claims, compare, extract, facts, families, hypotheses, ingest, matrix, packets, revisit, search, staleness
from .profile import analysis_hash, load_profile
from .repository import ReadRepository, Repository
from .runtime import canonical_json, sha256_obj

BASELINE = "analysis_baseline"
_after_stage: Callable[[str], None] | None = None  # test seam: raise here to simulate an interruption


def _stage(name: str) -> None:
    if _after_stage is not None:
        _after_stage(name)


def _original_of(docs: dict[str, dict[str, Any]], doc_id: str) -> str:
    return docs[doc_id].get("derived_from") or doc_id


def _baselines(rd: ReadRepository) -> list[dict[str, Any]]:
    return sorted((r for r in rd.frozen_rows("value_records") if r.get("kind") == BASELINE), key=lambda r: r["seq"])


def _fallback_documents(rd: ReadRepository) -> set[str]:
    """Without a baseline: originals that already have approved claims count as handled."""
    docs = {d["id"]: d for d in rd.frozen_rows("documents")}
    passage_doc = {p["id"]: p["document_id"] for p in rd.frozen_rows("passages")}
    return {_original_of(docs, passage_doc[c["passage_id"]]) for c in rd.approved_rows("claims")
            if c["passage_id"] in passage_doc}


def _representative_docs(rd: ReadRepository) -> list[str]:
    rows = rd.frozen_rows("family_memberships")
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    current = {r["document_id"]: (r["family_id"], r["basis"]) for r in rows if families._mid(r) not in superseded}
    return sorted(set(families.representatives(current).values()))


def corpus_hash(rd: ReadRepository) -> str:
    return sha256_obj(sorted(rd.frozen_rows("documents"), key=lambda d: d["id"]))


def _scopes(rd: ReadRepository) -> list[str]:
    return sorted({h["scope_id"] for h in rd.approved_rows("hypotheses")})


def _search_summary(rd: ReadRepository, now: str) -> dict[str, Any]:
    """Declarative: per search key, older empty records re-run on the current corpus."""
    by_key: dict[str, list[dict[str, Any]]] = {}
    for r in rd.frozen_rows("search_records"):
        by_key.setdefault(sha256_obj([r["query"], r["variants"], r["filters"]]), []).append(r)
    rerun, invalidated, still = 0, 0, 0
    for recs in by_key.values():
        old_empty = [r for r in recs if not r["hits"] and r["corpus_hash"] != now]
        cur = [r for r in recs if r["corpus_hash"] == now]
        if old_empty and cur:
            rerun += 1
            invalidated += any(r["hits"] for r in cur)
        elif old_empty:
            still += 1
    return {"rerun": rerun, "not_found_invalidated": invalidated, "stale_without_rerun": still}


def run(case_dir: Path | str, files: list[str] | None = None, *, batch_size: int = 10, resume: bool = False,
        max_files: int | None = None, max_file_bytes: int | None = None,
        coverage_threshold: float | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    cid = profile["case_id"]
    rd0 = ReadRepository(root / "case.db", cid)
    try:
        baselines = _baselines(rd0)
        base = baselines[-1] if baselines else None
        base_docs = set(base["document_ids"]) if base else _fallback_documents(rd0)
        base_reps = set(base["representative_docs"]) if base else set()
        base_passages = set(base["passage_ids"]) if base else None
    finally:
        rd0.close()
    if files:
        ingest.freeze(root, cid, files, batch_size=batch_size, resume=resume, max_files=max_files,
                      max_file_bytes=max_file_bytes)
    _stage("ingest")
    extract.extract_all(root, cid, batch_size=batch_size, resume=resume)
    _stage("extract")
    families.compute_families(root, cid)
    _stage("families")

    rd = ReadRepository(root / "case.db", cid)
    try:
        docs = {d["id"]: d for d in rd.frozen_rows("documents")}
        originals = sorted(i for i, d in docs.items() if d["kind"] == "original")
        new_originals = [i for i in originals if i not in base_docs]
        new_doc_ids = {i for i in docs if _original_of(docs, i) in set(new_originals)}
        passages = rd.frozen_rows("passages")
        versions = _current_versions(root)
        handled = base_passages if base_passages is not None else {
            p["id"] for p in passages if _original_of(docs, p["document_id"]) in base_docs}
        new_passages = sorted(p["id"] for p in passages if p["id"] not in handled
                              and (not versions or p["extraction_version"] in versions))
        reps_now = set(_representative_docs(rd))
        displaced = sorted(base_reps - reps_now)
        fam_of = families.document_family_map_from_rows(rd.frozen_rows("family_memberships"), list(docs.values()))
        new_fams = sorted({fam_of[i] for i in new_originals if i in fam_of})
        old_fams = {fam_of[i] for i in base_docs if i in fam_of}
        displaced_passages = sorted(p["id"] for p in passages if _original_of(docs, p["document_id"]) in set(displaced))
        stale_extraction = sorted(p["id"] for p in passages if versions and p["extraction_version"] not in versions)
    finally:
        rd.close()

    # vertical rules (roots are history; everything downstream becomes "to be reassessed")
    staleness.ensure_edges(root)
    if stale_extraction:
        staleness.invalidate(root, stale_extraction, "extraction_changed", flag_roots=False, auto=True, if_new=True)
    if displaced_passages:
        staleness.invalidate(root, displaced_passages, "family_representative_changed", flag_roots=False,
                             auto=True, if_new=True)
    _stage("vertical")

    # horizontal: claim packet only for new Passages of representatives
    objects = [o for o in claims.claim_objects(root, cid) if o["id"] in set(new_passages)]
    packed = sorted(o["id"] for o in objects)
    claims_packet: dict[str, Any] = {"needed": bool(objects), "passage_ids": packed,
                                     "new_passages": len(new_passages),
                                     "skipped_not_representative": len(new_passages) - len(packed)}
    outstanding = False
    if objects:
        out = packets.prepare(root, "claims", objects)
        claims_packet.update({k: out[k] for k in ("packet_id", "cache_key", "cache_hit") if k in out})
        outstanding = not out.get("cache_hit")  # a queued, non-rejected proposal for this exact packet counts as handled
    _stage("claims")

    rd = ReadRepository(root / "case.db", cid)
    try:
        scopes = _scopes(rd)
        stale = staleness.stale_records(rd)
        now = corpus_hash(rd)
    finally:
        rd.close()
    matrix_summary = {s: {k: v for k, v in matrix.check(root, s).items()
                          if k in ("expected_pairs", "assessed_pairs", "complete")} for s in scopes}
    for s in scopes:
        matrix_summary[s]["missing_pairs"] = matrix_summary[s]["expected_pairs"] - matrix_summary[s]["assessed_pairs"]
    _stage("matrix")
    search.rerun_stale(root)
    _stage("search")
    r11 = hypotheses.check_set(root)
    _stage("r11")
    comparisons = {}
    for s in scopes:
        c = compare.compare(root, s, coverage_threshold=coverage_threshold)
        comparisons[s] = {"status": c["status"], "leader": c["leader"], "unstable_families": c["unstable_families"],
                          "comparison_hash": c["comparison_hash"]}
    _stage("compare")

    rd = ReadRepository(root / "case.db", cid)
    try:
        runs = rd.runs()
        latest = runs[-1]
        search_summary = _search_summary(rd, now)
        events = [{"event": r["id"], "reason": r["reason"], "roots": len(r["roots"]), "flagged": len(r["flagged"]),
                   "auto": r["auto"]} for r in staleness.invalidations(rd)]
        stale_now = staleness.stale_records(rd)
        to_revisit = revisit.build(rd)
        base_analysis = base.get("analysis_hash") if base else None
    finally:
        rd.close()
    analysis_changed = base_analysis is not None and base_analysis != analysis_hash(profile)
    missing_total = sum(m["missing_pairs"] for m in matrix_summary.values())
    summary = {
        "ok": True, "run_id": latest["id"], "parent_run_id": latest["parent_run_id"], "corpus_hash": now,
        "baseline_seq": base["seq"] if base else 0,
        "new_documents": new_originals, "new_passages": len(new_passages),
        "families": {"new": new_fams, "extended": sorted(f for f in {fam_of[i] for i in new_originals if i in fam_of}
                                                        if f in old_fams),
                     "displaced_representatives": displaced},
        "claims_packet": claims_packet, "matrix": matrix_summary, "search": search_summary,
        "r11": {"complete": r11["complete"], "problems": len(r11["problems"]),
                "unconfirmed_assumptions": len(r11["unconfirmed_assumptions"])},
        "comparison": comparisons,
        "vertical": {"events": events, "stale_records": len(stale_now), "stale_before_update": len(stale)},
        "changed_facts": to_revisit["changed_facts"],
        "revisit": revisit.compact(to_revisit), "void_assessments": len(to_revisit["void_assessments"]),
        "analysis_changed": analysis_changed,
        "touched": {"new_documents": len(new_originals), "new_passages": len(new_passages),
                    "claims_objects": len(packed), "missing_pairs": missing_total,
                    "searches_rerun": search_summary["rerun"], "stale_records": len(stale_now),
                    "comparisons": len(comparisons)},
        "model_work": {"required": outstanding or missing_total > 0 or analysis_changed or bool(stale_now),
                       "claims_objects": len(packed), "missing_pairs": missing_total,
                       "stale_records": len(stale_now), "analysis_changed": analysis_changed},
    }
    summary["baseline_advanced"] = False
    if not (outstanding or missing_total or stale_now):  # advance only when no model/review work is outstanding
        summary["baseline_advanced"] = _write_baseline(root, cid, base, now, profile, summary)
    return summary


def _current_versions(root: Path) -> set[str]:
    try:
        return set(json.loads((root / "extraction.json").read_text(encoding="utf-8"))["extraction_versions"])
    except (OSError, ValueError, KeyError):
        return set()


def _write_baseline(root: Path, cid: str, base: dict[str, Any] | None, now: str, profile: dict[str, Any],
                    summary: dict[str, Any]) -> bool:
    rd = ReadRepository(root / "case.db", cid)
    try:
        ids = sorted(d["id"] for d in rd.frozen_rows("documents") if d["kind"] == "original")
        reps = _representative_docs(rd)
        versions = _current_versions(root)
        psg_ids = sorted(p["id"] for p in rd.frozen_rows("passages") if not versions or p["extraction_version"] in versions)
    finally:
        rd.close()
    ah = analysis_hash(profile)
    if base and base["document_ids"] == ids and base.get("analysis_hash") == ah and base.get("passage_ids") == psg_ids:
        return False
    seq = (base["seq"] if base else 0) + 1
    repo = Repository(root / "case.db", cid)
    try:
        run_id = repo.reader().runs()[-1]["id"]
        step = f"update:{sha256_obj([seq, now, ah])[:16]}"
        repo.add_step(step, run_id, "update", "software:la.py")
        repo.add_frozen_many("value_records", [
            {"id": f"baseline:{seq:04d}", "kind": BASELINE, "seq": seq, "document_ids": ids, "representative_docs": reps,
             "passage_ids": psg_ids, "corpus_hash": now, "analysis_hash": ah, "run_id": run_id},
            {"id": f"updsum:{seq:04d}", "kind": "update_summary", "seq": seq,
             "summary_hash": sha256_obj({k: v for k, v in summary.items() if k != "run_id"})}], step)
    finally:
        repo.close()
    return True


# --- semantic comparison with a from-scratch analysis -----------------------------------------

def _h(*parts: Any) -> str:
    return sha256_obj(parts)


def semantic_view(case_dir: Path | str, scope_id: str) -> dict[str, Any]:
    """Canonical content-key view of the current approved set that supports one scope."""
    root = Path(case_dir)
    profile = load_profile(root)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        docs = {d["id"]: d for d in rd.frozen_rows("documents")}
        psg = {p["id"]: p for p in rd.frozen_rows("passages")}
        clm = {c["id"]: c for c in rd.approved_rows("claims")}
        obs = {o["id"]: o for o in rd.approved_rows("observations")}
        sets = {s["id"]: s for s in rd.approved_rows("observation_sets")}
        hyps = {h["id"]: h for h in rd.approved_rows("hypotheses")}
        asm = rd.approved_rows("assumptions")
        ass = rd.current_assessments()
        tests = rd.approved_rows("tests")
        members = families.document_family_map_from_rows(rd.frozen_rows("family_memberships"), list(docs.values()))
        scope = sets[scope_id]
        effective = facts.effective_observation_ids(rd, scope)
        cmp_ = compare.compare_scope(rd, scope_id)
    finally:
        rd.close()
    kd = {i: _h("doc", d["sha256"], d["kind"]) for i, d in docs.items()}
    kp = {i: _h("psg", kd[p["document_id"]], p["locator"], p["text_sha256"], p["extraction_version"]) for i, p in psg.items()}
    kc = {i: _h("clm", kp[c["passage_id"]], *(c[k] for k in ("start", "end", "speaker", "speaker_role", "proposition",
                                                              "polarity", "modality", "epistemic_status", "source_lang")),
                sorted(c["guard_flags"])) for i, c in clm.items()}
    ko = {i: _h("obs", o["description"], sorted(kc[c] for c in o["claim_ids"]), o["in_scope"],
                o.get("relevance_note"), o.get("exclusion_reason")) for i, o in obs.items()}
    ks = {i: _h("set", sorted(ko[o] for o in s["observation_ids"]), s["rationale"]) for i, s in sets.items()}
    kh = {i: _h("hyp", h["mechanism"], ks[h["scope_id"]], h["kind"], sorted(h["burdens"]), h["attributes_intent"],
                h["concerns_natural_person"]) for i, h in hyps.items()}
    scope_hyps = sorted(i for i, h in hyps.items() if h["scope_id"] == scope_id)
    scope_obs = effective
    scope_claims = sorted({c for o in scope_obs for c in obs[o]["claim_ids"]})
    scope_psg = sorted({clm[c]["passage_id"] for c in scope_claims})
    scope_docs = sorted({_original_of(docs, psg[p]["document_id"]) for p in scope_psg} | {psg[p]["document_id"] for p in scope_psg})
    k_asm = sorted(_h("asm", kh[staleness._assumption_owner(a["id"])], a["statement"], a["kind"], a.get("basis"))
                   for a in asm if staleness._assumption_owner(a["id"]) in scope_hyps)
    k_ass = sorted(_h("ass", ko[a["observation_id"]], kh[a["hypothesis_id"]], a["relation"], a["reason"],
                      sorted(kp[p] for p in a["basis_passage_ids"]))
                   for a in ass if a["observation_id"] in set(scope_obs) and a["hypothesis_id"] in set(scope_hyps))
    k_tst = sorted(_h("tst", t["question"], sorted([o["label"], sorted((kh[h], v) for h, v in o["impact"].items())]
                                                    for o in t["outcomes"]), t["uninformative_outcome"], t["access_basis"])
                   for t in tests if all(set(o["impact"]) <= set(scope_hyps) for o in t["outcomes"]))
    fam_groups: dict[str, list[str]] = {}
    for d in scope_docs:
        if docs[d]["kind"] == "original" and d in members:
            fam_groups.setdefault(members[d], []).append(docs[d]["sha256"])
    fam_key = {f: _h("fam", sorted(v)) for f, v in fam_groups.items()}
    view = {
        "documents": sorted(kd[d] for d in scope_docs), "passages": sorted(kp[p] for p in scope_psg),
        "claims": sorted(kc[c] for c in scope_claims), "observations": sorted(ko[o] for o in scope_obs),
        "observation_set": ks[scope_id], "hypotheses": sorted(kh[h] for h in scope_hyps), "assumptions": k_asm,
        "assessments": k_ass, "tests": k_tst, "families": sorted(fam_key.values()),
        "comparison": {"status": cmp_["status"], "leader": kh.get(cmp_["leader"]) if cmp_["leader"] else None,
                       "unstable_families": sorted(fam_key.get(f, f) for f in cmp_["unstable_families"]),
                       "profiles": sorted([kh[p["hypothesis_id"]], p["conflicting_families"], p["supporting_families"],
                                           p["unconfirmed_assumptions"]] for p in cmp_["profiles"])},
    }
    return {"view": view, "semantic_hash": sha256_obj(view), "counts": {k: (len(v) if isinstance(v, list) else 1)
                                                                         for k, v in view.items() if k != "comparison"}}


def semantic_equal(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    diff = sorted(k for k in a["view"] if a["view"][k] != b["view"][k])
    return {"equal": not diff, "differing_sections": diff, "a": a["semantic_hash"], "b": b["semantic_hash"]}


def canonical_bytes(result: dict[str, Any]) -> bytes:
    return canonical_json(result)
