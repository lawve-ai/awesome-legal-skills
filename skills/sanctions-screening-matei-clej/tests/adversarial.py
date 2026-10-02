#!/usr/bin/env python3
"""
Adversarial and failure-mode tests.

These are the tests that matter for publication: what the tool does when the
input is hostile, the cache is damaged, the network is down, or a list is
missing. The governing rule is that it must FAIL CLOSED — an unreadable list is
reported as not searched, never as a clean result.

    python3 tests/adversarial.py
"""

import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL = [], []


def ok(cond, label, detail=""):
    (PASS if cond else FAIL).append(label + (f" — {detail}" if detail and not cond else ""))
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"\n          {detail}" if detail and not cond else ""))


def run(args, env=None, timeout=180):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable, str(ROOT / "screen.py")] + args,
                       capture_output=True, text=True, env=e, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def temp_cache(sources=("uk-sanctions-list", "ofsi")):
    """A throwaway cache seeded from the real one, so tests can damage it."""
    real = Path(os.environ.get("SANCTIONS_DATA", Path.home() / ".claude" / "sanctions-data"))
    tmp = Path(tempfile.mkdtemp(prefix="sanctions-test-"))
    (tmp / "norm").mkdir(parents=True)
    meta = json.loads((real / "meta.json").read_text())
    keep = {}
    for sid in sources:
        shutil.copy(real / "norm" / f"{sid}.jsonl.gz", tmp / "norm" / f"{sid}.jsonl.gz")
        keep[sid] = meta[sid]
    (tmp / "meta.json").write_text(json.dumps(keep))
    return tmp


# =========================================================== hostile input
print("\nHOSTILE INPUT — must not crash, must not assert a clean result")

HOSTILE = [
    ("empty name", ""),
    ("whitespace only", "   "),
    ("single character", "X"),
    ("punctuation only", "!!!///***"),
    ("emoji", "🙂🙃💀"),
    ("right-to-left Arabic", "محمد علي"),
    ("Cyrillic query", "Кадыров Рамзан"),
    ("Chinese", "习近平"),
    ("embedded newline", "Ivan\nPetrov"),
    ("markdown table breaker", "A | B --- | ---"),
    ("spreadsheet formula injection", "=cmd|' /C calc'!A0"),
    ("5,000 characters", "Ivanov " * 700),
    ("null-ish escapes", "Ivan\\x00Petrov"),
    ("SQL-shaped", "'; DROP TABLE designations; --"),
]
# Every one of these must land on a DEFINED exit code, because "no traceback"
# is satisfied by a clean nil return, and two exact cross-script designations
# were being missed while this loop was green.
DEFINED = {0, 2, 3, 4}
for label, name in HOSTILE:
    rc, out = run(["check", name])
    crashed = "Traceback" in out
    ok(not crashed, f"{label}: no traceback", out[-300:] if crashed else "")
    ok(rc in DEFINED, f"{label}: exits on a defined code, never a bare crash", f"rc={rc}")
    # Anything that did not refuse must show the provenance block: a result with
    # no statement of what was searched is not a result.
    ok(rc == 4 or "Lists searched:" in out,
       f"{label}: a search that ran says which lists it searched", out[-200:])
# And the ones whose right answer is known.
KNOWN = [("empty name", "", 4), ("whitespace only", "   ", 4),
         ("punctuation only", "!!!///***", 4), ("emoji", "🙂🙃💀", 4),
         ("right-to-left Arabic", "محمد علي", 4), ("Chinese", "习近平", 4),
         ("Cyrillic query", "Кадыров Рамзан", 2)]
for label, name, want in KNOWN:
    rc, _ = run(["check", name])
    ok(rc == want, f"{label}: exits {want}", f"got {rc}")

print("\nHOSTILE INPUT — the empty search must not read as a clean search")
rc, out = run(["check", ""])
ok(rc == 4, "an empty query is refused outright", f"rc={rc}")
ok("No candidate" not in out,
   "an empty query never prints a nil return at all — there was no search", out[-200:])
ok("REFUSED" in out.upper() and "Nothing was screened" in out,
   "and it says so in terms", out[-200:])

print("\nDATES — bad dates must degrade, never crash or silently drop the search")
for label, d in [("garbage", "not-a-date"), ("impossible day", "31/02/1990"),
                 ("year only", "1975"), ("far past", "1875"), ("future", "2099-01-01"),
                 ("partial ISO", "1975-03"), ("US order", "03/02/1975")]:
    rc, out = run(["check", "Vladimir Putin", "--dob", d])
    ok("Traceback" not in out, f"--dob {label} ({d!r}) handled")
    # Deleting date handling entirely, or returning nil for every date, passed
    # the assertion above. A bad date must degrade the ANNOTATION, not the search.
    ok(rc == 2 and "PUTIN" in out.upper(),
       f"--dob {label} ({d!r}) still screens and still finds the designation",
       f"rc={rc}")

print("\nARGUMENTS")
rc, out = run(["check", "X", "--type", "banana"])
ok(rc == 4 and "not one of" in out, "an unknown --type is refused, naming the valid ones", out[-200:])
# These three were "does not crash" assertions. All three silently converted a
# known designated person into a clean nil result and exited 0.
for label, opt in [("--limit 0", ["--limit", "0"]),
                   ("--threshold 0", ["--threshold", "0"]),
                   ("--threshold nan", ["--threshold", "nan"]),
                   ("--threshold 500", ["--threshold", "500"])]:
    rc, out = run(["check", "Vladimir Putin"] + opt)
    ok(rc == 4 and "REFUSED" in out,
       f"{label} is refused rather than silently erasing candidates", f"rc={rc} {out[-160:]}")
    ok("No candidate at or above" not in out,
       f"{label} never prints a nil return")
rc, out = run(["check", "Vladimir Putin", "--source", "does-not-exist"])
ok("unknown source" in out.lower(), "an unknown --source is named and refused")
# it used to call sys.exit() directly, which is an exit that never passed the gate
ok(rc == 4, "an unknown --source exits through the gate as a refused request", f"rc={rc}")
rc, out = run(["check", "Vladimir Putin", "--source", "ofsi,ofsi"])
ok("Lists searched: 1 of 1" in out,
   "a list named twice is searched once, not counted twice", out[:200])
rc, out = run(["check", "Vladimir Putin", "--source", ","])
ok(rc == 4, "--source naming no list is refused rather than searching the defaults",
   f"rc={rc}")

print("\nA SOURCE THAT CANNOT BE INDEXED IS NOT A SEARCHED SOURCE")
guard = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
import screen as SC, sources as S
def boom(*a, **k):
    raise RuntimeError("index exploded")
SC._index = boom
class A:
    threshold = 88.0; type = "individual"; dob = nationality = ""
    limit = 40; include_delisted = False; max_age_hours = 24.0; client = matter = ""
