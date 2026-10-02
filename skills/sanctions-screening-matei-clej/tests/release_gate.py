#!/usr/bin/env python3
"""
Release gate — every published name retrieves its own designation, end to end.

For every primary name, alias and native-script name on the selected lists,
run the real screen() — request validation, script gate, type filter, the
prefilter, the matcher, the threshold and the limit, exactly as `check` runs
them — against the list that publishes it, and require that the SAME source
and uid comes back. Not "a candidate with that normalised name": the record.

This is what the fourth review asked for and the index-level invariant in
test_screen.py cannot see: request refusal, type and status filtering, the
limit, and anything between "in the index under the right key" and "returned
at or above the shipped threshold". Every name is a full screen of its list —
about 131,000 screens over the six defaults, hours single-threaded — which is
why it is a release gate and not a unit test, and why it runs across
processes: one pool per list, each worker warming that list's index once.
Run it before a tag, and bind its attestation to the cache it ran against.

    python3 tests/release_gate.py --workers 8            # the six default lists, every name
    python3 tests/release_gate.py --sample 500           # a quick, seeded sample per list
    python3 tests/release_gate.py --source ofsi,un --workers 4
    python3 tests/release_gate.py --out release_gate.json

Exit 0: every accepted name retrieved its record. Exit 1: at least one did
not. Exit 3: a selected list could not be read. Names the request gate
refuses by design — scripts this tool cannot romanise — are counted and
listed separately, never as retrieved.
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import matching as M   # noqa: E402
import screen as SC    # noqa: E402
import sources as S    # noqa: E402

DEFAULTS = ("uk-sanctions-list", "ofsi", "un", "eu", "ofac-sdn", "ofac-cons")


def make_args(kind: str, limit: int) -> argparse.Namespace:
    return argparse.Namespace(dob="", nationality="", type=kind, client="", matter="",
                              threshold=SC.DEFAULT_THRESHOLD, limit=limit,
                              max_age_hours=24.0 * 365, include_delisted=True)


_W: dict = {}   # per-worker state: the manifest and the source, index warmed once


def _init(sid: str) -> None:
    _W["meta"] = S.load_meta()
    _W["src"] = S.BY_ID[sid]
    SC._index(sid, S.read_source(sid, _W["meta"][sid]))


def _run_chunk(chunk: list, limit: int) -> dict:
    """Screen one chunk of (name, kind, key, status) against the worker's list.
    Returns counts and the failures; the parent merges them."""
    src, meta = _W["src"], _W["meta"]
    sid = src.id
    out = {"retrieved": 0, "refused": 0, "failed": 0, "beyond_limit": 0,
           "refused_examples": [], "failures": []}
    for nm, kind, key, status in chunk:
        o = SC.screen(nm, make_args(kind, limit), [src], meta)
        if o.error:
            out["refused"] += 1
            if len(out["refused_examples"]) < 20:
                out["refused_examples"].append({"name": nm, "uid": key, "why": o.error[:80]})
            continue
        found = any(h["record"]["source"] == sid and
                    (h["record"].get("uid") or h["record"].get("ref")) == key for h in o.hits)
        if found:
            out["retrieved"] += 1
        else:
            out["failed"] += 1
            beyond = o.total_hits > len(o.hits)
            out["beyond_limit"] += int(beyond)
            if len(out["failures"]) < 200:
                out["failures"].append({"name": nm, "uid": key, "type": kind, "status": status,
                                        "total_hits": o.total_hits, "beyond_limit": beyond,
                                        "complete": o.complete})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=",".join(DEFAULTS))
    ap.add_argument("--sample", type=int, default=0, help="names per list; 0 = every name")
    ap.add_argument("--limit", type=int, default=40, help="the operational --limit of check")
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--out", default="")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                    help="processes per list; 1 runs in this process")
    a = ap.parse_args()

    meta = S.load_meta()
    attestation = {
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "threshold": SC.DEFAULT_THRESHOLD, "limit": a.limit, "sample": a.sample,
        "parser_version": S.PARSER_VERSION,
        "engine_version": S.ENGINE_VERSION,
        "code_sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()[:16]
                        for f in ("screen.py", "sources.py", "matching.py")},
        "sources": {},
    }
    worst = 0
    for sid in [x.strip() for x in a.source.split(",") if x.strip()]:
        src = S.BY_ID[sid]
        entry = meta.get(sid, {})
        try:
            recs = S.read_source(sid, entry)
        except S.CacheError as exc:
            print(f"{sid}: NOT READABLE — {exc}")
            attestation["sources"][sid] = {"readable": False, "error": str(exc)}
            worst = max(worst, 3)
            continue
        queries = []
        for rec in recs:
            rtype = rec.get("type") or "individual"
            kind = rtype if rtype in SC.TYPES else "any"
            key = rec.get("uid") or rec.get("ref")
            for nm in [rec.get("name", "")] + list(rec.get("aliases") or ()) \
                    + list(rec.get("nonlatin") or ()):
                if (nm or "").strip():
                    queries.append((nm, kind, key, rec.get("status")))
        if a.sample and a.sample < len(queries):
            queries = random.Random(a.seed).sample(queries, a.sample)
        res = {"readable": True, "records": len(recs), "norm_sha256": entry.get("norm_sha256"),
               "names": len(queries), "retrieved": 0, "refused": 0, "failed": 0,
               "beyond_limit": 0, "refused_examples": [], "failures": [], "workers": a.workers}
        t0 = time.time()

        def merge(part: dict) -> None:
            for k in ("retrieved", "refused", "failed", "beyond_limit"):
                res[k] += part[k]
            res["refused_examples"] = (res["refused_examples"] + part["refused_examples"])[:20]
            res["failures"] = (res["failures"] + part["failures"])[:200]

        if a.workers <= 1 or len(queries) < 200:
            _init(sid)
            step = 2000
            for start in range(0, len(queries), step):
                merge(_run_chunk(queries[start:start + step], a.limit))
                done = min(start + step, len(queries))
                if done < len(queries):
                    print(f"  {sid}: {done:,}/{len(queries):,} ({time.time() - t0:.0f}s)", flush=True)
        else:
            n_chunks = a.workers * 4
            chunks = [queries[i::n_chunks] for i in range(n_chunks)]
            done = 0
            with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                                     initargs=(sid,)) as pool:
                futures = {pool.submit(_run_chunk, c, a.limit): len(c) for c in chunks if c}
                for fut in as_completed(futures):
                    merge(fut.result())
                    done += futures[fut]
                    if done < len(queries):
                        print(f"  {sid}: {done:,}/{len(queries):,} ({time.time() - t0:.0f}s)",
                              flush=True)
        res["seconds"] = round(time.time() - t0, 1)
        attestation["sources"][sid] = res
        print(f"{sid:<20} names {res['names']:>7,}  retrieved {res['retrieved']:>7,}  "
              f"refused-by-gate {res['refused']:>5,}  FAILED {res['failed']:>5,}"
              f"{'  (' + str(res['beyond_limit']) + ' beyond --limit)' if res['beyond_limit'] else ''}"
              f"  {res['seconds']}s")
        for f in res["failures"][:8]:
            print(f"      FAILED  {f['name'][:50]!r:<52} uid {f['uid']} type {f['type']} "
                  f"hits {f['total_hits']}{' beyond limit' if f['beyond_limit'] else ''}")
        if res["failed"]:
            worst = max(worst, 1)
    attestation["exit"] = worst
    if a.out:
        Path(a.out).write_text(json.dumps(attestation, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"attestation written to {a.out}")
    print({0: "PASS — every accepted name retrieved its own designation",
           1: "FAIL — a published name did not retrieve its designation",
           3: "NOT RUN IN FULL — a list could not be read"}[worst])
    return worst


if __name__ == "__main__":
    sys.exit(main())
