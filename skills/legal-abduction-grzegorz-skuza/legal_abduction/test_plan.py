"""Discriminating-test plan (LA-017, R15).

Turns a tie or an unstable leader (LA-016) into a plan of lawful, accessible actions that
would separate the competing explanations. The plan never performs an action, never
fetches data and never grants access: `access_basis` is the proposer's statement, not a
legal assessment, and cost/availability remain a proposal for the reviewer.

Contracts enforced at ingest (codes are stable; a failure stores the proposal and an
`auto_rejected` review, never an approved record):
- `E_TEST_OUTCOMES_TOO_FEW` / `E_TEST_IDENTICAL_IMPACT`: at least two outcomes with
  *different* impact vectors (labels cannot fake a difference);
- `E_TEST_IMPACT_INCOMPLETE` / `E_TEST_IMPACT_SCOPE`: each vector covers every hypothesis
  of the scope and nothing else (unknown ids are `E_UNKNOWN_ID`);
- `E_TEST_NOT_DISCRIMINATING`: some outcome must treat two hypotheses differently;
- `E_TEST_UNINFORMATIVE_MISSING` / `E_TEST_UNINFORMATIVE_IMPACT`: an explicit uninformative
  outcome, and if it names an outcome label that outcome must impact nothing;
- `E_TEST_ACCESS_BASIS_MISSING`, `E_TEST_DUPLICATE_LABEL`.
Predictions are not linked: T-PREDICTION is undefined, so the plan reports
`predictions: blocked_T-PREDICTION`.
"""
from __future__ import annotations

import itertools
import json
import re
from pathlib import Path
from typing import Any

from . import compare as cmp
from . import packets, proposals
from .profile import load_profile
from .repository import ReadRepository, Repository
from .runtime import EXIT_USAGE, LaError, atomic_write, canonical_json, sha256_hex, sha256_obj

PAIR_PURPOSES = ("tie", "unstable")
ACTION_FIELDS = ("scope_id", "uncertainty", "document", "next_step")


def _err(code: str, en: str, pl: str, ids: dict[str, str] | None = None) -> LaError:
    return LaError(code, en, pl, EXIT_USAGE, ids)


def _vector(outcome: dict[str, Any], hyps: list[str]) -> tuple[str, ...]:
    return tuple(outcome["impact"].get(h, "?") for h in hyps)


def validate_test_item(item: dict[str, Any], scope_hyps: list[str]) -> str | None:
    """First contract violation of one proposed test, or None."""
    outcomes = item["outcomes"]
    if len(outcomes) < 2:
        return "E_TEST_OUTCOMES_TOO_FEW"
    labels = [o["label"] for o in outcomes]
    if len(set(labels)) != len(labels):
        return "E_TEST_DUPLICATE_LABEL"
    for o in outcomes:
        extra = set(o["impact"]) - set(scope_hyps)
        if extra:
            return "E_TEST_IMPACT_SCOPE"
        if set(scope_hyps) - set(o["impact"]):
            return "E_TEST_IMPACT_INCOMPLETE"
    vectors = {_vector(o, scope_hyps) for o in outcomes}
    if len(vectors) < 2:
        return "E_TEST_IDENTICAL_IMPACT"
    if all(len(set(v)) == 1 for v in vectors):
        return "E_TEST_NOT_DISCRIMINATING"
    unin = str(item.get("uninformative_outcome") or "").strip()
    if not unin:
        return "E_TEST_UNINFORMATIVE_MISSING"
    for o in outcomes:
        if o["label"] == unin and any(v != "none" for v in o["impact"].values()):
            return "E_TEST_UNINFORMATIVE_IMPACT"
    if not str(item.get("access_basis") or "").strip():
        return "E_TEST_ACCESS_BASIS_MISSING"
    return None


def discriminates(test: dict[str, Any], a: str, b: str) -> bool:
    """True when some outcome treats hypotheses a and b differently."""
    return any(o["impact"].get(a) != o["impact"].get(b) and a in o["impact"] and b in o["impact"]
               for o in test["outcomes"])