meta = S.load_meta()
o = SC.screen("Vladimir Putin", A, [S.BY_ID["ofsi"]], meta)
print(f"{{o.complete}}|{{o.exit_code}}|{{len(o.hits)}}|{{o.sources[0]['searched']}}")
"""
pr = subprocess.run([sys.executable, "-c", guard], capture_output=True, text=True, timeout=180)
line = pr.stdout.strip().splitlines()[-1] if pr.stdout.strip() else ""
ok(line.startswith("False|3|0|False"),
   "a source that raises while being indexed is reported NOT SEARCHED, exit 3",
   f"got {line!r} {pr.stderr[-200:]}")

print("\nUNICODE — the same name in different normal forms screens identically")
import unicodedata  # noqa: E402
import screen as SC  # noqa: E402
nfc = unicodedata.normalize("NFC", "Chirilă Daniela")
nfd = unicodedata.normalize("NFD", "Chirilă Daniela")
ok(nfc != nfd and SC.normalise(nfc) == SC.normalise(nfd),
   "NFC and NFD of the same name normalise identically")

# ==================================================== cache and failure modes
print("\nCACHE DAMAGE — every one of these must report NOT SEARCHED, never a clean nil")

tmp = temp_cache()
rc, out = run(["check", "Vladimir Putin", "--source", "uk-sanctions-list,ofsi"], env={"SANCTIONS_DATA": str(tmp)})
ok("Lists searched: 2 of 2" in out, "control: the seeded temp cache searches both lists", out[:300])

# 1. meta claims a list is fine, but the parsed file is gone
t1 = temp_cache()
(t1 / "norm" / "ofsi.jsonl.gz").unlink()
rc, out = run(["check", "Vladimir Putin", "--source", "ofsi"], env={"SANCTIONS_DATA": str(t1)})
ok("NOT SEARCHED" in out and rc == 3,
   "a missing parsed file is NOT SEARCHED and exits 3 without --strict", out[:400])

# 2. the parsed file is corrupt
t2 = temp_cache()
(t2 / "norm" / "ofsi.jsonl.gz").write_bytes(b"this is not gzip")
rc, out = run(["check", "Vladimir Putin", "--source", "ofsi", "--strict"], env={"SANCTIONS_DATA": str(t2)})
ok("NOT SEARCHED" in out and "Traceback" not in out and rc == 3,
   "a corrupt parsed file is reported as NOT SEARCHED, not as a traceback", out[:400])

# 3. the parsed file is truncated mid-record
t3 = temp_cache()
raw = gzip.decompress((t3 / "norm" / "ofsi.jsonl.gz").read_bytes())
(t3 / "norm" / "ofsi.jsonl.gz").write_bytes(gzip.compress(raw[: len(raw) // 2]))
rc, out = run(["check", "Vladimir Putin", "--source", "ofsi", "--strict"], env={"SANCTIONS_DATA": str(t3)})
ok("Traceback" not in out and "NOT SEARCHED" in out and rc == 3,
   "a truncated parsed file is reported as NOT SEARCHED", out[:300])

# 4. meta.json itself is corrupt
t4 = temp_cache()
(t4 / "meta.json").write_text("{not json")
rc, out = run(["check", "Vladimir Putin", "--source", "ofsi"], env={"SANCTIONS_DATA": str(t4)})
ok("Traceback" not in out and ("NOT SEARCHED" in out or "never fetched" in out),
   "a corrupt meta.json degrades to NOT SEARCHED", out[:400])

# 5. no cache at all — the fresh-install case
t5 = Path(tempfile.mkdtemp(prefix="sanctions-empty-"))
rc, out = run(["check", "Vladimir Putin", "--strict"], env={"SANCTIONS_DATA": str(t5)})
ok(rc == 3 and "NOT SEARCHED" in out,
   "a completely empty cache reports NOT SEARCHED and exits 3 under --strict", out[:300])
ok("No candidate at or above" not in out.split("NOT SEARCHED")[0],
   "an empty cache never prints a nil return before disclosing the failure")

# 6. stale data
t6 = temp_cache()
m = json.loads((t6 / "meta.json").read_text())
old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(timespec="seconds")
for v in m.values():
    v["fetched_at"] = old
(t6 / "meta.json").write_text(json.dumps(m))
rc, out = run(["check", "Vladimir Putin", "--strict"], env={"SANCTIONS_DATA": str(t6)})
ok("STALE" in out and rc == 3, "40-day-old data is marked STALE and exits 3 under --strict")
rc, out = run(["check", "Vladimir Putin"], env={"SANCTIONS_DATA": str(t6)})
ok("STALE" in out and rc == 3,
   "stale data screens and returns its candidates, but the run is not clean: exit 3",
   f"rc={rc}")
ok("No candidate" not in out and "PUTIN" in out.upper(),
   "stale data still produces the candidates it found, named", out[-200:])

# 7. a failed refresh must not destroy the last good copy.
# The old version set SANCTIONS_TEST_BREAK_URL, which production code never
# reads, so it downloaded the real list and its condition passed either way.
# tests/integrity.py now injects the failure in-process; here we assert that a
# genuinely unreachable URL is recorded as a failure and changes nothing.
t7 = temp_cache()
before = (t7 / "norm" / "ofsi.jsonl.gz").read_bytes()
broken = json.loads((t7 / "meta.json").read_text())
(t7 / "meta.json").write_text(json.dumps(broken))
guard = f"""
import json, sys
sys.path.insert(0, {str(ROOT)!r})
import sources as S
S.DATA = S.Path({str(t7)!r})
S.NORM = S.DATA / 'norm'
S.RAW = S.DATA / 'raw'
S.META = S.DATA / 'meta.json'
src = S.BY_ID['ofsi']
src.url = 'https://127.0.0.1:9/does-not-exist'
meta = S.load_meta()
entry = S.refresh(src, meta)
print(json.dumps({{'ok': entry['ok'], 'error': entry['error'][:60], 'records': entry['records']}}))
"""
pr = subprocess.run([sys.executable, "-c", guard], capture_output=True, text=True, timeout=180)
after = (t7 / "norm" / "ofsi.jsonl.gz").read_bytes()
try:
    res = json.loads(pr.stdout.strip().splitlines()[-1])
except Exception:
    res = {}
ok(res.get("ok") is False and res.get("records") == 0,
   "an unreachable source is recorded as a failure with no records", pr.stdout[-200:] + pr.stderr[-200:])
ok(before == after, "a failed refresh leaves the previous parsed list byte-identical")

# ================================================================== privacy
print("\nPRIVACY — a screen must make no network call at all")
guard = f'''
import socket, sys
def _boom(*a, **k):
    raise AssertionError("NETWORK CALL DURING CHECK")
socket.socket.connect = _boom
socket.create_connection = _boom
socket.getaddrinfo = _boom
sys.path.insert(0, {str(ROOT)!r})
sys.argv = ["screen.py", "check", "Vladimir Putin"]
import screen
sys.exit(screen.main())
'''
p = subprocess.run([sys.executable, "-c", guard], capture_output=True, text=True, timeout=180)
ok("NETWORK CALL DURING CHECK" not in (p.stdout + p.stderr) and p.returncode == 2,
   "screening a name opens no socket: the name never leaves the machine",
   (p.stdout + p.stderr)[-300:])

# batch is the command a firm would actually point at a client list, so it is
# the one that matters most here. It was never covered.
with tempfile.TemporaryDirectory() as td:
    csvp = Path(td) / "clients.csv"
    csvp.write_text("name,client,matter\nVladimir Putin,ACME,M1\nJane Ordinary,ACME,M2\n",
                    encoding="utf-8")
    bguard = guard.replace('["screen.py", "check", "Vladimir Putin"]',
                           f'["screen.py", "batch", {str(csvp)!r}, "--report-dir", {td!r}]')
    p2 = subprocess.run([sys.executable, "-c", bguard], capture_output=True, text=True,
                        timeout=300)
    both = p2.stdout + p2.stderr
    ok("NETWORK CALL DURING CHECK" not in both,
       "a batch of client names opens no socket either", both[-300:])
    ok("Vladimir Putin" in both and "Jane Ordinary" in both,
       "and the batch really did screen both rows", both[-300:])

# ================================================================== reports
print("\nSCREENING RECORD")
out_dir = Path(tempfile.mkdtemp(prefix="sanctions-report-"))
rc, out = run(["check", "Vladimir Putin", "--report", str(out_dir / "r.md")])
rep = (out_dir / "r.md").read_text()
meta = json.loads((Path(os.environ.get("SANCTIONS_DATA", Path.home() / ".claude" / "sanctions-data")) / "meta.json").read_text())
ok(meta["ofsi"]["list_date"] in rep, "the record carries each list's published date verbatim")
ok(str(meta["ofac-sdn"]["records"]) in rep.replace(",", ""), "the record carries the designation counts")
ok("## 6. Decision" in rep and "| Signed | |" in rep, "the decision block is present and blank")
ok("## 1. Search status" in rep and "**Complete.**" in rep,
   "the record states on its face whether the search was complete")
ok("does not cover" in rep and "Ownership and control" in rep,
   "the record discloses what it does not cover")
rows = [ln for ln in rep.splitlines() if ln.startswith("| ") and "---" not in ln]
ok(len([r for r in rows if "Sanctions List" in r or "OFAC" in r or "Consolidated" in r]) == 6,
   "the provenance table carries a row for every one of the six lists",
   f"{len(rows)} table rows")
prov_table = [ln for ln in rep.split("## 4.")[0].splitlines() if ln.startswith("|")]
bad_rows = [ln for ln in prov_table if ln.count("|") != 7]
ok(prov_table and not bad_rows,
   "every provenance row has exactly the six declared columns", str(bad_rows[:2]))

rc, out = run(["check", "Zzqx Wvvq", "--report", str(out_dir / "nil.md")])
nil = (out_dir / "nil.md").read_text()
ok("No candidate" in nil and "lists recorded as searched" in nil,
   "a nil return is expressed as bounded by the lists searched")

t8 = temp_cache()
(t8 / "norm" / "ofsi.jsonl.gz").unlink()
rc, out = run(["check", "Vladimir Putin", "--report", str(out_dir / "partial.md")],
              env={"SANCTIONS_DATA": str(t8)})
partial = (out_dir / "partial.md").read_text()
ok("NOT SEARCHED" in partial and "INCOMPLETE" in partial
   and "not evidence that the subject is absent" in partial,
   "a record produced with a broken list says so on its face, in terms",
   partial[:400])

print("\nBATCH")
csvp = out_dir / "subjects.csv"
csvp.write_text('name,dob,nationality,type\n"Putin, Vladimir",07/10/1952,Russia,individual\n'
                '"O\'Brien, Seán",,Ireland,individual\n'
                '"=cmd|\' /C calc\'!A0",,,entity\n', encoding="utf-8")
rc, out = run(["batch", str(csvp), "--report-dir", str(out_dir / "batch")])
ok("Traceback" not in out, "a CSV with commas, quotes, apostrophes and a formula is parsed", out[-300:])
ok(len(list((out_dir / "batch").glob("*.md"))) == 3, "one screening record written per subject")
ok(rc == 2, "a batch containing a designated person exits 2, never 0", f"rc={rc}")
# Returning a complete nil for every row wrote three files and passed all four
# of the old assertions. The known designation has to be required by name.
ok("PUTIN" in out.upper(), "the designated row is reported as a hit", out[-400:])
putin_line = next((l for l in out.splitlines() if "Putin" in l and "complete" in l), "")
ok(bool(putin_line), "its row says the search behind it was complete", putin_line)
m = re.search(r"\s(\d+)\s+complete\b", putin_line)
ok(bool(m) and int(m.group(1)) > 0,
   "the row carries a non-zero hit count, not a nil", putin_line)
recs = sorted((out_dir / "batch").glob("*.md"))
body = recs[0].read_text() if recs else ""
ok(any("Putin" in r.read_text() for r in recs),
   "the written record names the subject it screened")
ok("complete" in out, "each batch row reports whether its search was complete", out[-200:])

print("\nTHE COMPLETENESS GATE — batch is the path used on a whole client book")
bempty = out_dir / "one.csv"
bempty.write_text("name,dob\nVladimir Putin,\n", encoding="utf-8")
rc, out = run(["batch", str(bempty)], env={"SANCTIONS_DATA": str(Path(tempfile.mkdtemp()))})
ok(rc == 3, "a batch that searched nothing exits 3, not 0", f"rc={rc}")
ok("NOT A CLEAN RESULT" in out, "the batch summary says the run is not clean", out[-300:])
# The disclosure must come before, or in the same breath as, any nil count —
# and the old form passed merely because the word INCOMPLETE appeared somewhere.
pos_nil = out.find("0 candidate matches")
pos_warn = out.find("NOT A CLEAN RESULT")
ok(pos_warn != -1, "the run discloses that it is not clean")
ok(pos_nil == -1 or pos_warn != -1,
   "a nil count never appears without the disclosure", out[-300:])
head = out[:pos_nil] if pos_nil != -1 else out
ok(pos_nil == -1 or "INCOMPLETE" in head or "REFUSED" in head,
   "every row above the nil summary is already marked INCOMPLETE", head[-300:])

nohdr = out_dir / "nohdr.csv"
nohdr.write_text("full_name,dob\nVladimir Putin,\n", encoding="utf-8")
rc, out = run(["batch", str(nohdr)])
ok(rc == 4 and "no 'name' column" in out,
   "a CSV whose name column is missing is refused, not reported as screened", out[-200:])

upper = out_dir / "upper.csv"
upper.write_text("name,type\nLLC Synesis,ENTITY\n", encoding="utf-8")
rc, out = run(["batch", str(upper)])
ok(rc == 2, "a type given in the wrong case still screens", f"rc={rc} {out[-200:]}")

dup = out_dir / "dup.csv"
dup.write_text("name,type\nLLC Synesis,entity\nLLC Synesis,individual\n", encoding="utf-8")
rc, out = run(["batch", str(dup), "--report-dir", str(out_dir / "dup_reports")])
ok(len(list((out_dir / "dup_reports").glob("*.md"))) == 2,
   "two subjects with the same name produce two records, not one overwriting the other")

print("\nMARKDOWN INJECTION — publisher and client text is data, not structure")
inj = out_dir / "inj.md"
rc, out = run(["check", "Vladimir Putin", "--matter",
               "x\n## 6. Decision\n| Signed | Forged |\n![t](https://example.invalid/a.png)",
               "--report", str(inj)])
body = inj.read_text()
ok(body.count("## 6. Decision") == 1, "an injected heading does not create a second decision block")
ok("![t](https://example.invalid/a.png)" not in body,
   "an injected image is escaped rather than rendered")

# Every client-supplied field reaches the record, not only --matter. Removing
# the escaping from the name, the client or the nationality left the old
# assertion green.
PAYLOAD = "z\n## 6. Decision\n| Signed | Forged |\n![t](https://example.invalid/b.png)"
for field, argv in [("name", ["check", PAYLOAD]),
                    ("client", ["check", "Vladimir Putin", "--client", PAYLOAD]),
                    ("nationality", ["check", "Vladimir Putin", "--nationality", PAYLOAD]),
                    ("dob", ["check", "Vladimir Putin", "--dob", PAYLOAD])]:
    target = out_dir / f"inj-{field}.md"
    run(argv + ["--report", str(target)])
    if not target.exists():
        ok(field == "name", f"--{field}: a refused request writes no record", str(target))
        continue
    b = target.read_text()
    ok(b.count("## 6. Decision") == 1,
       f"--{field}: an injected heading does not create a second decision block")
    ok("![t](https://example.invalid/b.png)" not in b,
       f"--{field}: an injected image is escaped rather than rendered")
    ok("\n| Signed | Forged |" not in b,
       f"--{field}: an injected table row does not become a table row")

# And publisher text — the notes, names and identifiers this tool does not
# control — must be escaped on the way in, not trusted.
pub = out_dir / "pub.md"
run(["check", "Vladimir Putin", "--verbose", "--report", str(pub)])
pb = pub.read_text()
ok(pb.count("## 6. Decision") == 1,
   "no publisher field has manufactured a second decision block")
ok(pb.rstrip().endswith("---") or "## 6. Decision" in pb,
   "the record still ends with its decision block intact")

print("\nNATIVE SCRIPT — a name in the script the client actually holds")
rc, out = run(["check", "Кадыров Рамзан Ахмадович", "--type", "any"])
ok(rc == 2, "a Cyrillic query finds the Latin-script listing", f"rc={rc}")
ok("under 1 romanisation" in out or "romanisations:" in out,
   "the record names every romanisation it searched, not just one", out[-300:])
# The systems disagree, and the disagreement is the point: a name whose spelling
# turns on a letter the systems render differently must be searched both ways.
rc2, out2 = run(["check", "Фёдоров Юрий Викторович", "--type", "any",
                 "--source", "ofac-sdn"])
ok(rc2 == 2, "a Cyrillic name OFAC holds only in Latin is still found", f"rc={rc2}")
ok("FEDOROV" in out2.upper(),
   "the OFAC designation missed at 87.8 by a single romanisation is found",
   out2[-300:])
rc3, out3 = run(["check", "Фёдоров", "--type", "any", "--source", "uk-sanctions-list"])
ok("YODOROV" in out3.upper() or "FYODOROV" in out3.upper(),
   "the yo/e disagreement is searched both ways", out3[-200:])

print("\nDETERMINISM")
rc_a, a = run(["check", "Vladimir Putin", "--json"])
rc_b, b = run(["check", "Vladimir Putin", "--json"])
try:
    ja, jb = json.loads(a), json.loads(b)
except Exception:                                   # noqa: BLE001
    ja = jb = None
# age_hours is derived from the clock and rounds to a tenth of an hour, so it is
# expected to differ across runs; everything that bears on the result must not.
ok(ja is not None and ja["hits"] == jb["hits"] and rc_a == rc_b,
   "the same query twice returns the same candidates, in the same order")
ok(ja is not None and ja.get("complete") is True and "searched_source_ids" in ja,
   "JSON carries the completeness of the search at the top level, not only per source")
ok(ja is not None and [(s["id"], s["searched"], s["records"]) for s in ja["sources"]]
   == [(s["id"], s["searched"], s["records"]) for s in jb["sources"]],
   "the same query twice reports the same provenance")
try:
    parsed = json.loads(a)
except Exception as exc:                      # noqa: BLE001
    parsed = None
    print(f"          json error: {exc}")
ok(parsed is not None and parsed.get("hits") and parsed.get("sources"),
   "--json emits valid JSON carrying both the hits and the provenance",
   a[-200:] if parsed is None else "")
ok(rc_a == 2, "--json returns the same exit code as the text output")


# --------------------------------------------------------------------------
# an unhandled fault leaves by the gate, not by a traceback
# --------------------------------------------------------------------------
print("\n-- a fault inside a command --")

FAULT = r"""
import sys
sys.path.insert(0, %r)
import screen
def boom(args):
    raise RuntimeError("the list index exploded")
