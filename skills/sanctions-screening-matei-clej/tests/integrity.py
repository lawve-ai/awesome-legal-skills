#!/usr/bin/env python3
"""
Data integrity and refresh semantics.

A parser that maps a column wrongly does not crash — it quietly produces
plausible-looking designations with a passport number in the date-of-birth field
and a nationality in the regime. These tests assert the shape of what came out
of each parser, and check the behaviour of a refresh that fails.

    python3 tests/integrity.py
"""

import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import screen as SC  # noqa: E402
import sources as S  # noqa: E402

PASS, FAIL = [], []


def ok(cond, label, detail=""):
    (PASS if cond else FAIL).append(label)
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"\n          {detail}" if detail and not cond else ""))


meta = S.load_meta()
YEAR = datetime.now().year
TYPES = {"individual", "entity", "vessel", "aircraft", "unknown"}

print("FIELD SHAPE — a mis-mapped column produces plausible nonsense, not a crash")
for sid in ("uk-sanctions-list", "ofsi", "un", "eu", "ofac-sdn", "ofac-cons"):
    if not meta.get(sid, {}).get("ok"):
        print(f"  –  {sid}: not refreshed, skipped")
        continue
    recs = list(S.load_records(sid))
    ok(all(r["source"] == sid for r in recs), f"{sid}: every record is attributed to its source")
    ok(all(r["type"] in TYPES for r in recs), f"{sid}: every type is one of {sorted(TYPES)}")
    ok(all(isinstance(r.get("aliases"), list) and isinstance(r.get("dob"), list) for r in recs),
       f"{sid}: list-valued fields are lists")
    blank = [r for r in recs if not (r.get("name") or "").strip()]
    ok(not blank, f"{sid}: no designation has an empty name", f"{len(blank)} blank")
    # the null token must not survive AS A VALUE; it legitimately appears inside
    # free text (a Swiss federal number reads CH-2 17-0-431-423-3)
    def _leaks(rec):
        for v in rec.values():
            if isinstance(v, str) and v.strip() == "-0-":
                return True
            if isinstance(v, list) and any(str(x).strip() == "-0-" for x in v):
                return True
        return False
    nulls = [r for r in recs if _leaks(r)]
    ok(not nulls, f"{sid}: the CSV null token -0- never survives as a field value",
       f"{len(nulls)} records, e.g. {nulls[:1]}")

    # dates of birth must look like dates of birth, not identifiers
    years, bad = [], []
    for r in recs:
        if r["type"] != "individual":
            continue
        for d in r.get("dob", []):
            p = SC.parse_dob(d)
            if p:
                y = int(p[0])
                years.append(y)
                if not (1900 <= y <= YEAR):
                    bad.append((r["name"], d))
    ok(bool(years), f"{sid}: dates of birth are being extracted at all")
    if years:
        ok(len(bad) / len(years) < 0.01,
           f"{sid}: dates of birth fall in a human range ({len(years):,} parsed)",
           f"{len(bad)} outside 1900-{YEAR}: {bad[:3]}")
        ok(1930 <= (sum(years) / len(years)) <= 1995,
           f"{sid}: mean year of birth {sum(years)/len(years):.0f} is plausible")

print("\nCROSS-LIST IDENTITY — the same designation, found on each list under its own reference")


class A:
    threshold = 90.0
    type = "individual"
    dob = "1952-10-07"
    nationality = ""
    limit = 60
    include_delisted = False


srcs = [s for s in S.SOURCES if s.default and meta.get(s.id, {}).get("ok")]
A.max_age_hours = 24.0
A.client = A.matter = ""
hits = SC.screen("Vladimir Putin", A, srcs, meta).hits
# a dict comprehension keeps the LAST hit per source, not the best-ranked one
by_source = {}
for h in hits:
    by_source.setdefault(h["record"]["source"], []).append(h["record"])
for sid, expect_ref in [("uk-sanctions-list", "RUS0251"), ("ofsi", "RUS0251"),
                        ("ofac-sdn", None), ("eu", None)]:
    found = by_source.get(sid, [])
    ok(bool(found), f"{sid}: the designation is found")
    if found and expect_ref:
        match = [r for r in found if (r.get("ref") or "").startswith(expect_ref)]
        ok(bool(match), f"{sid}: carries the published reference {expect_ref}",
           f"refs seen: {[r.get('ref') for r in found][:4]}")
        if match:
            ok(any(SC.parse_dob(d) and SC.parse_dob(d)[0] == "1952" for d in match[0]["dob"]),
               f"{sid}: the date of birth parsed out of that list is 1952",
               str(match[0]["dob"][:3]))
    elif found:
        ok(any(any(SC.parse_dob(d) and SC.parse_dob(d)[0] == "1952" for d in r["dob"])
               for r in found), f"{sid}: a 1952 date of birth is parsed from that list")

print("\nREFRESH — a failed refresh must not destroy the last good copy")
tmp = Path(tempfile.mkdtemp(prefix="sanctions-refresh-"))
(tmp / "norm").mkdir(parents=True)
real = Path(os.environ.get("SANCTIONS_DATA", Path.home() / ".claude" / "sanctions-data"))
import shutil  # noqa: E402
shutil.copy(real / "norm" / "ofsi.jsonl.gz", tmp / "norm" / "ofsi.jsonl.gz")
before = (tmp / "norm" / "ofsi.jsonl.gz").read_bytes()

