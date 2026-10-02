#!/usr/bin/env python3
"""Search the domestic courts of 122 jurisdictions for extradition and
surrender decisions, with a relevance gate and a report for every search.

This is the accelerator for the extradition-case-law-search skill. It installs
and drives the open-source engine at

    https://github.com/mateiclej-wq/eu-extradition-search   (MIT)

which holds 153 adapters — one per national court database — each speaking that
database's own interface, language and vocabulary.

    python3 xsearch.py install
    python3 xsearch.py search --issuing-state RO --countries NL,DE,IE
    python3 xsearch.py preview AE --countries RO,IT,PL
    python3 xsearch.py sources --countries NL,DE
    python3 xsearch.py runs

Nothing here decides what a judgment holds. It finds candidates and says how
confident it is that they are about extradition at all.

Politeness — this is a condition of use, not a suggestion
--------------------------------------------------------
The engine queries public court databases on a deliberately low-volume footing:
one request per second per host, an honest User-Agent, and no automation of any
source whose terms bar it (those stay deep-link only). An advisory lock keeps
two sweeps from running at once. Do not parallelise this, loop it unattended
over a list of states, or raise --limit into the hundreds. Several of these
databases will block on far less, and they are a shared resource for everyone
who does this work.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ENGINE_URL = "https://github.com/mateiclej-wq/eu-extradition-search"
HOME = pathlib.Path(os.environ.get("LAWVE_EXTRADITION_HOME",
                                   pathlib.Path.home() / ".cache" /
                                   "lawve-extradition-search")).expanduser()
ENGINE = HOME / "engine"
RESULTS = HOME / "results"
SKILL_DIR = pathlib.Path(__file__).resolve().parent

# Slowest adapter by a wide margin, measured over recorded runs. Everything
# else answers in under five seconds. This one number is why an unconstrained
# sweep looks like it has hung when it has not.
SLOW = {"pl-saos": 98}


# ---------------------------------------------------------------- install ---

def _have_engine() -> bool:
    return (ENGINE / "engine.py").is_file()


def cmd_install(a) -> int:
    HOME.mkdir(parents=True, exist_ok=True)
    if _have_engine():
        print(f"Engine already present at {ENGINE}")
        if a.update:
            subprocess.run(["git", "-C", str(ENGINE), "pull", "--ff-only"],
                           check=False)
    else:
        print(f"Cloning the engine into {ENGINE} …")
        r = subprocess.run(["git", "clone", "--depth", "1", ENGINE_URL,
                            str(ENGINE)], check=False)
        if r.returncode != 0:
            return _fail("git clone failed. Clone it by hand:\n"
                         f"  git clone {ENGINE_URL} {ENGINE}")
    try:
        import requests  # noqa: F401
    except ImportError:
        print("\n! The engine needs `requests`:  pip install requests")
        return 1
    try:
        import babel  # noqa: F401
    except ImportError:
        print("\n! `babel` is missing. Without it, searching by requesting "
              "state stops localising that state's name into each "
              "jurisdiction's language, and every such search silently "
              "narrows.  pip install babel")
    print("\nReady.  Try:  python3 xsearch.py search --issuing-state RO "
          "--countries NL,DE")
    return 0


def _fail(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def _load_engine():
    """Put the engine on the path and return the pieces we drive."""
    if not _have_engine():
        sys.exit(f"Engine not installed. Run:  python3 {SKILL_DIR.name}/"
                 f"xsearch.py install")
    if str(ENGINE) not in sys.path:
        sys.path.insert(0, str(ENGINE))
    try:
        import adapters  # noqa: F401  (import populates the registry)
        from core.registry import adapters_for, all_adapters
        from engine import _run_adapter
    except ImportError as exc:
        sys.exit(f"Could not load the engine ({exc}). If `requests` is "
                 f"missing:  pip install requests")
    # The relevance gate lives upstream where present; the skill carries its
    # own copy so it works against any version of the engine.
    try:
        from core.quality import annotate
    except ImportError:
        sys.path.insert(0, str(SKILL_DIR))
        from quality import annotate  # vendored fallback
    return adapters_for, all_adapters, _run_adapter, annotate


# ------------------------------------------------------------------- lock ---

@contextlib.contextmanager
def _sweep_lock():
    """One sweep at a time on this machine — see the politeness note above."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    lock = RESULTS / ".sweep.lock"
    try:
        import fcntl
    except ImportError:      # Windows — best effort, no lock available
        yield
        return
    fh = lock.open("w")
    try:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("Another sweep is running — waiting, so we don't multiply "
                  "the request rate against the courts.", file=sys.stderr)
            fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