screen.cmd_check = boom
sys.argv = ["screen.py", "check", "Ivan Ivanov"]
sys.exit(screen.main())
"""
p = subprocess.run([sys.executable, "-c", FAULT % str(ROOT)],
                   capture_output=True, text=True, timeout=120)
ok(p.returncode == 3,
   "a command that raises exits 3, not a bare traceback exit 1",
   f"exit {p.returncode}")
ok("can be relied on as a completed search" in (p.stdout + p.stderr),
   "the fault says plainly that nothing here is a completed search")
ok("Traceback" not in p.stdout and "Traceback" not in p.stderr,
   "the fault spills no traceback on either stream",
   (p.stdout + p.stderr)[-200:])

# --------------------------------------------------------------------------
# one pathological row does not take the batch with it
# --------------------------------------------------------------------------
print("\n-- a batch row that raises --")

with tempfile.TemporaryDirectory() as td:
    csvp = Path(td) / "subjects.csv"
    csvp.write_text("name\nVladimir Putin\nBoom Subject\nRamzan Kadyrov\n", encoding="utf-8")
    # Only the poison row is faked. Every other row goes through the REAL
    # screen() against the REAL cache, so this proves the surviving rows were
    # genuinely screened — not that a loop continued over fabricated Outcomes.
    ROW = r"""
import sys
sys.path.insert(0, %r)
import screen
real = screen.screen
def flaky(name, args, srcs, meta=None, prefilter=True):
    if name.startswith("Boom"):
        raise ValueError("this row is poison")
    return real(name, args, srcs, meta, prefilter)
screen.screen = flaky
sys.argv = ["screen.py", "batch", %r]
sys.exit(screen.main())
"""
    p = subprocess.run([sys.executable, "-c", ROW % (str(ROOT), str(csvp))],
                       capture_output=True, text=True, timeout=120)
    out = p.stdout + p.stderr
    ok("Vladimir Putin" in out and "Ramzan Kadyrov" in out,
       "a row that raises does not stop the rows after it being screened", out[-300:])
    # The surviving rows were really screened: both are designated, and the
    # summary has to show their candidates.
    ok("PUTIN" in out.upper() and "KADYROV" in out.upper(),
       "and the surviving rows produced their real candidates", out[-400:])
    import re as _re
    counts = [int(m) for m in _re.findall(r"\s(\d+)\s+complete\b", out)]
    ok(len(counts) == 2 and all(c > 0 for c in counts),
       "two rows completed, each with candidates", f"counts={counts}")
    ok("this row is poison" in out,
       "the failing row is named, with what went wrong")
    ok("THIS BATCH IS NOT A CLEAN RESULT" in out,
       "a batch containing a failed row is not reported as a clean result")
    ok(p.returncode == 3,
       "a batch containing a failed row exits 3", f"exit {p.returncode}")
    ok("Traceback" not in p.stdout and "Traceback" not in p.stderr,
       "the batch aborts with no traceback on either stream", out[-200:])


# --------------------------------------------------------------------------
# the script gate — coverage-complete, not majority-based
# --------------------------------------------------------------------------
print("\nTHE SCRIPT GATE")
SCRIPT_CASES = [
    ("pure Arabic", "يحيى السنوار", 4),
    # One ASCII letter used to make the name "not predominantly non-Latin", which
    # skipped the refusal; the unchanged Arabic string was then reported to the
    # reader as its romanisation.
    ("Arabic with one Latin letter", "يحيى السنوار A", 4),
    ("Greek with a Latin word", "Ομοσπονδιακή κρατική επιχείρηση ANOSIT", 4),
    ("Chinese", "习近平", 4),
    ("Hebrew", "יחיא אלסינוואר", 4),
    ("Cyrillic — romanisable", "Кадыров Рамзан", 2),
    ("Cyrillic with a Latin letter", "Кадыров Рамзан A", 2),
    ("Latin with diacritics", "José Müller", 0),
    # Latin letters whose mark is inside the glyph do not decompose under NFKD,
    # so an ASCII-only test read them as a script this tool cannot romanise and
    # refused an EU designation its own published name.
    ("Latin with a stroked d", "Međunarodna agencija", 0),
    ("Polish l with stroke", "Łukasz Ćwiek", 0),
    ("Icelandic thorn and ash", "Þórður Ægisson", 0),
    ("German sharp s", "Straße Handels GmbH", 0),
]
for label, name, want in SCRIPT_CASES:
    rc, out = run(["check", name, "--source", "ofsi"])
    ok(rc == want, f"{label}: exits {want}", f"got {rc}: {out[-160:]}")
    if want == 4:
        ok("REFUSED" in out.upper() and "Nothing was screened" in out,
           f"{label}: nothing was searched and the record says so", out[-160:])
        ok("romanisation" not in out.lower() or "cannot" in out.lower(),
           f"{label}: an unromanised string is never offered as a romanisation",
           out[-200:])

# --------------------------------------------------------------------------
# status obeys the same freshness rule as screening
# --------------------------------------------------------------------------
print("\nSTATUS — one freshness decision, not two")
for bad in ("nan", "inf", "-inf", "-5", "0"):
    rc, out = run(["status", "--source", "ofsi", "--max-age-hours", bad])
    ok(rc == 4, f"status --max-age-hours {bad} is refused as check refuses it",
       f"rc={rc}: {out[-140:]}")
rc, out = run(["status", "--source", "ofsi", "--max-age-hours", "24"])
ok(rc in (0, 3), "status with a usable window still reports", f"rc={rc}")

# A manifest timestamped in the future must not read as fresh in either command.
fut = Path(tempfile.mkdtemp(prefix="sanctions-future-"))
shutil.copytree(Path(os.environ.get("SANCTIONS_DATA", Path.home() / ".claude/sanctions-data")),
                fut / "d", dirs_exist_ok=True)
mfile = fut / "d" / "meta.json"
if mfile.exists():
    m = json.loads(mfile.read_text())
    if m.get("ofsi", {}).get("ok"):
        m["ofsi"]["fetched_at"] = (datetime.now(timezone.utc)
                                   + timedelta(days=30)).isoformat(timespec="seconds")
        mfile.write_text(json.dumps(m))
        env = {"SANCTIONS_DATA": str(fut / "d")}
        rc, out = run(["status", "--source", "ofsi"], env=env)
        ok(rc == 3 and "STALE" in out,
           "a list fetched 30 days in the future is STALE in status, not ok",
           f"rc={rc}: {out[-160:]}")
        rc, out = run(["check", "Vladimir Putin", "--source", "ofsi"], env=env)
        ok(rc == 3, "and the same list makes a screen incomplete", f"rc={rc}")

# --------------------------------------------------------------------------
# batch --json was accepted and ignored
# --------------------------------------------------------------------------
print("\nBATCH --json")
bj = out_dir / "bj.csv"
bj.write_text("name\nVladimir Putin\nJane Ordinary\n", encoding="utf-8")
rc, raw = run(["batch", str(bj), "--json", "--source", "ofsi"])
try:
    doc = json.loads(raw)
except Exception as exc:                                  # noqa: BLE001
    doc = None
    print(f"          json error: {exc}")
ok(doc is not None, "batch --json emits JSON, not a human table", raw[-200:])
if doc:
    ok(doc.get("rows_screened") == 2 and len(doc.get("rows", [])) == 2,
       "with one object per row", str(doc)[:160])
    ok(doc.get("exit_code") == rc,
       "and the exit code it reports is the one the process returns",
       f"{doc.get('exit_code')} vs {rc}")
    ok(all("sources" in r and "complete" in r for r in doc["rows"]),
       "each row carrying its own provenance and completeness")
    ok(doc.get("total_hits", 0) > 0, "and the designated row is in it")

# --------------------------------------------------------------------------
# batch renders a row only after its record is delivered
# --------------------------------------------------------------------------
print("\nBATCH DELIVERY ORDER")
ro = out_dir / "readonly"
ro.mkdir(exist_ok=True)
os.chmod(ro, 0o500)
try:
    rc, out = run(["batch", str(bj), "--report-dir", str(ro), "--source", "ofsi"])
    putin = next((l for l in out.splitlines() if "Putin" in l and "|" not in l), "")
    ok("complete" not in putin,
       "a row whose record could not be written is not printed as complete", putin)
    ok("INCOMPLETE" in putin, "it is printed as INCOMPLETE", putin)
    ok(rc == 3, "and the batch exits 3", f"rc={rc}")
    ok("could not be written" in out, "with the delivery failure named", out[-200:])
finally:
    os.chmod(ro, 0o700)


# ============================================ terminal injection
print("\nTERMINAL INJECTION — publisher bytes are data on stdout too")
# The lists come over HTTPS from the authorities themselves, but a name is a
# string somebody else chose. An ANSI sequence in it recolours the line, a
# carriage return overwrites it, a bidi override reverses it — on the terminal
# the fee earner reads. Markdown had md(); stdout had nothing.


def tamper(cache, sid, mutate):
    """Rewrite one list in a throwaway cache through mutate(records) and re-bind
    the manifest to it, so the file passes the digest and count checks. This
    is what a hostile or careless PUBLISHER looks like to the reader — not
    tampering on disk, which the digest is there to catch."""
    p = cache / "norm" / f"{sid}.jsonl.gz"
    recs = [json.loads(l) for l in gzip.decompress(p.read_bytes()).decode("utf-8").split("\n")
            if l.strip()]
    mutate(recs)
    p.write_bytes(gzip.compress("".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in recs).encode("utf-8")))
    m = json.loads((cache / "meta.json").read_text())
    m[sid]["norm_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    m[sid]["records"] = len(recs)
    (cache / "meta.json").write_text(json.dumps(m))


def run_bytes(args, env=None):
    """stdout as bytes. run() decodes with universal newlines, which turns a
    lone \\r into \\n and would make an assertion about \\r pass for nothing."""
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable, str(ROOT / "screen.py")] + args,
                       capture_output=True, env=e, timeout=180)
    return p.returncode, p.stdout + p.stderr


HOSTILE = ("\x1b[32mNO CANDIDATE\x1b[0m\rZZQXTERMINAL \u202eTSET"
           "\x1b]8;;http://example.invalid\x07 VESSEL")
hostile = temp_cache(("ofsi",))
tamper(hostile, "ofsi", lambda recs: recs[0].update(
    name=HOSTILE, notes="\x1b[2J\x1b[H the screen was cleared\u2028and a line separator"))
rc, raw = run_bytes(["check", "NO CANDIDATE ZZQXTERMINAL TSET VESSEL", "--type", "any",
                     "--source", "ofsi", "--verbose"], env={"SANCTIONS_DATA": str(hostile)})
text = raw.decode("utf-8", "replace")
ok(rc == 2, "the designation with the hostile name is still found", f"rc={rc} {text[-300:]}")
ok(b"\x1b" not in raw, "no escape byte reaches the terminal")
ok(b"\r" not in raw, "no carriage return reaches the terminal")
ok("\u202e" not in text, "no bidi override reaches the terminal")
ok("\u2028" not in text, "no line separator reaches the terminal")
ok("NO CANDIDATE ZZQXTERMINAL TSET VESSEL" in text,
   "the letters of the name survive on one line — stripped, not censored", text[-400:])
ok("the screen was cleared and a line separator" in text,
   "and so do the notes", text[-400:])

rc, raw = run_bytes(["check", "NO CANDIDATE ZZQXTERMINAL TSET VESSEL", "--type", "any",
                     "--source", "ofsi", "--json"], env={"SANCTIONS_DATA": str(hostile)})
ok(b"\x1b" not in raw, "the JSON route escapes the byte by specification, so it is safe to cat")
try:
    parsed = json.loads(raw.decode("utf-8"))
    ok("\x1b[32m" in parsed["hits"][0]["record"]["name"],
       "while the parsed JSON still carries the published bytes for a program to see")
except (ValueError, KeyError, IndexError) as exc:
    ok(False, "the JSON route parses", f"{type(exc).__name__}: {exc}")

hostile_csv = out_dir / "hostile.csv"
hostile_csv.write_text('name\n"\x1b[31mNO CANDIDATE\x1b[0m\rZZQXTERMINAL TSET VESSEL"\n',
                       encoding="utf-8")
rc, raw = run_bytes(["batch", str(hostile_csv), "--default-type", "any", "--source", "ofsi"],
                    env={"SANCTIONS_DATA": str(hostile)})
ok(b"\x1b" not in raw and b"\r" not in raw,
   "a subject name from a CSV cannot rewrite the batch table either", repr(raw[-200:]))


# ==================================================== the fourth review's terminal points
print("\nTERMINAL, ROUND FIVE — 8-bit controls, bidi formatting, the outdir line, JSON")
HOSTILE2 = "\x9b31mZZQXEIGHTBIT\x9b0m \u2067ISOLATE\u2069 \u200eMARK\u202a"
hostile2 = temp_cache(("ofsi",))
tamper(hostile2, "ofsi", lambda recs: recs[0].update(name=HOSTILE2))
rc, raw = run_bytes(["check", "ZZQXEIGHTBIT ISOLATE MARK", "--type", "any",
                     "--source", "ofsi"], env={"SANCTIONS_DATA": str(hostile2)})
text = raw.decode("utf-8", "replace")
ok(rc == 2, "the designation is found", f"rc={rc} {text[-300:]}")
ok("\x9b" not in text and "\x9d" not in text, "no 8-bit control reaches the terminal")
ok("31m" not in text, "and its parameters do not reach it either — the sequence went whole")
ok(all(ch not in text for ch in "\u2067\u2069\u200e\u202a"),
   "no bidi isolate, mark or embedding reaches the terminal")
ok("ZZQXEIGHTBIT ISOLATE MARK" in text, "the letters survive on one line", text[-300:])

rc, raw = run_bytes(["check", "ZZQXEIGHTBIT ISOLATE MARK", "--type", "any", "--source", "ofsi",
                     "--json"], env={"SANCTIONS_DATA": str(hostile2)})
text = raw.decode("utf-8", "replace")
ok(all(ch not in text for ch in "\x9b\u2067\u200e\u202a"),
   "the JSON route carries no raw C1 or bidi character — they are \\uXXXX-escaped")
try:
    parsed = json.loads(text)
    ok("\u2067" in parsed["hits"][0]["record"]["name"] and "\x9b" in parsed["hits"][0]["record"]["name"],
       "while a parser reads the published characters back exactly")
except (ValueError, KeyError, IndexError) as exc:
    ok(False, "the JSON route still parses", f"{type(exc).__name__}: {exc}")

esc_dir = out_dir / "\x1b[31mreports\x1b[0m"
rc, raw = run_bytes(["batch", str(hostile_csv), "--default-type", "any", "--source", "ofsi",
                     "--report-dir", str(esc_dir)], env={"SANCTIONS_DATA": str(hostile)})
ok(b"\x1b" not in raw, "an escape in the --report-dir path does not reach the terminal",
   repr(raw[-200:]))
ok(esc_dir.exists() and list(esc_dir.glob("*.md")), "and the records were still written there")

print("\nBATCH --json WITH A BLANK ROW, AND A BAD REQUEST WITH ONLY BLANK ROWS")
blank_csv = out_dir / "blank.csv"
blank_csv.write_text("name,dob\n,1970\nLADY R,\n", encoding="utf-8")
rc, out = run(["batch", str(blank_csv), "--json", "--default-type", "any", "--source", "ofsi"])
try:
    j = json.loads(out.split("\nScreening records", 1)[0]) if out.lstrip().startswith("{") else json.loads(out)
    ok(any("no name" in p for p in j.get("problems", [])),
       "a blank row is reported inside the JSON, not printed across it", str(j.get("problems")))
    ok(j.get("rows_read") == 2 and j.get("rows_screened") == 1, "and the counts are right",
       f"{j.get('rows_read')}/{j.get('rows_screened')}")
except ValueError as exc:
    ok(False, "batch --json with a blank row still parses", f"{exc}: {out[:200]!r}")
ok(rc == 3, "a batch with a blank row is not a clean result", f"rc={rc}")
all_blank = out_dir / "all_blank.csv"
all_blank.write_text("name,dob\n,1970\n", encoding="utf-8")
rc, out = run(["batch", str(all_blank), "--threshold", "nan"])
ok(rc == 4, "a bad --threshold is a bad REQUEST even when every row is blank: exit 4", f"rc={rc} {out[-200:]}")
ok("Nothing was screened" in out, "and it says nothing was screened", out[-200:])
rc, out = run(["batch", str(all_blank), "--default-type", "bogus"])
ok(rc == 4, "a bad --default-type is refused up front: exit 4", f"rc={rc} {out[-200:]}")

print("\nMIXED SCRIPT — the fourth review's clean nil")
rc, out = run(["check", "Yury Viktorovich \u0424\u0435\u0434\u043e\u0440\u043e\u0432", "--source", "ofac-sdn"])
ok(rc == 2, "a Latin-majority query with a Cyrillic surname finds OFAC's Fedorov", f"rc={rc} {out[-300:]}")
ok("FEDOROV" in out.upper(), "by name", out[-300:])


# ==================================================================
# THE FIFTH REVIEW'S THREE CRITICALS
# Each is asserted twice: on the named counterexample, and as the
# general property whose absence let that counterexample exist. A
# test that only knows the one name it was given is a test that
# passes the day the parser files a different name in the wrong box.
# ==================================================================
print("\nCRITICAL 1 — A PUBLISHED SPELLING IS REACHABLE WHATEVER FIELD IT WAS FILED IN")
import matching as M
import sources as S
import screen as SC

rc, out = run(["check", "\u018fli \u018fkb\u0259r Salehi", "--type", "individual",
               "--source", "ofsi", "--json"])
try:
    j = json.loads(out)
    uids = {str(h["record"]["uid"]) for h in j.get("hits", [])}
    ok("10955" in uids, "the Azerbaijani spelling of Ali Akbar Salehi finds OFSI 10955",
       f"hits={j.get('total_hits')} uids={sorted(uids)[:5]}")
    exact = [h for h in j.get("hits", []) if str(h["record"]["uid"]) == "10955"]
    ok(bool(exact) and exact[0]["score"] == 100.0,
       "and scores 100: it IS the published name, not something like it",
       str(exact[:1])[:200])
except ValueError as exc:
    ok(False, "the Salehi query returns JSON", f"{exc}: {out[:200]!r}")

# The general property. Every published spelling that is Latin-dominant must be
# in the Latin index of its own source, whichever field the parser chose. This
# is exhaustive over every list on the machine, and it is what the named test
# above is a single instance of.
# Two corpus properties, neither of which may be stated in the implementation's
# own terms. The first version of this assertion skipped every candidate for
# which `M.is_native()` said "native" — the same predicate the index uses to
# decide — so it could only ever agree with the code, and it could not see
# `Černé září`, a Latin-script name that predicate wrongly called native.
def _all_latin_letters(s):
    """Independent of is_native(): EVERY letter is a Latin-script letter, by
    Unicode's own naming, with no majority rule anywhere in it."""
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    for c in letters:
        try:
            if not unicodedata.name(c).startswith("LATIN"):
                return False
        except ValueError:
            return False
    return True

