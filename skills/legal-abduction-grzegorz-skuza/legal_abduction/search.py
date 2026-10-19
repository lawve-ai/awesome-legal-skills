"""Search log (R6): literal search over an explicit scope and the only source of `not_found`.

A SearchRecord stores query, variants, filters (including the explicit scope),
the corpus_hash it ran against, parser errors, known limits and hits, even for zero
hits. `not_found` exists only for a record of the *current* corpus with no hits and
no parser errors; an extraction error or a missing extraction is `inconclusive`,
never proof of absence. A stale or missing record blocks the report gate; there is
no text fallback. `rerun_stale` re-executes old empty searches after an update.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .repository import Repository
from .runtime import EXIT_POLICY, EXIT_USAGE, LaError, sha256_obj

LIMITS = ["literal_substring_only", "no_stemming_or_semantic_search"]


def current_corpus_hash(repo: Repository) -> str:
    """Sorted manifest of originals and derived documents, hashed (same formula as ingest)."""
    return sha256_obj(sorted((b for b, _ in repo.frozen_bodies("documents")), key=lambda d: d["id"]))


def record_id(body: dict[str, Any]) -> str:
    return sha256_obj(body)[:32]


def _bad(code: str, en: str, pl: str) -> LaError:
    return LaError(code, en, pl, EXIT_USAGE)


def state_of(record: dict[str, Any]) -> str:
    if record["hits"]:
        return "found"
    return "inconclusive" if record["parser_errors"] else "not_found"


def run_search(case_dir: Path | str, query: str, *, scope: Any, variants: list[str] | None = None,
               case_sensitive: bool = True) -> dict[str, Any]:
    from .proposals import load_profile
    root = Path(case_dir)
    profile = load_profile(root)
    if not isinstance(query, str) or not query.strip():
        raise _bad("E_SEARCH_QUERY", "The query must be non-empty.", "Zapytanie nie może być puste.")
    if scope != "all" and not (isinstance(scope, list) and scope and all(isinstance(s, str) for s in scope)):
        raise _bad("E_SEARCH_SCOPE", "The scope must be explicit: 'all' or a list of document ids.",
                   "Zakres musi być jawny: 'all' albo lista identyfikatorów dokumentów.")
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        docs = {d["id"]: d for d, _ in repo.frozen_bodies("documents")}
        ids = sorted(docs) if scope == "all" else sorted(set(scope))
        if any(i not in docs for i in ids):
            raise _bad("E_SEARCH_SCOPE", "The scope names an unknown document.", "Zakres wskazuje nieznany dokument.")
        in_scope = set(ids)
        passages = [p for p, _ in repo.frozen_bodies("passages") if p["document_id"] in in_scope]
        terms = [query, *(variants or [])]
        fold = (lambda s: s) if case_sensitive else (lambda s: s.casefold())
        hits, detail = set(), []
        for p in passages:
            text = fold(p["text"])
            for term in terms:
                t, start = fold(term), 0
                while t and (pos := text.find(t, start)) != -1:
                    hits.add(p["id"])
                    detail.append({"passage_id": p["id"], "start": pos, "end": pos + len(t), "term": term})
                    start = pos + max(len(t), 1)
        errors, ocr = [], 0
        have_text = {p["document_id"] for p in passages}
        for d in ids:
            if docs[d]["kind"] == "original" and d not in have_text and not any(
                    docs[x].get("derived_from") == d and x in have_text for x in ids):
                errors.append(f"{d}:not_extracted")
        for p in passages:
            flags = p["quality_flags"]
            code = next((f.split(":", 1)[1] for f in flags if f.startswith("extraction_failed:")), None)
            if "needs_text" in flags:
                errors.append(f"{p['document_id']}:{code or 'needs_text'}")
            ocr += "ocr_unverified" in flags
        limits = [*LIMITS, f"case_sensitive={case_sensitive}", "extraction_versions=" + ",".join(
            sorted({p["extraction_version"] for p in passages}))]
        if ocr:
            limits.append(f"ocr_unverified_passages={ocr}")
        body = {"case_id": profile["case_id"], "query": query, "variants": list(variants or []),
                "corpus_hash": current_corpus_hash(repo),
                "filters": {"scope": "all" if scope == "all" else ids, "case_sensitive": case_sensitive},
                "parser_errors": sorted(set(errors)), "known_limits": limits, "hits": sorted(hits)}
        rid = record_id(body)
        run = repo.reader().runs()[-1]
        step = f"search:{rid[:16]}"
        repo.add_step(step, run["id"], "search", "software:la.py")
        repo.add_frozen_many("search_records", [body], step)
        repo.add_frozen_many("value_records", [{"id": f"searchhits:{rid}", "kind": "search_hits", "search_record_id": rid,
                                                "hits": sorted(detail, key=lambda h: (h["passage_id"], h["start"], h["term"]))}], step)
        repo.add_prov_edges([(f"sr:{rid}", "wasGeneratedBy", f"step:{step}")], step)
        return {"ok": True, "search_record_id": rid, "state": state_of(body), "hits": len(body["hits"]),
                "corpus_hash": body["corpus_hash"], "run_id": run["id"], "parser_errors": body["parser_errors"]}
    finally:
        repo.close()


def _records(repo: Repository) -> dict[str, dict[str, Any]]:
    return {record_id(b): b for b, _ in repo.frozen_bodies("search_records")}


def verify_not_found(case_dir: Path | str, record_ids: list[str]) -> dict[str, Any]:
    """Every `not_found` claim needs a current, clean, hit-free SearchRecord; otherwise the gate blocks."""
    from .proposals import load_profile
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        recs, now = _records(repo), current_corpus_hash(repo)
        problems = []
        for rid in record_ids:
            rec = recs.get(rid)
            if rec is None:
                problems.append({"record_id": rid, "code": "E_NO_SEARCH_RECORD"})
            elif rec["corpus_hash"] != now:
                problems.append({"record_id": rid, "code": "E_SEARCH_STALE"})
            elif rec["hits"]:
                problems.append({"record_id": rid, "code": "E_SEARCH_HAS_HITS"})
            elif rec["parser_errors"]:
                problems.append({"record_id": rid, "code": "E_SEARCH_INCONCLUSIVE"})
        return {"ok": not problems, "blocked": bool(problems), "problems": problems, "corpus_hash": now}
    finally:
        repo.close()


def require_not_found(case_dir: Path | str, record_ids: list[str]) -> None:
    r = verify_not_found(case_dir, record_ids)
    if r["blocked"]:
        raise LaError("E_NOT_FOUND_BLOCKED", "`not_found` needs a current SearchRecord with no hits and no parser errors.",
                      "`not_found` wymaga aktualnego SearchRecord bez trafień i bez błędów parsera.", EXIT_POLICY,
                      {"first": r["problems"][0]["code"], "count": str(len(r["problems"]))})


def rerun_stale(case_dir: Path | str) -> list[dict[str, Any]]:
    """Re-execute empty searches recorded against an older corpus; a hit invalidates `not_found`."""
    from .proposals import load_profile
    root = Path(case_dir)
    profile = load_profile(root)
    repo = Repository(root / "case.db", profile["case_id"])
    try:
        recs, now = _records(repo), current_corpus_hash(repo)
        key = lambda r: sha256_obj([r["query"], r["variants"], r["filters"]])  # noqa: E731
        current = {key(r) for r in recs.values() if r["corpus_hash"] == now}
        todo = [(rid, r) for rid, r in sorted(recs.items())
                if not r["hits"] and r["corpus_hash"] != now and key(r) not in current]
    finally:
        repo.close()
    out = []
    for rid, r in todo:
        res = run_search(root, r["query"], scope=r["filters"]["scope"], variants=r["variants"],
                         case_sensitive=r["filters"]["case_sensitive"])
        out.append({"old_record_id": rid, "new_record_id": res["search_record_id"], "state": res["state"]})
    return out