# ----------------------------------------------------------------- search ---

def _select(adapters_for, countries, include_manual):
    sel = adapters_for([c.strip().upper() for c in countries.split(",")
                        if c.strip()] if countries else None)
    if not include_manual:
        auto = [x for x in sel if x.access in ("api", "xhr", "form")]
        if auto:
            sel = auto
    return sel


def cmd_search(a) -> int:
    adapters_for, _all, _run_adapter, annotate = _load_engine()
    sel = _select(adapters_for, a.countries, a.include_manual)
    if not sel:
        return _fail("No databases match that selection. Try `sources`.")

    slow = [x.id for x in sel if x.id in SLOW]
    eta = max([SLOW[s] for s in slow] + [8])
    print(f"Searching {len(sel)} databases across "
          f"{len({x.country_iso for x in sel})} jurisdictions — expect about "
          f"{eta}s.", file=sys.stderr)
    if slow:
        print(f"  ({', '.join(slow)} accounts for most of that; narrow "
              f"--countries to finish in seconds.)", file=sys.stderr)

    issuing = (a.issuing_state or "").upper() or None
    ccs = ([c.strip().upper() for c in a.countries.split(",") if c.strip()]
           if a.countries else [])
    meta = {"query": a.query, "mode": a.mode, "since": a.since, "until": a.until,
            "issuing": issuing, "limit": a.limit, "countries": ccs,
            "include_manual": a.include_manual}

    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    hits: list[dict] = []
    statuses: list[dict] = []
    t0 = time.monotonic()

    with _sweep_lock():
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(_run_adapter, x, a.query, a.mode,
                                not a.no_expand, a.since, a.until, a.limit,
                                issuing) for x in sel]
            for n, fut in enumerate(as_completed(futs), 1):
                adapter, found, status = fut.result()
                rows = annotate([dataclasses.asdict(h) for h in found])
                hits.extend(rows)
                statuses.append({"source": status.source,
                                 "cc": status.country_iso, "ok": status.ok,
                                 "n": status.hits, "error": status.error,
                                 "elapsed": round(status.elapsed, 2)})
                on = sum(1 for r in rows
                         if (r.get("quality") or {}).get("verdict") == "on_topic")
                detail = (f"{len(rows):>3} hits, {on} on point" if status.ok
                          else (status.error or "")[:60])
                print(f"  [{n:>3}/{len(sel)}] {'ok  ' if status.ok else 'FAIL'} "
                      f"{adapter.id:<22} {detail}", file=sys.stderr)

        out = _write_report(run_id, hits, statuses, meta)

    _digest(hits, statuses, meta, run_id, out, time.monotonic() - t0, a.top)
    return 0


# ----------------------------------------------------------------- report ---

def _describe(meta: dict) -> str:
    bits = []
    if meta.get("issuing"):
        bits.append(f"{meta['issuing']} as requesting state")
    if meta.get("query"):
        bits.append(f'"{meta["query"]}"')
    bits.append("in " + ", ".join(meta["countries"]) if meta.get("countries")
                else "across every jurisdiction")
    if meta.get("mode") and meta["mode"] != "both":
        bits.append(f"({meta['mode']} vocabulary)")
    span = " to ".join(x for x in (meta.get("since"), meta.get("until")) if x)
    if span:
        bits.append(f"[{span}]")
    return " · ".join(bits) or "unconstrained sweep"


def _counts(hits) -> dict:
    out: dict[str, int] = {}
    for h in hits:
        v = (h.get("quality") or {}).get("verdict") or "unverified"
        out[v] = out.get(v, 0) + 1
    return out