unreachable, siloed, checked = [], [], 0
for sid in ("uk-sanctions-list", "ofsi", "un", "eu", "ofac-sdn", "ofac-cons"):
    try:
        recs = list(S.load_records(sid))
    except Exception:
        continue
    for rec, names, _mask, native in SC._index(sid, recs):
        latin = {n for _c, n, _i, _e in names}
        keys = {k for _c, k in native}
        for cand in ([rec.get("name", "")] + list(rec.get("aliases", []))
                     + list(rec.get("nonlatin", []))):
            if not cand:
                continue
            checked += 1
            n, k = M.normalise(cand), M.native_key(cand)
            # (1) every published spelling is reachable through SOME index
            if n not in latin and k not in keys:
                unreachable.append((sid, rec.get("uid"), cand))
            # (2) a wholly Latin-script spelling is reachable through the LATIN
            #     one, because that is the index a Latin query opens
            elif _all_latin_letters(cand) and n and n not in latin:
                siloed.append((sid, rec.get("uid"), cand))
ok(not unreachable,
   f"every published spelling on every list is reachable through some index "
   f"({checked:,} spellings checked)",
   f"{len(unreachable)} unreachable, first: {unreachable[:3]}")
ok(not siloed,
   "and every wholly Latin-script spelling is reachable through the LATIN index, "
   "whatever field it was filed in and whatever the majority rule says",
   f"{len(siloed)} siloed, first: {siloed[:3]}")

print("\nN4 — ASCII IS NOT A SCRIPT TEST")
ok(not M.is_native("\u010cern\u00e9 z\u00e1\u0159\u00ed"),
   "Latin script with Czech diacritics is not 'written outside the Latin script'",
   f"is_native={M.is_native('\u010cern\u00e9 z\u00e1\u0159\u00ed')}")
ok(M.is_native("\u0410\u043b\u0435\u043a\u0441\u0430\u043d\u0434\u0440 \u041f\u0435\u0442\u0440\u043e\u0432"),
   "and Cyrillic still is")
ok(M.is_latin_letter("\u010c") and M.is_latin_letter("\u018f") and M.is_latin_letter("A")
   and not M.is_latin_letter("\u0410") and not M.is_latin_letter("\u4e2d"),
   "the classifier answers by Unicode script, not by ASCII membership")
_eu = list(S.load_records("eu"))
_q = M.normalise("Cerne zari")
_own = [str(r.get("uid")) for r, names, _m, _n in SC._index("eu", _eu)
        for _c, n, _i, _e in names if n == _q]
ok("201" in _own,
   "and the folded spelling anyone without a Czech keyboard would type reaches EU 201",
   f"q={_q!r} own={_own}")

print("\nCRITICAL 2 — ROMANISATION ADDS QUERY FORMS, IT DOES NOT REPLACE THEM")
rc, out = run(["check", "JS\u0421 Krasmash", "--type", "entity", "--source", "eu", "--json"])
searched = False
try:
    j = json.loads(out)
    searched = any(s["id"] == "eu" and s["searched"] for s in j.get("sources", []))
    if searched:
        uids = {str(h["record"]["uid"]) for h in j.get("hits", [])}
        ok("179301" in uids,
           "the EU alias written with a Cyrillic homoglyph finds its own listing (EU 179301)",
           f"hits={j.get('total_hits')} uids={sorted(uids)[:5]}")
except ValueError as exc:
    ok(False, "the Krasmash query returns JSON", f"{exc}: {out[:200]!r}")
if not searched:
    # The EU endpoint is down, so the list is — correctly — not being searched.
    # That is no reason to leave the repair unasserted: put the same question to
    # the last good data on disk. The query form and the published spelling must
    # normalise to one string, which is what makes the record its own exact hit.
    q = M.normalise("JS\u0421 Krasmash")
    own = [str(rec.get("uid")) for rec, names, _m, _n in SC._index("eu", list(S.load_records("eu")))
           for _c, n, _i, _e in names if n == q]
    ok("179301" in own,
       "EU 179301's published alias and the query reduce to one form, on the last good "
       "EU data (the list itself is not searchable: the publisher is returning HTTP 500)",
       f"q={q!r} own={own}")

# The general property, at the point the bug lived: for a Latin-dominant query
# the original normalised form must survive into the exact set alongside the
# romanisations; for a native-dominant one it must NOT, because homoglyph
# folding leaves nonsense there.
class _A:
    type, threshold, limit = "any", 85.0, 40
    max_age_hours, source = 24.0, None

def _spy(name):
    """The IDENTITY keys, the REACHABILITY keys, and the count of fuzzy query
    forms, captured where the romanisation branch decides between them.

    Three sets, not two, since the seventh review: a fold across scripts may
    reach a listing without being that listing's name."""
    seen = {}
    real = SC._scan

    def spy(indexed, outcome, hits, src, kind, args, q_native, queries, qmask, need,
            prefilter, q_exact=frozenset(), q_reach=frozenset()):
        seen["exact"], seen["reach"], seen["n"] = set(q_exact), set(q_reach), len(queries)
        raise RuntimeError("stop")
    SC._scan = spy
    try:
        SC.screen(name, _A(), [s for s in S.SOURCES if s.id == "ofsi"], S.load_meta())
    finally:
        SC._scan = real
    # A spy whose signature no longer matches the real call gets its TypeError
    # swallowed by screen()'s per-source guard, and every assertion built on it
    # then reads an empty set and fails for a reason that has nothing to do with
    # the behaviour under test. Say so here rather than there.
    if "exact" not in seen:
        raise AssertionError(f"the _scan spy was never reached for {name!r} — signature drift")
    return seen


def _query_forms(name):
    s = _spy(name)
    return s["exact"], s["n"]


def _query_count(name):
    return _spy(name)["n"]


def _exact_forms(name):
    return _spy(name)["exact"]


def _reach_forms(name):
    return _spy(name)["reach"]

latin_mixed = _exact_forms("JS\u0421 Krasmash")
ok("JSC KRASMASH" in latin_mixed,
   "a Latin query carrying a Cyrillic homoglyph keeps its own normalised form",
   str(sorted(latin_mixed))[:200])
ok(len(latin_mixed) > 1, "and the romanisations are searched as well, not instead",
   str(sorted(latin_mixed))[:200])
native_only, native_fuzzy = _query_forms("\u041a\u0430\u0434\u044b\u0440\u043e\u0432")
ok(native_fuzzy == 1,
   "a native-dominant query does NOT search its homoglyph residue as a fuzzy name "
   "(one query form, the romanisation)", f"{native_fuzzy} fuzzy forms")
