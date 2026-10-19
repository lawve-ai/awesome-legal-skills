"""Changed and withdrawn facts and the effective scope of an analysis (R16 extension).

A *fact* here is an approved claim (`clm:`) or observation (`obs:`). `update withdraw`,
`update change` and `update reinstate` append a `fact_change` value record; nothing approved is
edited or deleted. The latest record per fact decides its state:

withdrawn   the fact no longer belongs to the current basis
changed     the fact is replaced by `replacement_id` (an approved record of the same type)
reinstated  an earlier withdrawal/change is undone; the fact is current again

The *effective* observations of a scope are the ObservationSet members without withdrawn or
changed observations, plus the replacements of changed ones (chains resolved). matrix, compare,
uncovered, review triage, hypothesis packets and the report read scopes through
`effective_observation_ids`: a replacement yields `not_assessed` pairs instead of vanishing, and a
withdrawn observation's cells stop counting (they are *void*, not stale).

Recording a change runs a precise invalidation rooted at the fact (staleness.invalidate with
`impact="standing"`): explanations whose current cell on the fact is `supports`/`conflicts` and
observations citing a withdrawn claim are flagged for renewed review; neutral cells, unrelated
hypotheses and the rest of the matrix are not. Changes are agent commands: the record carries
`recorded_by: agent_command` and evidence class `human_via_agent`, which the exhibit gate blocks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .profile import load_profile
from .repository import ReadRepository, Repository
from .runtime import EXIT_USAGE, LaError, sha256_obj

KIND = "fact_change"
CHANGES = ("withdrawn", "changed", "reinstated")
EXCLUDING = ("withdrawn", "changed")
FACT_TABLES = {"clm": "claims", "obs": "observations"}
VIA_AGENT = "human_via_agent"


def _err(code: str, en: str, pl: str, ids: dict[str, str] | None = None) -> LaError:
    return LaError(code, en, pl, EXIT_USAGE, ids)


def fact_changes(rd: ReadRepository) -> list[dict[str, Any]]:
    """All fact_change records in recording order (ids are `fct:<seq>-<hash>`)."""
    return sorted((r for r in rd.frozen_rows("value_records") if r.get("kind") == KIND), key=lambda r: r["seq"])


def states(rd: ReadRepository) -> dict[str, dict[str, Any]]:
    """fact id -> latest change record, only for facts currently withdrawn or changed."""
    latest: dict[str, dict[str, Any]] = {}
    for r in fact_changes(rd):
        latest[r["fact_id"]] = r
    return {k: v for k, v in sorted(latest.items()) if v["change"] in EXCLUDING}


def excluded_ids(rd: ReadRepository) -> set[str]:
    return set(states(rd))


def resolve(state: dict[str, dict[str, Any]], fact_id: str) -> str | None:
    """Current stand-in for a fact: itself, its (transitive) replacement, or None when withdrawn."""
    seen: set[str] = set()
    cur: str | None = fact_id
    while cur is not None and cur in state and cur not in seen:
        seen.add(cur)
        rec = state[cur]
        cur = rec.get("replacement_id") if rec["change"] == "changed" else None
    return None if cur in seen else cur


def effective_observation_ids(rd: ReadRepository, obs_set: dict[str, Any],
                              state: dict[str, dict[str, Any]] | None = None) -> list[str]:
    state = states(rd) if state is None else state
    out = {resolve(state, o) for o in obs_set["observation_ids"]}
    return sorted(o for o in out if o is not None)


def scope_changes(rd: ReadRepository, obs_set: dict[str, Any],
                  state: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Excluded members of a scope with the change that removed them and their current stand-in."""
    state = states(rd) if state is None else state
    out = []
    for o in sorted(obs_set["observation_ids"]):
        if o in state:
            r = state[o]
            out.append({"observation_id": o, "change": r["change"], "replacement_id": resolve(state, o),
                        "reason": r["reason"], "event": r["id"], "recorded_by": r["recorded_by"],
                        "evidence_class": r["evidence_class"]})
    return out