def _write_report(run_id, hits, statuses, meta) -> pathlib.Path:
    """A standing record of one search — what was asked, what answered, what
    came back — so the research is reconstructable months later without
    re-running it. That matters when you have to say where a citation came from.
    """
    RESULTS.mkdir(parents=True, exist_ok=True)
    v = _counts(hits)
    answered = [s for s in statuses if s["ok"]]
    failed = [s for s in statuses if not s["ok"]]
    stamp = (f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]} "
             f"{run_id[9:11]}:{run_id[11:13]}")

    L = [f"# Extradition case-law search — {stamp}", "",
         f"**Search:** {_describe(meta)}",
         f"**Run reference:** `{run_id}`",
         f"**Databases queried:** {len(statuses)} ({len(answered)} answered, "
         f"{len(failed)} failed)",
         f"**Results:** {len(hits)} — {v.get('on_topic', 0)} on point, "
         f"{v.get('unverified', 0)} unclear, {v.get('off_topic', 0)} off topic, "
         f"{v.get('broken', 0)} unusable links", "",
         "> Every result below is a lead, never an authority: the engine says "
         "a judgment exists and is probably relevant, not what it holds. A nil "
         "return is itself information — publication practice varies enormously "
         "between states, and in some the surrender decision is never published "
         "at all.", "",
         "## Databases searched", "",
         "| Database | Jurisdiction | Result | Time |", "|---|---|---|---|"]
    for s in sorted(statuses, key=lambda x: (not x["ok"], x["source"])):
        outcome = (f"{s['n']} hits" if s["ok"]
                   else f"failed — {(s['error'] or '')[:60]}")
        L.append(f"| `{s['source']}` | {s['cc']} | {outcome} | {s['elapsed']}s |")
    L.append("")
    if failed:
        L += ["A failed database is not a nil return: it was unreachable this "
              "run, so its material is simply unsearched.", ""]

    keep = [h for h in hits
            if (h.get("quality") or {}).get("verdict") in (None, "on_topic",
                                                           "unverified")]
    L += ["## Results", ""]
    if len(hits) - len(keep):
        L += [f"*{len(keep)} of {len(hits)} shown; {len(hits) - len(keep)} "
              f"suppressed as off-topic or unreachable.*", ""]
    by_country: dict[str, list[dict]] = {}
    for h in keep:
        by_country.setdefault(h.get("country", "?"), []).append(h)
    for country in sorted(by_country):
        L += [f"### {country}", "| Date | Court | Reference | Link |",
              "|---|---|---|---|"]
        for h in sorted(by_country[country], key=lambda x: x.get("date") or "",
                        reverse=True):
            ref = h.get("ecli") or h.get("ref") or h.get("title") or "—"
            L.append(f"| {h.get('date') or '—'} | "
                     f"{h.get('court') or h.get('source')} | {ref} "
                     f"| [link]({h.get('url')}) |")
        L.append("")

    path = RESULTS / f"{run_id}.md"
    path.write_text("\n".join(L), encoding="utf-8")
    with (RESULTS / f"{run_id}.jsonl").open("w", encoding="utf-8") as fh:
        for h in hits:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    with (RESULTS / "runs.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"run": run_id, "description": _describe(meta),
                             "hits": len(hits),
                             "on_topic": v.get("on_topic", 0),
                             "databases": len(statuses),
                             "answered": len(answered), "meta": meta},
                            ensure_ascii=False) + "\n")
    return path


def _digest(hits, statuses, meta, run_id, out, elapsed, top) -> None:
    v = _counts(hits)
    answered = sum(1 for s in statuses if s["ok"])
    failed = [s for s in statuses if not s["ok"]]
    print(f"\n{'=' * 40}\n{_describe(meta)}\n{'=' * 40}")
    print(f"{len(hits)} results from {answered}/{len(statuses)} databases in "
          f"{elapsed:.0f}s — {v.get('on_topic', 0)} on point, "
          f"{v.get('unverified', 0)} unclear, {v.get('off_topic', 0)} off "
          f"topic, {v.get('broken', 0)} unusable links.")

    on = [h for h in hits
          if (h.get("quality") or {}).get("verdict") in (None, "on_topic")]
    unclear = [h for h in hits
               if (h.get("quality") or {}).get("verdict") == "unverified"]
    shown = (on + unclear)[:top]
    if shown:
        print(f"\nOn point first ({len(shown)} of {len(on) + len(unclear)} "
              f"shown; the rest are in the report):\n")
        for h in sorted(shown, key=lambda x: (x.get("country") or "",
                                              x.get("date") or ""),
                        reverse=True):
            ref = h.get("ecli") or h.get("ref") or h.get("title") or "(untitled)"
            flag = ("" if (h.get("quality") or {}).get("verdict") == "on_topic"
                    else "  [relevance unclear]")
            print(f"  {h.get('country_iso', '??')} {h.get('date') or '----'}  "
                  f"{h.get('court') or h.get('source')}")
            print(f"     {ref}{flag}\n     {h.get('url')}")
    else:
        print("\nNothing came back on point. A nil return is itself "
              "information — but read the failures below before relying on it.")

    if failed:
        print(f"\n{len(failed)} database(s) did not answer — their material is "
              f"unsearched, not absent:")
        for s in failed:
            print(f"  {s['source']:<22} {(s['error'] or '')[:70]}")

    print(f"\nReport: {out}\nRun reference: {run_id}")
    print("\nEvery result is a LEAD, not an authority. The engine says a "
          "judgment exists and is probably relevant — never what it holds. "
          "Open it, and have it translated, before it reaches anything you file.")


