"""Human review (R8/R9): triage, class-II sampling, export/import and render gates.

The only road from a proposal to the approved set. The evidence class is derived
from the channel (a review file inside a directory that `doctor` observed to deny
writes, re-probed at import), never from a field in the file or from the agent's
say-so; `human_signed` is reserved for a verified P1 channel and is never produced.
Decision vocabulary (`approved`, `rejected`, `corrected`) is interim until T-ENUM.
A rejection or correction inside a class-II sample counts as a correction and sends
the rest of that batch to class I. Time between export and import is a signal, not
proof: it overstates time spent on breaks.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from . import claims as claims_mod
from . import facts, guards, proposals, review_history
from .doctor import probe_review_dir
from .repository import SCHEMA_DIR, Repository
from .review_budget import DEFAULT_SECONDS_PER_ITEM, sample_size
from .runtime import EXIT_INTEGRITY, EXIT_POLICY, EXIT_USAGE, LaError, atomic_write, canonical_json, sha256_hex, sha256_obj
from .validation import load_registry

DECISIONS = ("approved", "rejected", "corrected")
ADMITTING = frozenset({"approved", "corrected"})
HUMAN_FILE, VIA_AGENT = "human_file", "human_via_agent"
UNSUPPORTED_TASKS = frozenset({"event_time"})  # approved by LA-013, not here
PACE_THRESHOLD_S = 10
BULK_SHARE_PERCENT = 50
FLAG_CLASS_I = {"guard_mismatch", "forbidden_booster", "ocr_flagged"}
PROSE_FIELDS = ("mechanism", "proposition", "reason", "question", "statement")


def _err(code: str, en: str, pl: str, exit_code: int = EXIT_USAGE, **ids: str) -> LaError:
    return LaError(code, en, pl, exit_code, ids or None)


# --- triage -------------------------------------------------------------------------

def _prose_booster(item: dict[str, Any]) -> bool:
    texts = [item.get(f) for f in PROSE_FIELDS if isinstance(item.get(f), str)]
    texts += [a.get("statement", "") for a in item.get("assumptions", []) if isinstance(a, dict)]
    return any(guards.find_boosters(t) for t in texts)


def classify(task: str, item: dict[str, Any], passage_flags: dict[str, list[str]], distinguishing_obs: set[str],
             incomplete_obs: set[str] | None = None) -> str:
    """'I' (individual decision) or 'II' (bulk with sample); unknown task kinds are conservatively 'I'."""
    if _prose_booster(item):
        return "I"
    if task == "claims":
        flagged = FLAG_CLASS_I & set(item.get("guard_flags", [])) or passage_flags.get(item["passage_id"])
        return "I" if flagged else "II"
    if task == "matrix":
        incomplete_obs = incomplete_obs or set()
        return "I" if item["observation_id"] in distinguishing_obs | incomplete_obs else "II"
    return "I"  # hypotheses, altcause (bridge rules, intent, persons), tests and anything unknown


def _distinguishing(rows: list[tuple[str, str]]) -> set[str]:
    by: dict[str, dict[str, set[str]]] = {}
    for obs, rel_h in rows:
        h, rel = rel_h.split("\x00")
        by.setdefault(obs, {}).setdefault(h, set()).add(rel)
    return {o for o, hs in by.items() if len(hs) > 1 and len({r for rels in hs.values() for r in rels}) > 1}


# --- pending items and export ----------------------------------------------------------

def _pending(repo: Repository) -> list[dict[str, Any]]:
    reviewed = {r["item_id"] for r in repo.review_rows()}
    state = repo.proposal_state()
    out = []
    for pid, task, payload in repo.proposals_rows():
        if state.get(pid) not in ("pending", "partially_reviewed") or task in UNSUPPORTED_TASKS:
            continue
        for i, it in enumerate(payload.get("items", [])):
            iid = f"{pid}#{i}"
            if iid not in reviewed:
                out.append({"item_id": iid, "proposal_id": pid, "task_type": task, "item": it,
                            "item_hash": sha256_obj({"task": task, "item": it})})
    return out


def _context(repo: Repository, pending: list[dict[str, Any]]) -> tuple[dict[str, list[str]], dict[str, str], set[str], set[str]]:
    flags = {p["id"]: p["quality_flags"] for p, _ in repo.frozen_bodies("passages")}
    text = {p["id"]: p for p, _ in repo.frozen_bodies("passages")}
    rows = [(a["observation_id"], f"{a['hypothesis_id']}\x00{a['relation']}") for a in repo.reader().current_assessments()]
    rows += [(p["item"]["observation_id"], f"{p['item']['hypothesis_id']}\x00{p['item']['relation']}")
             for p in pending if p["task_type"] == "matrix"]
    approved = repo.reader().approved_rows("hypotheses")
    sets = repo.reader().approved_rows("observation_sets")
    expected: dict[str, set[tuple[str, str]]] = {}
    state = facts.states(repo.reader())
    for obs_set in sets:
        scope_hypotheses = {h["id"] for h in approved if h["scope_id"] == obs_set["id"]}
        for observation_id in facts.effective_observation_ids(repo.reader(), obs_set, state):
            expected.setdefault(observation_id, set()).update((observation_id, hid) for hid in scope_hypotheses)
    present = {(a["observation_id"], a["hypothesis_id"]) for a in repo.reader().current_assessments()}
    present.update((p["item"]["observation_id"], p["item"]["hypothesis_id"])
                   for p in pending if p["task_type"] == "matrix")
    incomplete = {obs for obs, pairs in expected.items() if pairs - present}
    return flags, text, _distinguishing(rows), incomplete


def _preview(task: str, item: dict[str, Any], passages: dict[str, Any]) -> dict[str, Any]:
    ids = [item["passage_id"]] if task == "claims" else item.get("basis_passage_ids", [])
    if task == "tests":
        ids = item.get("document", {}).get("basis_passage_ids", [])
    src = [{"passage_id": i, "locator": passages[i]["locator"], "text": passages[i]["text"][:300]}
           for i in ids if i in passages]
    out: dict[str, Any] = {"sources": src}
    if task == "claims":
        out["quote"] = item["quote"]
    if task == "tests":
        # A test reviewer needs the complete basis, not a potentially misleading prefix.
        out["sources"] = [{"passage_id": i, "document_id": passages[i]["document_id"],
                           "locator": passages[i]["locator"], "text": passages[i]["text"],
                           "text_sha256": passages[i]["text_sha256"]} for i in ids if i in passages]
    return out


def build_export(repo: Repository) -> dict[str, Any]:
    pending = _pending(repo)
    flags, passages, dist, incomplete = _context(repo, pending)
    markers = {b["item_id"] for b, _ in repo.frozen_bodies("value_records") if b.get("kind") == "item_class_I"}
    rows = []
    for p in pending:
        triage = "I" if p["item_id"] in markers else classify(p["task_type"], p["item"], flags, dist,
                                      incomplete)
        rows.append({**p, "triage": triage})
    batches: dict[str, dict[str, Any]] = {}
    by_task: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r["triage"] == "II":
            by_task.setdefault(r["task_type"], []).append(r)
    for task, items in sorted(by_task.items()):
        ids = sorted(i["item_id"] for i in items)
        bid = sha256_obj([task, ids])[:16]
        k = sample_size(len(ids))
        order = sorted(ids, key=lambda i: sha256_hex(f"{bid}:{i}".encode("utf-8")))
        batches[bid] = {"batch_id": bid, "task_type": task, "size": len(ids), "sample_size": k, "sample_ids": sorted(order[:k]),
                        "item_ids": ids}
    where = {i: b["batch_id"] for b in batches.values() for i in b["item_ids"]}
    sampled = {i for b in batches.values() for i in b["sample_ids"]}
    items = [{"item_id": r["item_id"], "task_type": r["task_type"], "triage": r["triage"],
              "batch_id": where.get(r["item_id"], "class-I"), "sampled": r["item_id"] in sampled,
              "item_hash": r["item_hash"], "proposed": r["item"], "source": _preview(r["task_type"], r["item"], passages),
              "decision": None, "reason": "", "mode": "individual", "corrected_item": None,
              "reconsiders_review_id": None} for r in rows]
    manifest = {"items": [{k: i[k] for k in ("item_id", "task_type", "triage", "batch_id", "sampled", "item_hash")}
                          for i in items],
                "batches": list(batches.values())}
    export_id = sha256_obj(manifest)[:16]
    return {"format": 1, "export_id": export_id, "case_id": repo.case_id, "reviewer": "", "items": items,
            "batches": list(batches.values()), "manifest": manifest,
            "review_history": review_history.read(repo.reader())}


def export_review(case_dir: Path | str, out: Path | str | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    profile = proposals.load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        rd = repo.reader()
        rd.assert_chain_ok()
        history_step = "review-history:" + sha256_obj([rd.runs()[-1]["id"], [r["id"] for r in repo.review_rows()]])[:20]
        with repo.transaction():
            repo.add_step(history_step, rd.runs()[-1]["id"], "review-history", "none")
            review_history.capture(repo, history_step)
        doc = build_export(repo)
        manifest = doc.pop("manifest")
        run = repo.reader().runs()[-1]
        step = f"review-export:{doc['export_id']}"
        if not any(s["id"] == step for s in repo.list_steps()):
            repo.add_step(step, run["id"], "review-export", "none")
        existing = {b["id"] for b, _ in repo.frozen_bodies("value_records")}
        recs = []
        if f"export:{doc['export_id']}" not in existing:
            recs.append({"id": f"export:{doc['export_id']}", "kind": "export", **manifest})
        if f"exportat:{doc['export_id']}" not in existing:
            recs.append({"id": f"exportat:{doc['export_id']}", "kind": "export_time", "exported_at": time.time()})
        repo.add_frozen_many("value_records", recs, step)
    finally:
        repo.close()
    data = canonical_json(doc) + b"\n"
    if out is None:
        atomic_write(root, f"review/export-{doc['export_id']}.json", data)
        path = str(root / "review" / f"export-{doc['export_id']}.json")
    else:
        target = Path(out)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(target, "xb") as fh:  # never overwrite an existing file
                fh.write(data)
        except FileExistsError as e:
            raise _err("E_OUT_EXISTS", "The output file already exists; it is never overwritten.",
                       "Plik wyjściowy już istnieje; nigdy nie jest nadpisywany.") from e
        path = str(out)
    classes = [i["triage"] for i in doc["items"]]
    return {"ok": True, "export_id": doc["export_id"], "path": path, "items": len(classes),
            "rejection_history_count": len(doc["review_history"]["rejections"]),
            "rejection_history_complete": doc["review_history"]["complete"],
            "class_I": classes.count("I"), "class_II": classes.count("II"),
            "batches": [{k: b[k] for k in ("batch_id", "task_type", "size", "sample_size")} for b in doc["batches"]]}


# --- evidence channel --------------------------------------------------------------------

def evidence_class_for(case_dir: Path | str, file_path: Path | str) -> str:
    cap = Path(case_dir) / "capabilities.json"
    if not cap.exists():
        return VIA_AGENT
    try:
        rd = json.loads(cap.read_text(encoding="utf-8")).get("review_dir", {})
    except (OSError, ValueError):
        return VIA_AGENT
    if not (rd.get("status") == "observed" and rd.get("result") == "read_only_confirmed" and rd.get("path")):
        return VIA_AGENT
    directory = Path(rd["path"]).resolve()
    f = Path(file_path).resolve()
    if directory != f.parent and directory not in f.parents:
        return VIA_AGENT
    again = probe_review_dir(directory)  # the denial must still hold at import time
    return HUMAN_FILE if again.get("result") == "read_only_confirmed" else VIA_AGENT


# --- records ---------------------------------------------------------------------------------

def _supersedes(repo: Repository, observation_id: str, hypothesis_id: str) -> str | None:
    r = repo.conn.execute(
        "SELECT a.id FROM assessments a WHERE a.case_id = ? AND a.observation_id = ? AND a.hypothesis_id = ?"
        " AND NOT EXISTS (SELECT 1 FROM assessments b WHERE b.case_id = a.case_id AND b.supersedes = a.id)",
        (repo.case_id, observation_id, hypothesis_id)).fetchone()
    return r[0] if r else None


def records_for(repo: Repository, task: str, item: dict[str, Any], pid: str, idx: int) -> list[tuple[str, dict[str, Any]]]:
    cid = repo.case_id
    base = sha256_obj({"p": pid, "i": idx, "item": item})[:16]
    if task == "claims":
        body = {k: item[k] for k in ("passage_id", "speaker", "speaker_role", "proposition", "polarity", "modality", "quote",
                                     "start", "end", "epistemic_status", "source_lang")}
        return [("claims", {"case_id": cid, "id": f"clm:{base}", **body, "guard_flags": item.get("guard_flags", [])})]
    if task in ("hypotheses", "altcause"):
        hid = f"hyp:{base}"
        out: list[tuple[str, dict[str, Any]]] = [("hypotheses", {
            "case_id": cid, "id": hid, **{k: item[k] for k in ("mechanism", "scope_id", "kind", "burdens",
                                                                 "attributes_intent", "concerns_natural_person")},
            "status": "hypothesis"})]
        for n, a in enumerate(item.get("assumptions", []), 1):
            out.append(("assumptions", {"case_id": cid, "id": f"asm:{base}-{n}", **a}))
        return out
    if task == "matrix":
        rec = {"case_id": cid, "id": f"ass:{base}", **{k: item[k] for k in (
            "observation_id", "hypothesis_id", "relation", "reason", "basis_passage_ids")}}
        head = _supersedes(repo, item["observation_id"], item["hypothesis_id"])
        if head:
            rec["supersedes"] = head
        return [("assessments", rec)]
    if task == "tests":
        return [("tests", {"case_id": cid, "id": f"tst:{base}", **{k: item[k] for k in (
            "question", "outcomes", "uninformative_outcome", "access_basis",
            "scope_id", "uncertainty", "document", "next_step")}})]
    raise _err("E_UNSUPPORTED_TASK", "This task type cannot be approved here.", "Tego typu zadania nie można tu zatwierdzić.")


# --- import ------------------------------------------------------------------------------------

def _load_manifest(repo: Repository, export_id: str) -> dict[str, Any]:
    for b, _ in repo.frozen_bodies("value_records"):
        if b["id"] == f"export:{export_id}":
            return b
    raise _err("E_REVIEW_UNKNOWN_EXPORT", "This review file was not exported by this case.",
               "Ten plik recenzji nie pochodzi z eksportu tej sprawy.")


def import_review(case_dir: Path | str, file_path: Path | str) -> dict[str, Any]:
    root = Path(case_dir)
    raw = Path(file_path).read_bytes()
    sha = sha256_hex(raw)
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise _err("E_REVIEW_FILE", "Review file is not valid JSON.", "Plik recenzji nie jest poprawnym JSON.") from e
    profile = proposals.load_profile(root)
    if not isinstance(doc, dict) or doc.get("case_id") != profile["case_id"] or not isinstance(doc.get("items"), list):
        raise _err("E_REVIEW_FILE", "Review file does not belong to this case.", "Plik recenzji nie należy do tej sprawy.")
    evidence = evidence_class_for(root, file_path)  # fields in the file can never raise this
    reviewer = str(doc.get("reviewer") or "").strip()
    repo = Repository(root / "case.db", profile["case_id"], admitting_decisions=ADMITTING)
    try:
        if any(b["id"] == f"reviewfile:{sha}" for b, _ in repo.frozen_bodies("value_records")):
            return {"ok": True, "already_imported": True, "file_sha256": sha, "evidence_class": evidence}
        manifest = _load_manifest(repo, str(doc.get("export_id")))
        m_items = {i["item_id"]: i for i in manifest["items"]}
        m_batches = {b["batch_id"]: b for b in manifest["batches"]}
        pending = {p["item_id"]: p for p in _pending(repo)}
        reviews = repo.review_rows()
        prior_reviews = {r["id"]: r for r in reviews}
        proposal_tasks = {pid: task for pid, task, _ in repo.proposals_rows()}
        done = {r["item_id"]: r for r in reviews}
        reverted = {b["item_id"] for b, _ in repo.frozen_bodies("value_records") if b.get("kind") == "item_class_I"}
        decided = [d for d in doc["items"] if isinstance(d, dict) and d.get("decision") is not None]
        if decided and not reviewer:
            raise _err("E_REVIEW_REVIEWER", "The review file must name the reviewer.", "Plik recenzji musi wskazywać recenzenta.")
        seen: set[str] = set()
        plan: list[dict[str, Any]] = []
        registry = load_registry(SCHEMA_DIR)
        for d in decided:
            iid = d.get("item_id")
            if iid not in m_items or iid in seen:
                raise _err("E_REVIEW_UNKNOWN_ITEM", "A decision refers to an unknown or repeated item.",
                           "Decyzja dotyczy nieznanej lub powtórzonej pozycji.")
            seen.add(iid)
            mi = m_items[iid]
            if iid in done:
                if done[iid]["decision"] == d["decision"]:
                    continue  # repeated identical decision: idempotent
                raise _err("E_REVIEW_STALE", "The item was already decided differently.", "Pozycja została już rozstrzygnięta inaczej.")
            if iid not in pending or pending[iid]["item_hash"] != mi["item_hash"]:
                raise _err("E_REVIEW_STALE", "The proposal changed since the export; export again.",
                           "Propozycja zmieniła się od eksportu; wyeksportuj ponownie.", EXIT_USAGE, item_id=iid)
            if d["decision"] not in DECISIONS:
                raise _err("E_REVIEW_DECISION", "Unknown decision value.", "Nieznana wartość decyzji.")
            if d["decision"] != "approved" and not str(d.get("reason") or "").strip():
                raise _err("E_REVIEW_REASON", "Rejections and corrections need a reason.",
                           "Odrzucenie i korekta wymagają uzasadnienia.")
            previous_id = d.get("reconsiders_review_id")
            if previous_id is not None:
                previous = prior_reviews.get(previous_id) if isinstance(previous_id, str) else None
                if (previous is None or previous["decision"] != "rejected" or previous["item_id"] == iid
                        or proposal_tasks.get(previous["item_id"].rsplit("#", 1)[0]) != mi["task_type"]):
                    raise _err("E_REVIEW_RECONSIDERS", "Reconsideration needs an earlier rejection of another item of this task.",
                               "Ponowna ocena wymaga wcześniejszego odrzucenia innej pozycji tego typu.")
                if not str(d.get("reason") or "").strip():
                    raise _err("E_REVIEW_REASON", "Reconsideration needs a human reason.",
                               "Ponowna ocena wymaga uzasadnienia człowieka.")
            triage = "I" if iid in reverted else mi["triage"]
            mode = "bulk" if d.get("mode") == "bulk" else "individual"
            if mode == "bulk" and triage == "I":
                raise _err("E_BULK_CLASS_I", "Class I items cannot be approved in bulk.",
                           "Pozycji klasy I nie można zatwierdzić hurtowo.", EXIT_POLICY, item_id=iid)
            if mode == "bulk" and mi["sampled"]:
                raise _err("E_SAMPLE_INDIVIDUAL", "Sampled items need an individual decision.",
                           "Pozycje z próby wymagają decyzji indywidualnej.", EXIT_POLICY, item_id=iid)
            plan.append({"d": d, "mi": mi, "triage": triage, "mode": mode, "pend": pending[iid]})
        # sample completeness and batch reversion
        by_id = {p["mi"]["item_id"]: p for p in plan}
        batches_bulk = {p["mi"]["batch_id"] for p in plan if p["mode"] == "bulk" and p["triage"] == "II"}
        reverted_now: set[str] = set()
        for bid in sorted(batches_bulk):
            b = m_batches[bid]
            for sid in b["sample_ids"]:
                prior = done.get(sid)
                ok_prior = prior is not None and prior.get("mode") == "individual"
                if sid not in by_id and not ok_prior:
                    raise _err("E_SAMPLE_INCOMPLETE", "A class II batch needs its full sample decided individually.",
                               "Partia klasy II wymaga kompletnej próby rozstrzygniętej indywidualnie.", EXIT_POLICY,
                               batch_id=bid)
        for b in m_batches.values():
            corrected = [s for s in b["sample_ids"] if s in by_id and by_id[s]["d"]["decision"] in ("rejected", "corrected")]
            corrected += [s for s in b["sample_ids"] if s in done and done[s]["decision"] in ("rejected", "corrected")]
            if corrected:
                for iid in b["item_ids"]:
                    if iid in by_id and by_id[iid]["mode"] == "bulk":
                        raise _err("E_BULK_CLASS_I", "A correction in the sample returned the batch to class I.",
                                   "Korekta w próbie cofnęła partię do klasy I.", EXIT_POLICY, batch_id=b["batch_id"])
                    if iid not in by_id and iid not in done and iid in pending:
                        reverted_now.add(iid)
        # build records
        built = []
        for p in plan:
            d, mi = p["d"], p["mi"]
            task, item = mi["task_type"], p["pend"]["item"]
            if task == "tests" and d["decision"] == "approved":
                code = proposals.validate_payload(task, {"items": [item]}, proposals._known(repo, profile), registry)
                if code:
                    raise _err("E_REVIEW_TEST_INVALID", "The test needs a current valid document/action contract.",
                               "Test wymaga aktualnego kontraktu dokumentu i działania.", EXIT_USAGE, reason=code)
            if d["decision"] == "corrected":
                item = d.get("corrected_item")
                if not isinstance(item, dict):
                    raise _err("E_REVIEW_DECISION", "A correction needs corrected_item.", "Korekta wymaga corrected_item.")
                known = proposals._known(repo, profile)
                code = proposals.validate_payload(task, {"items": [item]}, known, registry)
                if code is None and task == "matrix":
                    from . import matrix as matrix_mod
                    original = p["pend"]["item"]
                    if (item.get("observation_id"), item.get("hypothesis_id")) != (
                            original.get("observation_id"), original.get("hypothesis_id")):
                        code = "E_MATRIX_PAIR_IMMUTABLE"
                    else:
                        code = matrix_mod.basis_error(repo, item["observation_id"], item["basis_passage_ids"])
                if code is None and task == "claims":
                    enriched, code = claims_mod._enrich(task, {"items": [item]}, known)
                    item = enriched["items"][0] if code is None else item
                if code:
                    raise _err("E_REVIEW_CORRECTION_INVALID", "The corrected item failed technical validation.",
                               "Skorygowana pozycja nie przeszła walidacji technicznej.", EXIT_USAGE, reason=code)
            built.append((p, item))
        now = time.time()
        with repo.transaction():
            run = repo.reader().runs()[-1]
            step = f"review-import:{sha[:16]}"
            repo.add_step(step, run["id"], "review-import", "none")
            for p, item in built:
                d, mi, pend = p["d"], p["mi"], p["pend"]
                review = {"case_id": profile["case_id"], "id": f"rev:{sha256_obj([mi['item_id'], sha])[:20]}",
                          "item_id": mi["item_id"], "decision": d["decision"], "reviewer": reviewer,
                          "evidence_class": evidence, "review_file_sha256": sha, "batch_id": mi["batch_id"],
                          "sampled": bool(mi["sampled"]), "reason": str(d.get("reason") or "-"), "triage": p["triage"],
                          "mode": p["mode"], "item_hash": mi["item_hash"]}
                if d.get("reconsiders_review_id") is not None:
                    review["reconsiders_review_id"] = d["reconsiders_review_id"]
                idx = int(mi["item_id"].rsplit("#", 1)[1])
                if d["decision"] in ADMITTING:
                    for table, rec in records_for(repo, mi["task_type"], item, pend["proposal_id"], idx):
                        repo.approve(pend["proposal_id"], review, table, rec, step)
                else:
                    repo.record_review(review, step)
            extra = [{"id": f"itemclass:{i}", "kind": "item_class_I", "item_id": i, "reason": "sample_correction"}
                     for i in sorted(reverted_now)]
            first = next((b for b, _ in repo.frozen_bodies("value_records") if b["id"] == f"exportat:{doc['export_id']}"), None)
            class_i = sum(1 for p, _ in built if p["triage"] == "I")
            extra.append({"id": f"reviewfile:{sha}", "kind": "review_file", "sha256": sha, "file_path": str(file_path),
                          "export_id": doc["export_id"], "evidence_class": evidence, "decisions": len(built),
                          "class_I_decisions": class_i, "imported_at": now,
                          "exported_at": first["exported_at"] if first else now})
            repo.add_frozen_many("value_records", extra, step)
            review_history.capture(repo, step)
        return {"ok": True, "already_imported": False, "file_sha256": sha, "evidence_class": evidence,
                "decisions": len(built), "approved": sum(1 for p, _ in built if p["d"]["decision"] in ADMITTING),
                "rejected": sum(1 for p, _ in built if p["d"]["decision"] == "rejected"),
                "reverted_to_class_I": sorted(reverted_now)}
    finally:
        repo.close()


# --- gates and metrics --------------------------------------------------------------------------------

def _facts(case_dir: Path | str) -> dict[str, Any]:
    root = Path(case_dir)
    profile = proposals.load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        reviews = repo.review_rows()
        approved = [r for r in reviews if r["decision"] in ADMITTING]
        vr = [b for b, _ in repo.frozen_bodies("value_records")]
        manifests = [b for b in vr if b.get("kind") == "export"]
        files = [b for b in vr if b.get("kind") == "review_file"]
        indiv = {r["item_id"] for r in reviews if r.get("mode") == "individual"}
        bulk_ok = [r for r in approved if r.get("mode") == "bulk"]
        bad_batches = []
        for m in manifests:
            for b in m["batches"]:
                if any(r["batch_id"] == b["batch_id"] for r in bulk_ok) and not all(s in indiv for s in b["sample_ids"]):
                    bad_batches.append(b["batch_id"])
        pending = len(_pending(repo))
        reviewed_ids = {r["item_id"] for r in reviews}
        pending += sum(1 for pid, task, payload in repo.proposals_rows() if task in UNSUPPORTED_TASKS
                       for i in range(len(payload.get("items", []))) if f"{pid}#{i}" not in reviewed_ids)
        changes = [b for b in vr if b.get("kind") == facts.KIND and b.get("evidence_class") == VIA_AGENT]
        return {"reviews": reviews, "approved": approved, "bulk_approved": bulk_ok, "files": files, "manifests": manifests,
                "fact_changes": changes,
                "bad_batches": sorted(set(bad_batches)), "pending": pending, "chain": repo.reader().verify(),
                "class_i_bulk": [r for r in bulk_ok if r.get("triage") == "I"]}
    finally:
        repo.close()


def evaluate_gates(case_dir: Path | str, profile_name: str) -> dict[str, Any]:
    """Render gates of the PRD table for `working` or `exhibit`."""
    if profile_name not in ("working", "exhibit"):
        raise _err("E_UNKNOWN_PROFILE", "Report profile must be working or exhibit.", "Profil raportu: working lub exhibit.")
    f = _facts(case_dir)
    ex = profile_name == "exhibit"
    out: list[dict[str, Any]] = []

    def add(gate: str, outcome: str, **detail: Any) -> None:
        out.append({"gate": gate, "outcome": outcome, **detail})
    if f["class_i_bulk"]:
        add("class_I_bulk_approved", "block", count=len(f["class_i_bulk"]))
    if f["bad_batches"]:
        add("class_II_batch_incomplete_sample", "block", batches=f["bad_batches"])
    if f["pending"]:
        add("pending_review", "block" if ex else "partial_label", count=f["pending"])
    total = len(f["approved"])
    via = sum(1 for r in f["approved"] if r["evidence_class"] == VIA_AGENT)
    if via:
        add("human_via_agent_basis", "block" if ex else "warn", count=via, percent=round(100 * via / total, 1))
    if total and len(f["bulk_approved"]) * 100 > BULK_SHARE_PERCENT * total:
        add("bulk_share_over_50_percent", "warn_and_declaration_required" if ex else "warn",
            percent=round(100 * len(f["bulk_approved"]) / total, 1))
    for fl in f["files"]:
        n = fl["class_I_decisions"]
        if n and (fl["imported_at"] - fl["exported_at"]) / n < PACE_THRESHOLD_S:
            add("pace_under_10s_per_class_I_item", "block_until_rereview" if ex else "warn_possible_superficial_review",
                file=fl["sha256"], seconds_per_item=round((fl["imported_at"] - fl["exported_at"]) / n, 2))
    if not f["chain"].ok:
        add("hash_chain_broken", "block", first_broken_id=f["chain"].first_broken_id)
    if f["fact_changes"]:  # withdraw/change/reinstate are agent commands (human_via_agent), never reviewed files
        add("fact_change_via_agent", "block" if ex else "warn", count=len(f["fact_changes"]),
            fact_ids=sorted({c["fact_id"] for c in f["fact_changes"]}))
    from . import hypotheses as hyp_mod
    out += hyp_mod.gate_findings(case_dir, ex)
    blocked = any(o["outcome"].startswith("block") for o in out)
    return {"ok": True, "profile": profile_name, "blocked": blocked, "findings": out}


def review_metrics(case_dir: Path | str) -> dict[str, Any]:
    f = _facts(case_dir)
    sampled = [r for r in f["reviews"] if r.get("sampled")]
    corrections = [r for r in sampled if r["decision"] in ("rejected", "corrected")]
    actual_s = sum(fl["imported_at"] - fl["exported_at"] for fl in f["files"])
    predicted_items = max((sum(1 for i in m["items"] if i["triage"] == "I") + sum(b["sample_size"] for b in m["batches"])
                           for m in f["manifests"]), default=0)
    classes: dict[str, int] = {}
    for r in f["reviews"]:
        classes[r["evidence_class"]] = classes.get(r["evidence_class"], 0) + 1
    total = len(f["approved"])
    cls_i = sum(fl["class_I_decisions"] for fl in f["files"])
    return {"ok": True, "predicted_minutes": predicted_items * DEFAULT_SECONDS_PER_ITEM / 60, "actual_minutes": actual_s / 60,
            "bulk_share": (len(f["bulk_approved"]) / total) if total else None,
            "sample_correction_rate": (len(corrections) / len(sampled)) if sampled else None,
            "evidence_class_counts": dict(sorted(classes.items())),
            "seconds_per_class_I_item": (actual_s / cls_i) if cls_i else None,
            "note": "Export-to-import time is a signal, not proof of review quality; it includes breaks."}