def _approved_ids(rd: ReadRepository, prefix: str) -> set[str]:
    return {r["id"] for r in rd.approved_rows(FACT_TABLES[prefix])}


def record(case_dir: Path | str, fact_id: str, change: str, reason: str,
           replacement_id: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Append a fact_change record and flag what depends on the fact. Never edits an approved row.

    `dry_run` validates exactly like a real call, then reports what the change would flag and void
    without writing anything (no record, no edges, no invalidation).
    """
    from . import staleness
    root = Path(case_dir)
    reason = str(reason or "").strip()
    if change not in CHANGES:
        raise _err("E_FACT_CHANGE", "change must be withdrawn, changed or reinstated.",
                   "Zmiana musi być: withdrawn, changed albo reinstated.")
    if not reason:
        raise _err("E_FACT_REASON", "A reason is required for every fact change.",
                   "Każda zmiana faktu wymaga uzasadnienia.")
    prefix = str(fact_id).split(":", 1)[0]
    if prefix not in FACT_TABLES:
        raise _err("E_FACT_TYPE", "Only approved claims (clm:) and observations (obs:) can be withdrawn or changed.",
                   "Wycofać lub zmienić można tylko zatwierdzone twierdzenia (clm:) i obserwacje (obs:).",
                   {"id": str(fact_id)})
    profile = load_profile(root)
    repo = None if dry_run else Repository(root / "case.db", profile["case_id"])
    if repo is None:
        rd = ReadRepository(root / "case.db", profile["case_id"])
    else:
        staleness.ensure_edges(root)
        rd = repo.reader()
    try:
        if fact_id not in _approved_ids(rd, prefix):
            raise _err("E_UNKNOWN_ID", "The fact is not an approved record.", "Fakt nie jest zatwierdzonym rekordem.",
                       {"id": fact_id})
        state = states(rd)
        if change == "changed":
            if not replacement_id:
                raise _err("E_FACT_REPLACEMENT", "A changed fact needs --replacement.",
                           "Zmieniony fakt wymaga --replacement.", {"id": fact_id})
            if replacement_id == fact_id or str(replacement_id).split(":", 1)[0] != prefix \
                    or replacement_id not in _approved_ids(rd, prefix):
                raise _err("E_FACT_REPLACEMENT", "The replacement must be a different approved record of the same type.",
                           "Zamiennik musi być innym zatwierdzonym rekordem tego samego typu.", {"id": str(replacement_id)})
            if replacement_id in state or resolve({**state, fact_id: {"change": "changed",
                                                                       "replacement_id": replacement_id}}, fact_id) is None:
                raise _err("E_FACT_REPLACEMENT", "The replacement is itself withdrawn/changed or would form a cycle.",
                           "Zamiennik jest sam wycofany/zmieniony albo tworzy cykl.", {"id": str(replacement_id)})
        elif replacement_id:
            raise _err("E_FACT_REPLACEMENT", "--replacement is only valid with change.",
                       "--replacement dotyczy tylko change.")
        if change == "reinstated" and fact_id not in state:
            raise _err("E_FACT_NOT_CHANGED", "The fact is current; there is nothing to reinstate.",
                       "Fakt jest aktualny; nie ma czego przywracać.", {"id": fact_id})
        if change in EXCLUDING and fact_id in state:
            cur = state[fact_id]
            if cur["change"] == change and cur.get("replacement_id") == replacement_id and cur["reason"] == reason:
                return {"ok": True, "already_recorded": True, "event": cur["id"], "fact_id": fact_id,
                        **({"dry_run": True, "recorded": False} if dry_run else {})}
            if not (cur["change"] == "withdrawn" and change == "changed"):  # a withdrawn fact may get its replacement
                raise _err("E_FACT_ALREADY_CHANGED", "The fact is already withdrawn/changed; reinstate it first.",
                           "Fakt jest już wycofany/zmieniony; najpierw go przywróć.",
                           {"id": fact_id, "event": cur["id"]})
        if dry_run:
            return preview(rd, fact_id, change, replacement_id, reason, state)
        seq = len(fact_changes(rd)) + 1
        body = {"kind": KIND, "seq": seq, "fact_id": fact_id, "change": change, "replacement_id": replacement_id,
                "reason": reason, "recorded_by": "agent_command", "evidence_class": VIA_AGENT}
        rec = {"id": f"fct:{seq:04d}-{sha256_obj(body)[:12]}", **body}
        step = f"fact-change:{rec['id'].split(':', 1)[1]}"
        repo.add_step(step, rd.runs()[-1]["id"], "fact-change", "software:la.py")
        repo.add_frozen_many("value_records", [rec], step)
    finally:
        if repo is None:
            rd.close()
        else:
            repo.close()
    inv = staleness.invalidate(root, [fact_id], f"fact_{change}: {reason}", flag_roots=False,
                               impact="standing", cause=rec["id"])
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        void = void_assessments(rd) if change in EXCLUDING else []
    finally:
        rd.close()
    return {"ok": True, "event": rec["id"], "fact_id": fact_id, "change": change, "replacement_id": replacement_id,
            "evidence_class": VIA_AGENT, "flagged": inv["flagged"], "flagged_by_type": inv["flagged_by_type"],
            "voided_assessments": sorted(a["id"] for a in void if a["observation_id"] == fact_id),
            "next": "update revisit"}


def preview(rd: ReadRepository, fact_id: str, change: str, replacement_id: str | None, reason: str,
            state: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """What `record` would flag and void for this change, computed read-only (nothing is written)."""
    from . import staleness
    after = dict(state)
    if change in EXCLUDING:
        after[fact_id] = {"change": change, "replacement_id": replacement_id}
    else:
        after.pop(fact_id, None)
    cells = rd.current_assessments()
    void = set(after) | {a["id"] for a in cells if a["observation_id"] in after}
    reached = staleness.walk(rd, [fact_id], "standing", void=void)
    flagged = [i for i in reached if i != fact_id and i not in void]
    stale_now = set(staleness.stale_records(rd))
    by_type: dict[str, int] = {}
    for i in flagged:
        by_type[i.split(":", 1)[0]] = by_type.get(i.split(":", 1)[0], 0) + 1
    on_fact = sorted(a["id"] for a in cells if a["observation_id"] == fact_id)
    stand_in = resolve(after, fact_id) if change in EXCLUDING else fact_id
    pairs: list[dict[str, str]] = []
    if change in EXCLUDING and stand_in and stand_in != fact_id and stand_in.startswith("obs:"):
        have = {(a["observation_id"], a["hypothesis_id"]) for a in cells}
        scopes = [s for s in rd.approved_rows("observation_sets") if fact_id in s["observation_ids"]]
        hyps = rd.approved_rows("hypotheses")
        pairs = sorted(({"observation_id": stand_in, "hypothesis_id": h["id"]} for s in scopes for h in hyps
                        if h["scope_id"] == s["id"] and (stand_in, h["id"]) not in have),
                       key=lambda p: (p["hypothesis_id"], p["observation_id"]))
    return {"ok": True, "dry_run": True, "recorded": False, "fact_id": fact_id, "change": change,
            "replacement_id": replacement_id, "reason": reason, "evidence_class": VIA_AGENT,
            "would_flag": flagged, "would_flag_by_type": dict(sorted(by_type.items())),
            "details": {i: {"impact": reached[i]["impact"], "path": reached[i]["path"]} for i in flagged},
            "already_stale": sorted(i for i in flagged if i in stale_now),
            "would_void_assessments": on_fact if change in EXCLUDING else [],
            "would_restore_assessments": on_fact if change == "reinstated" else [],
            "pairs_to_assess": pairs,
            "next": "rerun without --dry-run to record it (the human states the change and the reason)"}


def void_assessments(rd: ReadRepository) -> list[dict[str, Any]]:
    """Current assessments whose observation is withdrawn or changed: no longer basis, never stale."""
    ex = excluded_ids(rd)
    return [a for a in rd.current_assessments() if a["observation_id"] in ex]