def validate_action_item(item: dict[str, Any], known: dict[str, Any]) -> str | None:
    """Check typed links, scope and the stated basis; never certify source authenticity."""
    scope = item["scope_id"]
    if scope not in known["observation_sets"]:
        return "E_UNKNOWN_ID"
    uncertainty, document = item["uncertainty"], item["document"]
    for oid in uncertainty["observation_ids"]:
        if oid not in known["observations"]:
            return "E_UNKNOWN_ID"
        if oid not in known["scope_observations"][scope]:
            return "E_TEST_UNCERTAINTY_SCOPE"
    for hid in uncertainty["hypothesis_ids"]:
        if hid not in known["hypotheses"]:
            return "E_UNKNOWN_ID"
        if known["hypothesis_scopes"][hid] != scope:
            return "E_TEST_UNCERTAINTY_SCOPE"
    if not any(discriminates(item, a, b) for a, b in itertools.combinations(uncertainty["hypothesis_ids"], 2)):
        return "E_TEST_UNCERTAINTY_NOT_DISCRIMINATING"
    did, basis = document["document_id"], document["basis_passage_ids"]
    if any(p not in known["passages"] for p in basis):
        return "E_UNKNOWN_ID"
    if document["status"] == "in_corpus":
        if did not in known["documents"]:
            return "E_TEST_DOCUMENT_MISSING"
        if not basis or not any(known["passage_documents"][p] == did for p in basis):
            return "E_TEST_DOCUMENT_BASIS"
    elif did is not None:
        return "E_TEST_DOCUMENT_STATUS"
    elif document["status"] == "referenced_not_obtained" and not basis:
        return "E_TEST_DOCUMENT_BASIS"
    return None


def required_pairs(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    """Hypothesis pairs that a test must separate: tied leaders, or leader vs LOO successors."""
    out: dict[tuple[str, str], list[str]] = {}

    def add(a: str, b: str, why: str) -> None:
        key = tuple(sorted((a, b)))
        out.setdefault(key, [])
        if why not in out[key]:
            out[key].append(why)

    for reason in comparison["underdetermined_reasons"]:
        if reason["code"] == "tie":
            for a, b in itertools.combinations(sorted(reason["hypothesis_ids"]), 2):
                add(a, b, "tie")
    leader = comparison.get("leader") or comparison.get("provisional_leader")
    if comparison["status"] == "unstable" and leader:
        for entry in comparison["loo"]:
            if not entry["changes_leader"]:
                continue
            others = [entry["leader"]] if entry["leader"] else entry["tied_top"]
            for o in others:
                if o and o != leader:
                    add(leader, o, f"unstable:{entry['family_id']}")
    return [{"pair": list(k), "reasons": sorted(v)} for k, v in sorted(out.items())]


# --- no-test reasons (individual class I decisions) --------------------------------------------

def grant_no_test_reasons(case_dir: Path | str, file_path: Path | str) -> dict[str, Any]:
    from .review import evidence_class_for
    root = Path(case_dir)
    raw = Path(file_path).read_bytes()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise _err("E_REASON_FILE", "The reasons file is not valid JSON.", "Plik uzasadnień nie jest poprawnym JSON.") from e
    profile = load_profile(root)
    if not isinstance(doc, dict) or doc.get("case_id") != profile["case_id"] or not isinstance(doc.get("reasons"), list):
        raise _err("E_REASON_FILE", "The reasons file does not belong to this case.",
                   "Plik uzasadnień nie należy do tej sprawy.")
    reviewer = str(doc.get("reviewer") or "").strip()
    if not reviewer or not doc["reasons"]:
        raise _err("E_REASON_FILE", "A reviewer and at least one reason are required.",
                   "Wymagany jest recenzent i co najmniej jedno uzasadnienie.")
    evidence = evidence_class_for(root, file_path)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        rd = repo.reader()
        scopes = {s["id"] for s in rd.approved_rows("observation_sets")}
        hyps = {h["id"]: h["scope_id"] for h in rd.approved_rows("hypotheses")}
        recs = []
        for r in doc["reasons"]:
            pair = r.get("pair") if isinstance(r, dict) else None
            if (not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1]
                    or any(h not in hyps for h in pair) or r.get("scope_id") not in scopes
                    or any(hyps[h] != r["scope_id"] for h in pair)):
                raise _err("E_REASON_PAIR", "A reason needs two distinct approved hypotheses of the named scope.",
                           "Uzasadnienie wymaga dwóch różnych zatwierdzonych hipotez z podanego zakresu.")
            if not str(r.get("reason") or "").strip():
                raise _err("E_REASON_TEXT", "A missing test needs a written reason.",
                           "Brak testu wymaga pisemnego uzasadnienia.")
            body = {"kind": "no_test_reason", "scope_id": r["scope_id"], "pair": sorted(pair),
                    "reason": str(r["reason"]).strip(), "reviewer": reviewer, "evidence_class": evidence,
                    "triage": "I", "mode": "individual"}
            recs.append({"id": "ntr:" + sha256_obj(body)[:20], **body})
        run = rd.runs()[-1]
        step = f"no-test-reason:{sha256_hex(raw)[:16]}"
        repo.add_step(step, run["id"], "no-test-reason", "none")
        repo.add_frozen_many("value_records", recs, step)
    finally:
        repo.close()
    return {"ok": True, "granted": len(recs), "evidence_class": evidence, "file_sha256": sha256_hex(raw)}