_SAVED = (S.DATA, S.NORM, S.RAW, S.META)
S.DATA = tmp     # the refresh lock lives under DATA. Left at the live cache, this
                 # test locked the real cache — and aborted the suite under a
                 # sandbox that could not write there.
S.NORM = tmp / "norm"
S.RAW = tmp / "raw"
S.META = tmp / "meta.json"
original_download = S.download


def boom(src, timeout=600):
    raise OSError("simulated network failure")


S.download = boom
m = {}
entry = S.refresh(S.BY_ID["ofsi"], m)
S.download = original_download
ok(entry["ok"] is False and "simulated network failure" in entry["error"],
   "a download failure is recorded against the source, with the reason", str(entry)[:200])
ok(entry["records"] == 0, "a failed refresh claims no records")
ok((tmp / "norm" / "ofsi.jsonl.gz").read_bytes() == before,
   "the previously parsed list is left untouched by the failed refresh")
ok(m["ofsi"]["ok"] is False, "the failure is written into the metadata, not swallowed")
S.DATA, S.NORM, S.RAW, S.META = _SAVED   # a test must not leave the module pointing elsewhere

print("\nLICENCE GATE — the CC BY-NC sources must refuse to fetch without acknowledgement")
os.environ.pop("SANCTIONS_OPENSANCTIONS_LICENCE", None)
m2 = {}
e = S.refresh(S.BY_ID["opensanctions-peps"], m2)
ok(e["ok"] is False and "CC BY-NC" in e["error"],
   "the PEP dataset refuses to refresh unless the licence is acknowledged", str(e)[:200])
ok("commercial" in e["error"].lower(),
   "the refusal explains that fee-earning use is commercial use")
os.environ["SANCTIONS_OPENSANCTIONS_LICENCE"] = "noncommercial"
allowed, note = S.licence_ok(S.BY_ID["opensanctions-peps"])
ok(allowed and note == "noncommercial", "an acknowledgement is accepted and recorded")
os.environ.pop("SANCTIONS_OPENSANCTIONS_LICENCE", None)
for s in S.SOURCES:
    if "CC BY-NC" not in s.licence:
        ok(S.licence_ok(s)[0], f"{s.id}: an open-government source needs no gate")

print("\nOPENSANCTIONS PARSER — exercised on a synthetic file, not their data")
# The licence gate means this parser never runs unless someone acknowledges
# CC BY-NC, so it would otherwise ship untested. A file in their published
# targets.simple schema exercises the mapping without downloading anything.
os_dir = Path(tempfile.mkdtemp(prefix="sanctions-os-"))
(os_dir / "raw").mkdir()
sample = (
    "id,schema,name,aliases,birth_date,countries,addresses,identifiers,sanctions,"
    "phones,emails,dataset,first_seen,last_seen,last_change\n"
    "NK-abc123,Person,Ivan Petrov,Ivan Petroff;И. Петров,1975-03-02,ru,"
    "\"12 Tverskaya, Moscow\",PASSPORT-1234,EU asset freeze,,,sanctions,"
    "2022-03-15T00:00:00,2026-09-01T00:00:00,2026-08-01T00:00:00\n"
    "NK-def456,Company,Acme Trading LLC,Acme Trading,,cy,Nicosia,REG-99,,,,"
    "sanctions,2021-01-01T00:00:00,2026-09-01T00:00:00,2026-01-01T00:00:00\n"
    "NK-ghi789,Vessel,MV Northern Star,,,pa,,IMO-9999999,,,,sanctions,"
    "2020-01-01T00:00:00,2026-09-01T00:00:00,2026-01-01T00:00:00\n"
    "NK-jkl012,Airplane,EP-GOL,,,ir,,TAIL-EPGOL,,,,sanctions,"
    "2019-01-01T00:00:00,2026-09-01T00:00:00,2026-01-01T00:00:00\n"
    "NK-mno345,Organization,Northern Front,NF,,sy,,ORG-1,,,,sanctions,"
    "2019-01-01T00:00:00,2026-09-01T00:00:00,2026-01-01T00:00:00\n")
src = S.BY_ID["opensanctions-sanctions"]
(os_dir / "raw" / src.filename).write_text(sample, encoding="utf-8")
saved_raw = S.RAW
S.RAW = os_dir / "raw"
try:
    recs, extra = S.parse_opensanctions(src)
finally:
    S.RAW = saved_raw
by_name = {r["name"]: r for r in recs}
ok(len(recs) == 5, "every row becomes a designation", f"got {len(recs)}")
ok(by_name["Ivan Petrov"]["type"] == "individual", "schema Person maps to individual")
ok(by_name["Acme Trading LLC"]["type"] == "entity", "schema Company maps to entity")
ok(by_name["MV Northern Star"]["type"] == "vessel", "schema Vessel maps to vessel")
ok(by_name["Northern Front"]["type"] == "entity", "schema Organization maps to entity")
# Airplane was being emitted as a vessel, so --type aircraft excluded it and
# --type vessel returned an aeroplane. There was no Airplane row to catch it.
ok(by_name["EP-GOL"]["type"] == "aircraft", "schema Airplane maps to aircraft, not vessel",
   by_name["EP-GOL"]["type"])

# A schema the parser has never seen must stop the refresh, not become an entity.
unknown = ("id,schema,name,aliases,birth_date,countries,addresses,identifiers,sanctions,"
           "phones,emails,dataset,first_seen,last_seen,last_change\n"
           "NK-zzz999,Spacecraft,Voyager 3,,,us,,SC-1,,,,sanctions,"
           "2019-01-01T00:00:00,2026-09-01T00:00:00,2026-01-01T00:00:00\n")
