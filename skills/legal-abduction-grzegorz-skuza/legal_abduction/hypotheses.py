"""Hypotheses, perspectives and protection of persons (LA-014, R11/R12).

Everything here is deterministic (D): it checks structure of the *approved* hypothesis set. The
hypotheses themselves are model proposals (H) that only an individual class I review admits (O).

Interim interpretation (documented in docs/decisions.md):
- Perspective.conduct_in_scope is prose in the profile; a perspective is "in scope" when the text is
  non-empty and not a literal negation (false/no/nie/none). A boolean is honoured as is.
- Predictions (Prediction entity, observability condition) are NOT checked: T-PREDICTION is undefined,
  so the report states `predictions: blocked_T-PREDICTION` instead of inventing a contract.
- Mechanism de-duplication is exact equality of the normalized text *and* identical scope, kind,
  burdens and intent attribution. Similar wording never merges anything and nothing is deleted.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import facts, packets, proposals, staleness
from .profile import HIGH_RISK_CONTEXTS, load_profile, normalize_context
from .repository import Repository
from .runtime import EXIT_POLICY, EXIT_USAGE, LaError, atomic_write, canonical_json, sha256_hex, sha256_obj

LEXICON = Path(__file__).resolve().parent.parent / "references" / "lexicons" / "person_evaluation.json"
NEGATIONS = frozenset({"false", "no", "nie", "none", "n/a", "-"})
EXCEPTION_RULES = ("alternative_for_perspective", "data_error", "empty_burdens")
INDIVIDUAL_CLASS_I = ("I", "individual")


def _err(code: str, en: str, pl: str, exit_code: int = EXIT_USAGE, **ids: str) -> LaError:
    return LaError(code, en, pl, exit_code, ids or None)


# --- perspectives, normalisation, de-duplication ------------------------------------------------

def in_scope(perspective: dict[str, Any]) -> bool:
    v = perspective.get("conduct_in_scope")
    if isinstance(v, bool):
        return v
    s = str(v or "").strip().casefold()
    return bool(s) and s not in NEGATIONS


def normalize_mechanism(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.sub(r"[\W_]+", " ", t).split())


def dedupe_groups(hyps: list[dict[str, Any]]) -> list[list[str]]:
    groups: dict[Any, list[str]] = {}
    for h in hyps:
        key = (h["scope_id"], h["kind"], tuple(sorted(h["burdens"])), bool(h["attributes_intent"]),
               normalize_mechanism(h["mechanism"]))
        groups.setdefault(key, []).append(h["id"])
    return [sorted(g) for g in groups.values() if len(g) > 1]


def _perspectives(repo: Repository, profile: dict[str, Any]) -> list[dict[str, Any]]:
    out = {p["id"]: p for p in profile["perspectives"]}
    for p in repo.reader().approved_rows("perspectives"):
        out.setdefault(p["id"], p)
    return [out[k] for k in sorted(out)]


# --- person-evaluation screen (R12) -------------------------------------------------------------

@lru_cache(maxsize=1)
def _lexicon() -> dict[str, Any]:
    return json.loads(LEXICON.read_text(encoding="utf-8"))


def person_evaluation_findings(text: str) -> list[dict[str, str]]:
    """Screen only (regex): numbers/probabilities, rankings and judgemental labels. Never decides guilt."""
    lex = _lexicon()
    t = unicodedata.normalize("NFKC", text).casefold()
    out: list[dict[str, str]] = []
    for kind, words in (("label", lex["labels"]), ("ranking", lex["rank_markers"])):
        for w in words:
            if re.search(rf"(?<!\w){re.escape(w.casefold())}(?!\w)", t):
                out.append({"type": kind, "term": w})
    for pat in lex["number_patterns"]:
        m = re.search(pat, t)
        if m:
            out.append({"type": "number", "term": m.group(0).strip()})
    return out


def is_high_risk(profile: dict[str, Any]) -> bool:
    return normalize_context(profile["deployment_context"]) in HIGH_RISK_CONTEXTS


def _item_texts(item: dict[str, Any]) -> list[str]:
    texts = [str(item.get("mechanism", ""))]
    for a in item.get("assumptions", []) or []:
        if isinstance(a, dict):
            texts += [str(a.get("statement", "")), str(a.get("basis", ""))]
    return texts


def _enrich(profile: dict[str, Any], approved: dict[str, dict[str, Any]], altcause: bool):
    high = is_high_risk(profile)

    def enrich(task: str, payload: dict[str, Any], known: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        for item in payload["items"]:
            if high and any(person_evaluation_findings(t) for t in _item_texts(item)):
                return payload, "E_PERSON_EVALUATION"
            if altcause:
                tgt = approved.get(item["alternative_to"])
                if (tgt is None or not tgt["attributes_intent"] or item["attributes_intent"]
                        or item["scope_id"] != tgt["scope_id"]):
                    return payload, "E_ALTCAUSE_INVALID"
        return payload, None
    return enrich


# --- packets and ingest -------------------------------------------------------------------------

def prepare_hypotheses(case_dir: Path | str, scope_id: str, **kw: Any) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        sets = {s["id"]: s for s in repo.reader().approved_rows("observation_sets")}
        if scope_id not in sets:
            raise _err("E_SCOPE_UNKNOWN", "No approved ObservationSet with this id.",
                       "Brak zatwierdzonego ObservationSet o tym id.", scope_id=scope_id)
        wanted = set(facts.effective_observation_ids(repo.reader(), sets[scope_id]))
        objs = [packets.make_object("observation_set", scope_id, {"rationale": sets[scope_id]["rationale"]})]
        objs += [packets.make_object("observation", o["id"], {"description": o["description"], "claim_ids": o["claim_ids"]})
                 for o in repo.reader().approved_rows("observations") if o["id"] in wanted]
        objs += [packets.make_object("perspective", p["id"], {"label": p.get("label", p["id"]), "role": p["role"],
                                      "conduct_in_scope": p["conduct_in_scope"]})
                 for p in _perspectives(repo, profile)]
        marker = staleness.marker_object(repo.reader(), [scope_id, *sorted(wanted)])
        if marker:  # stale inputs must change the cache key so an old proposal cannot be reused
            objs.append(marker)
    finally:
        repo.close()
    return packets.prepare(root, "hypotheses", objs, **kw)


def _ingest(case_dir: Path | str, packet: dict[str, Any], payload: Any, task: str) -> dict[str, Any]:
    if packet.get("task_type") != task:
        raise _err("E_UNKNOWN_TASK", f"This is not a {task} packet.", f"To nie jest pakiet {task}.")
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        approved = {h["id"]: h for h in repo.reader().approved_rows("hypotheses")}
    finally:
        repo.close()
    r = proposals.ingest_proposal(root, packet, payload, enrich=_enrich(profile, approved, task == "altcause"))
    r["triage"] = ["I"] * len(r["payload"].get("items", []))  # hypotheses/altcause are always class I
    return r


def ingest_hypotheses(case_dir: Path | str, packet: dict[str, Any], payload: Any) -> dict[str, Any]:
    return _ingest(case_dir, packet, payload, "hypotheses")


def ingest_altcause(case_dir: Path | str, packet: dict[str, Any], payload: Any) -> dict[str, Any]:
    return _ingest(case_dir, packet, payload, "altcause")


def prepare_altcause(case_dir: Path | str, **kw: Any) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        hyps = repo.reader().approved_rows("hypotheses")
        missing = [h for h in hyps if h["attributes_intent"] and not _has_alternative(h, hyps)]
        if not missing:
            return {"ok": True, "needed": False}
        objs = [packets.make_object("hypothesis", h["id"], {k: h[k] for k in ("mechanism", "scope_id", "kind", "burdens")})
                for h in missing]
        objs += [packets.make_object("perspective", p["id"], {"label": p.get("label", p["id"]), "role": p["role"]})
                 for p in _perspectives(repo, profile)]
    finally:
        repo.close()
    return {**packets.prepare(root, "altcause", objs, **kw), "needed": True}


def _has_alternative(h: dict[str, Any], hyps: list[dict[str, Any]]) -> bool:
    return any(a["id"] != h["id"] and a["scope_id"] == h["scope_id"] and not a["attributes_intent"] for a in hyps)


# --- exceptions (individual class I decisions) --------------------------------------------------

def grant_exceptions(case_dir: Path | str, file_path: Path | str) -> dict[str, Any]:
    from .review import evidence_class_for
    root = Path(case_dir)
    raw = Path(file_path).read_bytes()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise _err("E_EXCEPTION_FILE", "The exceptions file is not valid JSON.", "Plik odstępstw nie jest poprawnym JSON.") from e
    profile = load_profile(root)
    if not isinstance(doc, dict) or doc.get("case_id") != profile["case_id"] or not isinstance(doc.get("exceptions"), list):
        raise _err("E_EXCEPTION_FILE", "The exceptions file does not belong to this case.",
                   "Plik odstępstw nie należy do tej sprawy.")
    reviewer = str(doc.get("reviewer") or "").strip()
    if not reviewer or not doc["exceptions"]:
        raise _err("E_EXCEPTION_FILE", "A reviewer and at least one exception are required.",
                   "Wymagany jest recenzent i co najmniej jedno odstępstwo.")
    evidence = evidence_class_for(root, file_path)
    sha = sha256_hex(raw)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        scopes = {s["id"] for s in repo.reader().approved_rows("observation_sets")}
        pers = {p["id"] for p in _perspectives(repo, profile)}
        recs = []
        for e in doc["exceptions"]:
            if not isinstance(e, dict) or e.get("rule") not in EXCEPTION_RULES:
                raise _err("E_EXCEPTION_RULE", "Unknown exception rule.", "Nieznana reguła odstępstwa.")
            if not str(e.get("reason") or "").strip():
                raise _err("E_EXCEPTION_REASON", "An exception needs a written reason.", "Odstępstwo wymaga uzasadnienia.")
            if e.get("scope_id") not in scopes:
                raise _err("E_SCOPE_UNKNOWN", "Unknown scope.", "Nieznany zakres.")
            per = e.get("perspective_id")
            if (e["rule"] == "alternative_for_perspective") != (per is not None) or (per is not None and per not in pers):
                raise _err("E_EXCEPTION_RULE", "perspective_id is required for (and only for) alternative_for_perspective, "
                           "and must exist.", "perspective_id jest wymagane tylko dla alternative_for_perspective "
                           "i musi istnieć.")
            body = {"kind": "hypothesis_exception", "rule": e["rule"], "scope_id": e["scope_id"], "perspective_id": per,
                    "reason": str(e["reason"]).strip(), "reviewer": reviewer, "evidence_class": evidence,
                    "triage": "I", "mode": "individual"}
            recs.append({"id": "hexc:" + sha256_obj(body)[:20], **body})
        run = repo.reader().runs()[-1]
        step = f"hypothesis-exception:{sha[:16]}"
        repo.add_step(step, run["id"], "hypothesis-exception", "none")
        repo.add_frozen_many("value_records", recs, step)
    finally:
        repo.close()
    return {"ok": True, "granted": len(recs), "evidence_class": evidence, "file_sha256": sha}


def exceptions(repo: Repository) -> list[dict[str, Any]]:
    return [b for b, _ in repo.frozen_bodies("value_records") if b.get("kind") == "hypothesis_exception"]


# --- the check ----------------------------------------------------------------------------------

def _review_problems(repo: Repository, hyps: list[dict[str, Any]]) -> tuple[dict[str, bool], list[dict[str, Any]]]:
    """Per hypothesis id: was it admitted by individual class I decisions only?"""
    reviews = repo.review_rows()
    edges = {s: o[len("proposal:"):] for s, o in repo.conn.execute(
        "SELECT subject_id, object_id FROM prov_edges WHERE case_id = ? AND predicate = 'wasDerivedFrom'",
        (repo.case_id,)) if o.startswith("proposal:")}
    ok: dict[str, bool] = {}
    problems = []
    for h in hyps:
        pid = edges.get(h["id"])
        rs = [r for r in reviews if pid and str(r["item_id"]).startswith(pid + "#")
              and r["decision"] in ("approved", "corrected")]
        good = bool(rs) and all((r.get("triage"), r.get("mode")) == INDIVIDUAL_CLASS_I for r in rs)
        ok[h["id"]] = good
        if not good:
            problems.append({"rule": "not_individual_class_I", "hypothesis_id": h["id"]})
    return ok, problems


def check_set(case_dir: Path | str) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        rd = repo.reader()
        hyps = rd.approved_rows("hypotheses")
        assumptions = rd.approved_rows("assumptions")
        pers = [p for p in _perspectives(repo, profile) if in_scope(p)]
        excs = exceptions(repo)
        class_i, review_problems = _review_problems(repo, hyps)
    finally:
        repo.close()
    waived = {(e["rule"], e["scope_id"], e.get("perspective_id")): e for e in excs}
    problems: list[dict[str, Any]] = []
    used: list[dict[str, Any]] = []

    def need(ok: bool, rule: str, scope: str, per: str | None = None) -> None:
        if ok:
            return
        w = waived.get((rule, scope, per))
        if w:
            used.append({"rule": rule, "scope_id": scope, "perspective_id": per, "reason": w["reason"], "id": w["id"]})
        else:
            problems.append({"rule": rule, "scope_id": scope, **({"perspective_id": per} if per else {})})
    if not hyps:
        problems.append({"rule": "hypotheses_missing"})
    for scope in sorted({h["scope_id"] for h in hyps}):
        sh = [h for h in hyps if h["scope_id"] == scope]
        for p in pers:
            need(any(p["id"] not in h["burdens"] for h in sh), "alternative_for_perspective", scope, p["id"])
        need(any(h["kind"] == "data_error" for h in sh), "data_error", scope)
        need(any(h["kind"] in ("process", "data_error") and not h["burdens"] for h in sh), "empty_burdens", scope)
    problems += review_problems
    intent = intent_gate(hyps, class_i)
    high = is_high_risk(profile)
    person = []
    if high:
        for rec in hyps + assumptions:
            texts = _item_texts({"mechanism": rec.get("mechanism", rec.get("statement", "")), "assumptions": []})
            texts.append(str(rec.get("basis", "")))
            f = [x for t in texts for x in person_evaluation_findings(t)]
            if f:
                person.append({"id": rec["id"], "findings": f})
    unconfirmed = [{"id": a["id"], "kind": a["kind"], "unconfirmed": True} for a in assumptions
                   if not str(a.get("basis") or "").strip()]
    return {"ok": True, "complete": not problems, "problems": problems, "exceptions_used": used,
            "duplicates": dedupe_groups(hyps), "unconfirmed_assumptions": unconfirmed, "intent": intent,
            "high_risk": high, "person_evaluation": person, "hypotheses": len(hyps),
            "predictions": "blocked_T-PREDICTION", "status": "hypothesis"}


def intent_gate(hyps: list[dict[str, Any]], class_i: dict[str, bool]) -> list[dict[str, Any]]:
    out = []
    for h in hyps:
        if not h["attributes_intent"]:
            continue
        if not _has_alternative(h, hyps):
            out.append({"hypothesis_id": h["id"], "code": "E_INTENT_NO_ALTERNATIVE"})
        if not class_i.get(h["id"], False):
            out.append({"hypothesis_id": h["id"], "code": "E_INTENT_NOT_CLASS_I"})
    return out


def require_complete(case_dir: Path | str) -> dict[str, Any]:
    r = check_set(case_dir)
    if not r["complete"]:
        rules = ", ".join(sorted({p["rule"] for p in r["problems"]}))
        raise _err("E_HYPOTHESIS_SET_INCOMPLETE", f"The hypothesis set is incomplete: {rules}.",
                   f"Zestaw hipotez jest niekompletny: {rules}.", EXIT_POLICY, problems=str(len(r["problems"])))
    return r


def gate_findings(case_dir: Path | str, exhibit: bool) -> list[dict[str, Any]]:
    """Render-gate findings (R12) and the exhibit header marker for exceptions (R11)."""
    r = check_set(case_dir)
    out: list[dict[str, Any]] = []
    if r["intent"]:
        out.append({"gate": "intent_without_alternative_or_class_I", "outcome": "block", "items": r["intent"]})
    if r["person_evaluation"]:
        out.append({"gate": "person_evaluation_content", "outcome": "block",
                    "ids": [p["id"] for p in r["person_evaluation"]]})
    if r["exceptions_used"] and exhibit:
        out.append({"gate": "hypothesis_rule_exception", "outcome": "header_declaration_required",
                    "exceptions": r["exceptions_used"]})
    return out


# --- audit log export (high-risk deployers) -----------------------------------------------------

def export_audit_log(case_dir: Path | str, out: Path | str | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        steps = repo.list_steps()
        vr = [b for b, _ in repo.frozen_bodies("value_records")]
        times = {f"review-export:{b['id'][len('exportat:'):]}": b["exported_at"] for b in vr if b.get("kind") == "export_time"}
        times |= {f"review-import:{b['sha256'][:16]}": b["imported_at"] for b in vr if b.get("kind") == "review_file"}
        classes: dict[str, set[str]] = {}
        for sid, ev in repo.conn.execute("SELECT created_step_id, json_extract(body_json, '$.evidence_class') "
                                         "FROM reviews WHERE case_id = ?", (repo.case_id,)):
            classes.setdefault(sid, set()).add(ev)
    finally:
        repo.close()
    rows = []
    for s in steps:
        t = times.get(s["id"])
        ev = sorted(classes.get(s["id"], ())) or (["model_proposal"] if s["agent"].startswith("model:") else ["auto_technical"])
        rows.append({"step": s["id"], "name": s["name"], "agent": s["agent"],
                     "time": datetime.fromtimestamp(t, timezone.utc).isoformat() if t is not None else None,
                     "evidence_class": ev[0] if len(ev) == 1 else ev})
    doc = {"case_id": profile["case_id"], "deployment_context": profile["deployment_context"],
           "high_risk": is_high_risk(profile), "steps": rows,
           "note": {"en": "Steps record name, agent, evidence class; time is known only for review export/import steps "
                          "(steps carry no timestamp). Contains no case content.",
                    "pl": "Kroki zawierają nazwę, agenta i klasę dowodu; czas jest znany tylko dla eksportu/importu "
                          "recenzji (kroki nie mają znacznika czasu). Brak treści akt."}}
    if doc["high_risk"]:
        doc["annex"] = "docs/ai-act/ (Zał. III / Annex III)"
    data = canonical_json(doc) + b"\n"
    if out is None:
        atomic_write(root, "audit/audit-log.json", data)
        path = str(root / "audit" / "audit-log.json")
    else:
        try:
            with open(out, "xb") as fh:
                fh.write(data)
        except FileExistsError as e:
            raise _err("E_OUT_EXISTS", "The output file already exists; it is never overwritten.",
                       "Plik wyjściowy już istnieje; nigdy nie jest nadpisywany.") from e
        path = str(out)
    return {"ok": True, "path": path, "steps": len(rows), "high_risk": doc["high_risk"], "exported_at": time.time()}
