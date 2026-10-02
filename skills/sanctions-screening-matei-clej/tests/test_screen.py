#!/usr/bin/env python3
"""
Regression tests for the sanctions screening skill.

    python3 test_screen.py

The matching tests run offline. The data tests are skipped if nothing has been
refreshed yet. Every assertion here exists because the behaviour it pins was
wrong at some point and would have been silent in use.
"""

import argparse
import collections
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matching as M
import screen as SC
import sources as S

PASS, FAIL = [], []


def ok(cond, label, detail=""):
    text = label + (f" — {detail}" if detail and not cond else "")
    (PASS if cond else FAIL).append(text)
    print(("  ✓ " if cond else "  ✗ ") + text)


def sc(q, c, kind="individual"):
    return SC.score(q, c, kind)


print("matching")
ok(sc("Vladimir Putin", "Vladimir Putin") == 100, "identical names score 100")
ok(sc("Vladimir Putin", "PUTIN Vladimir Vladimirovich") >= 95,
   "surname-first listing with a patronymic still matches")
ok(sc("Putin", "PUTIN Vladimir Vladimirovich") >= 85,
   "a client who gives fewer names than the listing still matches")
ok(sc("Mian Mithoo", "ASHRAF, Haji M.") < 85,
   "initials alone are not a match (the M. defect)")
ok(sc("John Smith", "John") < 85,
   "a listing carrying only a bare forename is not a 100 match (subset inflation)")
# A name typed without its spaces is the same name, and must score as one — but
# the comparison that recovers it is the same shape as subset inflation, so it
# is guarded on length and both halves are asserted here.
ok(sc("JieShun", "Jie Shun", "entity") >= 95,
   "a name typed without its spaces still matches the listing that has them")
ok(sc("Jie Shun", "JieShun", "entity") >= 95,
   "and the reverse: a listing published without spaces is still found")
ok(sc("SEAMAVERICK", "SEA MAVERICK", "entity") >= 95,
   "a vessel name run together matches")
# The guard is what keeps the two apart: a run-together query that is far LONGER
# than the listing is a different name, not the same one missing its spaces.
ok(sc("JieShunLimitedCompany", "Jie Shun", "entity") < 85,
   "a longer run-together query does not concatenate its way onto a shorter listing")
ok(sc("JohnSmithPeterson", "John Smith") < 85,
   "and the length guard holds for individuals too")
ok(sc("V Putin", "PUTIN Vladimir") >= 85, "an initial corroborates a real surname match")
ok(sc("X", "XI Jinping") < 85, "a query that is only an initial identifies nobody")
ok(sc("Putin", "PUTIN Vladimir Vladimirovich") >= 85,
   "a single full surname is a legitimate broad search")
ok(sc("Chirila Daniela", "CHIRILĂ DANIELA") == 100, "diacritics are folded")
ok(sc("Mr Ivan Petrov", "Ivan Petrov") == 100, "titles are stripped")
ok(sc("Ruslan Romashkin", "Ruslan Alexandrovich ROMASHKІN") >= 90,
   "a Cyrillic homoglyph inside a Latin name does not break the match")
ok(sc("Acme Trading LLC", "Acme Trading", "entity") >= 95,
   "corporate suffixes do not defeat an entity match")
ok(sc("Acme Trading LLC", "Zenith Shipping", "entity") < 60, "unrelated entities score low")

print("the gate and the matcher")
ok(SC.Outcome(subject={}, threshold=88.0).exit_code == SC.EXIT_INCOMPLETE,
   "an outcome with no sources is incomplete, never clean")
ok(sc("LLC Synesis", "Synesis", "entity") >= 88,
   "an entity query keeps its corporate suffix from defeating the match")
ok(M.transliterate("Кадыров") == "Kadyrov", "Cyrillic romanises for the Latin lists")
ok(M.native_key("КАДЫРОВ") == M.native_key("кадыров"), "native keys fold case")
# Latin letters that carry their mark inside the glyph must survive as letters,
# not be cut to spaces: "Međunarodna" was becoming "ME UNARODNA".
ok(M.normalise("Međunarodna") == "MEDUNARODNA", "d with stroke folds to d",
   M.normalise("Međunarodna"))