(os_dir / "raw" / src.filename).write_text(unknown, encoding="utf-8")
S.RAW = os_dir / "raw"
try:
    S.parse_opensanctions(src)
    caught_type, why_type = False, ""
except Exception as exc:
    caught_type, why_type = True, str(exc)
finally:
    S.RAW = saved_raw
ok(caught_type, "an unmapped publisher subject type stops the parse", why_type[:120])
ok("Spacecraft" in why_type, "and the refusal names the word it did not recognise", why_type[:120])
(os_dir / "raw" / src.filename).write_text(sample, encoding="utf-8")
ok(by_name["Ivan Petrov"]["aliases"] == ["Ivan Petroff"],
   "Latin aliases are split on the semicolon", str(by_name["Ivan Petrov"]["aliases"]))
ok(by_name["Ivan Petrov"]["nonlatin"] == ["И. Петров"],
   "the Cyrillic alias is kept out of the Latin alias list",
   str(by_name["Ivan Petrov"]["nonlatin"]))
ok(by_name["Ivan Petrov"]["dob"] == ["1975-03-02"], "the date of birth maps across")
ok(by_name["Ivan Petrov"]["ids"] == ["PASSPORT-1234"], "identifiers map across")
ok(by_name["Ivan Petrov"]["listed_on"] == "2022-03-15", "first seen becomes the listing date")
ok("Moscow" in by_name["Ivan Petrov"]["address"], "a quoted address survives the CSV")
ok(all(r["source"] == src.id for r in recs), "records are attributed to the source")

print("\nCLI — the housekeeping commands survive an empty cache")
empty = Path(tempfile.mkdtemp(prefix="sanctions-blank-"))
p = subprocess.run([sys.executable, str(ROOT / "screen.py"), "sources"], capture_output=True,
                   text=True, env={**os.environ, "SANCTIONS_DATA": str(empty)})
ok(p.returncode == 0 and "Traceback" not in p.stdout + p.stderr,
   "`sources` runs against an empty cache", (p.stdout + p.stderr)[-200:])
p = subprocess.run([sys.executable, str(ROOT / "screen.py"), "status"], capture_output=True,
                   text=True, env={**os.environ, "SANCTIONS_DATA": str(empty)})
out = p.stdout + p.stderr
ok("Traceback" not in out, "`status` runs against an empty cache", out[-200:])
# status exists to say whether a screen run now would be complete, so an unusable
# cache must not report success
ok(p.returncode == 3, "`status` exits 3 when the cache cannot support a search",
   f"rc={p.returncode}")
ok("NOT USABLE" in out, "`status` names each unusable list", out[-200:])

bad_csv = empty / "bad.csv"
bad_csv.write_text("full_name,dob\nSomebody,1980\n")
p = subprocess.run([sys.executable, str(ROOT / "screen.py"), "batch", str(bad_csv)],
                   capture_output=True, text=True)
out = p.stdout + p.stderr
# "no traceback" passed while the command reported one clean subject and exited 0
ok(p.returncode == 4, "a CSV with no name column is REFUSED, not screened as clean",
   f"rc={p.returncode}")
ok("no 'name' column" in out, "the refusal names the missing column", out[-200:])
ok("0 candidate matches" not in out, "it never reports a nil result for an unread file")

print("\nTRUNCATED DOWNLOAD — a partial file must not become the whole list")
raw_dir = Path(tempfile.mkdtemp(prefix="sanctions-trunc-")) / "raw"
raw_dir.mkdir(parents=True)
src = S.BY_ID["uk-sanctions-list"]
whole = (S.RAW / src.filename).read_text(encoding="utf-8-sig", errors="replace").splitlines()
(raw_dir / src.filename).write_text("\n".join(whole[:3]) + "\n", encoding="utf-8")
saved = S.RAW
S.RAW = raw_dir
try:
    recs, _ = S.parse_uksl(src)
    parsed = len(recs)
    try:
        S.validate(src, recs, None)
        refused = False
    except S.CacheError as exc:
        refused, why = True, str(exc)
finally:
    S.RAW = saved
ok(refused, f"a download truncated at a line boundary is refused ({parsed} designations parsed)")
ok("partial download" in why, "the refusal says why", why)

print("\nTAMPERING — the manifest is bound to the data")
entry = dict(meta.get("ofsi", {}))
if entry.get("ok"):
    bad_entry = dict(entry, norm_sha256="0" * 64)
    try:
        S.read_source("ofsi", bad_entry, use_cache=False)
        caught = False
    except S.CacheError as exc:
        caught, msg = True, str(exc)
    ok(caught, "a digest that does not match the recorded one is refused")
    ok("altered or replaced" in msg, "the refusal says the list was altered", msg)
    old_version = dict(entry, parser_version=0)
    try:
        S.read_source("ofsi", old_version, use_cache=False)
        caught2 = False
    except S.CacheError:
        caught2 = True
    ok(caught2, "a list parsed by a different parser version is refused")
    try:
        S.read_source("ofsi", {k: v for k, v in entry.items() if k != "norm_sha256"},
                      use_cache=False)
        caught3 = False
    except S.CacheError:
        caught3 = True
    ok(caught3, "a list with no recorded digest is refused")


