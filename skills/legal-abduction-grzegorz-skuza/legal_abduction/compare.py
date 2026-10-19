"""Profile comparison of explanations and leave-one-family-out stability (LA-016, R14).

Reads only the approved set and frozen records through `ReadRepository` (the SQLite
authorizer denies `proposals`). There is no score and no probability: each hypothesis
gets a profile of integers and profiles are ordered lexicographically by
(fewer conflicting families, more supporting families, fewer unconfirmed assumptions).
A family counts at most once for support and once for conflict. Full equality of the
top profiles is `underdetermined`; the IDs never break a tie. The ranking concerns
explanations of events, never persons.

Interpretations (docs/decisions.md, LA-016): an assumption belongs to the hypothesis
whose id suffix it shares (`asm:<base>-<n>` for `hyp:<base>`, the ids `review` mints
on approval); "unconfirmed" means an empty `basis`. The "material coverage" threshold
is T-COVERAGE and stays undefined: it is only evaluated when the caller supplies an
explicit `coverage_threshold`. Report 8.1 dimensions (T-PROFILE) are not used.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import facts, families, staleness
from .profile import load_profile
from .repository import ReadRepository
from .runtime import EXIT_USAGE, LaError, atomic_write, canonical_json, sha256_obj

SCHEMA_VERSION = 1
_ASM = re.compile(r"^asm:(?P<base>.+)-\d+$")


def _err(code: str, en: str, pl: str, ids: dict[str, str] | None = None) -> LaError:
    return LaError(code, en, pl, EXIT_USAGE, ids)


def profile_key(p: dict[str, Any]) -> tuple[int, int, int]:
    """Lexicographic sort key: smaller is better."""
    return (p["conflicting_families"], -p["supporting_families"], p["unconfirmed_assumptions"])


def _assumptions_of(hypothesis_id: str, assumptions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = hypothesis_id.split(":", 1)[1]
    out = []
    for a in assumptions:
        m = _ASM.match(a["id"])
        if m and m.group("base") == base:
            out.append(a)
    return out


def _unconfirmed(a: dict[str, Any]) -> bool:
    return not str(a.get("basis") or "").strip()


def build_profiles(hypotheses: list[dict[str, Any]], assessments: list[dict[str, Any]],
                   assumptions: list[dict[str, Any]], passage_document: dict[str, str],
                   doc_family: dict[str, str], *, exclude_family: str | None = None) -> dict[str, dict[str, Any]]:
    """Per hypothesis profile; with `exclude_family` that family is removed from every count."""
    ids = {h["id"] for h in hypotheses}
    agg = families.aggregate_by_family([a for a in assessments if a["hypothesis_id"] in ids],
                                       passage_document, doc_family)
    out: dict[str, dict[str, Any]] = {}
    for h in sorted(hypotheses, key=lambda h: h["id"]):
        a = agg.get(h["id"], {"support_families": [], "conflict_families": [], "unattributed": 0})
        sup = [f for f in a["support_families"] if f != exclude_family]
        con = [f for f in a["conflict_families"] if f != exclude_family]
        own = _assumptions_of(h["id"], assumptions)
        out[h["id"]] = {
            "hypothesis_id": h["id"], "conflicting_families": len(con), "supporting_families": len(sup),
            "unconfirmed_assumptions": sum(_unconfirmed(x) for x in own),
            "conflict_family_ids": con, "support_family_ids": sup, "unattributed_assessments": a["unattributed"],
            "bridge_rules_without_basis": sorted(x["id"] for x in own if x["kind"] == "bridge_rule" and _unconfirmed(x)),
        }
    return out


def order(profiles: dict[str, dict[str, Any]]) -> list[list[str]]:
    """Tiers of hypotheses with equal profiles, best tier first; ids only sort within a tier."""
    tiers: dict[tuple[int, int, int], list[str]] = {}
    for hid, p in profiles.items():
        tiers.setdefault(profile_key(p), []).append(hid)
    return [sorted(tiers[k]) for k in sorted(tiers)]


def leader_of(profiles: dict[str, dict[str, Any]]) -> str | None:
    tiers = order(profiles)
    return tiers[0][0] if tiers and len(tiers[0]) == 1 else None


def _doc_family(rd: ReadRepository) -> dict[str, str]:
    return families.document_family_map_from_rows(rd.frozen_rows("family_memberships"), rd.frozen_rows("documents"))


def compare_scope(rd: ReadRepository, scope_id: str, *, coverage_threshold: float | None = None) -> dict[str, Any]:
    sets = {s["id"]: s for s in rd.approved_rows("observation_sets")}
    if scope_id not in sets:
        raise _err("E_SCOPE_UNKNOWN", "No approved ObservationSet with this id.",
                   "Brak zatwierdzonego ObservationSet o tym id.", {"scope_id": scope_id})
    if coverage_threshold is not None and not 0.0 <= coverage_threshold <= 1.0:
        raise _err("E_BAD_THRESHOLD", "coverage_threshold must be between 0 and 1.",
                   "coverage_threshold musi mieścić się w przedziale 0–1.")
    state = facts.states(rd)
    obs_ids = facts.effective_observation_ids(rd, sets[scope_id], state)  # withdrawn out, replacements in
    changes = facts.scope_changes(rd, sets[scope_id], state)
    hyps = [h for h in rd.approved_rows("hypotheses") if h["scope_id"] == scope_id]
    hyp_ids = sorted(h["id"] for h in hyps)
    current = {(a["observation_id"], a["hypothesis_id"]): a for a in rd.current_assessments()}
    in_scope = [a for (o, h), a in sorted(current.items()) if o in set(obs_ids) and h in set(hyp_ids)]
    missing = [{"observation_id": o, "hypothesis_id": h} for o in obs_ids for h in hyp_ids if (o, h) not in current]
    passage_document = {p["id"]: p["document_id"] for p in rd.frozen_rows("passages")}
    doc_family = _doc_family(rd)
    assumptions = rd.approved_rows("assumptions")
    profiles = build_profiles(hyps, in_scope, assumptions, passage_document, doc_family)
    tiers = order(profiles)
    top = tiers[0] if tiers else []
    reasons: list[dict[str, Any]] = []
    if not hyps:
        reasons.append({"code": "no_approved_hypotheses"})
    if len(top) > 1:
        reasons.append({"code": "tie", "hypothesis_ids": top})
    if missing:
        reasons.append({"code": "missing_assessments", "count": len(missing)})
    bridge = sorted({(h, b) for h in top for b in profiles[h]["bridge_rules_without_basis"]})
    if bridge:
        reasons.append({"code": "bridge_rule_without_basis", "assumption_ids": sorted({b for _, b in bridge}),
                        "hypothesis_ids": sorted({h for h, _ in bridge})})
    stale = staleness.stale_records(rd)
    basis_ids = (set(obs_ids) | set(hyp_ids) | {a["id"] for a in in_scope}
                 | {x["id"] for h in hyp_ids for x in _assumptions_of(h, assumptions)}
                 | {p for a in in_scope for p in a["basis_passage_ids"]} | {scope_id})
    stale_in_scope = sorted(i for i in basis_ids if i in stale)
    if stale_in_scope:
        reasons.append({"code": "stale_records", "ids": stale_in_scope})
    complete_obs = sum(1 for o in obs_ids if all((o, h) in current for h in hyp_ids)) if hyp_ids else 0
    coverage: dict[str, Any] = {"observations": len(obs_ids), "complete_observations": complete_obs,
                                "ratio": (complete_obs / len(obs_ids)) if obs_ids and hyp_ids else 0.0}
    if coverage_threshold is None:
        coverage["threshold"] = "undefined_T-COVERAGE"
    else:
        coverage["threshold"] = coverage_threshold
        if coverage["ratio"] < coverage_threshold:
            reasons.append({"code": "insufficient_coverage", "ratio": coverage["ratio"],
                            "threshold": coverage_threshold})
    base_leader = leader_of(profiles)
    families_all = sorted({f for p in profiles.values() for f in p["support_family_ids"] + p["conflict_family_ids"]})
    loo = []
    for fam in families_all:
        without = build_profiles(hyps, in_scope, assumptions, passage_document, doc_family, exclude_family=fam)
        lead = leader_of(without)
        loo.append({"family_id": fam, "leader": lead, "changes_leader": lead != base_leader,
                    "tied_top": order(without)[0] if lead is None and without else [],
                    "profiles": {h: {k: p[k] for k in ("conflicting_families", "supporting_families",
                                                      "unconfirmed_assumptions")} for h, p in without.items()}})
    unstable = [e["family_id"] for e in loo if e["changes_leader"]] if base_leader is not None else []
    if reasons:
        status = "underdetermined"
    elif unstable:
        status = "unstable"
    else:
        status = "determined"
    return {
        "schema_version": SCHEMA_VERSION, "scope_id": scope_id, "status": status,
        "leader": base_leader if not reasons else None,
        "provisional_leader": base_leader if reasons else None,
        "partial": bool(missing), "missing_assessments": missing, "underdetermined_reasons": reasons,
        "coverage": coverage, "order": [{"tier": i + 1, "hypothesis_ids": t, "tied": len(t) > 1}
                                         for i, t in enumerate(tiers)],
        "profiles": [profiles[h] for h in sorted(profiles)], "loo": loo, "unstable_families": unstable,
        "ranking_subject": "explanations_of_events",
        "fact_changes": changes, "observation_ids": obs_ids,
    }


def _file_name(scope_id: str) -> str:
    return f"comparison/comparison-{re.sub(r'[^A-Za-z0-9._-]', '_', scope_id.split(':', 1)[-1])}.json"


def compare(case_dir: Path | str, scope_id: str, *, coverage_threshold: float | None = None,
            write: bool = True) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        rd.assert_chain_ok()
        result = compare_scope(rd, scope_id, coverage_threshold=coverage_threshold)
        result["approved_set_hash"] = rd.approved_set_hash()
        result["chain_head"] = rd.chain_head()
    finally:
        rd.close()
    result["comparison_hash"] = sha256_obj(result)
    if write:
        atomic_write(root, _file_name(scope_id), canonical_json(result) + b"\n")
        result["path"] = _file_name(scope_id)
    return {"ok": True, **result}


def read_comparison(case_dir: Path | str, scope_id: str) -> dict[str, Any]:
    try:
        return json.loads((Path(case_dir) / _file_name(scope_id)).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise _err("E_NO_COMPARISON", "No comparison.json for this scope; run compare first.",
                   "Brak comparison.json dla tego zakresu; najpierw uruchom compare.") from e