ok(M.normalise("Straße") == "STRASSE", "sharp s folds to ss", M.normalise("Straße"))
ok(M.normalise("Þórður Ægisson") == "THORDUR AEGISSON",
   "thorn, eth and ash fold to Latin", M.normalise("Þórður Ægisson"))
ok(not M.unmappable_letters("Međunarodna Łukasz Þór Straße"),
   "and none of them is read as a script the tool cannot romanise",
   "".join(M.unmappable_letters("Međunarodna Łukasz Þór Straße")))
ok(M.unmappable_letters("يحيى") and M.unmappable_letters("习近平")
   and M.unmappable_letters("Ομοσπονδιακή"),
   "while Arabic, Han and Greek still are")
ok(M.is_native("Кадыров") and not M.is_native("Kadyrov"), "script detection")

print("dates")
ok(SC.parse_dob("07 Oct 1952") == ("1952", "1952-10-07"), "OFAC textual date parses")
ok(SC.parse_dob("07/10/1952") == ("1952", "1952-10-07"), "UK dd/mm/yyyy parses")
ok(SC.parse_dob("1952-10-07") == ("1952", "1952-10-07"), "ISO date parses")
ok(SC.parse_dob("1952") == ("1952", ""), "bare year parses as a year")
ok(SC.parse_dob("") is None, "empty date is no date")
ok(SC.dob_verdict("1952-10-07", ["07 Oct 1952"])[0] == "DOB exact match", "exact DOB is recognised")
ok(SC.dob_verdict("1952-01-01", ["07 Oct 1952"])[0] == "DOB year match", "same year, different day")
n, adj = SC.dob_verdict("1980-01-01", ["07 Oct 1952"])
ok(n == "DOB conflict" and -8 < adj < 0,
   "a DOB conflict downgrades and annotates, and never eliminates")

print("data — every default list must be present and parse")
meta = S.load_meta()
LATIN_CH = re.compile(r"[A-Za-z]")
LETTER_CH = re.compile(r"[^\W\d_]", re.UNICODE)


def _mostly_nonlatin(s):
    letters = LETTER_CH.findall(s or "")
    return bool(letters) and sum(1 for c in letters if LATIN_CH.match(c)) * 2 < len(letters)

# What each list must yield if its parser is doing its job. A suite that quietly
# executes fewer assertions on an empty cache passes just as loudly as one that
# checked everything, so an unrefreshed default list is a FAILURE here, not a
# skip. SANCTIONS_TESTS_ALLOW_UNREFRESHED=1 for a deliberately offline run.
# Per-type FLOORS, not a presence check. A parser that misclassifies all but one
# vessel satisfies "at least one vessel exists", which is how 81 OFSI ships and
# 342 OFAC aircraft sat in the wrong bucket. Floors are roughly a third below
# what the live files held on 02.09.2026.
EXPECTED = {
    # id                 min records  min non-Latin  {type: minimum}
    "uk-sanctions-list": (5_000, 1_000, {"individual": 2_500, "entity": 1_000,
                                         "vessel": 400}),
    "ofsi":              (4_000,     0, {"individual": 2_500, "entity": 800,
                                         "vessel": 10}),
    "un":                (  800,   100, {"individual": 500, "entity": 180}),
    "eu":                (5_000,   500, {"individual": 3_000, "entity": 1_200}),
    "ofac-sdn":          (15_000,    0, {"individual": 5_000, "entity": 6_500,
                                         "vessel": 1_000, "aircraft": 200}),
    "ofac-cons":         (  300,     0, {"individual": 70, "entity": 240}),
}
ALLOW_UNREFRESHED = os.environ.get("SANCTIONS_TESTS_ALLOW_UNREFRESHED") == "1"