# --------------------------------------------------------------------------
# the verified copy cannot be emptied under the caller, and the recorded count
# is part of what is verified. Both are on the CACHED path, which the tampering
# tests above deliberately bypass with use_cache=False.
# --------------------------------------------------------------------------
print("\nTHE VERIFIED COPY IN MEMORY")
if entry.get("ok"):
    got = S.read_source("ofsi", entry)
    ok(not hasattr(got, "clear") and not hasattr(got, "append"),
       "a caller is handed a copy it cannot empty, truncate or extend",
       f"got {type(got).__name__}")
    n_before = len(got)
    ok(n_before == entry["records"],
       "the copy holds every designation the manifest records",
       f"{n_before} vs {entry['records']}")

    # Priming the cache and then editing the manifest count must not be served
    # from the primed entry: the count is bound into the key.
    try:
        S.read_source("ofsi", dict(entry, records=1))
        caught4, msg4 = False, ""
    except S.CacheError as exc:
        caught4, msg4 = True, str(exc)
    ok(caught4, "a manifest count edited after the cache was primed is refused", msg4)
    ok(str(n_before) in msg4.replace(",", "") or f"{n_before:,}" in msg4,
       "the refusal states how many designations were actually there", msg4)

    # And the cached entry survives that refusal intact.
    ok(len(S.read_source("ofsi", entry)) == n_before,
       "a refused read does not damage the verified copy")

# --------------------------------------------------------------------------
# the freshness window is itself validated
# --------------------------------------------------------------------------
print("\nTHE FRESHNESS WINDOW")
import argparse as _ap
import copy as _copy
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(ROOT))
import screen as SC

def _args(**kw):
    base = dict(dob="", nationality="", type="individual", client="", matter="",
                threshold=88.0, limit=40, max_age_hours=24.0, include_delisted=False)
    base.update(kw)
    return _ap.Namespace(**base)

if entry.get("ok"):
    old = _copy.deepcopy(meta)
    old["ofsi"]["fetched_at"] = "2020-01-01T00:00:00+00:00"
    o = SC.screen("Ivan Ivanov", _args(), [S.BY_ID["ofsi"]], old)
    ok(o.complete is False and o.exit_code == 3,
       "a list six years old is stale and exits 3", f"exit {o.exit_code}")

    for bad in (float("nan"), float("inf"), -5.0, 0.0):
        o = SC.screen("Ivan Ivanov", _args(max_age_hours=bad), [S.BY_ID["ofsi"]], old)
        ok(o.exit_code == 4 and "max-age-hours" in o.error,
           f"--max-age-hours {bad!r} is refused, not treated as no limit",
           f"exit {o.exit_code}: {o.error[:60]}")
    ok(all(not s["searched"] for s in
           SC.screen("X", _args(max_age_hours=float("nan")), [S.BY_ID["ofsi"]], old).sources),
       "a refused window screens nothing at all")

    future = _copy.deepcopy(meta)
    future["ofsi"]["fetched_at"] = (datetime.now(timezone.utc)
                                    + timedelta(days=30)).isoformat()
    o = SC.screen("Ivan Ivanov", _args(), [S.BY_ID["ofsi"]], future)
    ok(o.sources[0]["stale"] and o.exit_code == 3,
       "a list claiming to have been fetched in the future is stale, not fresh",
       f"stale={o.sources[0]['stale']} exit={o.exit_code}")


# --------------------------------------------------------------------------
# validate() across the whole range, not only the floor
# --------------------------------------------------------------------------
print("\nVALIDATION — the shapes a truncated list can arrive in")
_uk = S.BY_ID["uk-sanctions-list"]


def _fake(n, name="Ivan Petrov", alias=True):
    return [{"name": f"{name} {i}", "aliases": ["A"] if alias else [],
             "type": "individual"} for i in range(n)]


def _validated(recs, previous):
    try:
        S.validate(_uk, recs, previous)
        return True, ""
    except S.CacheError as exc:
        return False, str(exc)

good = {"ok": True, "records": 6334}
floor = S.MIN_RECORDS.get(_uk.id, 100)

passed, _ = _validated(_fake(floor - 1), good)
ok(not passed, f"a list under the {floor:,} floor is refused")

# The floor is not a completeness check. A list well above it that has lost a
# fifth of its designations is the realistic truncation, and it was accepted.
passed, why = _validated(_fake(int(6334 * 0.79)), good)
ok(not passed, "a 21% shrink against a healthy previous count is quarantined", why[:90])
passed, _ = _validated(_fake(int(6334 * 0.95)), good)
ok(passed, "an ordinary 5% movement is not quarantined")

# One failed refresh used to wipe the baseline, so the very next refresh could
# lose 90% unnoticed. The last known good count has to survive the failure.
after_failure = {"ok": False, "records": 0, "last_good_records": 6334}
# 3,000 is ABOVE the 2,000 floor, so only the last-known-good baseline can
# refuse it. The earlier version of this test used 600, which the floor rejects
# on its own — it would have passed with the baseline repair removed.
assert 3000 > S.MIN_RECORDS["uk-sanctions-list"], "the probe must clear the floor"
passed, why = _validated(_fake(3000), after_failure)
ok(not passed,
   "a collapse after a FAILED refresh is still measured against the last good count",
   why[:90])
ok("5,067" in why or "6,334" in why,
   "and the refusal quotes the last good count, not the failed one", why[:90])
passed, _ = _validated(_fake(3000), {"ok": False, "records": 0})
ok(passed,
   "with no last good count there is nothing to measure against, and the floor "
   "alone applies — stated, not implied")
ok(S.last_good_count(after_failure) == 6334,
   "the last known good count survives a failed refresh")