# ------------------------------------------------------------------ other ---

def cmd_sources(a) -> int:
    _af, all_adapters, _r, _q = _load_engine()
    rows = all_adapters()
    if a.countries:
        want = {c.strip().upper() for c in a.countries.split(",")}
        rows = [x for x in rows if x.country_iso in want]
    w = max((len(x.id) for x in rows), default=10)
    for x in rows:
        slow = f"  ~{SLOW[x.id]}s" if x.id in SLOW else ""
        print(f"{x.id:<{w}}  {x.country_iso}  {x.access:<8}  {x.status:<8}  "
              f"{x.source_name}{slow}")
    autos = sum(1 for x in rows if x.access in ("api", "xhr", "form"))
    print(f"\n{len(rows)} sources | {autos} automated | "
          f"{len({x.country_iso for x in rows})} jurisdictions")
    return 0


def cmd_preview(a) -> int:
    _load_engine()
    from core.terms import issuing_state_names
    state = a.issuing_state.upper()
    ccs = ([c.strip().upper() for c in a.countries.split(",") if c.strip()]
           if a.countries else ["RO", "IT", "PL", "NL", "DE", "ES", "HU"])
    print(f"{state} is searched for as:\n")
    for cc in ccs:
        names = issuing_state_names(state, cc) or ["(not localised)"]
        print(f"  {cc}  {' / '.join(names)}")
    try:
        import babel  # noqa: F401
    except ImportError:
        print("\n! babel is not installed — names are NOT being localised, "
              "which silently narrows every requesting-state search.")
    return 0


def cmd_runs(a) -> int:
    idx = RESULTS / "runs.jsonl"
    if not idx.exists():
        print("No searches recorded yet.")
        return 0
    rows = []
    for line in idx.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    for r in list(reversed(rows))[:a.limit]:
        print(f"{r['run']}  {r.get('hits', 0):>4} hits "
              f"({r.get('on_topic', 0)} on point)  {r.get('description', '')}")
    return 0


def cmd_show(a) -> int:
    p = RESULTS / f"{a.run}.md"
    if not p.exists():
        return _fail(f"No report {a.run}. `runs` lists what exists.")
    print(p.read_text(encoding="utf-8"))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="xsearch.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("install", help="fetch the engine (one-off)")
    i.add_argument("--update", action="store_true", help="git pull if present")

    s = sub.add_parser("search")
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--countries", help="ISO codes, e.g. NL,DE,IE")
    s.add_argument("--issuing-state", dest="issuing_state",
                   help="ISO code of the requesting state, localised per jurisdiction")
    s.add_argument("--mode", choices=["both", "eaw", "extradition"], default="both")
    s.add_argument("--since"), s.add_argument("--until")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--top", type=int, default=25)
    s.add_argument("--include-manual", action="store_true")
    s.add_argument("--no-expand", action="store_true")

    o = sub.add_parser("sources"); o.add_argument("--countries")
    v = sub.add_parser("preview")
    v.add_argument("issuing_state"), v.add_argument("--countries")
    r = sub.add_parser("runs"); r.add_argument("--limit", type=int, default=20)
    w = sub.add_parser("show"); w.add_argument("run")

    a = p.parse_args(argv)
    return {"install": cmd_install, "search": cmd_search, "sources": cmd_sources,
            "preview": cmd_preview, "runs": cmd_runs, "show": cmd_show}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