for sid, (min_recs, min_nl, must_types) in EXPECTED.items():
    e = meta.get(sid, {})
    if not e.get("ok"):
        if ALLOW_UNREFRESHED:
            print(f"  – {sid}: not refreshed, skipped by request")
            continue
        ok(False, f"{sid}: is refreshed and testable",
           "run `python3 screen.py refresh`; an unchecked list is not a passing test")
        continue
    recs = list(S.load_records(sid))
    ok(len(recs) >= min_recs,
       f"{sid}: parsed {len(recs):,} designations (>= {min_recs:,})")
    ok(all(r.get("name") for r in recs), f"{sid}: every designation has a name")
    bad = [r for r in recs if r.get("nonlatin") and _mostly_nonlatin(r.get("name", ""))]
    ok(not bad, f"{sid}: the display name is a Latin-script name where one is published")
    # A positive floor. Deleting all non-Latin extraction satisfied the negative
    # assertion above, because a record with no nonlatin cannot be a bad one.
    got_nl = sum(1 for r in recs if r.get("nonlatin"))
    ok(got_nl >= min_nl,
       f"{sid}: {got_nl:,} designations carry a native-script name (>= {min_nl:,})")
    counts = collections.Counter(r.get("type") for r in recs)
    short = {k: (counts.get(k, 0), floor) for k, floor in must_types.items()
             if counts.get(k, 0) < floor}
    ok(not short,
       f"{sid}: every subject type is mapped in the numbers the publisher gives "
       f"({', '.join(f'{k} {counts.get(k, 0):,}' for k in sorted(must_types))})",
       "; ".join(f"{k}: {got:,} < {want:,}" for k, (got, want) in short.items()))
    unknown = counts.get("unknown", 0)
    ok(unknown <= len(recs) * 0.01,
       f"{sid}: at most 1% of designations are of unknown type ({unknown:,})")

if meta.get("ofsi", {}).get("ok") and meta.get("uk-sanctions-list", {}).get("ok"):
    class A:
        dob = nationality = ""
        type = "individual"
        threshold = 85.0
        limit = 40
        include_delisted = False
    A.max_age_hours = 24.0
    A.client = A.matter = ""
    o = SC.screen("Vladimir Putin", A, [S.BY_ID["ofsi"], S.BY_ID["uk-sanctions-list"]])
    hits = o.hits
    # asserted per source: "any hit anywhere" passed even if one list returned nothing
    for sid in ("ofsi", "uk-sanctions-list"):
        found = [h for h in hits if h["record"]["source"] == sid
                 and h["record"]["ref"].startswith("RUS0251")]
        ok(bool(found), f"{sid}: the designation is found under its published reference")
    ok(bool(hits) and hits[0]["score"] >= 99, "the designated person ranks first")
    ok(o.complete, "a search of two healthy lists reports itself complete")
    ok(o.exit_code == 2, "candidates exit 2")

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


print("\nONE CACHE GENERATION — SO AN ENGINE CHANGE MOVES WHAT OLD BUILDS CHECK")
ok(S.PARSER_VERSION == S.CACHE_GENERATION == S.ENGINE_VERSION,
   "the parser version, the engine version and the cache generation are ONE number. "
   "Two numbers meant an engine-only change moved a field that older builds have "
   "never heard of, while leaving the one they do check untouched — which is how a "
   "four-round-stale install went on sharing this cache and reporting six of six "
   "lists searched, exit 0, on names that were on them",
   f"parser {S.PARSER_VERSION}, engine {S.ENGINE_VERSION}, generation {S.CACHE_GENERATION}")

_SW_OK, _SW_WHY = _swiss_ready(meta)
if not _SW_OK:
    ok(False, "swiss: the cached list is readable by the build running these tests",
       _SW_WHY[:150])