ok(S.last_good_count({"ok": False, "records": 0}) == 0,
   "and is zero when there has never been a good one")

# A first refresh has no baseline at all, so only the floor protects it. Say so
# rather than implying the shrink rule covers it.
passed, _ = _validated(_fake(floor + 1), None)
ok(passed, "a first refresh is bounded only by the floor — recorded, not claimed otherwise")

# --------------------------------------------------------------------------
# the shrink override must be deliberate
# --------------------------------------------------------------------------
print("\nTHE SHRINK OVERRIDE")
import os as _os
_saved_env = _os.environ.get("SANCTIONS_ALLOW_SHRINK")
try:
    for value, should_disable in (("1", True), ("0", False), ("no", False),
                                  ("false", False), ("", False)):
        _os.environ["SANCTIONS_ALLOW_SHRINK"] = value
        allow = _os.environ.get("SANCTIONS_ALLOW_SHRINK", "").strip() == "1"
        ok(allow is should_disable,
           f"SANCTIONS_ALLOW_SHRINK={value!r} "
           f"{'disables' if should_disable else 'does NOT disable'} the quarantine")
finally:
    if _saved_env is None:
        _os.environ.pop("SANCTIONS_ALLOW_SHRINK", None)
    else:
        _os.environ["SANCTIONS_ALLOW_SHRINK"] = _saved_env

# --------------------------------------------------------------------------
# the production commit path, not the in-memory dictionary
# --------------------------------------------------------------------------
print("\nTHE MANIFEST IS COMMITTED, NOT JUST UPDATED IN MEMORY")
commit_dir = Path(tempfile.mkdtemp(prefix="sanctions-commit-"))
_S2 = (S.DATA, S.NORM, S.RAW, S.META)
try:
    S.DATA, S.NORM, S.RAW = commit_dir, commit_dir / "norm", commit_dir / "raw"
    S.META = commit_dir / "meta.json"
    S.NORM.mkdir(parents=True, exist_ok=True)
    S.RAW.mkdir(parents=True, exist_ok=True)
    original = S.download
    S.download = boom
    try:
        entry = S.refresh_and_commit(S.BY_ID["ofsi"])
    finally:
        S.download = original
    ok(entry["ok"] is False, "refresh_and_commit reports the failure")
    ok(S.META.exists(), "and the manifest was actually written to disk")
    on_disk = json.loads(S.META.read_text())
    ok(on_disk.get("ofsi", {}).get("ok") is False,
       "the failure is on disk, where the next process will read it",
       str(on_disk)[:150])
    # Removing the commit entirely is what this catches: the old test asserted
    # only against the dictionary the function had just mutated.
    ok("error" in on_disk.get("ofsi", {}) and on_disk["ofsi"]["error"],
       "with the reason recorded alongside it")
finally:
    S.DATA, S.NORM, S.RAW, S.META = _S2


# --------------------------------------------------------------------------
# the frozen cache, below the outer tuple
# --------------------------------------------------------------------------
print("\nTHE CACHE IS FROZEN ALL THE WAY DOWN")
# `entry` here used to be whatever the last refresh test left in it — a failed
# refresh, ok=False — so this block printed its heading and ran no assertion.
ofsi_entry = meta.get("ofsi", {})
if ofsi_entry.get("ok"):
    got = S.read_source("ofsi", ofsi_entry)
    rec = got[0]
    for label, fn in [("clear the record", lambda: rec.clear()),
                      ("assign a field", lambda: rec.__setitem__("name", "X")),
                      ("delete a field", lambda: rec.__delitem__("name")),
                      ("append to its aliases", lambda: rec["aliases"].append("X"))]:
        try:
            fn()
            ok(False, f"a caller cannot {label}", "it succeeded — the cache is mutable")
        except (AttributeError, TypeError) as exc:
            ok(True, f"a caller cannot {label} ({type(exc).__name__})")
    ok(len(S.read_source("ofsi", ofsi_entry)) == len(got),
       "and the verified copy is intact after every attempt")
else:
    ok(False, "the frozen-cache section ran", "ofsi is not cached ok")

# --------------------------------------------------------------------------
# the auxiliary file is part of the list
# --------------------------------------------------------------------------
print("\nAUXILIARY FILES")
osdn = S.BY_ID["ofac-sdn"]
if meta.get("ofac-sdn", {}).get("ok"):
    fp = S.raw_fingerprints(osdn)
    ok(len(fp) == 2 and all(v.get("sha256") for v in fp.values()),
       "every file the OFAC parse reads is fingerprinted, not just the primary",
       str(fp)[:140])
    ok(meta["ofac-sdn"].get("raw_files"),
       "and the fingerprints are committed to the manifest")

    ofac_recs, _ = S.PARSERS[osdn.parser](osdn)
    n_alias = sum(1 for r in ofac_recs if r.get("aliases"))
    prev_ok = {"ok": True, "records": len(ofac_recs), "aliased": n_alias}
    try:
        S.validate(osdn, ofac_recs, prev_ok)
        whole_ok = True
    except S.CacheError as exc:
        whole_ok, why = False, str(exc)
    ok(whole_ok, "the whole OFAC list validates", "" if whole_ok else why[:100])

    # The alias file is a separate download. Losing it leaves the primary file
    # perfectly intact, so nothing but an alias count can notice.
    stripped = [dict(r, aliases=([] if i else r.get("aliases")))
                for i, r in enumerate(ofac_recs)]
    try:
        S.validate(osdn, stripped, prev_ok)
        caught_alt = False, ""
    except S.CacheError as exc:
        caught_alt = True, str(exc)
    ok(caught_alt[0],
       "an OFAC list whose alias file did not arrive is refused, not committed",
       "it was accepted, and every published alias would be unsearchable")
    ok("alias" in (caught_alt[1] or "").lower(),
       "and the refusal says the alias file is the problem", (caught_alt[1] or "")[:90])