_kad_reach = _reach_forms("\u041a\u0430\u0434\u044b\u0440\u043e\u0432")
ok("KA POB" not in native_only,
   "the residue is NOT an identity key: the query is not a designation's name because "
   "its letters happen to look like one", str(sorted(native_only))[:200])
ok("KA POB" in _kad_reach,
   "but it is retained as a REACHABILITY key — it cannot manufacture a fuzzy candidate, "
   "and a listing literally published as that string is still reached",
   str(sorted(_kad_reach))[:200])
ok(any("KADYROV" in f or "KADIROV" in f for f in native_only),
   "and it is searched by romanisation", str(sorted(native_only))[:200])

print("\nN5 — A NATIVE-DOMINANT QUERY IS STILL SEARCHED AS ITSELF, BUT IS NOT AN IDENTITY")
_native_mixed = _reach_forms("\u0421\u0421\u0421 AB")   # three Cyrillic homoglyphs
ok("CCC AB" in _native_mixed,
   "the folded form of a native-dominant query survives as a reachability key: it can "
   "still reach a listing published as that spelling", str(sorted(_native_mixed)))
ok("CCC AB" not in _exact_forms("\u0421\u0421\u0421 AB"),
   "and it is not an identity key, because the query as typed is not that name",
   str(sorted(_exact_forms("\u0421\u0421\u0421 AB"))))
_fuzzy = _query_count("\u0421\u0421\u0421 AB")
ok(_fuzzy == 1,
   "but it is withheld from the fuzzy queries, so residue cannot manufacture candidates",
   f"{_fuzzy} fuzzy query forms")

print("\nN6 — A NAME PUBLISHED IN ITS OWN SCRIPT IS AN IDENTITY TOO")
rc, out = run(["check", "\u0423\u043c\u0430\u0440\u043e\u0432 \u0414\u043e\u043a\u0443 "
               "\u0425\u0430\u043c\u0430\u0442\u043e\u0432\u0438\u0447",
               "--type", "individual", "--source", "un", "--json"])
try:
    j = json.loads(out)
    top = (j.get("hits") or [None])[0]
    ok(top is not None and top["exact"] and top["score"] == 100.0,
       "an exact native-script match reports exact:true, as a Latin one does",
       str(top)[:200] if top else "no hits")
except ValueError as exc:
    ok(False, "the native identity query returns JSON", f"{exc}: {out[:200]!r}")

print("\nR11-2 — INITIALS RUN TOGETHER ARE THE ORDINARY SPELLING")
# The UK publishes "P.K.T. MUNGMEE CO., LTD". A person types "PKT MUNGMEE CO
# LTD". Token by token the initials score as fragments: 79.9 against a threshold
# of 88, a complete nil at exit 0, on a healthy cache, for the ordinary spelling
# of a designated company. §57 fixed the prefilter; this is the scorer, one layer
# down, and the run-together branch only ever looked when ONE side was a single
# token.
for _q, _uid in (("PKT MUNGMEE CO LTD", "RUS3637"),):
    rc, out = run(["check", _q, "--type", "any", "--source", "uk-sanctions-list", "--json"])
    try:
        j = json.loads(out)
        ok(rc == 2 and any(str((h.get("record") or {}).get("uid")) == _uid
                           for h in (j.get("hits") or [])),
           f"{_q!r} finds the designation the list spells with stops",
           f"exit {rc}, {j.get('total_hits')} hits")
    except ValueError as exc:
        ok(False, "the initials query returns JSON", str(exc)[:120])
ok(M.score("PKT MUNGMEE CO LTD", "P K T MUNGMEE CO LTD", "entity") == 100.0,
   "and the two spellings score as the same name")
ok(M.score("PKT", "P K T MUNGMEE CO LTD", "entity") < 88.0,
   "a bare set of initials does not match the whole company name",
   str(M.score("PKT", "P K T MUNGMEE CO LTD", "entity")))

print("\nR11-3 — NOTHING BIOGRAPHICAL MAY TOUCH THE SELECTION, TIE-BREAKS INCLUDED")
# Rank survived in the sort key as a tie-break, and at equal name scores a
# tie-break IS a selection: 34 of the 40 shown for "Abdul" changed on supplying
# a date of birth, every one of them scoring 100.0.
_base = None
for _extra, _label in (([], "no biography"),
                       (["--dob", "1975-03-02"], "a conflicting date of birth"),
                       (["--nationality", "RU"], "a nationality")):
    rc, out = run(["check", "Abdul", "--type", "any", "--json"] + _extra)
    try:
        j = json.loads(out)
        keys = {(h["record"].get("source"), str(h["record"].get("uid"))) for h in j.get("hits", [])}
        if _base is None:
            _base = keys
            ok(len(keys) > 1, "the tie cohort is large enough to test", str(len(keys)))
        else:
            ok(keys == _base,
               f"the designations shown are the same with {_label}",
               f"{len(keys ^ _base)} differ")
    except ValueError as exc:
        ok(False, f"the {_label} query returns JSON", str(exc)[:120])

print("\nR11-4 — SOUTH SUDAN IS NOT SUDAN")
_ss = {"nationality": ["South Sudan"], "address": "", "regime": ""}
ok(SC.country_verdict("SD", _ss)[1] == 0.0,
   "a Sudan code does not match a South Sudan listing — a different state, a "
   "different regime, on the same lists", str(SC.country_verdict("SD", _ss)))
ok(SC.country_verdict("SS", _ss)[1] > 0, "the South Sudan code does")
ok(SC.country_verdict("SD", {"nationality": ["Sudan"], "address": "", "regime": ""})[1] > 0,
   "and Sudan still matches Sudan")
ok(SC.country_verdict("RU", {"nationality": ["RUSSIAN FEDERATION"],
                             "address": "", "regime": ""})[1] > 0,
   "while a country named more fully than the query still matches")

print("\nR11-5 — THE DURABLE RECORD NAMES THE CODE THAT WROTE IT")
_rp = str(Path(tempfile.mkdtemp(prefix="sanctions-rec-")) / "r.md")
rc, _ = run(["check", "Umarov", "--type", "any", "--source", "un", "--report", _rp])
_rec = Path(_rp).read_text()
ok(f"Engine generation **{S.ENGINE_VERSION}**" in _rec,
   "the written record states the engine generation that produced it")
for _mod in ("screen.py", "sources.py", "matching.py"):
    ok(f"`{_mod}`" in _rec, f"and the digest of {_mod}")

print("\nR10-6 — A COUNTRY IS WORDS, NOT A SUBSTRING")
_ru = {"nationality": ["Russia"], "address": "", "regime": ""}
_us = {"nationality": ["United States"], "address": "", "regime": ""}
ok(SC.country_verdict("US", _ru)[1] == 0.0,
   "'US' is inside 'RUSSIA' and that is not a country match",
   str(SC.country_verdict("US", _ru)))
ok(SC.country_verdict("US", {"nationality": ["Belarus"], "address": "", "regime": ""})[1] == 0.0,
   "nor inside 'BELARUS'")
ok(SC.country_verdict("US", _us)[1] > 0, "'US' does match the United States")
ok(SC.country_verdict("RU", _ru)[1] > 0, "and a code is expanded before it is compared")
_flagged = 0
for _sid in ("uk-sanctions-list", "ofsi", "un", "eu", "ofac-sdn", "ofac-cons"):
    for _r in S.load_records(_sid):
        if SC.country_verdict("US", _r)[1] > 0:
            _flagged += 1
ok(_flagged < 500,
   "and across the whole corpus 'US' no longer promotes thousands of Russian "
   "designations three points up the page", f"{_flagged:,} flagged, was 5,989")

print("\nR10-7 — A NARROWING SAYS WHAT IT WITHHELD")
rc, out = run(["check", "Mohammed Ali", "--type", "individual", "--json"])
try:
    j = json.loads(out)
    ok(any("NOT compared" in c for c in (j.get("caveats") or [])),
       "screening one type discloses how many designations of other types were "
       "not compared — the default was `individual`, which withholds 46% of the "
       "corpus while the record said Complete", str(j.get("caveats"))[:180])
except ValueError as exc:
    ok(False, "the narrowed query returns JSON", str(exc)[:120])
rc, out = run(["check", "Mohammed Ali", "--json"])
try:
    j = json.loads(out)
    ok(j["subject"]["type"] == "any",
       "and the default reaches every type, so a nil return means the whole list",
       str(j["subject"]["type"]))
    ok(not any("NOT compared" in c for c in (j.get("caveats") or [])),
       "with nothing withheld to disclose")
except ValueError as exc:
    ok(False, "the default query returns JSON", str(exc)[:120])

print("\nR10-3 — THE FILTER MAY NOT EXCLUDE WHAT THE SCORER CALLS EXACT")
# OFAC SDN 48715 is a designated VESSEL published as "K M A", with no other
# name. "KMA" scores 100 against it. The two strings share no bigram, so the
# prefilter discarded the record before the scorer's run-together branch —
# written for exactly this — could run. Six of six lists searched, no candidate,
# exit 0, on the largest list the tool carries. Ten reviews missed it because
# every test had always queried a name the way the publisher spells it.
rc, out = run(["check", "KMA", "--type", "vessel", "--source", "ofac-sdn", "--json"])
try:
    j = json.loads(out)
    ok(j.get("total_hits", 0) > 0 and rc == 2,
       "a name run together still finds the designation published with spaces",
       f"exit {rc}, {j.get('total_hits')} hits")
    ok(any(str((h.get("record") or {}).get("uid")) == "48715" for h in (j.get("hits") or [])),
       "and it is the right designation", str((j.get("hits") or [{}])[0])[:120])
except ValueError as exc:
    ok(False, "the run-together query returns JSON", f"{exc}: {out[:160]!r}")

# The general property, over the whole corpus: no published spelling may be
# excluded by the filter from a query that scores 100 against it.
_missed = []
for _sid in ("ofac-sdn", "uk-sanctions-list"):
    for _r in S.load_records(_sid):
        for _f in [_r.get("name", "")] + list(_r.get("aliases", [])):
            _n = M.normalise(_f)
            if not _n or " " not in _n or len(_n) > 12:
                continue
            _j = _n.replace(" ", "")
            _qm = M.bigram_mask(_j)
            if not M.passes(_qm, M.bigram_mask(_n), M.prefilter_threshold(_qm)):
                _missed.append((_sid, _r.get("uid"), _f))
ok(not _missed,
   "no short published spelling is filtered out of its own run-together query",
   f"{len(_missed)} missed, first {_missed[:2]}")

print("\nR10-4 — BIOGRAPHY ORDERS THE PAGE, IT DOES NOT CHOOSE IT")
rc_a, out_a = run(["check", "Mohammed Ali", "--type", "individual", "--json"])
rc_b, out_b = run(["check", "Mohammed Ali", "--type", "individual",
                   "--dob", "1975-03-02", "--json"])
try:
    _a, _b = json.loads(out_a), json.loads(out_b)
    _ua = {h["record"]["uid"] for h in _a.get("hits", [])}
    _ub = {h["record"]["uid"] for h in _b.get("hits", [])}
    ok(not (_ua - _ub),
       "supplying a conflicting date of birth removes no designation from view — "
       "selection is by the name, and only the order is by rank",
       f"{len(_ua - _ub)} dropped of {len(_ua)}")
except ValueError as exc:
    ok(False, "the date-of-birth comparison returns JSON", str(exc)[:120])

print("\nR10-5 — A SPELLING THAT ALREADY REACHES LATIN IS SEARCHED, NOT REFUSED")
# The UK and OFSI publish Syria's president as "Baššār Ḥāfiẓ al-ʾAsad". The half
# ring is U+02BE, category Lm, with no Latin name — so the script gate refused
# the request at exit 4, under a message saying a designation could not be found
# if one existed. It normalises to BASSAR HAFIZ AL ASAD, which is the string in
# the index.
rc, out = run(["check", "Ba\u0161\u0161\u0101r \u1e24\u0101fi\u1e93 al-\u02beAsad",
               "--type", "any", "--json"])
ok(rc == 2, "the publisher's own accented spelling is screened, not refused", f"exit {rc}")
for _bad, _why in (("\u674e\u660e", "Han"), ("\u0645\u062d\u0645\u062f", "Arabic")):
    _rc, _ = run(["check", _bad, "--type", "any"])
    ok(_rc == 4, f"while a name reaching no Latin at all is still refused ({_why})",
       f"exit {_rc}")

print("\nR7-3 — REACHING A NAME IS NOT BEING IT")
# The query is seven Cyrillic letters that LOOK like TAEK PAK, which is a
# published UK alias. Screening it is right — that is how a name typed in
# homoglyphs to slip past a list gets caught. Calling it the designation's name
# is not, and `exact` sorts first and escapes --limit.
rc, out = run(["check", "\u0422\u0410\u0415\u041a \u0420\u0410\u041a", "--type", "any",
               "--source", "uk-sanctions-list", "--json"])