if _SW_OK:
    recs = list(S.load_records("swiss"))
    ok(any(r["status"] == "delisted" for r in recs),
       "the Swiss whole-list file does carry de-listed targets")
    class B:
        dob = nationality = ""
        type = "any"
        threshold = 85.0
        limit = 50
        include_delisted = False
    B.max_age_hours = 24.0
    B.client = B.matter = ""
    sw = SC.screen("Lukashenka", B, [S.BY_ID["swiss"]]).hits
    # all() over an empty list is vacuously true: require hits before asserting
    ok(bool(sw) and all(h["record"]["status"] == "active" for h in sw),
       f"de-listed targets are excluded unless asked for ({len(sw)} live hits)")


# --------------------------------------------------------------------------
# End to end, through the real screen(), against the real cache. The unit-level
# assertions above passed while every one of these returned a clean nil.
# --------------------------------------------------------------------------
print("end to end — the designations a scorer test cannot vouch for")


def args(**kw):
    base = dict(dob="", nationality="", type="individual", client="", matter="",
                threshold=88.0, limit=40, max_age_hours=24.0, include_delisted=False)
    base.update(kw)
    return argparse.Namespace(**base)


def run_screen(name, **kw):
    srcs = [S.BY_ID[i] for i in kw.pop("sources", ("ofsi",))]
    return SC.screen(name, args(**kw), srcs, meta)


if all(meta.get(s, {}).get("ok") for s in ("ofsi", "ofac-sdn", "uk-sanctions-list")):
    # A ship typed "entity" is invisible to --type vessel and reports a clean
    # nil. OFSI publishes 81 such rows; they were all filed as entities.
    o = run_screen("AN SAN 1", type="vessel", sources=("ofsi",))
    ok(o.total_hits >= 1 and o.exit_code == 2,
       "an OFSI ship is found by a vessel search",
       f"{o.total_hits} hits, exit {o.exit_code}")
    ok(any(h["record"]["ref"].startswith("DPR0097") for h in o.hits),
       "the ship found is the designation, by its published reference")

    o = run_screen("EP-GOL", type="aircraft", sources=("ofac-sdn",))
    ok(o.total_hits >= 1, "an OFAC aircraft is found by an aircraft search",
       f"{o.total_hits} hits")

    # One romanisation system missed this by two tenths of a point.
    o = run_screen("Юрий Викторович Федоров", type="any", sources=("ofac-sdn",))
    ok(any("FEDOROV" in h["record"]["name"].upper() for h in o.hits),
       "a Cyrillic query finds the OFAC listing published only in Latin",
       f"{o.total_hits} hits")
    ok(len(o.subject.get("romanisations") or []) > 1,
       "more than one romanisation was actually compared, and the record says so")

    # A script that cannot be romanised is refused, not quietly reported clean.
    o = run_screen("يحيى السنوار", type="any", sources=("uk-sanctions-list", "ofac-sdn"))
    ok(o.exit_code == 4 and not o.complete,
       "an unromanisable script is refused, not reported as a complete nil",
       f"exit {o.exit_code}, complete {o.complete}")
    ok(all(not s["searched"] for s in o.sources),
       "a refused query leaves every list marked not searched")

    # --type any must dispatch tokenisation on the CANDIDATE's type. Tested
    # through screen(), because the scorer test passes kind="entity" by hand.
    o = run_screen("LLC Synesis", type="any", sources=("uk-sanctions-list",))
    ok(any(h["record"]["ref"].startswith("BEL") or "SYNESIS" in h["record"]["name"].upper()
           for h in o.hits),
       "--type any finds an entity whose corporate suffix the query carries",
       f"{o.total_hits} hits")

    # The threshold applies to the NAME. A wrong date of birth annotates and
    # reorders; it must never remove a candidate that the name reached.
    clean = run_screen("Vladimir Putin", sources=("ofsi",))
    wrong = run_screen("Vladimir Putin", dob="1801-01-01", sources=("ofsi",))
    ok(clean.total_hits and wrong.total_hits == clean.total_hits,
       "a conflicting date of birth removes no candidate end to end",
       f"{clean.total_hits} -> {wrong.total_hits}")
    ok(any("DOB conflict" in f for h in wrong.hits for f in h["flags"]),
       "the conflict is recorded on the candidate as a flag")