# --------------------------------------------------------------------------
# Swiss, quantified
# --------------------------------------------------------------------------
print("\nSWISS — the fields that were silently empty")
def _swiss_ready(meta):
    """Whether the Swiss cache can actually be READ by this build.

    `ok` in the manifest means the last refresh committed; it does not mean the
    file on disk is still readable by the code running now. A failed refresh
    keeps the last good entry, so `ok` stayed true while the cache sat at an
    older parser version and every read raised — which aborted this suite in the
    middle rather than failing an assertion. Ask the reader, and where it says
    no, fail loudly and carry on: a suite that quietly executes fewer assertions
    passes just as loudly as one that fails."""
    if not meta.get("swiss", {}).get("ok"):
        why = (meta.get("swiss", {}).get("error")
               or "swiss has never refreshed on this machine")
        return False, f"last refresh did not commit — {why}"
    try:
        S.read_source("swiss", meta["swiss"])
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


print("\nR10-8 — WHAT THE MANIFEST KNOWS, THE READER IS TOLD")
# alias_baseline and alias_removal_override were written onto the manifest by
# refresh() and read by nothing at all. A result produced against a list whose
# refresh skipped the published-name comparison looked exactly like one that
# passed it.
_base = {k: v for k, v in (meta.get("un") or {}).items()
         if k not in ("alias_baseline", "alias_removal_override")}
_fake = dict(_base, alias_removal_override=True)
_row = SC._prov_row(S.BY_ID["un"], {"un": _fake}, type("A", (), {"max_age_hours": 999999.0}),
                    searched=True, records=1)
ok("SANCTIONS_ALLOW_ALIAS_REMOVAL" in (_row.get("name_comparison") or ""),
   "a list refreshed under the name-removal override says so on its provenance row",
   str(_row.get("name_comparison"))[:120])
_fake2 = dict(_base, alias_baseline="not compared — generation change")
_row2 = SC._prov_row(S.BY_ID["un"], {"un": _fake2}, type("A", (), {"max_age_hours": 999999.0}),
                     searched=True, records=1)
ok("generation change" in (_row2.get("name_comparison") or ""),
   "and so does one whose comparison was skipped across a generation change",
   str(_row2.get("name_comparison"))[:120])
_clean = SC._prov_row(S.BY_ID["un"], {"un": _base}, type("A", (), {"max_age_hours": 999999.0}),
                      searched=True, records=1)
ok(not _clean.get("name_comparison"),
   "while an ordinary refresh carries no such note")

_SW_OK, _SW_WHY = _swiss_ready(meta)
if not _SW_OK:
    ok(False, "swiss: the cached list is readable by the build running these tests",
       _SW_WHY[:150])

if _SW_OK:
    sw = S.read_source("swiss", meta["swiss"])
    n = len(sw)
    for field, floor in (("regime", int(n * 0.9)), ("listed_on", int(n * 0.9)),
                         ("ids", 500), ("nationality", 1500), ("nonlatin", 3000)):
        got_n = sum(1 for r in sw if r.get(field))
        ok(got_n >= floor,
           f"swiss: {got_n:,} records carry {field} (>= {floor:,})")
    # The repeated-variant repair, measured against the raw file.
    import xml.etree.ElementTree as _ET
    _s = lambda tag: tag.split("}")[-1]
    root = _ET.parse(S.RAW / "swiss.xml").getroot()
    multi = 0
    for np in root.iter():
        if _s(np.tag) != "name-part":
            continue
        keys = {}
        for sv in np:
            if _s(sv.tag) == "spelling-variant" and (sv.text or "").strip():
                k = (sv.get("lang", ""), sv.get("script", ""))
                keys[k] = keys.get(k, 0) + 1
        if any(v > 1 for v in keys.values()):
            multi += 1
    ok(multi > 0,
       f"the raw file really does carry repeated same-key variants ({multi:,} name-parts)")
    total_names = sum(1 + len(r.get("aliases") or ()) + len(r.get("nonlatin") or ())
                      for r in sw)
    ok(total_names > n * 1.5,
       f"and the parser emits {total_names:,} names from {n:,} targets, so the "
       "repeated variants are kept rather than overwritten")