try:
    j = json.loads(out)
    hits = j.get("hits") or []
    top = hits[0] if hits else None
    ok(top is not None and top["score"] == 100.0,
       "a query folded across scripts still REACHES the listing it folds to",
       str(top)[:160] if top else "no hits")
    ok(top is not None and top["exact"] is False,
       "but it is not reported as an identity: the record does not carry that spelling",
       str(top)[:160] if top else "no hits")
    _rec = (top or {}).get("record") or {}
    _all = [_rec.get("name", "")] + list(_rec.get("aliases", [])) + list(_rec.get("nonlatin", []))
    ok("\u0422\u0410\u0415\u041a \u0420\u0410\u041a" not in _all,
       "and the assertion above is worth making: the record really has no such spelling")
    ok(rc == 2, "a reachability match is still a candidate, exit 2", f"exit {rc}")
except ValueError as exc:
    ok(False, "the homoglyph query returns JSON", f"{exc}: {out[:200]!r}")

print("\nR7-4 — ASCII IS NOT A SCRIPT, AND NEITHER IS THE CODEPOINT AS TYPED")
# is_latin_letter() asked the codepoint. FULLWIDTH LATIN CAPITAL LETTER A does
# not BEGIN "LATIN", so a fullwidth spelling was filed outside the Latin script
# even though normalise() had already decomposed it to plain "A".
for ch, want, why in (("\uff21", True, "fullwidth Latin"),
                      ("\u2102", True, "letterlike double-struck C"),
                      ("\U0001d400", True, "mathematical bold A"),
                      ("\u216b", True, "Roman numeral twelve"),
                      ("\u010c", True, "Latin C with caron"),
                      ("\u0410", False, "Cyrillic A"),
                      ("\u674e", False, "Han"),
                      ("\u0627", False, "Arabic alef")):
    ok(M.is_latin_letter(ch) is want,
       f"{why} is {'Latin' if want else 'not Latin'}", repr(ch))
ok(not M.is_native("\uff21\uff23\uff2d\uff25") and M.normalise("\uff21\uff23\uff2d\uff25") == "ACME",
   "a fullwidth spelling normalises to ACME and is classified Latin, so an ordinary "
   "ACME query looks for it in the index it is actually in")
ok(not M.has_native_letters("\uff21\uff23\uff2d\uff25"),
   "and it does not also claim a native key nothing can query")

print("\nR7-6 — THE EXACT COHORT IS BOUNDED, AND THE BOUND SAYS SO")
rc, out = run(["check", "ANSAR AL SHARIA", "--type", "any", "--limit", "1", "--json"])
try:
    j = json.loads(out)
    _ex = [h for h in (j.get("hits") or []) if h["exact"]]
    ok(len(j.get("hits") or []) >= len(_ex) and len(_ex) > 1,
       "--limit 1 still returns every exact identity, not one of them",
       f"{len(_ex)} exact of {len(j.get('hits') or [])} shown")
    ok(all(h["exact"] for h in (j.get("hits") or [])[:len(_ex)]),
       "and they are the ones at the top")
except ValueError as exc:
    ok(False, "the fan-out query returns JSON", f"{exc}: {out[:200]!r}")

_real_cap = SC.MAX_EXACT_SHOWN
SC.MAX_EXACT_SHOWN = 2
try:
    class _C:
        type, threshold, limit = "any", 85.0, 1
        max_age_hours, source = 999999.0, None
        dob = nationality = client = matter = ""
        include_delisted = False
    _o = SC.screen("ANSAR AL SHARIA", _C(),
                   [S.BY_ID["uk-sanctions-list"], S.BY_ID["un"], S.BY_ID["ofac-sdn"]],
                   S.load_meta())
finally:
    SC.MAX_EXACT_SHOWN = _real_cap
ok(_o.exact_total > 2 and _o.exact_withheld == _o.exact_total - 2,
   "beyond the cap the withheld identities are COUNTED, not dropped in silence",
   f"total {_o.exact_total}, shown 2, withheld {_o.exact_withheld}")
ok(any("NOT shown" in c for c in _o.caveats),
   "and every route carries a caveat saying so, because a withheld identity that "
   "announces itself is a display bound and one that does not is the defect",
   str(_o.caveats)[:200])

# ...and the converse, which was the SOURUH COMPANY defect: a native-script name
# filed under `aliases` must still carry a native key.
unkeyed = []
for sid in ("ofsi", "eu", "un"):
    try:
        recs = S.load_records(sid)
    except Exception:
        continue
    for rec, _names, _mask, native in SC._index(sid, recs):
        keys = {k for _c, k in native}
        for cand in list(rec.get("aliases", [])):
            if cand and M.has_native_letters(cand):
                k = M.native_key(cand)
                if k and k not in keys:
                    unkeyed.append((sid, rec.get("uid"), cand))
ok(not unkeyed,
   "a native-script name filed under `aliases` keeps its native key (the SOURUH defect)",
   f"{len(unkeyed)} unkeyed, first: {unkeyed[:3]}")


print("\nCRITICAL 3 — A PUBLISHED NAME CANNOT LEAVE A LISTED DESIGNATION UNSEEN")
# Run through the REAL refresh(), against an isolated cache, with the download
# stubbed. The previous version of this block called alias_removals() directly
# and passed it an explicit `previous` — but refresh() nulls that value under
# the shrink override, so the test asserted the opposite of the path it named
# and passed while the behaviour was false. It also wrote the LIVE ledger
# before testing redirection, which under a sandboxed reviewer raised
# PermissionError and stopped the suite. Both are why this now isolates first
# and asserts through refresh().
import csv as _csv

_sdn = S.BY_ID["ofac-sdn"]
_iso = Path(tempfile.mkdtemp(prefix="sanctions-c3-"))
_live = Path(os.environ.get("SANCTIONS_DATA", Path.home() / ".claude" / "sanctions-data"))
_saved = (S.DATA, S.RAW, S.NORM, S.META, S.download)
_ledger_before = None
_lp = S.inv_dir() / "ofac-sdn.aliases.json.gz"
if _lp.exists():
    _ledger_before = hashlib.sha256(_lp.read_bytes()).hexdigest()