# --------------------------------------------------------------------------
# THE SELF-RETRIEVAL INVARIANT
#
# Every name a publisher prints must be findable by typing that name. It sounds
# too obvious to test, which is why nobody did: 54 published designations could
# not find themselves, capped at 70 as "uncorroborated initials" — among them
# "E. S. Co.", "T.R.O.S" and the tanker LADY R, an exact primary designation on
# two lists returning a clean nil and exit 0. This is a release gate.
# --------------------------------------------------------------------------
print("self-retrieval — every published name finds itself")

SEED_SELF = 20260902   # fixed, so the sample is the same every run
SELF_SOURCES = ("uk-sanctions-list", "ofsi", "un", "eu", "ofac-sdn", "ofac-cons")
if all(meta.get(s, {}).get("ok") for s in SELF_SOURCES):
    # (a) Indexing must produce, for every published name, a candidate whose
    #     normalised form is exactly what screen() will normalise that name to.
    #     A name that normalises to nothing is dropped from the index and is then
    #     unfindable by any query, including its own.
    missing, checked, scorer_only, native_fallback = [], 0, [], []
    for sid in SELF_SOURCES:
        recs = S.read_source(sid, meta[sid])
        indexed = SC._index(sid, recs)
        for rec, names, _mask, _native in indexed:
            have = {n for _c, n, _i, _e in names}
            as_entity = rec.get("type") in ("entity", "vessel", "aircraft")
            kind = "entity" if as_entity else "individual"
            for nm in [rec.get("name", "")] + list(rec.get("aliases") or []):
                if not nm.strip():
                    continue
                n = M.normalise(nm)
                if not n:
                    # Not indexable in Latin — it must then be reachable
                    # natively, or it is reachable by nothing at all.
                    if not M.native_key(nm):
                        missing.append((sid, nm, "reaches neither index"))
                    else:
                        native_fallback.append((sid, nm))
                    continue
                checked += 1
                if n not in have:
                    missing.append((sid, nm, "not in the index"))
                    continue
                # What the SCORER alone would give, with the exact-name rule off.
                # These are the names that depend on it, and the count is the
                # measure of how much work it is doing.
                tk = M.tokens_from_normalised(n, kind)
                if not tk or M.score_tokens(tk, tk) < SC.DEFAULT_THRESHOLD:
                    scorer_only.append((sid, rec.get("type"), nm))
    for sid, nm in native_fallback:
        recs = S.read_source(sid, meta[sid])
        idx = SC._index(sid, recs)
        reachable = any(nm in [c for c, _k in nat] for _r, _n, _m, nat in idx)
        ok(reachable,
           f"{sid}: the native-script name {nm[:24]!r} filed under aliases is still indexed",
           "it reaches neither the Latin index nor the native one")
    ok(not missing,
       f"all {checked:,} published names are indexed under the form screen() will look for",
       "; ".join(f"{m[1]!r}: {m[2]}" for m in missing[:6]))
    print(f"       ({len(scorer_only)} of them reach the threshold only because an exact "
          f"published name scores 100; e.g. "
          f"{', '.join(repr(s[2]) for s in scorer_only[:3])})")

    # (b) A real end-to-end sample, through screen(), at about a second each.
    sample = random.Random(SEED_SELF).sample(
        [r for r in S.read_source("ofsi", meta["ofsi"]) if r.get("name")], 25)
    lost = []
    for rec in sample:
        o = SC.screen(rec["name"], args(type="any", limit=5, include_delisted=True),
                      [S.BY_ID["ofsi"]], meta)
        if not any(h["record"]["uid"] == rec["uid"] for h in o.hits):
            lost.append((rec["name"], rec.get("type"), o.total_hits))
    ok(not lost, f"{len(sample)} designations sampled at random each find themselves "
                 f"through the real screen()",
       "; ".join(f"{l[0]!r} ({l[1]})" for l in lost[:4]))

    # And the same thing end to end, for the shapes that were failing: a name
    # that survives tokenisation only as initials, and one whose first word is a
    # personal title on a vessel.
    for nm, kind in [("LADY R", "vessel"), ("E. S. Co.", "entity"),
                     ("T.R.O.S", "entity"), ("G-9", "entity"), ("1-P", "any")]:
        o = SC.screen(nm, args(type=kind, limit=5, include_delisted=True),
                      [S.BY_ID["uk-sanctions-list"], S.BY_ID["ofsi"],
                       S.BY_ID["ofac-sdn"]], meta)
        ok(o.total_hits >= 1 and o.hits[0]["score"] >= 99,
           f"{nm!r} finds its own designation through the real screen()",
           f"{o.total_hits} hits, top {o.hits[0]['score'] if o.hits else 0}")

    # The rule must not become a licence: a query that is NOT the published name
    # still has to earn its score.
    o = SC.screen("R", args(type="vessel", limit=5), [S.BY_ID["uk-sanctions-list"]], meta)
    ok(not any(h["record"]["name"].upper() == "LADY R" for h in o.hits),
       "a bare initial does not reach LADY R merely because LADY R reduces to one",
       f"{o.total_hits} hits")

    # A personal title is still stripped from a person, and now kept on a ship.
    ok(M.tokens("Dr Ivan Petrov", "individual") == ["IVAN", "PETROV"],
       "a personal title is still stripped from an individual")
    ok(M.tokens("LADY R", "entity") == ["LADY", "R"],
       "and is kept where the designation is a vessel or an entity")
    ok(M.tokens("The Acme Company", "entity") == ["ACME"],
       "the definite article is dropped whatever is designated")