# --------------------------------------------------------------------------
# line separators — a designation is one line, whatever it contains
# --------------------------------------------------------------------------
print("\nLINE SEPARATORS — a designation is one line whatever it contains")
# Canada's list carries U+2028 inside one record. json.dumps(ensure_ascii=False)
# writes it raw; str.splitlines() treats it — and U+2029, NEL, VT, FF, FS, GS
# and RS — as a line break. The reader split the record in two and refused the
# whole list as damaged. Every Canadian screen since the fetch was NOT SEARCHED.
sep_dir = Path(tempfile.mkdtemp(prefix="sanctions-sep-"))
(sep_dir / "norm").mkdir()
sep_entry = dict(meta.get("ofsi", {}))
if sep_entry.get("ok"):
    sep_recs = [dict(r) for r in S.read_source("ofsi", sep_entry, use_cache=False)]
    SEPS = "line\u2028separator\u2029paragraph\x85nel\x0cff\x0bvt\x1cfs\x1dgs\x1ers "
    sep_recs[0]["notes"] = SEPS + (sep_recs[0].get("notes") or "")
    sep_path = sep_dir / "norm" / "ofsi.jsonl.gz"
    sep_path.write_bytes(gzip.compress("".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in sep_recs).encode("utf-8")))
    ok(len(gzip.decompress(sep_path.read_bytes()).decode("utf-8").splitlines()) > len(sep_recs),
       "control: splitlines() really does see more lines than there are records")
    _S3 = S.NORM
    S.NORM = sep_dir / "norm"
    try:
        sep_e = {"records": len(sep_recs),
                 "norm_sha256": hashlib.sha256(sep_path.read_bytes()).hexdigest(),
                 "parser_version": S.PARSER_VERSION,
                 "engine_version": S.ENGINE_VERSION}
        try:
            back = S.read_source("ofsi", sep_e, use_cache=False)
            sep_err = ""
        except S.CacheError as exc:
            back, sep_err = (), str(exc)
        ok(len(back) == len(sep_recs),
           f"a record carrying U+2028, U+2029, NEL, FF, VT, FS, GS and RS reads back whole "
           f"({len(sep_recs):,} designations)", sep_err)
        ok(bool(back) and "\u2028" in (back[0].get("notes") or ""),
           "and the separator survives inside the record rather than breaking it")
    finally:
        S.NORM = _S3

canada = meta.get("canada", {})
if canada.get("ok"):
    try:
        n_can = len(S.read_source("canada", canada, use_cache=False))
        can_err = ""
    except S.CacheError as exc:
        n_can, can_err = 0, str(exc)
    ok(n_can == canada["records"],
       f"the cached Canadian list — the one that carries U+2028 — reads in full ({n_can:,})",
       can_err)
else:
    print("       (Canada is not cached here; the live regression is not exercised)")

# --------------------------------------------------------------------------
# refresh reads back what it wrote before the manifest calls it good
# --------------------------------------------------------------------------
print("\nREFRESH READS BACK WHAT IT WROTE")
if sep_entry.get("ok"):
    rt = Path(tempfile.mkdtemp(prefix="sanctions-roundtrip-"))
    _S4 = (S.DATA, S.NORM, S.RAW, S.META)
    S.DATA, S.NORM, S.RAW, S.META = rt, rt / "norm", rt / "raw", rt / "meta.json"
    S.NORM.mkdir()
    S.RAW.mkdir()
    ofsi_src = S.BY_ID["ofsi"]
    saved_dl, saved_parser = S.download, S.PARSERS[ofsi_src.parser]

    def stub_download(src, timeout=600):
        (S.RAW / src.filename).write_bytes(b"stub raw file")
        return {str(S.RAW / src.filename): 13}

    try:
        S.download = stub_download
        S.PARSERS[ofsi_src.parser] = lambda src: (sep_recs, {"list_date": "", "list_date_source": "test"})
        rt_e = S.refresh(ofsi_src, {})
        ok(rt_e.get("ok") is True,
           "a list whose records carry line separators is committed", rt_e.get("error", ""))
        ok(rt_e.get("ok") and len(S.read_source("ofsi", rt_e, use_cache=False)) == len(sep_recs),
           "and reads back through read_source in full")
        # Now make the reader disagree with the writer, and see whether refresh
        # notices. Before the round trip, it did not: Canada was committed ok.
        good_bytes = (S.NORM / "ofsi.jsonl.gz").read_bytes()
        real_reader = S._load_norm
        S._load_norm = lambda path, entry: real_reader(path, entry)[:-1]
        try:
            rt_bad = S.refresh(ofsi_src, {"ofsi": rt_e})
        finally:
            S._load_norm = real_reader
        ok(rt_bad.get("ok") is False,
           "a list the reader cannot read back in full is NOT committed as good", str(rt_bad)[:200])
        ok("reads back" in rt_bad.get("error", ""),
           "and the error says the round trip failed", rt_bad.get("error", ""))
        ok(rt_bad.get("records") == 0, "and it claims no records")
        # The first repair read back the INSTALLED file, after it had replaced
        # the last good one: a failed readback left no good copy on disk.
        ok((S.NORM / "ofsi.jsonl.gz").read_bytes() == good_bytes,
           "and the last good file is untouched — the candidate never replaced it")
        ok(not list(S.NORM.glob(".*.candidate")), "and no candidate file lingers")
        ok(rt_bad.get("last_good_records") == len(sep_recs),
           "and the last good count is carried on the failed entry")
    finally:
        S.download, S.PARSERS[ofsi_src.parser] = saved_dl, saved_parser
        S.DATA, S.NORM, S.RAW, S.META = _S4