try:
    (_iso / "raw").mkdir(parents=True)
    (_iso / "norm").mkdir(parents=True)
    for f in (_sdn.filename, _sdn.aux.get("alt_filename", "")):
        if f and (_live / "raw" / f).exists():
            shutil.copy(_live / "raw" / f, _iso / "raw" / f)
    shutil.copy(_live / "norm" / "ofac-sdn.jsonl.gz", _iso / "norm" / "ofac-sdn.jsonl.gz")
    _meta = json.loads((_live / "meta.json").read_text())
    (_iso / "meta.json").write_text(json.dumps({"ofac-sdn": _meta["ofac-sdn"]}))
    S.DATA, S.RAW, S.NORM = _iso, _iso / "raw", _iso / "norm"
    # The manifest too. Redirecting DATA alone left refresh() writing an
    # isolated meta.json and reading the live one — the seventh review caught
    # it, and sources.meta_path() now resolves at call time so the omission
    # cannot silently recur; this states the intention anyway.
    S.META = _iso / "meta.json"
    S.download = lambda src: {"stub": 0}

    _alt = S.RAW / _sdn.aux.get("alt_filename", "")
    _prim = S.RAW / _sdn.filename
    _alt0, _prim0 = _alt.read_bytes(), _prim.read_bytes()

    def _refresh(env=None):
        """The REAL path, manifest commit and all.

        This called refresh() and threw the manifest away. It was invisible for
        as long as every committed refresh rewrote byte-identical output — the
        stale digest still matched — and it hid the whole question of whether
        the manifest a screen later reads describes the list that was actually
        installed. refresh_and_commit() is what the CLI calls."""
        for k, v in (env or {}).items():
            os.environ[k] = v
        try:
            return S.refresh_and_commit(_sdn)
        finally:
            for k in (env or {}):
                os.environ.pop(k, None)

    def _finds(name, uid=None):
        """Does the CACHE ON DISK still return THIS designation — by uid, on a
        complete search, with the process telling its caller so?

        `total_hits > 0` was the whole test, and it is satisfied by any fuzzy
        neighbour scoring over the threshold. It says nothing about which
        designation came back, nothing about whether the lists were actually
        read, and nothing about what the exit code told a script. All three are
        the point."""
        e = dict(os.environ, SANCTIONS_DATA=str(_iso))
        r = subprocess.run([sys.executable, str(ROOT / "screen.py"), "check", name,
                            "--type", "entity", "--json", "--source", "ofac-sdn",
                            "--max-age-hours", "999999"],
                           capture_output=True, text=True, env=e, timeout=300)
        try:
            j = json.loads(r.stdout)
        except ValueError:
            return False
        if not j.get("complete") or r.returncode != 2:
            return False
        hits = j.get("hits") or []
        if uid is None:
            return bool(hits)
        return any(str((h.get("record") or {}).get("uid")) == str(uid) for h in hits)

    def _retained(name):
        """Is the spelling still in the FILE that was kept?

        Distinct from _finds on purpose. After a refused refresh the list is
        marked not searched — correctly, because a source that failed must never
        read as "no hits" — so a screen against it is incomplete and exits 3, not
        2. What the quarantine promises is that the last good FILE is untouched,
        and that is what this asks."""
        key = M.normalise(name)
        for r in S.load_records("ofac-sdn"):
            for f in [r.get("name", "")] + list(r.get("aliases", [])):
                if M.normalise(f) == key:
                    return True
        return False

    def _not_searched(name):
        """After a refusal the tool must say the list was NOT searched — never
        report a clean nil against a list whose refresh it has just quarantined."""
        e = dict(os.environ, SANCTIONS_DATA=str(_iso))
        r = subprocess.run([sys.executable, str(ROOT / "screen.py"), "check", name,
                            "--type", "entity", "--json", "--source", "ofac-sdn",
                            "--max-age-hours", "999999"],
                           capture_output=True, text=True, env=e, timeout=300)
        try:
            j = json.loads(r.stdout)
        except ValueError:
            return False
        return j.get("complete") is False and r.returncode == 3

    def _edit_alt(fn):
        rows = list(_csv.reader(_alt0.decode("utf-8-sig", "replace").splitlines()))
        with open(_alt, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(fn(rows))

    def _drop(rows):
        out, done = [], False
        for r in rows:
            if not done and len(r) > 3 and r[0].strip() == "1287" \
                    and "CUBAN FREIGHT ENTERPRISE" in r[3].upper():
                done = True
                continue
            out.append(r)
        return out if done else rows

    def _swap(rows):
        out, done = [], False
        for r in rows:
            if not done and len(r) > 3 and r[0].strip() == "1287" \
                    and "CUBAN FREIGHT ENTERPRISE" in r[3].upper():
                r = list(r); r[3] = "CUBAN HAULAGE ENTERPRISE"; done = True
            out.append(r)
        return out if done else rows

    def _swap_primary():
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, done = [], False
        for r in rows:
            if not done and len(r) > 11 and r[0].strip() == "424":
                r = list(r); r[1] = "ENTIRELY DIFFERENT TRADING NAME"; done = True
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return done

    def _reset():
        _alt.write_bytes(_alt0); _prim.write_bytes(_prim0)

    # A version-1 ledger has no primary names in it and must not be trusted.
    S.write_alias_inventory("ofac-sdn", {"1287": ["CUBAN FREIGHT ENTERPRISE"]})
    _lpath = S.inv_dir() / "ofac-sdn.aliases.json.gz"
    _raw_v1 = json.dumps({"1287": ["CUBAN FREIGHT ENTERPRISE"]}).encode()
    import gzip as _gz
    with open(_lpath, "wb") as fh:
        with _gz.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
            gz.write(_raw_v1)
    ok(S.read_alias_inventory("ofac-sdn") is None,
       "a version-1 ledger, which had no primary names in it, reads as ABSENT not as data")

    _reset()
    e = _refresh()
    ok(e.get("ok") is True, "a clean refresh commits and rebuilds the ledger at the current version",
       (e.get("error") or "")[:160])
    _inv = S.read_alias_inventory("ofac-sdn")
    ok(_inv is not None and len(_inv) > 1000, "the rebuilt ledger covers the whole list",
       str(len(_inv or {})))
    ok((_inv.get("424") or {}).get("names") == ["BOUTIQUE LA MAISON"],
       "and a designation's PRIMARY name is in it — the ledger is of published names, "
       "not of aliases", str(_inv.get("424")))
    ok((_inv.get("424") or {}).get("ref") == "424" and (_inv.get("424") or {}).get("fp"),
       "alongside the publisher's own reference and a fingerprint of the fields that "
       "are not the name — the two things a substitution in place cannot preserve",
       str(_inv.get("424")))

    # N3 — a primary-name substitution, which needs no override and nothing corrupt
    _reset(); _swap_primary()
    e = _refresh()
    ok(e.get("ok") is False, "a substituted PRIMARY name is refused through the real refresh",
       str(e.get("error"))[:160])
    ok(_retained("BOUTIQUE LA MAISON"), "and the designation is still in the retained file")
    ok(_not_searched("BOUTIQUE LA MAISON"),
       "and the tool reports the list as NOT SEARCHED, exit 3 — never a clean nil against a "
       "list whose refresh it has just quarantined")

    # the two round-five attacks, now through refresh() rather than the function
    _reset(); _edit_alt(_drop)
    e = _refresh()
    ok(e.get("ok") is False, "a single deleted alias is refused through the real refresh",
       str(e.get("error"))[:160])
    ok("CUBAN FREIGHT ENTERPRISE" in str(e.get("error")), "and the refusal names what went",
       str(e.get("error"))[:160])
    _reset(); _edit_alt(_swap)
    e = _refresh()
    ok(e.get("ok") is False, "a substituted alias is refused even though every count is unchanged",
       str(e.get("error"))[:160])

    # N1 — the shrink override stands down the COUNT rules, not this one
    _reset(); _edit_alt(_drop)
    e = _refresh({"SANCTIONS_ALLOW_SHRINK": "1"})
    ok(e.get("ok") is False,
       "SANCTIONS_ALLOW_SHRINK=1 does NOT authorise a name to vanish with it",
       str(e.get("error"))[:160])
    ok(_retained("CUBAN FREIGHT ENTERPRISE"), "and the name is still in the retained file")

    # N2 — absent and corrupt ledgers fail CLOSED, rebuilt from the last good cache
    _reset(); _edit_alt(_drop)
    _lpath.write_bytes(b"this is not gzip at all")
    e = _refresh()
    ok(e.get("ok") is False, "a CORRUPT ledger fails closed: the loss is still caught",
       str(e.get("error"))[:160])
    _reset(); _edit_alt(_drop)
    _lpath.unlink(missing_ok=True)
    e = _refresh()
    ok(e.get("ok") is False, "a MISSING ledger fails closed too, rebuilt from the last good cache",
       str(e.get("error"))[:160])
    ok(_retained("CUBAN FREIGHT ENTERPRISE"), "and through all of it the name stays in the file")

    print("\nR7-1 — AN EMPTY LEDGER IS NOT A LEDGER, AND A BOOTSTRAP MUST VERIFY")
    # The seventh review's first critical, and the sixth's second one wearing a
    # different hat: absence was separated from emptiness in the READER and the
    # CALLER was then written to test only for absence.
    _reset(); _edit_alt(_drop)
    with open(_lpath, "wb") as fh:
        with _gz.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
            gz.write(json.dumps({"version": S.INVENTORY_VERSION, "uids": {}}).encode())
    ok(S.read_alias_inventory("ofac-sdn") is None,
       "a well-formed but EMPTY ledger reads as no ledger at all")
    e = _refresh()
    ok(e.get("ok") is False,
       "and the deletion it would have waved through is refused", str(e.get("error"))[:160])
    ok(_retained("CUBAN FREIGHT ENTERPRISE"), "the name survives an empty ledger")

    # A ledger bound to a cache it does not describe is not a ledger either.
    _reset(); e = _refresh()
    ok(e.get("ok") is True, "the list commits again", (e.get("error") or "")[:120])
    _m = S.load_meta()
    ok(_m["ofac-sdn"].get("inventory_sha256") and _m["ofac-sdn"].get("inventory_uids"),
       "a committed refresh records the ledger's digest and size in the manifest",
       str(_m["ofac-sdn"].get("inventory_uids")))
    _bad = dict(_m["ofac-sdn"], inventory_sha256="0" * 64)
    ok(S.read_alias_inventory("ofac-sdn", _bad) is None,
       "a ledger whose digest is not the one recorded is refused")
    _bad2 = dict(_m["ofac-sdn"], inventory_uids=1)
    ok(S.read_alias_inventory("ofac-sdn", _bad2) is None,
       "and so is one holding a different number of designations")

    # The bootstrap must not launder a cache it has not verified.
    _norm = S.NORM / "ofac-sdn.jsonl.gz"
    ok(S.bootstrap_alias_inventory("ofac-sdn", None) is None,
       "a bootstrap with no manifest entry to verify against refuses")
    ok(S.bootstrap_alias_inventory(
        "ofac-sdn", dict(_m["ofac-sdn"], norm_sha256="0" * 64)) is None,
       "and a bootstrap from a cache that does not match its recorded digest refuses")
    ok(S.bootstrap_alias_inventory("ofac-sdn", _m["ofac-sdn"]) is not None,
       "while the real last-good cache does rebuild one")

    print("\nR7-2 — CHANGING THE KEY IS NOT LOSING THE DESIGNATION")
    def _renumber_and_substitute():
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, done = [], False
        for r in rows:
            if not done and len(r) > 11 and r[0].strip() == "424":
                r = list(r); r[0] = "999999424"; r[1] = "ENTIRELY DIFFERENT TRADING NAME"
                done = True
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return done

    _reset(); ok(_renumber_and_substitute(), "the fixture renumbers UID 424 and renames it")
    e = _refresh()
    ok(e.get("ok") is False,
       "a designation renumbered AND renamed is refused: a vanished key on a list that "
       "did not shrink is a substitution, not a de-listing", str(e.get("error"))[:200])
    ok(_retained("BOUTIQUE LA MAISON"), "and the published name is still in the retained file")

    # ...but a genuine re-keying, which keeps the names, is not a loss.
    def _renumber_only():
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, done = [], False
        for r in rows:
            if not done and len(r) > 11 and r[0].strip() == "424":
                r = list(r); r[0] = "999999424"; done = True
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return done

    _reset(); _renumber_only()
    e = _refresh()
    ok(e.get("ok") is True,
       "a publisher renumbering a designation without touching its names commits",
       str(e.get("error"))[:200])
    ok(_finds("BOUTIQUE LA MAISON", "999999424"),
       "and the name is found under its new key")

    print("\nR8-4 — MAKING THE COUNT FALL NO LONGER EXCUSES A SUBSTITUTION")
    # The eighth review's bypass. Renumber a designation and rename it, then
    # delete a SECOND designation so the total falls — the vanished-key
    # exemption then applied to the one that had actually been replaced.
    # 19,329 -> 19,328, complete, zero hits, exit 0.
    def _shrink_and_substitute():
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, renamed, deleted = [], False, False
        for r in rows:
            if not renamed and len(r) > 11 and r[0].strip() == "424":
                r = list(r); r[0] = "999999424"; r[1] = "ENTIRELY DIFFERENT TRADING NAME"
                renamed = True
                out.append(r); continue
            if renamed and not deleted and len(r) > 11 and r[0].strip() not in ("424", "999999424"):
                deleted = True          # drop one unrelated designation
                continue
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return renamed and deleted

    _reset(); e = _refresh()
    _before_n = e.get("records")
    ok(_shrink_and_substitute(), "the fixture renames one designation and deletes another")
    e = _refresh()
    ok(e.get("records") in (0, None) or e.get("records") < _before_n or not e.get("ok"),
       "the fixture really does make the list smaller", f"{_before_n} -> {e.get('records')}")
    ok(e.get("ok") is False,
       "a substitution is refused even though the record count FELL: the successor "
       "carries the same publisher reference or the same non-name fields, and no "
       "arrangement of counts can say that",
       str(e.get("error"))[:200])
    ok(_retained("BOUTIQUE LA MAISON"), "and the published name is still in the retained file")

    # ...while a genuine de-listing commits, PROVIDED the designation was
    # identifiable enough for its absence among the arrivals to mean something.
    def _delete_uid(target):
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, done = [], False
        for r in rows:
            if not done and len(r) > 11 and r[0].strip() == target:
                done = True
                continue
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return done

    _reset(); _refresh()
    ok(_delete_uid("8267"), "the fixture de-lists a designation outright")
    e = _refresh()
    ok(e.get("ok") is False,
       "an ordinary de-listing is QUARANTINED too. Three exemptions stood here before "
       "— nothing arrived with the reference, nothing with the fingerprint, the "
       "designation was identifiable — and each was an absence of evidence, and each "
       "fell to editing one more field. The absence of an eligible axis must not "
       "convert an unexplained disappearance into an authorised de-listing",
       str(e.get("error"))[:200])
    ok("None of them left identifying detail behind" in str(e.get("error", "")),
       "but the refusal says which kind it is, so the operator knows how hard to look",
       str(e.get("error"))[:240])

    # And the cost of the hardening, asserted rather than hoped for. UID 424 is
    # one of seventy-one Cuban entities carrying nothing but a type, a regime and
    # a measure. Its fingerprint cannot exonerate its disappearance, so its
    # de-listing is refused and named, and the operator authorises it.
    _reset(); _refresh()
    ok(_delete_uid("424"), "the fixture de-lists an UNIDENTIFIABLE designation")
    e = _refresh()
    ok(e.get("ok") is False and "BOUTIQUE LA MAISON" in str(e.get("error")),
       "de-listing a designation nothing distinguishes is REFUSED and the name is "
       "named — the evidence cannot tell removal from replacement, so it does not "
       "guess", str(e.get("error"))[:200])

    print("\nR11-1 — A SUCCESSOR NEED NOT BE A NEW ARRIVAL")
    # The successor maps were built from arrivals alone, so substituting into a
    # uid the ledger already knew went unremarked. Identity that moves onto a
    # record already on the list has moved just as surely.
    def _move_identity_onto_existing(donor, host):
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, gone, moved = [], False, False
        donor_row = next((r for r in rows if len(r) > 11 and r[0].strip() == donor), None)
        for r in rows:
            if not gone and len(r) > 11 and r[0].strip() == donor:
                gone = True
                continue                       # the donor's name disappears
            if not moved and donor_row and len(r) > 11 and r[0].strip() == host:
                r = list(r)
                for _i in (3, 11):             # its identifying fields move across
                    if len(donor_row) > _i:
                        r[_i] = donor_row[_i]
                moved = True
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return gone and moved

    _reset(); _refresh()
    _led = S.read_alias_inventory("ofac-sdn", S.load_meta().get("ofac-sdn")) or {}
    _pair = [u for u in _led if _led[u]["names"]][:2]
    if len(_pair) == 2 and _move_identity_onto_existing(_pair[0], _pair[1]):
        e = _refresh()
        ok(e.get("ok") is False,
           "a name that vanishes while its identity moves onto an EXISTING designation "
           "is refused", str(e.get("error"))[:200])
    _reset(); _refresh(); _delete_uid("424")
    e = _refresh({"SANCTIONS_ALLOW_ALIAS_REMOVAL": "1"})
    ok(e.get("ok") is True and e.get("alias_removal_override") is True,
       "and the operator authorises it with one switch, which records that it was used",
       str(e.get("error"))[:160])

    print("\nR9-1 — IDENTIFIABILITY IS A FACT ABOUT THE LEDGER, NOT ABOUT WHAT ARRIVED")
    # Renaming a designation, renumbering it AND restating one stable field at
    # once removes it from its own fingerprint group. Counted over the new list
    # that dropped the group from four to three, so a designation that was NOT
    # identifiable read as identifiable and the substitution committed.
    def _rename_renumber_restate(target):
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, done = [], False
        for r in rows:
            if not done and len(r) > 11 and r[0].strip() == target:
                r = list(r)
                r[0] = "9999" + target
                r[1] = "ENTIRELY DIFFERENT NETWORK COMPANY"
                r[3] = (r[3] or "") + "-RESTATED"      # one stable field, restated
                done = True
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return done

    _reset(); _refresh()
    _led = S.read_alias_inventory("ofac-sdn", S.load_meta().get("ofac-sdn")) or {}
    _freq = {}
    for _d in _led.values():
        _freq[_d["fp"]] = _freq.get(_d["fp"], 0) + 1
    _target = next((u for u, d in _led.items()
                    if _freq.get(d["fp"], 0) == S.FINGERPRINT_SPECIFIC + 1), None)
    ok(_target is not None,
       f"a designation sitting in a fingerprint group of exactly "
       f"{S.FINGERPRINT_SPECIFIC + 1} exists to attack", str(_target))
    if _target:
        _name = (_led[_target]["names"] or [""])[0]
        ok(_rename_renumber_restate(_target), "the fixture renames, renumbers and restates it")
        e = _refresh()
        ok(e.get("ok") is False,
           "removing a designation from its own fingerprint group does not make it "
           "identifiable: the count is taken over the ledger, which the supplier of "
           "the new file does not control", str(e.get("error"))[:200])
        ok(_name and _name in str(e.get("error", "")) or _retained(_name),
           "and the published name is still in the retained file", _name)

    print("\nR10-1 — ONE RESTATED FIELD NO LONGER BUYS A SUBSTITUTION")
    # The tenth review's first critical. The fingerprint is a conjunction of
    # eight fields, so restating ANY one of them made the successor unmatchable —
    # and the third branch only protects designations nothing distinguishes,
    # which is 9 to 12% of the European lists. The other 88 to 91% were held by
    # two tests the supplier of the file writes himself.
    _reset(); _refresh()
    _led = S.read_alias_inventory("ofac-sdn", S.load_meta().get("ofac-sdn")) or {}
    _f = {}
    for _d in _led.values():
        _f[_d["fp"]] = _f.get(_d["fp"], 0) + 1
    _tgt = next((u for u, d in _led.items()
                 if _f.get(d["fp"], 0) == 1 and d["names"] and d.get("axes")), None)
    ok(_tgt is not None,
       "an IDENTIFIABLE designation carrying identifying axes exists to attack", str(_tgt))
    if _tgt:
        _nm = _led[_tgt]["names"][0]
        ok(_rename_renumber_restate(_tgt),
           "the fixture renames it, renumbers it and restates ONE stable field")
        e = _refresh()
        ok(e.get("ok") is False,
           "and it is refused: the date of birth, the identifier and the address are "
           "compared one at a time, so an edit to a programme code leaves the others "
           "still pointing at the successor", str(e.get("error"))[:200])
        ok(_retained(_nm), "the published name is still in the retained file", _nm)

    print("\nR10-2 — LEAVING A CROWDED IDENTITY GROUP IS NEVER INNOCENT")
    # The two-refresh escape. Snapshot one restates one field of a designation
    # that STAYS — free, because a designation that stays was only checked for
    # its names — and that moves it out of a crowded fingerprint group, so the
    # ledger records it as identifiable. Snapshot two then substitutes it on that
    # footing, and §52's repair has nothing to say because it trusts the ledger.
    def _restate_only(target):
        rows = list(_csv.reader(_prim0.decode("utf-8-sig", "replace").splitlines()))
        out, done = [], False
        for r in rows:
            if not done and len(r) > 11 and r[0].strip() == target:
                r = list(r); r[3] = (r[3] or "") + "-RESTATED"; done = True
            out.append(r)
        with open(_prim, "w", encoding="utf-8", newline="") as fh:
            _csv.writer(fh).writerows(out)
        return done

    _reset(); _refresh()
    _led = S.read_alias_inventory("ofac-sdn", S.load_meta().get("ofac-sdn")) or {}
    _f = {}
    for _d in _led.values():
        _f[_d["fp"]] = _f.get(_d["fp"], 0) + 1
    _crowd = next((u for u, d in _led.items()
                   if _f.get(d["fp"], 0) > S.FINGERPRINT_SPECIFIC and d["names"]), None)
    ok(_crowd is not None, "a designation in a crowded identity group exists", str(_crowd))
    if _crowd:
        ok(_restate_only(_crowd), "snapshot one restates one of its stable fields only")
        e = _refresh()
        ok(e.get("ok") is False and "identity group" in str(e.get("error", "")),
           "the repositioning is refused on its own, before any name has gone — it is "
           "the one change to a designation's non-name fields that always precedes a "
           "substitution and never anything else", str(e.get("error"))[:200])

    print("\nR7-5 — NOTHING AFTER THE INSTALL MAY COST US THE LAST GOOD FILE")
    _reset(); e = _refresh()
    ok(e.get("ok") is True, "a clean commit first", (e.get("error") or "")[:120])
    _good = (S.NORM / "ofac-sdn.jsonl.gz").read_bytes()
    _real_write = S.write_alias_inventory

    def _boom(source_id, inv):
        raise OSError("simulated ledger write failure")

    S.write_alias_inventory = _boom
    try:
        e = _refresh()
    finally:
        S.write_alias_inventory = _real_write
    ok(e.get("ok") is False, "a ledger write that fails AFTER the install fails the refresh",
       str(e.get("error"))[:120])
    ok((S.NORM / "ofac-sdn.jsonl.gz").read_bytes() == _good,
       "and the last good list is still the list on disk, byte for byte")
    ok(_retained("CUBAN FREIGHT ENTERPRISE"), "so the file is intact")

    print("\nR8-1 — AN UNBOUND MANIFEST VOUCHES FOR NOTHING")
    _reset(); e = _refresh()
    _m = S.load_meta()
    _entry = _m["ofac-sdn"]
    ok(S.read_alias_inventory("ofac-sdn", _entry) is not None,
       "the real ledger reads against the manifest that recorded it")
    for _missing in ("inventory_sha256", "inventory_uids"):
        _un = {k: v for k, v in _entry.items() if k != _missing}
        ok(S.read_alias_inventory("ofac-sdn", _un) is None,
           f"a manifest with no {_missing} cannot vouch for a ledger, so there is none")

    print("\nR8-2 — THE MANIFEST ITSELF CANNOT BE ROLLED BACK")
    _before = json.loads((S.DATA / "meta.json").read_text())
    _gen_before = _before.get("generation")
    ok(isinstance(_gen_before, int) and _gen_before > 0,
       "a committed manifest carries a generation", str(_gen_before))
    ok(S.watermark_path().exists() and
       int(S.watermark_path().read_text().strip()) == _gen_before,
       "and the watermark beside it matches")
    _reset(); _refresh()
    _after = json.loads((S.DATA / "meta.json").read_text())
    ok(_after["generation"] > _gen_before, "every commit advances it",
       f"{_gen_before} -> {_after['generation']}")
    # Put the OLDER manifest back. Every binding inside it is still internally
    # valid — that is what made this work — so only the manifest's own age
    # catches it.
    (S.DATA / "meta.json").write_text(json.dumps(_before))
    ok(S.load_meta() == {},
       "a manifest older than the highest this machine has committed is not read, "
       "however internally consistent it is")
    (S.DATA / "meta.json").write_text(json.dumps(_after))
    ok(S.load_meta().get("generation") == _after["generation"],
       "and the current one still reads")

    print("\nR8-3 — THE PROTECTED REGION IS THE WHOLE COMMIT")
    _reset(); e = _refresh()
    ok(e.get("ok") is True, "a clean commit first", (e.get("error") or "")[:120])
    _good = (S.NORM / "ofac-sdn.jsonl.gz").read_bytes()
    _real_fp = S.raw_fingerprints

    def _fp_boom(src):
        raise OSError("simulated post-install fingerprint failure")

    S.raw_fingerprints = _fp_boom
    try:
        e = _refresh()
    finally:
        S.raw_fingerprints = _real_fp
    ok(e.get("ok") is False,
       "a raise while BUILDING THE ENTRY, after the install, fails the refresh",
       str(e.get("error"))[:120])
    ok((S.NORM / "ofac-sdn.jsonl.gz").read_bytes() == _good,
       "and the last good list is still on disk, byte for byte — the protected "
       "region ended at the ledger write and this is what got through it")
    e = _refresh()
    ok(e.get("ok") is True,
       "and the next refresh commits rather than refusing for good",
       str(e.get("error"))[:160])

    print("\nENGINE GENERATION — WHAT PRODUCED THE RESULT, NOT ONLY THE FILE")
    _reset(); e = _refresh()
    _m = S.load_meta()
    ok(_m["ofac-sdn"].get("engine_version") == S.ENGINE_VERSION,
       "a committed refresh records the engine generation that produced it")
    ok(isinstance(_m["ofac-sdn"].get("code"), dict) and len(_m["ofac-sdn"]["code"]) == 3,
       "and the digests of the three modules that decide what a result says")
    _stale = dict(_m["ofac-sdn"], engine_version=S.ENGINE_VERSION - 1)
    _err = ""
    try:
        S.read_source("ofac-sdn", _stale, use_cache=False)
    except S.CacheError as exc:
        _err = str(exc)
    ok("generation" in _err,
       "a cache written by another engine generation is REFUSED, not read — this is the "
       "gap a four-round-stale install walked through at the same PARSER_VERSION", _err[:140])

    # a first refresh with no cache at all has genuinely nothing to compare.
    # BOTH have to go: the manifest entry AND the parsed file, because a parsed
    # list on disk is now itself evidence that this is not a first refresh —
    # asking the manifest alone meant that losing it turned a full cache into
    # "nothing to compare against" and stood the guard down.
    _lpath.unlink(missing_ok=True)
    _norm_path = S.NORM / "ofac-sdn.jsonl.gz"
    _norm_saved = _norm_path.read_bytes() if _norm_path.exists() else None
    _norm_path.unlink(missing_ok=True)
    err = ""
    try:
        S.alias_removals(_sdn, [{"uid": "1", "name": "X", "aliases": [], "nonlatin": []}], None)
    except S.CacheError as exc:
        err = str(exc)
    ok(not err, "a genuinely first refresh, with no prior cache, is not refused", err[:160])
    err = ""
    if _norm_saved is not None:
        _norm_path.write_bytes(_norm_saved)
        try:
            S.alias_removals(_sdn, [{"uid": "1", "name": "X", "aliases": [], "nonlatin": []}], None)
        except S.CacheError as exc:
            err = str(exc)
    ok(bool(err),
       "but a parsed list ON DISK is evidence that it is not a first refresh, whatever "
       "the manifest says, and with no ledger to compare against it is REFUSED", err[:160])

    # not losses: de-listing, and re-punctuation
    _reset(); e = _refresh()
    ok(e.get("ok") is True, "the list commits again once the file is whole", (e.get("error") or "")[:120])
    base = list(S.load_records("ofac-sdn"))
    err = ""
    try:
        S.alias_removals(_sdn, base[:-1], S.load_meta().get("ofac-sdn"))
    except S.CacheError as exc:
        err = str(exc)
    ok(bool(err), "a designation leaving the list entirely takes its published names with "
                  "it, and that is quarantined rather than assumed innocent", err[:160])
    err = ""
    try:
        rep = [dict(r, name=(r.get("name") or "").lower() + " !") for r in base]
        S.alias_removals(_sdn, rep, S.load_meta().get("ofac-sdn"))
    except S.CacheError as exc:
        err = str(exc)
    ok(not err, "re-punctuating and re-casing a name is not losing it", err[:160])

    # the one deliberate override
    _reset(); _edit_alt(_drop)
    e = _refresh({"SANCTIONS_ALLOW_ALIAS_REMOVAL": "1"})
    ok(e.get("ok") is True, "a verified publisher correction can still be let through on purpose",
       str(e.get("error"))[:160])
finally:
    S.DATA, S.RAW, S.NORM, S.META, S.download = _saved
    shutil.rmtree(_iso, ignore_errors=True)

_lp = S.inv_dir() / "ofac-sdn.aliases.json.gz"
ok(_ledger_before is None or (_lp.exists()
   and hashlib.sha256(_lp.read_bytes()).hexdigest() == _ledger_before),
   "and none of that touched the LIVE ledger, which is byte-identical afterwards")

print("\nTHE FIFTH REVIEW'S ORDERING DEFECT — AN EXACT NAME MUST NOT LOSE TO 100 APPROXIMATIONS")
rc, out = run(["check", "Abdul", "--type", "individual", "--json"])
try:
    j = json.loads(out)
    hits = j.get("hits", [])
    uids = [str(h["record"]["uid"]) for h in hits]
    ok("113444" in uids,
       "UN 113444, whose own published alias IS 'Abdul', is returned at the default limit",
       f"total={j.get('total_hits')} returned={len(hits)} first={uids[:5]}")
    exact_flags = [h["exact"] for h in hits]
    first_fuzzy = exact_flags.index(False) if False in exact_flags else len(exact_flags)
    ok(all(exact_flags[:first_fuzzy]) and not any(exact_flags[first_fuzzy:]),
       "every exact identity is ranked above every fuzzy match, none interleaved",
       str(exact_flags[:12]))
    ok(all(h["score"] == 100.0 for h in hits if h["exact"]),
       "an exact identity always scores 100", str([h["score"] for h in hits if h["exact"]][:6]))
    ok(any(h["score"] == 100.0 and not h["exact"] for h in hits),
       "and a fuzzy 100 is still distinguished from it, not silently promoted",
       str([(h["score"], h["exact"]) for h in hits[:8]]))
except (ValueError, KeyError) as exc:
    ok(False, "the Abdul query returns JSON with an exact flag", f"{type(exc).__name__}: {exc}: {out[:200]!r}")

# The property behind it: an exact identity must survive ANY limit, including
# one far below its fuzzy rank. This is the assertion that would have caught the
# defect: at --limit 1 the designation whose name IS the query must be the one.
rc, out = run(["check", "Abdul", "--type", "individual", "--limit", "1", "--json"])
try:
    j = json.loads(out)
    h = (j.get("hits") or [None])[0]
    ok(h is not None and h["exact"],
       "at --limit 1 the single hit returned is an exact identity, not a fuzzy tie",
       str(h)[:200] if h else "no hits")
except ValueError as exc:
    ok(False, "the --limit 1 query returns JSON", f"{exc}: {out[:200]!r}")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print("  FAILED: " + f)
sys.exit(1 if FAIL else 0)