# --- plan -----------------------------------------------------------------------------------------

def _trace(rd: ReadRepository, test_id: str) -> dict[str, Any]:
    """test -> proposal -> human review decisions (the approval path)."""
    proposal = next((o[len("proposal:"):] for s, _, o in rd.prov_edges("wasDerivedFrom")
                     if s == test_id and o.startswith("proposal:")), None)
    test = next(t for t in rd.approved_rows("tests") if t["id"] == test_id)
    item = {k: v for k, v in test.items() if k not in ("case_id", "id")}
    reviews = []
    for r in rd.review_rows():
        if not proposal or r["decision"] not in ("approved", "corrected"):
            continue
        pid, sep, index = r["item_id"].rpartition("#")
        if not sep or pid != proposal or not index.isdigit():
            continue
        expected = "tst:" + sha256_obj({"p": proposal, "i": int(index), "item": item})[:16]
        if expected == test_id:
            reviews.append(r)
    return {"proposal_id": proposal,
            "reviews": [{"id": r["id"], "decision": r["decision"], "reviewer": r["reviewer"],
                         "evidence_class": r["evidence_class"]} for r in reviews],
            "predictions": "blocked_T-PREDICTION"}


def _name(scope_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", scope_id.split(":", 1)[-1])


def plan(case_dir: Path | str, scope_id: str, *, coverage_threshold: float | None = None,
         write: bool = True) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        rd.assert_chain_ok()
        comparison = cmp.compare_scope(rd, scope_id, coverage_threshold=coverage_threshold)
        scope_hyps = sorted(h["id"] for h in rd.approved_rows("hypotheses") if h["scope_id"] == scope_id)
        hyp_set = set(scope_hyps)
        tests = [t for t in rd.approved_rows("tests")
                 if t.get("scope_id", scope_id) == scope_id
                 and all(o["impact"] and set(o["impact"]) <= hyp_set for o in t["outcomes"])]
        from . import facts
        sets = rd.approved_rows("observation_sets")
        passages = rd.frozen_rows("passages")
        known = {"observation_sets": {s["id"] for s in sets},
                 "scope_observations": {s["id"]: facts.effective_observation_ids(rd, s) for s in sets},
                 "observations": {o["id"] for o in rd.approved_rows("observations")},
                 "hypotheses": {h["id"] for h in rd.approved_rows("hypotheses")},
                 "hypothesis_scopes": {h["id"]: h["scope_id"] for h in rd.approved_rows("hypotheses")},
                 "passages": {p["id"] for p in passages},
                 "passage_documents": {p["id"]: p["document_id"] for p in passages},
                 "documents": {d["id"] for d in rd.frozen_rows("documents")}}
        issues = {t["id"]: validate_test_item(t, scope_hyps) or
                  (validate_action_item(t, known) if all(k in t for k in ACTION_FIELDS) else None) for t in tests}
        reasons = [b for b in rd.frozen_rows("value_records")
                   if b.get("kind") == "no_test_reason" and b.get("scope_id") == scope_id]
        needed = required_pairs(comparison)
        entries = []
        for req in needed:
            a, b = req["pair"]
            covering = sorted(t["id"] for t in tests if not issues[t["id"]] and discriminates(t, a, b))
            waived = [{"id": r["id"], "reason": r["reason"], "reviewer": r["reviewer"],
                       "evidence_class": r["evidence_class"]} for r in reasons if r["pair"] == [a, b]]
            state = "covered" if covering else ("no_test_reason_approved" if waived else "gap")
            linked = [t["id"] for t in tests if t["id"] in covering and all(k in t for k in ACTION_FIELDS)]
            entries.append({**req, "state": state, "test_ids": covering,
                            "document_linked_test_ids": sorted(linked), "no_test_reasons": waived})
        trace = {t["id"]: _trace(rd, t["id"]) for t in tests}
        result = {
            "schema_version": 2, "scope_id": scope_id, "comparison_status": comparison["status"],
            "leader": comparison["leader"], "required": entries,
            "complete": all(e["state"] != "gap" for e in entries),
            "invalid_test_ids": sorted(tid for tid, issue in issues.items() if issue),
            "gaps": [e["pair"] for e in entries if e["state"] == "gap"],
            "tests": [{"id": t["id"], "question": t["question"], "outcomes": t["outcomes"],
                       "uninformative_outcome": t["uninformative_outcome"], "access_basis": t["access_basis"],
                       "access_basis_note": "proposer's statement; not a legal assessment or a granted permission",
                       "action_status": ("requires_reassessment" if issues[t["id"]] else
                                         "document_linked" if all(k in t for k in ACTION_FIELDS) else "legacy_missing_details"),
                       "contract_issue": issues[t["id"]],
                       **{k: t[k] for k in ACTION_FIELDS if k in t},
                       "trace": trace[t["id"]]} for t in sorted(tests, key=lambda t: t["id"])],
            "legacy_test_ids": sorted(t["id"] for t in tests if not all(k in t for k in ACTION_FIELDS)),
            "action_details_complete": (all(e["document_linked_test_ids"] or e["no_test_reasons"] for e in entries)
                                        if entries else (not tests or any(not issues[t["id"]] and
                                         all(k in t for k in ACTION_FIELDS) for t in tests))),
            "executes_actions": False, "predictions": "blocked_T-PREDICTION",
            "approved_set_hash": rd.approved_set_hash(), "chain_head": rd.chain_head(),
        }
    finally:
        rd.close()
    result["plan_hash"] = sha256_obj(result)
    if write:
        rel = f"test_plan/test-plan-{_name(scope_id)}.json"
        atomic_write(root, rel, canonical_json(result) + b"\n")
        result["path"] = rel
    return {"ok": True, **result}


# --- packets and ingest -------------------------------------------------------------------------

def prepare(case_dir: Path | str, scope_id: str, **kw: Any) -> dict[str, Any]:
    root = Path(case_dir)
    current = plan(root, scope_id, write=False)
    gaps = [e for e in current["required"] if e["state"] == "gap"]
    if not gaps and current["tests"] and current["action_details_complete"] and current["complete"]:
        return {"ok": True, "needed": False, "scope_id": scope_id, "required": len(current["required"])}
    profile = load_profile(root)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        comparison = cmp.compare_scope(rd, scope_id)
        hyps = [h for h in rd.approved_rows("hypotheses") if h["scope_id"] == scope_id]
        from . import facts
        scope = next(s for s in rd.approved_rows("observation_sets") if s["id"] == scope_id)
        obs_ids = facts.effective_observation_ids(rd, scope)
        observations = [o for o in rd.approved_rows("observations") if o["id"] in obs_ids]
        claim_ids = {c for o in observations for c in o["claim_ids"]}
        claims = [c for c in rd.approved_rows("claims") if c["id"] in claim_ids]
        passage_ids = {c["passage_id"] for c in claims}
        passages = [p for p in rd.frozen_rows("passages") if p["id"] in passage_ids]
        document_ids = {p["document_id"] for p in passages}
        documents = [d for d in rd.frozen_rows("documents") if d["id"] in document_ids]
    finally:
        rd.close()
    objects = [packets.make_object("test_scope", scope_id, {
        "hypothesis_ids": sorted(h["id"] for h in hyps), "required_pairs": [e["pair"] for e in gaps],
        "observation_ids": sorted(obs_ids),
        "invalid_test_ids": current["invalid_test_ids"],
        "action_contract": "scope_id, uncertainty, document, next_step; document existence must not be invented",
        "comparison_hash": sha256_obj(comparison)})]
    objects += [packets.make_object("hypothesis", h["id"], {k: h[k] for k in ("mechanism", "scope_id", "kind")})
                for h in hyps]
    for kind, rows in (("observation", observations), ("claim", claims), ("passage", passages), ("document", documents)):
        objects += [packets.make_object(kind, row["id"], row) for row in rows]
    objects += [packets.make_object("profile", p["hypothesis_id"], {k: p[k] for k in (
        "conflicting_families", "supporting_families", "unconfirmed_assumptions")}) for p in comparison["profiles"]]
    out = packets.prepare(root, "tests", objects, **kw)
    return {**out, "needed": True, "scope_id": scope_id, "gaps": [e["pair"] for e in gaps]}


def ingest(case_dir: Path | str, packet: dict[str, Any], payload: Any) -> dict[str, Any]:
    if packet.get("task_type") != "tests":
        raise _err("E_UNKNOWN_TASK", "This is not a tests packet.", "To nie jest pakiet testów.")
    root = Path(case_dir)
    scope_obj = next((o for o in packet.get("items", []) if o.get("type") == "test_scope"), None)
    if scope_obj is None:
        raise _err("E_TEST_SCOPE_MISSING", "The packet has no test scope descriptor.",
                   "Pakiet nie zawiera opisu zakresu testów.")
    scope_hyps = sorted(scope_obj["content"]["hypothesis_ids"])
    profile = load_profile(root)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        live = sorted(h["id"] for h in rd.approved_rows("hypotheses") if h["scope_id"] == scope_obj["id"])
    finally:
        rd.close()
    if live != scope_hyps:
        raise LaError("E_TEST_STALE", "The hypothesis set changed after packet preparation.",
                      "Zbiór hipotez zmienił się po przygotowaniu pakietu.", EXIT_USAGE)

    def enrich(task: str, body: dict[str, Any], known: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        for item in body["items"]:
            if item["scope_id"] != scope_obj["id"]:
                return body, "E_TEST_UNCERTAINTY_SCOPE"
            code = validate_test_item(item, scope_hyps)
            if code:
                return body, code
        return body, None

    result = proposals.ingest_proposal(root, packet, payload, enrich=enrich)
    result["triage"] = ["I"] * len(result.get("payload", {}).get("items", [])) if result["code"] is None else []
    return result


def read_plan(case_dir: Path | str, scope_id: str) -> dict[str, Any]:
    try:
        return json.loads((Path(case_dir) / f"test_plan/test-plan-{_name(scope_id)}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise _err("E_NO_PLAN", "No test plan for this scope; run tests plan first.",
                   "Brak planu testów dla tego zakresu; najpierw uruchom tests plan.") from e