# --------------------------------------------------------------------------
# the alias file is measured in rows — not in designations carrying one alias
# --------------------------------------------------------------------------
print("\nALIAS ROWS — one alias per designation is not the alias file")
if meta.get("ofac-sdn", {}).get("ok"):
    # The fourth review kept the first ALT row for each of the 8,811 aliased
    # designations and dropped the other 11,336 — 56% of the file. Every floor
    # and shrink rule passed, because they counted designations with at least
    # one alias. CUBAN FREIGHT ENTERPRISE then returned a clean nil, exit 0.
    live_recs, live_extra = S.PARSERS[osdn.parser](osdn)
    ok(live_extra.get("alias_rows", 0) > 15_000 and live_extra.get("alias_total", 0) > 15_000,
       f"the parser reports the alias file in rows ({live_extra.get('alias_rows'):,}) and "
       f"emitted aliases ({live_extra.get('alias_total'):,})")
    try:
        S.alias_delta(osdn, live_extra, meta["ofac-sdn"])
        ok(True, "the live alias file passes against the live manifest")
    except S.CacheError as exc:
        ok(False, "the live alias file passes against the live manifest", str(exc))
    kept_one = dict(live_extra, alias_rows=8_811, alias_total=8_811)
    for label, prev in [("with no previous manifest (the floor)", None),
                        ("against the last good refresh (the shrink rule)",
                         {"ok": True, "alias_rows": live_extra["alias_rows"],
                          "alias_total": live_extra["alias_total"]})]:
        try:
            S.alias_delta(osdn, kept_one, prev)
            ok(False, f"one alias per designation is refused {label}", "it passed")
        except S.CacheError as exc:
            ok(True, f"one alias per designation is refused {label}")
            ok("alias" in str(exc), "and the refusal names the alias file", str(exc))
    fewer_aliases = dict(live_extra, alias_total=int(live_extra["alias_total"] * 0.7))
    try:
        S.alias_delta(osdn, fewer_aliases,
                      {"ok": True, "alias_rows": live_extra["alias_rows"],
                       "alias_total": live_extra["alias_total"]})
        ok(False, "a 30% fall in emitted aliases with the row count intact is refused", "it passed")
    except S.CacheError:
        ok(True, "a 30% fall in emitted aliases with the row count intact is refused")
    try:
        S.alias_delta(S.BY_ID["ofsi"], {"list_date": "x"}, {"ok": True, "alias_rows": 999})
        ok(True, "a parser with no auxiliary file is not measured against one")
    except S.CacheError as exc:
        ok(False, "a parser with no auxiliary file is not measured against one", str(exc))

# --------------------------------------------------------------------------
# chronology — a list dated earlier than the last good one is a rollback
# --------------------------------------------------------------------------
print("\nCHRONOLOGY — an older list is not a fresher one")
os.environ.pop("SANCTIONS_ALLOW_ROLLBACK", None)
ofsi_src2 = S.BY_ID["ofsi"]
good_prev = {"ok": True, "list_date": "03/06/2026"}
for label, new_date, prev, should_refuse in [
        ("an OFSI list dated 01/01/2000 after one dated 03/06/2026", "01/01/2000", good_prev, True),
        ("the same date again", "03/06/2026", good_prev, False),
        ("a later date", "04/06/2026", good_prev, False),
        ("a rollback measured against the LAST GOOD date after a failed refresh", "01/01/2000",
         {"ok": False, "last_good_list_date": "03/06/2026"}, True),
        ("no previous manifest at all", "01/01/2000", None, False),
        ("a publisher that dates nothing (OFAC, Canada)", "", good_prev, False),
        ("a UK-format date against an ISO one", "01-Jan-2000", {"ok": True, "list_date": "2026-09-01T23:00:05.434Z"}, True)]:
    try:
        S.chronology(ofsi_src2, new_date, prev)
        refused, why = False, ""
    except S.CacheError as exc:
        refused, why = True, str(exc)
    ok(refused == should_refuse, f"{label}: {'refused' if should_refuse else 'accepted'}", why)
    if should_refuse and refused:
        ok("rollback" in why, "and the refusal calls it a rollback", why)
os.environ["SANCTIONS_ALLOW_ROLLBACK"] = "1"
try:
    S.chronology(ofsi_src2, "01/01/2000", good_prev)
    ok(True, "SANCTIONS_ALLOW_ROLLBACK=1 lets a verified publisher correction through")
except S.CacheError as exc:
    ok(False, "SANCTIONS_ALLOW_ROLLBACK=1 lets a verified publisher correction through", str(exc))
finally:
    os.environ.pop("SANCTIONS_ALLOW_ROLLBACK", None)
ok(S.parse_list_date("02-Sep-2026") == S.parse_list_date("2026-09-02") == S.parse_list_date("2026-09-02T10:00:00Z"),
   "the UK, ISO and ISO-with-time forms of one day compare equal")
ok(S.parse_list_date("03/06/2026").month == 6, "OFSI's date is read day-first")
ok(S.parse_list_date("not a date") is None and S.parse_list_date("") is None,
   "an unknown form is no date, not a wrong one")
for sid, e in meta.items():
    if isinstance(e, dict) and e.get("ok"):
        ok(bool(e.get("chronology")),
           f"{sid}: the manifest states whether chronology can be established "
           f"({str(e.get('chronology'))[:28]})")

# --------------------------------------------------------------------------
# a de-listed Swiss target carries the date it was taken off
# --------------------------------------------------------------------------
print("\nDE-LISTED — the record says so, and when")
if _SW_OK:
    sw2 = S.read_source("swiss", meta["swiss"])
    gone = [r for r in sw2 if r.get("status") == "delisted"]
    dated = [r for r in gone if r.get("delisted_on")]
    ok(len(gone) > 1_000, f"the Swiss list carries de-listed targets ({len(gone):,})")
    ok(len(dated) > len(gone) * 0.9,
       f"and {len(dated):,} of them carry the date they were de-listed")
    ok(all(not r.get("delisted_on") for r in sw2 if r.get("status") == "active"),
       "an active target carries no de-listing date")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print("  FAILED: " + f)
sys.exit(1 if FAIL else 0)
