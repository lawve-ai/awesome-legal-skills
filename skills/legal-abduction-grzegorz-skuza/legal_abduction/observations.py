"""Observations (R6): selection from approved claims, event time, coverage report.

Observations come only from approved Claims; every exclusion carries a human
`exclusion_reason`. Observations and the ObservationSet are approved-set records
written through the review chain (the selection file is the human decision and its
evidence class follows the same channel rules as a review file). Event time is a
separate frozen entity (earliest/latest/basis/ambiguous), versioned with
`supersedes`. "Before" holds only when latest(A) < earliest(B); overlapping
intervals are `undetermined`; a numeric date such as 03/04/2025 without context is
`ambiguous` (both readings are enclosed in the interval); time without a zone is
never turned into UTC and cannot be ordered against a zoned time.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .repository import Repository
from .review import ADMITTING, evidence_class_for
from .runtime import EXIT_USAGE, LaError, sha256_hex, sha256_obj

_MONTHS = {
    **{m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september",
                                   "october", "november", "december"], 1)},
    **{m: i for i, m in enumerate(["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
                                   "września", "października", "listopada", "grudnia"], 1)},
    **{m: i for i, m in enumerate(["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień",
                                   "wrzesień", "październik", "listopad", "grudzień"], 1)},
}
_ISO_DT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(Z|[+-]\d{2}:\d{2})?$")
_ISO_D = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_NUM = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")
_RANGE = re.compile(r"^(\d{1,2})\s*[–-]\s*(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})$")
_DMY_TXT = re.compile(r"^(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})$")
_MDY_TXT = re.compile(r"^([^\W\d_]+)\s+(\d{1,2}),?\s+(\d{4})$")


def _err(code: str, en: str, pl: str) -> LaError:
    return LaError(code, en, pl, EXIT_USAGE)


def _d(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_time(text: str, date_order: str | None = None) -> dict[str, Any]:
    """Interval for a date expression; `date_order` ('DMY'/'MDY') must come from explicit human context."""
    t = text.strip()
    out = {"earliest": None, "latest": None, "ambiguous": True, "time_basis": "unparsed"}
    if m := _ISO_DT.match(t):
        y, mo, d, hh, mm = (int(x) for x in m.groups()[:5])
        if _d(y, mo, d) and hh < 24 and mm < 60:
            return {"earliest": t, "latest": t, "ambiguous": False,
                    "time_basis": "iso_datetime_zoned" if m.group(7) else "iso_datetime_no_zone"}
    if m := _ISO_D.match(t):
        if _d(*(int(x) for x in m.groups())):
            return {"earliest": t, "latest": t, "ambiguous": False, "time_basis": "iso_date"}
    if m := _NUM.match(t):
        a, b, y = (int(x) for x in m.groups())
        dmy, mdy = _d(y, b, a), _d(y, a, b)
        if date_order == "DMY":
            dmy, mdy = dmy, None
        elif date_order == "MDY":
            dmy, mdy = None, mdy
        cands = sorted({x for x in (dmy, mdy) if x})
        if cands:
            amb = len(cands) > 1
            return {"earliest": cands[0].isoformat(), "latest": cands[-1].isoformat(), "ambiguous": amb,
                    "time_basis": "numeric_ambiguous" if amb else "numeric_resolved"}
    if m := _RANGE.match(t):
        d1, d2, mon, y = int(m.group(1)), int(m.group(2)), _MONTHS.get(m.group(3).lower()), int(m.group(4))
        if mon and _d(y, mon, d1) and _d(y, mon, d2) and d1 <= d2:
            return {"earliest": date(y, mon, d1).isoformat(), "latest": date(y, mon, d2).isoformat(), "ambiguous": False,
                    "time_basis": "day_range"}
    if m := _DMY_TXT.match(t):
        mon = _MONTHS.get(m.group(2).lower())
        if mon and (x := _d(int(m.group(3)), mon, int(m.group(1)))):
            return {"earliest": x.isoformat(), "latest": x.isoformat(), "ambiguous": False, "time_basis": "named_month"}
    if m := _MDY_TXT.match(t):
        mon = _MONTHS.get(m.group(1).lower())
        if mon and (x := _d(int(m.group(3)), mon, int(m.group(2)))):
            return {"earliest": x.isoformat(), "latest": x.isoformat(), "ambiguous": False, "time_basis": "named_month"}
    return out


def _bound(s: str | None, high: bool) -> tuple[datetime, bool] | None:
    """(comparable instant, zone known). Date-only values are naive whole days."""
    if not s:
        return None
    if m := _ISO_D.match(s):
        d = date(*(int(x) for x in m.groups()))
        return (datetime(d.year, d.month, d.day, 23, 59, 59, 999999) if high else datetime(d.year, d.month, d.day)), False
    if m := _ISO_DT.match(s):
        y, mo, d, hh, mm = (int(x) for x in m.groups()[:5])
        ss = int(m.group(6) or 0)
        z = m.group(7)
        dt = datetime(y, mo, d, hh, mm, ss)
        if z is None:
            return dt, False
        if z == "Z":
            return dt.replace(tzinfo=timezone.utc), True
        sign = 1 if z[0] == "+" else -1
        from datetime import timedelta
        return dt.replace(tzinfo=timezone(sign * timedelta(hours=int(z[1:3]), minutes=int(z[4:6])))), True
    return None


def order(a: dict[str, Any], b: dict[str, Any]) -> str:
    """'before', 'after' or 'undetermined' (overlap, missing bounds, or zoned vs zone-less time)."""
    ba = (_bound(a.get("earliest"), False), _bound(a.get("latest"), True))
    bb = (_bound(b.get("earliest"), False), _bound(b.get("latest"), True))
    if None in ba or None in bb:
        return "undetermined"
    (a_lo, az1), (a_hi, az2), (b_lo, bz1), (b_hi, bz2) = ba[0], ba[1], bb[0], bb[1]
    if len({az1, az2, bz1, bz2}) != 1:
        return "undetermined"  # mixed zoned / zone-less values are never normalised to UTC
    if a_hi < b_lo:
        return "before"
    if b_hi < a_lo:
        return "after"
    return "undetermined"


# --- selection -------------------------------------------------------------------------

def select_observations(case_dir: Path | str, selection_file: Path | str) -> dict[str, Any]:
    from .proposals import load_profile
    root = Path(case_dir)
    raw = Path(selection_file).read_bytes()
    sha = sha256_hex(raw)
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise _err("E_SELECTION_FILE", "Selection file is not valid JSON.", "Plik wyboru nie jest poprawnym JSON.") from e
    profile = load_profile(root)
    reviewer = str(doc.get("reviewer") or "").strip() if isinstance(doc, dict) else ""
    sels = doc.get("selections") if isinstance(doc, dict) else None
    if not reviewer or not isinstance(sels, list) or not sels:
        raise _err("E_SELECTION_FILE", "The file needs a reviewer and a non-empty selections list.",
                   "Plik wymaga recenzenta i niepustej listy selections.")
    evidence = evidence_class_for(root, selection_file)
    repo = Repository(root / "case.db", profile["case_id"], admitting_decisions=ADMITTING)
    try:
        approved = {c["id"] for c in repo.reader().approved_rows("claims")}
        items = []
        for s in sels:
            ids = s.get("claim_ids") if isinstance(s, dict) else None
            if not isinstance(ids, list) or not ids or any(i not in approved for i in ids):
                raise _err("E_CLAIM_NOT_APPROVED", "An observation can only be built from approved claims.",
                           "Obserwację można zbudować wyłącznie z zatwierdzonych twierdzeń.")
            if not str(s.get("description") or "").strip():
                raise _err("E_SELECTION_FILE", "Every selection needs a description.", "Każdy wybór wymaga opisu.")
            in_scope = bool(s.get("in_scope", True))
            reason = str(s.get("exclusion_reason") or "").strip()
            if not in_scope and not reason:
                raise _err("E_EXCLUSION_REASON", "Every exclusion needs a reason decided by a human.",
                           "Każde wyłączenie wymaga uzasadnienia człowieka.")
            item = {"claim_ids": sorted(set(ids)), "description": s["description"].strip(), "in_scope": in_scope,
                    "relevance_note": str(s.get("relevance_note") or "").strip()}
            if reason and not in_scope:
                item["exclusion_reason"] = reason
            items.append(item)
        if not any(i["in_scope"] for i in items):
            raise _err("E_NO_OBSERVATIONS_IN_SCOPE", "At least one observation must stay in scope.",
                       "Co najmniej jedna obserwacja musi pozostać w zakresie.")
        pid = f"obsel:{sha[:20]}"
        with repo.transaction():
            run = repo.reader().runs()[-1]
            step = f"observations-select:{sha[:16]}"
            repo.add_step(step, run["id"], "observations-select", "none")
            repo.add_proposal({"id": pid, "task_type": "observation_select", "cache_key": sha,
                               "payload_json": {"items": items}}, step)
            obs_ids = []
            first_review: dict[str, Any] | None = None
            for i, item in enumerate(items):
                oid = f"obs:{sha256_obj([pid, i, item])[:16]}"
                obs_ids.append((oid, item["in_scope"]))
                review = {"case_id": profile["case_id"], "id": f"rev:{sha256_obj([pid, i, sha])[:20]}",
                          "item_id": f"{pid}#{i}", "decision": "approved", "reviewer": reviewer, "evidence_class": evidence,
                          "review_file_sha256": sha, "batch_id": "class-I", "sampled": False,
                          "reason": "human selection", "triage": "I", "mode": "individual"}
                first_review = first_review or review
                rec = {"case_id": profile["case_id"], "id": oid, "description": item["description"],
                       "claim_ids": item["claim_ids"], "in_scope": item["in_scope"]}
                if item["relevance_note"]:
                    rec["relevance_note"] = item["relevance_note"]
                if "exclusion_reason" in item:
                    rec["exclusion_reason"] = item["exclusion_reason"]
                repo.approve(pid, review, "observations", rec, step)
            in_ids = sorted(o for o, ins in obs_ids if ins)
            set_id = f"set:{sha256_obj(in_ids)[:16]}"
            assert first_review is not None
            repo.approve(pid, first_review, "observation_sets", {
                "case_id": profile["case_id"], "id": set_id, "observation_ids": in_ids,
                "rationale": str(doc.get("rationale") or "human selection of in-scope observations")}, step)
        return {"ok": True, "observation_ids": sorted(o for o, _ in obs_ids), "observation_set_id": set_id,
                "excluded": sum(1 for _, ins in obs_ids if not ins), "evidence_class": evidence}
    finally:
        repo.close()


# --- event time --------------------------------------------------------------------------

def _row_id(body: dict[str, Any]) -> str:
    return sha256_obj(body)[:32]


def current_event_times(repo: Repository) -> dict[str, dict[str, Any]]:
    rows = [b for b, _ in repo.frozen_bodies("event_time_assessments")]
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    return {r["observation_id"]: r for r in rows if _row_id(r) not in superseded}


def record_event_time(case_dir: Path | str, observation_id: str, *, text: str | None = None, earliest: str | None = None,
                      latest: str | None = None, time_basis: str | None = None, ambiguous: bool | None = None,
                      date_order: str | None = None) -> dict[str, Any]:
    from .proposals import load_profile
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        if observation_id not in {o["id"] for o in repo.reader().approved_rows("observations")}:
            raise _err("E_UNKNOWN_OBSERVATION", "Event time needs an approved observation.",
                       "Czas zdarzenia wymaga zatwierdzonej obserwacji.")
        if text is not None:
            parsed = parse_time(text, date_order)
        else:
            parsed = {"earliest": earliest, "latest": latest, "ambiguous": bool(ambiguous),
                      "time_basis": time_basis or "explicit"}
            lo, hi = _bound(earliest, False), _bound(latest, True)
            if (earliest and lo is None) or (latest and hi is None) or (lo and hi and (
                    (lo[0].tzinfo is None) != (hi[0].tzinfo is None) or lo[0] > hi[0])):
                raise _err("E_TIME_INVALID", "earliest/latest must be ISO values with earliest <= latest, same zone kind.",
                           "earliest/latest muszą być wartościami ISO, earliest <= latest, ten sam rodzaj strefy.")
        body = {"case_id": profile["case_id"], "observation_id": observation_id, "time_basis": parsed["time_basis"],
                "ambiguous": parsed["ambiguous"]}
        for k in ("earliest", "latest"):
            if parsed[k]:
                body[k] = parsed[k]
        cur = current_event_times(repo).get(observation_id)
        if cur is not None:
            if {k: v for k, v in cur.items() if k != "supersedes"} == body:
                return {"ok": True, "new": False, **parsed}
            body["supersedes"] = _row_id(cur)
        run = repo.reader().runs()[-1]
        step = f"event-time:{sha256_obj(body)[:16]}"
        repo.add_step(step, run["id"], "event-time", "software:la.py")
        repo.add_frozen_many("event_time_assessments", [body], step)
        return {"ok": True, "new": True, **parsed}
    finally:
        repo.close()


# --- coverage ------------------------------------------------------------------------------

def _months(window: dict[str, str]) -> list[str] | None:
    try:
        a, b = date.fromisoformat(window["from"]), date.fromisoformat(window["to"])
    except (KeyError, ValueError):
        return None
    out, y, m = [], a.year, a.month
    while (y, m) <= (b.year, b.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def coverage_report(case_dir: Path | str) -> dict[str, Any]:
    """Documents and periods without in-scope observations, plus the exclusion log."""
    from .proposals import load_profile
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        reader = repo.reader()
        observations = reader.approved_rows("observations")
        claims = {c["id"]: c for c in reader.approved_rows("claims")}
        passages = {p["id"]: p for p, _ in repo.frozen_bodies("passages")}
        docs = {d["id"]: d for d, _ in repo.frozen_bodies("documents")}
        original = {i: (d.get("derived_from") or i) for i, d in docs.items()}
        in_scope = [o for o in observations if o["in_scope"]]
        covered = set()
        for o in in_scope:
            for cid in o["claim_ids"]:
                c = claims.get(cid)
                if c and c["passage_id"] in passages:
                    covered.add(original[passages[c["passage_id"]]["document_id"]])
        originals = sorted(i for i, d in docs.items() if d["kind"] == "original")
        times = current_event_times(repo)
        months = _months(profile["time_window"])
        uncovered_months, untimed = [], sorted(o["id"] for o in in_scope if o["id"] not in times)
        if months is not None:
            hit: set[str] = set()
            for o in in_scope:
                t = times.get(o["id"])
                lo, hi = (_bound(t.get("earliest"), False), _bound(t.get("latest"), True)) if t else (None, None)
                if lo and hi:
                    y, m = lo[0].year, lo[0].month
                    while (y, m) <= (hi[0].year, hi[0].month):
                        hit.add(f"{y:04d}-{m:02d}")
                        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
            uncovered_months = [m for m in months if m not in hit]
        return {"ok": True, "documents_without_observations": [d for d in originals if d not in covered],
                "periods_without_observations": uncovered_months if months is not None else None,
                "period_note": None if months is not None else "time_window is not ISO; periods cannot be computed",
                "observations_without_event_time": untimed,
                "exclusion_log": [{"observation_id": o["id"], "reason": o.get("exclusion_reason")}
                                  for o in observations if not o["in_scope"]]}
    finally:
        repo.close()