# --------------------------------------------------------------------------
# control characters — a name is letters, not instructions to the terminal
# --------------------------------------------------------------------------
print("control characters")
ESCAPED = "\x1b[32mLADY\x1b[0m R"
ok(M.strip_control(ESCAPED) == "LADY R",
   "a CSI colour sequence is stripped whole, not left behind as digits", repr(M.strip_control(ESCAPED)))
ok(M.normalise(ESCAPED) == "LADY R",
   "and never reaches the index as name parts", repr(M.normalise(ESCAPED)))
ok(M.tokens(ESCAPED, "entity") == ["LADY", "R"],
   "so the tokens are the name's, not the sequence's", M.tokens(ESCAPED, "entity"))
LINK = "\x1b]8;;http://example.invalid\x07LADY R\x1b]8;;\x07"
ok(M.strip_control(LINK) == "LADY R", "an OSC hyperlink is stripped whole", repr(M.strip_control(LINK)))
ok(M.strip_control("\x1b]0;title with no terminator") == "",
   "an unterminated OSC is swallowed to the end rather than let through")
ok(M.strip_control("PUT\u202eNIT") == "PUTNIT", "a bidi override is stripped")
ARABIC = "ABD ALLAH \u202b\u0639\u0628\u062f\u202c"
ok(M.strip_control(ARABIC) == "ABD ALLAH \u0639\u0628\u062f",
   "a bidi embedding is stripped and the Arabic it wrapped survives — the UK and "
   "OFSI lists carry these; the fourth review showed a terminal honours them too",
   repr(M.strip_control(ARABIC)))
ok(M.strip_control("\x9b31mLADY\x9b0m R") == "LADY R",
   "an 8-bit CSI is consumed whole — its parameters are not left behind as name",
   repr(M.strip_control("\x9b31mLADY\x9b0m R")))
ok(M.strip_control("\x9d0;title\x9cLADY R") == "LADY R", "an 8-bit OSC is consumed whole")
ok(M.strip_control("\u2067LADY R\u2069\u200e\u061c\u202a") == "LADY R",
   "bidi isolates, marks and embeddings are all stripped")
ok(M.normalise("\x9b31mLADY\x9b0m R") == "LADY R",
   "and the index never sees the parameters", repr(M.normalise("\x9b31mLADY\x9b0m R")))
ok(M.strip_control("A\x00B\x7fC\x8fD\x1cE") == "ABCDE", "C0, DEL, C1 and the field separators go")
# 0x9B is the 8-bit CSI introducer and "D" is a valid final byte (cursor back),
# so "\x9bD" is one sequence and goes whole — the old assertion expected the D
# to survive, which is exactly the residue the fourth review found.
ok(M.strip_control("A\x9bDB") == "AB", "an 8-bit CSI with a bare final byte goes whole")
ok(M.strip_control("A\tB\nC\rD") == "A\tB\nC\rD",
   "tab, newline and carriage return are whitespace and are left for the consumer to fold")
ok(M.normalise("LADY\rR\u2028X") == "LADY R X",
   "the index folds that whitespace, and U+2028, to a space")
ok(SC.term("LADY\r\nR\u2028X\x1b[2K") == "LADY R X",
   "term() keeps a value on one line with no escape in it", repr(SC.term("LADY\r\nR\u2028X\x1b[2K")))
ok(M.native_key("\x1b[31m\u041a\u0430\u0434\u044b\u0440\u043e\u0432\x1b[0m") == M.native_key("\u041a\u0430\u0434\u044b\u0440\u043e\u0432"),
   "the native index is stripped the same way")


# --------------------------------------------------------------------------
# mixed script — a Cyrillic surname in a Latin name is still Cyrillic
# --------------------------------------------------------------------------
print("mixed script")
MIXED = "Yury Viktorovich \u0424\u0435\u0434\u043e\u0440\u043e\u0432"
ok(M.has_romanisable(MIXED) and not M.is_native(MIXED),
   "a Latin-majority name with Cyrillic in it is romanisable without being native")
ok(M.transliterate_variants(MIXED)[0] == "Yury Viktorovich Fedorov",
   "and romanises to the spelling OFAC publishes", M.transliterate_variants(MIXED)[:2])
ok(not M.has_romanisable("Yury Fedorov"), "a Latin name is not romanised")
if meta.get("ofac-sdn", {}).get("ok"):
    # Reproduced by the fourth review against a fresh OFAC list: exit 0, zero
    # hits, complete, while the Latin spelling found him at 100.
    o = run_screen(MIXED, sources=("ofac-sdn",))
    ok(o.total_hits >= 1 and o.exit_code == 2,
       "a Latin-majority query with a Cyrillic surname finds OFAC's FEDOROV, Yury Viktorovich",
       f"{o.total_hits} hits, exit {o.exit_code}")
    ok(any("FEDOROV" in h["record"]["name"].upper() for h in o.hits), "and it is him")
    ok(bool(o.subject.get("romanisations")), "and the record says it was romanised")

# --------------------------------------------------------------------------
# the index is frozen — the source records were, the index built from them was not
# --------------------------------------------------------------------------
print("the index is frozen")
if meta.get("ofsi", {}).get("ok"):
    frozen_recs = S.read_source("ofsi", meta["ofsi"])
    idx = SC._index("ofsi", frozen_recs)
    ok(isinstance(idx, tuple), "the index is a tuple, not a list")
    entry_with_names = next(e for e in idx if e[1])
    for label, fn in [("clear the index", lambda: idx.clear()),
                      ("append to it", lambda: idx.append(None)),
                      ("append to a record's names", lambda: entry_with_names[1].append(None)),
                      ("append to a token list", lambda: entry_with_names[1][0][2].append("X"))]:
        try:
            fn()
            ok(False, f"a caller cannot {label}", "it succeeded — the index is mutable")
        except (AttributeError, TypeError) as exc:
            ok(True, f"a caller cannot {label} ({type(exc).__name__})")
    o = run_screen("AN SAN 1", type="vessel", sources=("ofsi",))
    ok(o.total_hits >= 1, "and AN SAN 1 is still found after every attempt")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print("  FAILED: " + f)
sys.exit(1 if FAIL else 0)
