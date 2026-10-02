#!/usr/bin/env python3
"""
Open-source sanctions and PEP screening.

    python3 screen.py refresh                      # fetch + parse the default lists
    python3 screen.py status                       # what is cached, how old, how many
    python3 screen.py sources                      # the registry, with licences
    python3 screen.py check "Ivan Petrov" --dob 1975-03-02 --nationality RU
    python3 screen.py batch clients.csv --report-dir ./screening/

The tool produces CANDIDATES and provenance. It never clears anybody: the
decision, and the record of the decision, belong to the fee earner.

Every route out of this program — text, JSON, a written record, a batch summary,
an exit code — is rendered from one Outcome object, and an Outcome knows whether
the search was complete. There is no path that reports "nothing found" without
also carrying whether anything was actually searched.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matching as M  # noqa: E402
import sources as S  # noqa: E402

normalise = M.normalise
tokens = M.tokens
score = M.score
TITLES = M.TITLES
CORP = M.CORP

DEFAULT_THRESHOLD = 88.0
"""Set from measurement, not taste — see tests/threshold_sweep.py.

Across 347 searches for real designations under deformed spellings, recall is
identical at every cut-off from 85 to 92 (99.7%), while the false-positive rate
on ordinary names falls from 20.0% to 2.0%. No true match scored anywhere
between 85 and 92: genuine matches cluster at 92 and above, and the noise sits
just above 85."""

TYPES = ("individual", "entity", "vessel", "aircraft", "any")

CLOCK_SKEW_HOURS = 1.0   # tolerated disagreement between this clock and the manifest's

EXIT_CLEAN = 0        # complete search, nothing found
EXIT_CANDIDATES = 2   # candidates to consider
EXIT_INCOMPLETE = 3   # the search cannot be relied on
EXIT_USAGE = 4        # the request itself was invalid


# --------------------------------------------------------------------------
# dates — biographical detail annotates and ranks, and never suppresses
# --------------------------------------------------------------------------

DATE_RE = re.compile(r"(\d{4})[-/. ]?(\d{2})?[-/. ]?(\d{2})?")
DMY_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")
TEXT_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})")
MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def parse_dob(raw: str):
    """Return (year, iso-or-empty). Handles 1975, 1975-03-02, 02/03/1975 and
    OFAC's "07 Oct 1952"."""
    raw = (raw or "").strip()
    if not raw:
        return None
    m = DMY_RE.search(raw)
    if m:
        d, mo, y = m.groups()
        return y, f"{y}-{int(mo):02d}-{int(d):02d}"
    m = TEXT_DATE_RE.search(raw)
    if m:
        d, mon, y = m.groups()
        mo = MONTHS.get(mon[:3].upper())
        if mo:
            return y, f"{y}-{mo:02d}-{int(d):02d}"
    m = DATE_RE.search(raw)
    if m:
        y, mo, d = m.groups()
        return y, f"{y}-{mo}-{d}" if mo and d else ""
    return None


def dob_verdict(query_dob: str, record_dobs: list) -> tuple:
    """Return (note, rank_adjustment).

    The adjustment orders candidates on screen. It is NEVER applied before the
    threshold: a date of birth that disagrees is a reason for a human to discount
    a candidate, not a reason the tool should hide one. "John Smythe" against a
    listed "John Smith" scores 92.9 on the name; a conflicting date once dropped
    that to 86.9 and removed the candidate entirely."""
    q = parse_dob(query_dob)
    if not q or not record_dobs:
        return "", 0.0
    qy, qiso = q
    best, adj = "", 0.0
    for raw in record_dobs:
        r = parse_dob(raw)
        if not r:
            continue
        ry, riso = r
        if qiso and riso and qiso == riso:
            return "DOB exact match", 8.0
        if qy == ry:
            best, adj = "DOB year match", 4.0
        elif not best:
            best, adj = "DOB conflict", -6.0
    return best, adj


# ISO 3166 alpha-2 and alpha-3 for the states that actually appear on these
# lists, so that a user who types a code is not silently told the country is not
# stated. Deliberately not exhaustive: a code that is not here is compared as
# written, which is the honest failure — an annotation that is absent costs a
# reader nothing, and one that is wrong moves a candidate up the page.
_ISO = {
    "RU": "RUSSIA", "RUS": "RUSSIA", "BY": "BELARUS", "BLR": "BELARUS",
    "IR": "IRAN", "IRN": "IRAN", "SY": "SYRIA", "SYR": "SYRIA",
    "KP": "KOREA", "PRK": "KOREA", "IQ": "IRAQ", "IRQ": "IRAQ",
    "AF": "AFGHANISTAN", "AFG": "AFGHANISTAN", "UA": "UKRAINE", "UKR": "UKRAINE",
    "CN": "CHINA", "CHN": "CHINA", "VE": "VENEZUELA", "VEN": "VENEZUELA",
    "LB": "LEBANON", "LBN": "LEBANON", "MX": "MEXICO", "MEX": "MEXICO",
    "LY": "LIBYA", "LBY": "LIBYA", "MM": "MYANMAR", "MMR": "MYANMAR",
    "SD": "SUDAN", "SDN": "SUDAN", "SS": "SOUTH SUDAN", "SSD": "SOUTH SUDAN",
    "YE": "YEMEN", "YEM": "YEMEN", "SO": "SOMALIA", "SOM": "SOMALIA",
    "ZW": "ZIMBABWE", "ZWE": "ZIMBABWE", "CU": "CUBA", "CUB": "CUBA",
    "TR": "TURKEY", "TUR": "TURKEY", "PK": "PAKISTAN", "PAK": "PAKISTAN",
    "IN": "INDIA", "IND": "INDIA", "GB": "UNITED KINGDOM", "GBR": "UNITED KINGDOM",
    "US": "UNITED STATES", "USA": "UNITED STATES", "RO": "ROMANIA", "ROU": "ROMANIA",
    "MD": "MOLDOVA", "MDA": "MOLDOVA", "RS": "SERBIA", "SRB": "SERBIA",
    "AL": "ALBANIA", "ALB": "ALBANIA", "LT": "LITHUANIA", "LTU": "LITHUANIA",
    "LV": "LATVIA", "LVA": "LATVIA", "PL": "POLAND", "POL": "POLAND",
    "HU": "HUNGARY", "HUN": "HUNGARY", "CZ": "CZECH", "CZE": "CZECH",
    "SK": "SLOVAKIA", "SVK": "SLOVAKIA", "BG": "BULGARIA", "BGR": "BULGARIA",
    "IL": "ISRAEL", "ISR": "ISRAEL", "EG": "EGYPT", "EGY": "EGYPT",
    "SA": "SAUDI ARABIA", "SAU": "SAUDI ARABIA", "AE": "UNITED ARAB EMIRATES",
    "ARE": "UNITED ARAB EMIRATES", "NG": "NIGERIA", "NGA": "NIGERIA",
    "CD": "CONGO", "COD": "CONGO", "CF": "CENTRAL AFRICAN", "CAF": "CENTRAL AFRICAN",
    "ML": "MALI", "MLI": "MALI", "NI": "NICARAGUA", "NIC": "NICARAGUA",
    "HT": "HAITI", "HTI": "HAITI", "GN": "GUINEA", "GIN": "GUINEA",
}


def country_verdict(query_country: str, rec: dict) -> tuple:
    """Whether the listing states the country given, as WORDS.

    This was `q in hay` — a naked substring test over the nationality, address
    and regime run together. "US" is inside "BELARUS" and inside "RUSSIAN
    FEDERATION", so `--nationality US` reported "country match" against 5,989
    designations, almost all of them Russian, and moved every one of them three
    points up the page. A country is compared as whole words now, and a two- or
    three-letter code is expanded before it is compared rather than being matched
    as a fragment of somebody else's country."""
    if not query_country:
        return "", 0.0
    # list(...) because the cache hands out frozen records whose fields are
    # tuples, and a tuple will not concatenate with a list.
    hay = normalise(" ".join(list(rec.get("nationality", ()))
                             + [rec.get("address", ""), rec.get("regime", "")]))
    q = normalise(query_country)
    if not hay or not q:
        return "", 0.0
    forms = {q}
    if len(q) in (2, 3) and q in _ISO:
        forms.add(normalise(_ISO[q]))

    def _names(value: str) -> bool:
        """Does this published value NAME the country asked for?

        Whole words alone said yes to SUDAN against a record whose only
        nationality is SOUTH SUDAN, because every word of the one occurs in the
        other. A country name is matched from its start: "IRAN" names "IRAN
        (ISLAMIC REPUBLIC OF)" and "RUSSIA" names "RUSSIAN FEDERATION", while
        "SUDAN" does not name "SOUTH SUDAN" — which is a different state, with a
        different regime, on the same lists."""
        vt = normalise(value).split()
        for form in forms:
            qt = form.split()
            if not qt or len(qt) > len(vt):
                continue
            if all(a == b for a, b in zip(qt[:-1], vt[:len(qt) - 1])) \
                    and vt[len(qt) - 1].startswith(qt[-1]):
                return True
        return False

    for value in list(rec.get("nationality", ())) + [rec.get("regime", "")]:
        if value and _names(value):
            return "country match", 3.0
    # An address is free text, so the country is looked for as a whole phrase
    # anywhere inside it rather than from the start.
    addr = normalise(rec.get("address", "") or "").split()
    for form in forms:
        qt = form.split()
        if qt and any(addr[i:i + len(qt)] == qt for i in range(len(addr) - len(qt) + 1)):
            return "country match", 3.0
    return "country not stated on listing", 0.0


# --------------------------------------------------------------------------
# the outcome — the only thing any renderer is allowed to read
# --------------------------------------------------------------------------

# How many character-for-character identities will be printed. Beyond this the
# count is reported and the names are not: see the bound in screen().
MAX_EXACT_SHOWN = 500


@dataclass
class Outcome:
    subject: dict
    threshold: float
    sources: list = field(default_factory=list)
    hits: list = field(default_factory=list)
    total_hits: int = 0
    type_withheld: int = 0
    exact_total: int = 0
    exact_withheld: int = 0
    error: str = ""
    delivery_error: str = ""

    @property
    def searched(self) -> list:
        return [s for s in self.sources if s["searched"]]

    @property
    def caveats(self) -> list:
        out = []
        forms = self.subject.get("romanisations") or []
        if forms:
            spelt = ", ".join(repr(f) for f in forms)
            out.append(f"The name contains Cyrillic letters. It was searched as "
                       f"published and under {len(forms)} romanisation"
                       f"{'s' if len(forms) > 1 else ''}: {spelt}. Publishers romanise "
                       "differently and none of these is authoritative: search the "
                       "passport spelling as well.")
        for s in self.searched:
            if s.get("name_comparison"):
                out.append(f"{s['title']}: the refresh that produced this cache did not "
                           f"fully verify that its published names survived — "
                           f"{s['name_comparison']}.")
        if self.type_withheld:
            out.append(f"Only {self.subject.get('type')} designations were compared. "
                       f"{self.type_withheld:,} designation(s) on the lists searched are of "
                       "another type and were NOT compared against this name. Screen with "
                       "--type any to reach them.")
        if self.exact_withheld:
            out.append(f"{self.exact_total:,} names on the lists are character-for-character "
                       f"this query, more than this tool will print; "
                       f"{self.exact_withheld:,} of them are NOT shown. Narrow the query or "
                       "raise --limit. This is a display bound, not a search bound: every one "
                       "of them was found and is counted in the total.")
        elif self.subject.get("native_no_translit"):
            out.append("The name was given in a script this tool cannot romanise. It was "
                       "compared only against names the publishers supply in that script. "
                       "A Romanised spelling MUST also be searched separately.")
        return out

    @property
    def incomplete_reasons(self) -> list:
        out = []
        if self.error:
            out.append(self.error)
        if self.delivery_error:
            # A screening record that was not written is not a screening record.
            # Reporting the search as clean and then failing to file it leaves a
            # clean result on screen and nothing on the file.
            out.append(self.delivery_error)
        for s in self.sources:
            if not s["searched"]:
                out.append(f"{s['title']}: {s['reason']}")
            elif s["stale"]:
                out.append(f"{s['title']}: last retrieved {s['age_hours']}h ago")
        if not self.sources:
            out.append("no list was requested")
        return out

    @property
    def complete(self) -> bool:
        """A search is complete only if the request was valid and every list
        asked for was read in full and is fresh. Nothing else may set this."""
        return not self.incomplete_reasons

    @property
    def exit_code(self) -> int:
        if self.error:
            return EXIT_USAGE
        if not self.complete:
            return EXIT_INCOMPLETE
        return EXIT_CANDIDATES if self.hits else EXIT_CLEAN


def validate_max_age(args) -> str:
    """The freshness window, checked once and used everywhere.

    `status` had its own copy of the comparison and none of the validation, so
    `status --max-age-hours nan` reported a list years out of date as `ok` and
    exited 0 while `check` refused the same argument. One decision, one place."""
    max_age = getattr(args, "max_age_hours", 24.0)
    if max_age is None or not math.isfinite(max_age) or max_age <= 0:
        return (f"--max-age-hours {max_age!r} is not a usable window: it must be a "
                "finite number of hours above zero. NaN and infinity compare false "
                "against every age, which would report a list years out of date as "
                "freshly retrieved.")
    return ""


def is_stale(age, max_age) -> bool:
    """A list is stale if it is older than the window, if its age is unknown, or
    if it claims to have been retrieved in the future."""
    return age is None or age > max_age or age < -CLOCK_SKEW_HOURS


def validate_args(args) -> str:
    """The parts of a request that do not depend on the subject.

    Batch checks these once, before any row. Checked per row only, a bad
    --threshold refused every row; and with every row blank there was no row
    to refuse, so the run exited 3 — an incomplete search — for what was a
    bad request from the start."""
    threshold = getattr(args, "threshold", DEFAULT_THRESHOLD)
    if threshold is None or not math.isfinite(threshold) or not (0 < threshold <= 100):
        return (f"--threshold {threshold!r} is not a usable score: it must be a number "
                "above 0 and at most 100. A threshold of NaN compares false against "
                "every candidate and would report a designated person as clear.")
    bad_age = validate_max_age(args)
    if bad_age:
        return bad_age
    limit = getattr(args, "limit", 40)
    if limit is not None and limit < 1:
        return (f"--limit {limit} would discard every candidate found. Use a positive "
                "limit; the record always states how many candidates there were.")
    return ""


def validate_request(name: str, args) -> str:
    """Return an error string, or "" if the request can be screened at all."""
    bad = validate_args(args)
    if bad:
        return bad
    kind = (getattr(args, "type", "individual") or "").strip().lower()
    if kind not in TYPES:
        return f"--type {kind!r} is not one of {', '.join(TYPES)}"
    args.type = kind
    if not (name or "").strip():
        return "no name was given to screen"
    if not M.tokens(name) and not M.native_key(name):
        return (f"{name!r} contains nothing searchable once punctuation is removed. "
                "Give a name in Latin script or in the script the lists publish.")
    # A script this tool cannot romanise is refused before anything is searched.
    # It used to be screened against native aliases alone and the shortfall
    # carried as a footnote, while the run still reported itself complete and
    # exited 0. That is the shape of a false negative: OFAC's SDN file carries no
    # non-Latin name at all (0 of 19,321), so a query that never reaches Latin
    # cannot match there however it is scored, and a nil return from it means
    # nothing. Better to say so and ask for the passport spelling.
    # ...but only where the spelling does not ALREADY reach Latin. The check
    # asked whether every letter could be romanised, and a modifier letter
    # cannot: U+02BE, the half ring in "al-ʾAsad", is category Lm and has no
    # Latin name. So the UK's and OFSI's own published spelling of
    # "Baššār Ḥāfiẓ al-ʾAsad" — which normalises to BASSAR HAFIZ AL ASAD, the
    # exact string in the index — was refused at exit 4, under a message telling
    # the user a designation could not be found if one existed. It exists, and
    # the tool holds it. A name that yields a searchable Latin form is searched;
    # the refusal is for names that reach no Latin at all.
    unmappable = M.unmappable_letters(name)
    if unmappable and not M.is_native(name) and M.normalise(name):
        unmappable = ""
    if unmappable:
        scripts = ", ".join(M.script_names(unmappable))
        return (f"{name!r} contains {scripts} letters, which this tool cannot render "
                "into Latin (it romanises Cyrillic only). The lists publish "
                "overwhelmingly in Latin script — OFAC's SDN file, the largest, "
                "carries no non-Latin name at all — so a search on this spelling "
                "could not find a designation even if one exists. Screen the "
                "passport or publisher spelling in Latin script instead. Nothing "
                "was searched.")
    return ""


# --------------------------------------------------------------------------
# the index
# --------------------------------------------------------------------------

_INDEX: dict = {}


def _index(source_id: str, records: list) -> tuple:
    """Normalise, tokenise and bigram-mask every designation once per process.

    Names are tokenised BOTH as an individual and as an entity, because a query
    of --type any cannot know in advance which it is comparing against: tokenised
    one way only, "LLC Synesis" missed its own exact listing.

    Native-script names are indexed too. They are published, and a client whose
    passport is in Cyrillic must be findable."""
    cached = _INDEX.get(source_id)
    if cached is not None and cached[0] is records:
        return cached[1]
    idx = []
    for rec in records:
        names, native, mask = [], [], 0
        seen_norm, seen_key = set(), set()
        # EVERY published spelling, whatever field the parser filed it in.
        # The field was deciding which index a name entered, and so which
        # queries could ever reach it. Both directions failed. A native-script
        # name filed under `aliases` normalises to nothing and entered neither
        # index — OFSI publishes the Arabic alias of SOURUH COMPANY that way.
        # And a LATIN name filed under `nonlatin` went only to the native
        # index, which a Latin query never opens: OFSI files the Azerbaijani
        # spelling of Ali Akbar Salehi, "Əli Əkbər Salehi", there because of
        # the schwa, and that exact published spelling returned nothing,
        # complete, exit 0, against a list holding him. Script decides the
        # representation now. The field decides nothing.
        for cand in ([rec.get("name", "")] + list(rec.get("aliases", []))
                     + list(rec.get("nonlatin", []))):
            if not cand:
                continue
            # Latin — unless the spelling is written mostly outside Latin, in
            # which case homoglyph folding leaves partial nonsense
            # ("Александр Петров" -> "A EKCA P ETPOB") which is not empty and
            # has no business being searched as though it were a name.
            if not M.is_native(cand):
                n = M.normalise(cand)
                if n and n not in seen_norm:
                    seen_norm.add(n)
                    names.append((cand, n,
                                  tuple(M.tokens_from_normalised(n, "individual")),
                                  tuple(M.tokens_from_normalised(n, "entity"))))
                    mask |= M.bigram_mask(n)
            # Native AS WELL AS Latin, never instead of it. A spelling carrying
            # any letter outside A-Z stays reachable in the script it is
            # published in; one carrying none is not given a key it could never
            # be found by.
            if M.has_native_letters(cand):
                key = M.native_key(cand)
                if key and key not in seen_key:
                    seen_key.add(key)
                    native.append((cand, key))
        if names or native:
            idx.append((rec, tuple(names), mask, tuple(native)))
    # Handed out as a tuple of tuples of tuples. The source records were frozen
    # and the index built from them was a plain list: clearing that list left
    # the source "searched" in full and an exact vessel query with no hits,
    # complete, exit 0 — the AN SAN 1 failure again, one layer down.
    frozen = tuple(idx)
    _INDEX[source_id] = (records, frozen)
    return frozen


# --------------------------------------------------------------------------
# screening
# --------------------------------------------------------------------------

def age_hours(entry: dict):
    ts = entry.get("fetched_at")
    if not ts:
        return None
    return (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() / 3600


def screen(name: str, args, srcs: list, meta: dict | None = None,
           prefilter: bool = True) -> Outcome:
    """Screen one subject and return the Outcome. This is the only place a
    search result is produced, and the only place the sources are marked
    searched."""
    meta = meta if meta is not None else S.load_meta()
    subject = {"name": name, "dob": getattr(args, "dob", ""),
               "nationality": getattr(args, "nationality", ""),
               "type": getattr(args, "type", "any"),
               "client": getattr(args, "client", ""), "matter": getattr(args, "matter", "")}
    outcome = Outcome(subject=subject, threshold=getattr(args, "threshold", DEFAULT_THRESHOLD))

    err = validate_request(name, args)
    if err:
        outcome.error = err
        outcome.sources = [_prov_row(s, meta, args, searched=False,
                                     reason="not searched: the request was refused")
                           for s in srcs]
        return outcome

    kind = args.type
    qnorm = M.normalise(name)
    q_individual = M.tokens_from_normalised(qnorm, "individual")
    q_entity = M.tokens_from_normalised(qnorm, "entity")
    qmask = M.bigram_mask(qnorm)
    need = M.prefilter_threshold(qmask)
    q_native = M.native_key(name) if M.is_native(name) else ""
    # A query with Cyrillic in it is also romanised and screened against the
    # Latin names, because a client whose passport reads КАДЫРОВ must still find
    # a listing spelled KADYROV — and under every romanisation system this tool
    # knows, not one. Publishers disagree, and picking a single spelling is how
    # OFAC's "FEDOROV, Yury Viktorovich" was missed at 87.8 against a threshold
    # of 88. ANY Cyrillic letter triggers this, not a Cyrillic majority: "Yury
    # Viktorovich Федоров" is Latin by count, was never romanised, and returned
    # a clean nil against a fresh OFAC list while "Yury Viktorovich Fedorov"
    # found him. A script that cannot be romanised at all never reaches here:
    # it is refused by validate_request before anything is searched.
    translits = M.transliterate_variants(name) if M.has_romanisable(name) else []
    queries = [(q_individual, q_entity, qmask, need)]
    # Every spelling of the query as a normalised string. A candidate whose own
    # normalised name is in this set IS the query, and is scored 100 without
    # passing through the caps that are there to restrain similarity judgments.
    # The identity/reachability split applies whether or not this tool happens to
    # romanise the script. It was written inside the romanisation branch, which
    # only Cyrillic reaches, so a GREEK query — "ΑΒΓ" folding to "ABG" — took the
    # default above and was reported exact: true, while the identical Cyrillic
    # case correctly reported false. A fold across scripts is a fold across
    # scripts; which alphabet it came from does not change what it proves.
    _latin_query = bool(qnorm) and not M.is_native(name)
    q_exact = {qnorm} if _latin_query else set()
    q_reach: set = set() if _latin_query else ({qnorm} if qnorm else set())
    if translits:
        # The romanisations are ADDED to the query, not put in place of it.
        # Replacing it outright threw away the one form that reaches a
        # published Latin name written with a Cyrillic homoglyph: the EU
        # publishes the alias "JSС Krasmash" — the final "С" is Cyrillic
        # U+0421 — which folds to "JSC KRASMASH" and is its own listing, until
        # this branch discarded that form and searched the romanised "JSS
        # KRASMASH" instead, and the exact published alias returned nothing,
        # complete, exit 0. The original survives only where it is genuine
        # Latin text: where the name is written mostly outside Latin, homoglyph
        # folding leaves nonsense ("Кадыров" -> "KA POB") and that nonsense
        # must not be screened as a name.
        # Two different questions, and they had one answer. Whether the folded
        # original may be SEARCHED as a name, and whether it may be recognised
        # as one. Homoglyph residue must not generate fuzzy candidates — but it
        # can still literally be a published spelling, and refusing to know that
        # lost the mirror image of the Krasmash defect: a listing published as
        # "CCC AB", queried with three Cyrillic homoglyphs, folds to exactly
        # "CCC AB", was romanised to "SSS AB", and returned nothing. The exact
        # key is kept whenever it is non-empty; only the fuzzy query form is
        # withheld from a native-dominant name.
        # THIRD question, which the second answer swallowed. Whether the
        # folded original may be SEARCHED, whether it may be RECOGNISED, and
        # whether recognising it makes it the NAME. It does not. "ТАЕК РАК" is
        # seven Cyrillic letters; it folds to "TAEK PAK", which is a published
        # UK alias, and screening it is right — that is how a name typed in
        # homoglyphs to evade a list gets caught. But the query is not that
        # designation's name, and reporting exact:true said it was. Identity
        # sorts ahead of every approximation and escapes --limit; a visual
        # confusable must not inherit either. So the fold is kept as a
        # REACHABILITY key: it forces the candidate into consideration at 100,
        # and it is reported as the approximation it is.
        keep = bool(qnorm) and not M.is_native(name)
        queries = [(q_individual, q_entity, qmask, need)] if keep else []
        q_exact = {qnorm} if keep else set()
        q_reach = set() if keep else ({qnorm} if qnorm else set())
        seen_forms = {qnorm} if keep else set()
        for form in translits:
            tnorm = M.normalise(form)
            if tnorm in seen_forms:      # several systems collapse once normalised
                continue
            seen_forms.add(tnorm)
            q_exact.add(tnorm)
            m = M.bigram_mask(tnorm)
            queries.append((M.tokens_from_normalised(tnorm, "individual"),
                            M.tokens_from_normalised(tnorm, "entity"),
                            m, M.prefilter_threshold(m)))
        # Each romanisation keeps its OWN prefilter. The union admits so much
        # that the filter stops filtering — screening one Cyrillic name across
        # every list went from 0.7s to 21s. The union survives only as a cheap
        # first gate: a record no romanisation shares bigrams with is skipped
        # before any of them is tried.
        if not queries:      # every romanisation normalised away: search as given
            queries = [(q_individual, q_entity, qmask, need)]
            q_exact = {qnorm} if (qnorm and keep) else set()
            q_reach = {qnorm} if (qnorm and not keep) else set()
        qmask = 0
        for _, _, m, _ in queries:
            qmask |= m
        need = min(q[3] for q in queries)
        outcome.subject["also_searched_as"] = translits[0]
        outcome.subject["romanisations"] = translits

    hits = []
    for src in srcs:
        entry = meta.get(src.id, {})
        if not entry.get("ok"):
            outcome.sources.append(_prov_row(src, meta, args, searched=False,
                                             reason=entry.get("error") or "never fetched"))
            continue
        try:
            records = S.read_source(src.id, entry)
        except S.CacheError as exc:
            outcome.sources.append(_prov_row(src, meta, args, searched=False, reason=str(exc)))
            continue
        row = _prov_row(src, meta, args, searched=True, records=len(records))
        outcome.sources.append(row)
        try:
            indexed = _index(src.id, records)
        except Exception as exc:   # an unusable list is not a searched list
            row["searched"], row["records"] = False, 0
            row["reason"] = f"could not be indexed ({type(exc).__name__}: {exc})"
            continue
        try:
            _scan(indexed, outcome, hits, src, kind, args, q_native, queries,
                  qmask, need, prefilter, q_exact, q_reach)
        except Exception as exc:   # nothing half-scanned is reported as searched
            row["searched"], row["records"] = False, 0
            row["reason"] = f"could not be searched ({type(exc).__name__}: {exc})"
            hits[:] = [h for h in hits if h["record"]["source"] != src.id]
    # Exact identity sorts ahead of everything, because a fuzzy score can tie
    # it at 100 and the tiebreak was then alphabetical on the record's primary
    # name. "Abdul" is UN 113444's own published alias; 173 records scored 100
    # by fuzzy containment, the designation whose name IS the query sat at
    # position 164, and at the operational --limit 40 it was not returned at
    # all — a published name losing its own search to a hundred approximations
    # of it.
    # SELECTION is by the NAME, and by NOTHING ELSE that biography can touch.
    # Rank survived here as a tie-break, and at equal name scores a tie-break is
    # a selection: 34 of the 40 candidates shown for "Abdul" changed on supplying
    # a date of birth, every one of them scoring 100.0. The tie-break is now the
    # source and the uid, which no fact about the subject can move.
    # ORDERING is by rank. Selection and ordering were the same
    # operation, and with a limit that made biographical detail suppressive: a
    # conflicting date of birth costs six rank points, so a designation scoring
    # 95.5 on its name sorted below one scoring 89.8 whose listing publishes no
    # date at all, and at --limit 40 it left the page. Twenty-two of the forty
    # shown for "Mohammed Ali" changed that way on supplying a date. Two
    # screening records for the same subject on the same day, under identical
    # headline text, one naming a designation five times and the other not at
    # all. README.md says a date of birth never suppresses a candidate; this is
    # what makes that true.
    hits.sort(key=lambda h: (not h["exact"], -h["score"],
                             h["record"].get("source", ""), str(h["record"].get("uid", ""))))
    outcome.total_hits = len(hits)
    # --limit bounds how many APPROXIMATIONS are shown. It may not cut a name
    # that is the query: sorting exact first makes that true for every list
    # published today — the largest same-key collision on any of them is 28 —
    # but "today" is not a guarantee, and the claim being made here is
    # absolute. Every exact identity is returned however many there are.
    limit = getattr(args, "limit", 40)
    n_exact = sum(1 for h in hits if h["exact"])
    # ...but "however many there are" is not a promise a printer can keep. A
    # query that is exact against thousands — and a two-thousand-record
    # collision produced 1.4 MB of JSON — turns the safety property into a
    # denial of service on the reader. The cohort is bounded, generously, and
    # the bound SAYS SO on every route: a withheld identity that announces
    # itself is a display limit, and a withheld identity that does not is the
    # defect this promise exists to prevent.
    shown = max(limit, min(n_exact, MAX_EXACT_SHOWN))
    outcome.exact_total = n_exact
    outcome.exact_withheld = max(0, n_exact - shown)
    kept = hits[:shown]
    # ...and now rank orders what survived, which is what it is for.
    kept.sort(key=lambda h: (not h["exact"], -h["rank"], -h["score"],
                             h["record"].get("name", "")))
    outcome.hits = kept
    return outcome


def _scan(indexed, outcome, hits, src, kind, args, q_native, queries,
          qmask, need, prefilter, q_exact=frozenset(), q_reach=frozenset()) -> None:
    subject = outcome.subject
    for rec, names, rmask, native in indexed:
            if rec.get("status") == "delisted" and not getattr(args, "include_delisted", False):
                continue
            rtype = rec.get("type") or "individual"
            if kind != "any" and rtype not in (kind, "unknown"):
                # Counted, because it was not compared. The default was
                # `individual`, which withholds 46.3% of the corpus — every
                # entity, vessel and aircraft — while the text said "6 of 6
                # (38,524 designations)" and the record said Complete. A nil
                # return that covered half the designations is the shape of
                # defect this whole tool exists to avoid. The default is `any`
                # now, and a narrowing the user asks for says what it cost.
                outcome.type_withheld += 1
                continue
            best_s, best_n, best_exact = 0.0, "", False
            if q_native:
                for cand, key in native:
                    sc = M.native_score(q_native, key)
                    if sc > best_s:
                        # A name published in its own script that IS the query
                        # is an identity exactly as a Latin one is. Only the
                        # Latin branch said so, so UN 2960872's own spelling
                        # "Умаров Доку Хаматович" scored 100 and reported
                        # exact:false — ranked among approximations, and cut by
                        # --limit in a large enough collision.
                        best_s, best_n, best_exact = sc, cand, (key == q_native)
            # An exact published name is checked before the prefilter, because a
            # name that reduces to initials shares few bigrams with anything and
            # has no business being filtered out of its own search.
            if q_exact:
                for cand, c_norm, _, _ in names:
                    if c_norm in q_exact:
                        # Not merely a score of 100: this candidate's own
                        # normalised name IS the query. A fuzzy 100 is a
                        # judgment; this is an identity.
                        best_s, best_n, best_exact = 100.0, cand, True
                        break
            if best_s < 100 and q_reach:
                for cand, c_norm, _, _ in names:
                    if c_norm in q_reach:
                        # The query folded to this published name across
                        # scripts. That is worth surfacing at the top of the
                        # approximations — a name written in homoglyphs to slip
                        # past a list is exactly what this catches — but the
                        # query as typed is not this designation's name, and
                        # `exact` is a claim about what the record says, not
                        # about how hard the match was to find.
                        best_s, best_n, best_exact = 100.0, cand, False
                        break
            if best_s < 100 and queries and not (
                    prefilter and qmask and not M.passes(qmask, rmask, need)):
                as_entity = rtype in ("entity", "vessel", "aircraft")
                live = [(q_ent if as_entity else q_ind) for q_ind, q_ent, qm, qn in queries
                        if (q_ent if as_entity else q_ind)
                        and not (prefilter and qm and not M.passes(qm, rmask, qn))]
                for cand, c_norm, c_ind, c_ent in names:
                    ct = c_ent if as_entity else c_ind
                    for qt in live:
                        sc = M.score_tokens(qt, ct)
                        if sc > best_s:
                            best_s, best_n, best_exact = sc, cand, False
                    if best_s >= 100:
                        break
            # The threshold applies to the NAME. Biographical detail annotates
            # and orders; it never removes a candidate.
            if best_s < outcome.threshold:
                continue
            flags, rank = [], best_s
            d_note, d_adj = dob_verdict(subject["dob"], rec.get("dob", []))
            if d_note:
                flags.append(d_note)
                rank += d_adj
            c_note, c_adj = country_verdict(subject["nationality"], rec)
            if c_note:
                flags.append(c_note)
                rank += c_adj
            # Counted against the first query form, which is the name as given
            # for a Latin query and the primary romanisation for a Cyrillic one.
            n_query = len(queries[0][0]) if queries else 0   # (tokens, _, mask, need)
            if n_query > len(M.tokens(best_n)):
                flags.append("query has names the listing does not")
            elif len(M.tokens(best_n)) > n_query + 1:
                flags.append("listing has names the query does not")
            hits.append({"score": round(best_s, 1), "rank": round(min(100.0, rank), 1),
                         "exact": best_exact,
                         "matched_name": best_n, "flags": flags, "record": rec,
                         "source_title": src.title, "authority": src.authority})


def _prov_row(src, meta: dict, args, searched: bool, reason: str = "", records: int = 0) -> dict:
    entry = meta.get(src.id, {})
    age = age_hours(entry)
    max_age = getattr(args, "max_age_hours", 24.0)
    return {"id": src.id, "title": src.title, "authority": src.authority,
            "searched": searched, "reason": reason,
            "records": records if searched else 0,
            "list_date": entry.get("list_date", ""),
            "list_date_source": entry.get("list_date_source", "unknown"),
            "fetched_at": entry.get("fetched_at", ""),
            "age_hours": None if age is None else round(age, 1),
            "stale": searched and is_stale(age, max_age),
            # What the last refresh of this list did NOT check. Both of these
            # were written onto the manifest and read by nothing — not by
            # screen.py, not by SKILL.md, not by README.md — so a result
            # produced against a list whose refresh skipped the published-name
            # comparison, or was authorised to drop names, looked identical to
            # one that passed it. Provenance the reader cannot see is not
            # provenance.
            "name_comparison": (entry.get("alias_baseline")
                                or ("authorised to drop published names "
                                    "(SANCTIONS_ALLOW_ALIAS_REMOVAL)"
                                    if entry.get("alias_removal_override") else "")),
            "url": src.url, "licence": src.licence}


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

MD_UNSAFE = re.compile(r"([\\`*_\[\]<>|#])")


def md(value) -> str:
    """Escape publisher and user data before it is placed in Markdown.

    Names, aliases, statements of reasons and the client's own matter text are
    all third-party strings. Unescaped, a batch field can close the document's
    structure and forge a signed decision block, or pull a remote image."""
    s = "" if value is None else str(value)
    s = s.replace("\r", " ").replace("\n", " ")
    return MD_UNSAFE.sub(r"\\\1", s)


def term(value) -> str:
    """Make third-party text safe for the terminal.

    The terminal is an output format like Markdown, and publisher data reaches
    it through fmt_hit, the batch table and the refresh and status lines. An
    ANSI sequence inside a name recolours the line or rewrites it after it was
    printed; a carriage return overwrites it; a bidi override reverses it; a
    newline forges a line of this program's own output ("No candidate at or
    above 88."). md() covered the record and nothing covered stdout. Strip the
    control bytes, then fold every run of whitespace — including U+2028, which
    a Canadian designation really carries — to one space, so a value stays on
    the line it was printed on. JSON is left to its encoder: C0 bytes are
    escaped by specification, and the rest is read by programs, not people."""
    s = M.strip_control("" if value is None else str(value))
    return " ".join(s.split())


_JSON_UNSAFE = re.compile("[\x7f-\x9f\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def json_safe(s: str) -> str:
    r"""JSON escapes C0 by specification and nothing else. C1 bytes and bidi
    format controls are legal inside a JSON string and are still display
    controls when the output is catted, logged or piped through jq. Escape
    them as \uXXXX, which every parser reads back to the same character: the
    published bytes reach a program intact and never reach a terminal raw."""
    return _JSON_UNSAFE.sub(lambda m: "\\u%04x" % ord(m.group()), s)


class RequestError(Exception):
    """The request cannot be turned into a search at all."""


def enabled_sources(args) -> list:
    """Resolve --source. Raises RequestError rather than calling sys.exit, so
    that every exit from this program still goes through the gate, and
    de-duplicates so a list named twice is not searched — and counted — twice."""
    if getattr(args, "source", None):
        ids, seen = [], set()
        for spec in args.source:
            for i in spec.split(","):
                i = i.strip()
                if i and i not in seen:
                    seen.add(i)
                    ids.append(i)
        missing = [i for i in ids if i not in S.BY_ID]
        if missing:
            raise RequestError(f"unknown source(s): {', '.join(missing)}. "
                               f"Known: {', '.join(sorted(S.BY_ID))}")
        if not ids:
            raise RequestError("--source was given but named no list")
        return [S.BY_ID[i] for i in ids]
    return [s for s in S.SOURCES if s.default]


def fmt_hit(h: dict, verbose: bool) -> str:
    # Every field here is the publisher's text, passed through term() where it
    # is placed. The assembled block goes through strip_control once more at
    # the door of render_text, so a field added later without term() still
    # cannot carry an escape to the screen — only, at worst, a line break.
    r = h["record"]
    lines = [f"  {h['score']:5.1f}  {term(r['name'])[:52]:<52} "
             f"{term(r.get('type', ''))[:10]:<10} {term(r['source'])}",
             f"         matched on: {term(h['matched_name'])}"]
    if r.get("status") == "delisted":
        # Returned only under --include-delisted, and then it looked like any
        # other candidate: the Swiss list carries 1,559 de-listed targets.
        lines.insert(1, "         DE-LISTED — the publisher records this designation as no "
                        "longer in force"
                        + (f" (de-listed {term(r['delisted_on'])})" if r.get("delisted_on") else "")
                        + "; shown because --include-delisted was given")
    bits = []
    if r.get("dob"):
        bits.append("DOB " + "; ".join(term(d) for d in r["dob"][:3]))
    if r.get("nationality"):
        bits.append("nat " + "; ".join(term(n) for n in r["nationality"][:3]))
    if r.get("regime"):
        bits.append("regime: " + term(r["regime"])[:60])
    if r.get("measures"):
        bits.append(term(r["measures"]).replace("|", "; ")[:70])
    if r.get("ref"):
        bits.append("ref " + term(r["ref"]))
    if bits:
        lines.append("         " + " | ".join(bits))
    if h["flags"]:
        lines.append("         flags: " + "; ".join(term(f) for f in h["flags"]))
    if verbose and r.get("notes"):
        lines.append("         " + term(r["notes"])[:300])
    return "\n".join(lines)


def render_text(o: Outcome, verbose: bool = False) -> str:
    L = [""]
    s = o.subject
    L.append(f"Screened: {term(s['name'])}"
             + (f"  |  DOB {term(s['dob'])}" if s["dob"] else "")
             + (f"  |  {term(s['nationality'])}" if s["nationality"] else "")
             + f"  |  type {term(s['type'])}  |  threshold {o.threshold}")
    L.append("")
    if o.error:
        L.append(f"REFUSED: {term(o.error)}")
        L.append("Nothing was screened.")
        return M.strip_control("\n".join(L))
    L.append(f"Lists searched: {len(o.searched)} of {len(o.sources)} "
             f"({sum(p['records'] for p in o.searched):,} designations)")
    for p in o.sources:
        if not p["searched"]:
            L.append(f"  x NOT SEARCHED — {p['title']}: {p['reason']}")
        elif p["stale"]:
            L.append(f"  ! STALE — {p['title']}: retrieved {p['age_hours']}h ago")
    L.append("")
    for c in o.caveats:
        L.append(f"  NOTE: {c}")
    if o.caveats:
        L.append("")
    if not o.complete and not o.hits:
        L.append("THIS SEARCH IS NOT COMPLETE, so it says nothing about the subject:")
        for r in o.incomplete_reasons:
            L.append(f"  - {r}")
        L.append("Refresh the lists and screen again.")
    elif not o.hits:
        L.append(f"No candidate at or above {o.threshold}.")
        L.append("A nil return covers only the lists marked searched, the name as "
                 "spelled, and the list dates shown above.")
    else:
        more = (f" (showing the top {len(o.hits)} of {o.total_hits} by score)"
                if o.total_hits > len(o.hits) else "")
        L.append(f"{len(o.hits)} candidate(s){more}:")
        L.append("")
        for h in o.hits:
            L.append(fmt_hit(h, verbose))
            L.append("")
        if not o.complete:
            L.append("WARNING: these candidates come from an INCOMPLETE search — "
                     + "; ".join(o.incomplete_reasons))
        L.append("Candidates require human comparison. The tool does not clear or "
                 "confirm anyone.")
    # The door. Every line above is either this program's own words or text that
    # went through term(); this pass is what makes that true of lines added
    # later, and of the caveats and reasons that quote the subject or a path.
    return M.strip_control("\n".join(L))


def _jsonable(x):
    """json.dumps writes bare NaN and Infinity, which no strict parser accepts,
    and does not know the read-only mappings the cache hands out."""
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, MappingProxyType):
        return dict(x)
    raise TypeError(repr(x))


def render_json(o: Outcome) -> str:
    threshold = o.threshold if isinstance(o.threshold, (int, float)) and \
        math.isfinite(o.threshold) else None
    return json_safe(json.dumps({
        "subject": o.subject, "threshold": threshold,
        "complete": o.complete, "incomplete_reasons": o.incomplete_reasons,
        "searched_source_ids": [p["id"] for p in o.searched],
        "error": o.error, "caveats": o.caveats, "total_hits": o.total_hits,
        "hits": o.hits, "sources": o.sources, "exit_code": o.exit_code,
    }, ensure_ascii=False, indent=2, allow_nan=False, default=_jsonable))


DISCLOSED_LIMITS = [
    "Name-and-date matching against published lists only. It does not establish "
    "identity: a match is a candidate for human comparison, not a finding.",
    "Ownership and control are NOT screened. An entity that is not itself listed "
    "may still be caught because a designated person owns or controls it; that "
    "has to be worked out from the ownership structure.",
    "Sectoral, trade, transport and financial-services restrictions attach to "
    "conduct rather than to a named person, and no name search will surface them.",
    "PEP status is only searched when an OpenSanctions PEP dataset is enabled, "
    "and adverse media is not searched at all.",
    "A list is only as current as the retrieval recorded above, and only as good "
    "as the spelling searched. Transliterated names should be searched in more "
    "than one spelling.",
]


def write_report(path: Path, o: Outcome) -> None:
    now = datetime.now(timezone.utc).astimezone()
    s = o.subject
    L = [f"# Sanctions screening record — {md(s['name'])}", ""]
    L.append(f"**Screened** {now.strftime('%d %B %Y at %H:%M %Z')}  ")
    L.append(f"**Subject type** {md(s['type'])}  ")
    if s.get("dob"):
        L.append(f"**Date of birth given** {md(s['dob'])}  ")
    if s.get("nationality"):
        L.append(f"**Nationality / country given** {md(s['nationality'])}  ")
    if s.get("matter"):
        L.append(f"**Matter** {md(s['matter'])}  ")
    if s.get("client"):
        L.append(f"**Client / file reference** {md(s['client'])}  ")
    L.append(f"**Match threshold** {o.threshold} of 100  ")
    L.append(f"**Screened by** {md(os.environ.get('SANCTIONS_SCREENED_BY', '(complete on signing)'))}")
    L.append("")

    L.append("## 1. Search status")
    L.append("")
    if o.complete:
        L.append("**Complete.** Every list requested was read in full and is current.")
    else:
        L.append("**INCOMPLETE — this record is not evidence that the subject is absent "
                 "from any list.** The search did not run as requested:")
        L.append("")
        for r in o.incomplete_reasons:
            L.append(f"- {md(r)}")
    L.append("")

    # What produced this record. §45 put the engine generation and the module
    # digests on the manifest so a result could be tied to its code after the
    # fact — and then the durable output, which is the thing anyone reads a year
    # later, carried neither. A build identifier the reader never sees is a
    # build identifier that answers nobody's question.
    L.append("## 2. What produced this record")
    L.append("")
    L.append(f"- Engine generation **{S.ENGINE_VERSION}**, parser version "
             f"{S.PARSER_VERSION}")
    for _mod, _dig in sorted(dict(S.code_fingerprint()).items()):
        L.append(f"- `{_mod}` `{_dig}`")
    L.append("")

    L.append("## 3. Lists searched")
    L.append("")
    L.append("| List | Authority | List date | Retrieved | Designations | Status |")
    L.append("|---|---|---|---|---|---|")
    for p in o.sources:
        if not p["searched"]:
            status = "**NOT SEARCHED**"
        elif p["stale"]:
            status = "STALE"
        else:
            status = "searched"
        listed = md(p["list_date"]) if p["list_date"] else f"_{md(p['list_date_source'])}_"
        L.append(f"| {md(p['title'])} | {md(p['authority'])} | {listed} | "
                 f"{md((p['fetched_at'] or '—')[:16].replace('T', ' '))} | "
                 f"{p['records']:,} | {status} |")
    L.append("")

    L.append("## 4. Result")
    L.append("")
    if o.error:
        L.append(f"**Refused.** {md(o.error)} Nothing was screened.")
    elif not o.hits and not o.complete:
        L.append("**Nothing can be concluded.** The search was incomplete, so this record "
                 "is evidence that the check did not run — not that the subject is absent "
                 "from any list.")
    elif not o.hits:
        L.append(f"**No candidate at or above {o.threshold}** on the lists recorded as "
                 "searched above, for the name and spelling as searched.")
    else:
        more = (f" {o.total_hits} candidates met the threshold; the top {len(o.hits)} are "
                "set out below, so this record is not a complete list of candidates."
                if o.total_hits > len(o.hits) else "")
        L.append(f"**{len(o.hits)} candidate match{'es' if len(o.hits) != 1 else ''}** at or "
                 f"above {o.threshold}. Each requires human comparison against what is known "
                 f"of the subject before it is either adopted or discounted.{more}")
        L.append("")
        for i, h in enumerate(o.hits, 1):
            r = h["record"]
            L.append(f"### {i}. {md(r['name'])} — score {h['score']}")
            L.append("")
            L.append(f"- **List** {md(h['source_title'])} ({md(h['authority'])})")
            L.append(f"- **Matched on** {md(h['matched_name'])}")
            if r.get("status") == "delisted":
                L.append("- **DE-LISTED** — the publisher records this designation as no "
                         "longer in force"
                         + (f", de-listed {md(r['delisted_on'])}" if r.get("delisted_on") else "")
                         + ". It appears only because `--include-delisted` was given and "
                         "is not a current designation.")
            for label, key in (("Type", "type"), ("Regime / programme", "regime"),
                               ("Measures", "measures"), ("Designated", "listed_on"),
                               ("De-listed on", "delisted_on"),
                               ("Address", "address"), ("Reference", "ref")):
                if r.get(key):
                    L.append(f"- **{label}** {md(str(r[key]).replace('|', '; '))}")
            for label, key in (("Date(s) of birth on the listing", "dob"),
                               ("Nationality", "nationality"), ("Identifiers", "ids"),
                               ("Non-Latin script names", "nonlatin")):
                if r.get(key):
                    L.append(f"- **{label}** {md('; '.join(r[key][:6]))}")
            if h["flags"]:
                L.append(f"- **Flags** {md('; '.join(h['flags']))}")
            if r.get("notes"):
                L.append(f"- **Statement of reasons / notes** {md(r['notes'])}")
            L.append("")

    if o.caveats:
        L.append("### Caveats on this search")
        L.append("")
        for c in o.caveats:
            L.append(f"- {md(c)}")
        L.append("")
    L.append("## 5. What this check does not cover")
    L.append("")
    for lim in DISCLOSED_LIMITS:
        L.append(f"- {lim}")
    L.append("")
    L.append("## 6. Decision")
    L.append("")
    L.append("*To be completed by the fee earner. The search above is evidence; the "
             "decision is not made by the tool.*")
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    L.append("| Candidates adopted as the subject | |")
    L.append("| Candidates discounted, and why | |")
    L.append("| Decision | proceed / proceed with EDD / do not proceed / licence needed |")
    L.append("| Report to OFSI considered | yes / no — reason |")
    L.append("| Suspicion of money laundering considered (POCA 2002 Part 7) | yes / no — reason |")
    L.append("| Signed | |")
    L.append("| Date | |")
    L.append("")
    L.append("---")
    L.append("")
    L.append("Produced by the `sanctions-screening` skill from official published lists. "
             "Where the Money Laundering Regulations 2017 apply to the retainer, reg "
             "40(2)(a) requires the customer due diligence material to be kept and reg "
             "40(3) sets five years from the end of the business relationship.")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Written through a temporary file in the same directory and moved into
    # place, so an interrupted write cannot leave a half-record that reads as a
    # whole one. x-mode on the final name: an existing record is never replaced.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(L))
            fh.flush()
            os.fsync(fh.fileno())
        with open(path, "x", encoding="utf-8"):   # claims the name, or raises
            pass
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def slug(s: str) -> str:
    base = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")[:60]
    # A name that is entirely non-Latin slugs to nothing, and two subjects can
    # share a slug. A digest of the original keeps records from overwriting.
    digest = hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}" if base else f"subject-{digest}"


def report_path(directory: Path, name: str, index: int | None = None) -> Path:
    """A path no earlier record is already using.

    Screening the same subject twice in a day is ordinary — a name is re-run
    after a refresh, or a batch is re-run with one row corrected. Keyed on row,
    name and date alone, the second record silently replaced the first, and the
    record that was destroyed was the one that had been relied on."""
    stem = slug(name)
    if index is not None:
        stem = f"{index:03d}-{stem}"
    base = f"{stem}-screening-{datetime.now().date().isoformat()}"
    path = directory / f"{base}.md"
    n = 2
    while path.exists():
        path = directory / f"{base}-{n}.md"
        n += 1
    return path


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_sources(args) -> int:
    for s in S.SOURCES:
        print(f"{'*' if s.default else ' '} {s.id:<26} {s.title}")
        print(f"    {s.authority}")
        print(f"    coverage: {s.coverage}")
        print(f"    licence:  {s.licence}")
        if s.notes:
            print(f"    note:     {s.notes}")
        print()
    print("* = fetched by `refresh` with no --source given")
    return EXIT_CLEAN


def cmd_refresh(args) -> int:
    # No manifest is loaded here: refresh_and_commit re-reads it inside the lock,
    # so this command never holds a snapshot that could be written back stale.
    rc = EXIT_CLEAN
    try:
        wanted = enabled_sources(args)
    except RequestError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_USAGE
    for s in wanted:
        print(f"... {s.id}", end="", flush=True)
        # Refresh and manifest commit happen together, under one lock.
        e = S.refresh_and_commit(s)
        if e.get("ok"):
            print(f"\r[ok] {s.id:<26} {e['records']:>7,} designations  "
                  f"list dated {term(e.get('list_date') or e.get('list_date_source', '—'))}  "
                  f"{e.get('seconds')}s")
        else:
            rc = EXIT_INCOMPLETE
            print(f"\r[--] {s.id:<26} FAILED — {term(e.get('error'))}")
    return rc


def cmd_status(args) -> int:
    """Reads the cache rather than trusting the manifest: the point of the
    command is to say whether a screen run now would be complete."""
    meta = S.load_meta()
    bad_age = validate_max_age(args)
    if bad_age:
        print(f"REFUSED: {bad_age}", file=sys.stderr)
        return EXIT_USAGE
    try:
        srcs = enabled_sources(args)
    except RequestError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(f"{'source':<26} {'designations':>13}  {'list date':<24} {'age':>8}  status")
    rc = EXIT_CLEAN
    for s in srcs:
        entry = meta.get(s.id, {})
        age = age_hours(entry)
        if not entry.get("ok"):
            status, n = f"NOT USABLE: {entry.get('error') or 'never fetched'}", 0
            rc = EXIT_INCOMPLETE
        else:
            try:
                n = len(S.read_source(s.id, entry))
                if is_stale(age, args.max_age_hours):
                    status, rc = "STALE", EXIT_INCOMPLETE
                else:
                    status = "ok"
            except S.CacheError as exc:
                status, n, rc = f"NOT USABLE: {exc}", 0, EXIT_INCOMPLETE
        listed = entry.get("list_date") or f"({entry.get('list_date_source', 'unknown')})"
        print(f"{s.id:<26} {n:>13,}  {term(listed)[:24]:<24} "
              f"{('—' if age is None else f'{age:.1f}h'):>8}  {term(status)}")
    return rc


def cmd_check(args) -> int:
    meta = S.load_meta()
    try:
        srcs = enabled_sources(args)
    except RequestError as exc:
        print(f"\nREFUSED: {exc}\nNothing was screened.", file=sys.stderr)
        return EXIT_USAGE
    o = screen(args.name, args, srcs, meta)

    # Delivery happens BEFORE the result is rendered. Printing a clean result and
    # then failing to write the record leaves the reader with a clean answer on
    # screen, a non-zero exit nobody reads, and no record at all.
    written = None
    if args.report or args.report_dir:
        try:
            path = (Path(args.report) if args.report
                    else report_path(Path(args.report_dir), args.name))
            write_report(path, o)
            written = path
        except Exception as exc:
            o.delivery_error = (f"the screening record could not be written "
                                f"({type(exc).__name__}: {exc})")

    if args.json:
        print(render_json(o))
    else:
        print(render_text(o, args.verbose))

    if written is not None:
        # stderr, so that --json --report leaves stdout parseable
        print(f"\nScreening record written to {written}", file=sys.stderr)

    # --strict is a no-op: an incomplete search exits 3 whether it is given or
    # not, and letting it override turned a refusal (4) into an incomplete (3).
    return o.exit_code


def cmd_batch(args) -> int:
    meta = S.load_meta()
    try:
        srcs = enabled_sources(args)
    except RequestError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        with open(args.file, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
            headers = [h.strip().lower() for h in (rows[0].keys() if rows else [])]
    except OSError as exc:
        print(f"cannot read {args.file}: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not rows:
        print(f"no rows in {args.file}", file=sys.stderr)
        return EXIT_USAGE
    if "name" not in headers:
        print(f"{args.file} has no 'name' column (found: {', '.join(headers) or 'nothing'}). "
              "Every row would be skipped and the run would report nothing found.",
              file=sys.stderr)
        return EXIT_USAGE

    outdir = Path(args.report_dir) if args.report_dir else None
    if outdir:
        # Refused up front rather than discovered a hundred rows in. A directory
        # that cannot be made is a bad request, not an incomplete search.
        try:
            outdir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"REFUSED: the records cannot be written to {outdir} ({exc}). "
                  "Nothing was screened.", file=sys.stderr)
            return EXIT_USAGE
    bad = validate_args(args)
    default_type = (args.default_type or "individual").strip().lower()
    if not bad and default_type not in TYPES:
        bad = f"--default-type {default_type!r} is not one of {', '.join(TYPES)}"
    if bad:
        print(f"REFUSED: {term(bad)}\nNothing was screened.", file=sys.stderr)
        return EXIT_USAGE
    outcomes, problems, rows_json = [], [], []
    if not args.json:
        print(f"{'subject':<42} {'hits':>5}  {'search':<12} top candidate")
    for i, row in enumerate(rows, 1):
        low = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        name = low.get("name", "")
        if not name:
            problems.append(f"row {i}: no name")
            if not args.json:   # a human line inside --json output broke the parse
                print(f"{'(row ' + str(i) + ': no name)':<42} {'—':>5}  {'REFUSED':<12} —")
            continue
        args.dob = low.get("dob", "")
        args.nationality = low.get("nationality") or low.get("country", "")
        args.type = (low.get("type") or args.default_type or "individual").strip().lower()
        args.client = low.get("client", "")
        args.matter = low.get("matter", "")
        try:
            o = screen(name, args, srcs, meta)
        except Exception as exc:   # one bad row is not a verdict on the rest
            problems.append(f"row {i} ({name}): the search failed "
                            f"({type(exc).__name__}: {exc})")
            print(f"{term(name)[:42]:<42} {'—':>5}  {'FAILED':<12} —")
            continue
        # Deliver BEFORE the row is printed, exactly as `check` does. Printing a
        # clean row and then failing to write its record left the clean row on
        # screen with nothing behind it, and the row itself never said so.
        if outdir:
            try:
                write_report(report_path(outdir, name, index=i), o)
            except Exception as exc:
                o.delivery_error = (f"the screening record could not be written "
                                    f"({type(exc).__name__}: {exc})")
        outcomes.append(o)
        if o.error:
            problems.append(f"row {i} ({name}): {o.error}")
        elif o.delivery_error:
            problems.append(f"row {i} ({name}): {o.delivery_error}")
        elif not o.complete:
            problems.append(f"row {i} ({name}): incomplete search")
        state = "complete" if o.complete else ("REFUSED" if o.error else "INCOMPLETE")
        top = (f"{o.hits[0]['score']} "
               f"{'DE-LISTED ' if o.hits[0]['record'].get('status') == 'delisted' else ''}"
               f"{term(o.hits[0]['record']['name'])[:36]} "
               f"[{term(o.hits[0]['record']['source'])}]") if o.hits else "—"
        rows_json.append(o)
        if not args.json:
            print(f"{term(name)[:42]:<42} {o.total_hits:>5}  {state:<12} {top}")
            # Every other route renders these. Batch text did not, so a Cyrillic
            # subject printed "0  complete  —" and exited 0 without a word about
            # the romanisations the tool had guessed on its behalf, or about a
            # script it could not reach, or about identities withheld by the
            # limit. A caveat that appears on five routes out of six is a caveat
            # the reader of the sixth does not have.
            for c in o.caveats:
                print(f"{'':<42} {'':>5}  {'':<12} ⚠ {term(c)}")

    total_hits = sum(o.total_hits for o in outcomes)
    complete = all(o.complete for o in outcomes) and not problems
    # A flag that refuses every row is a bad REQUEST, not an incomplete search.
    # `check --threshold nan` exits 4; batch was exiting 3 for the same mistake.
    refused_request = bool(outcomes) and all(o.error for o in outcomes)
    if args.json:
        # --json was accepted and ignored, so a caller parsing the output got a
        # human table and no error.
        print(json_safe(json.dumps({
            "rows": [json.loads(render_json(o)) for o in rows_json],
            "rows_read": len(rows), "rows_screened": len(outcomes),
            "total_hits": total_hits, "complete": complete, "problems": problems,
            "exit_code": _batch_exit(refused_request, complete, total_hits),
        }, ensure_ascii=False, indent=2, allow_nan=False, default=_jsonable)))
        return _batch_exit(refused_request, complete, total_hits)
    print()
    print(f"{len(rows)} rows, {len(outcomes)} screened, {total_hits} candidate matches.")
    if problems:
        print("\nTHIS BATCH IS NOT A CLEAN RESULT:")
        for p in problems[:20]:
            print(f"  - {term(p)}")
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more")
    if outdir:
        print(f"Screening records in {term(outdir)}")
    return _batch_exit(refused_request, complete, total_hits)


def _batch_exit(refused_request: bool, complete: bool, total_hits: int) -> int:
    if refused_request:
        return EXIT_USAGE
    if not complete:
        return EXIT_INCOMPLETE
    return EXIT_CANDIDATES if total_hits else EXIT_CLEAN


def main() -> int:
    class Parser(argparse.ArgumentParser):
        """argparse exits 2 on a usage error. Here 2 means candidates were found,
        so a mistyped flag would read to any script as a hit."""

        def error(self, message):
            self.print_usage(sys.stderr)
            print(f"{self.prog}: {message}\nNothing was screened.", file=sys.stderr)
            raise SystemExit(EXIT_USAGE)

    p = Parser(prog="screen.py", description=__doc__,
               formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=Parser)

    def common(sp):
        sp.add_argument("--source", action="append",
                        help="source id(s), comma-separated; repeatable")
        sp.add_argument("--max-age-hours", type=float, default=24.0)

    sp = sub.add_parser("sources", help="the source registry and its licences")
    sp.set_defaults(func=cmd_sources)

    sp = sub.add_parser("refresh", help="download and parse lists")
    common(sp)
    sp.set_defaults(func=cmd_refresh)

    sp = sub.add_parser("status", help="cache freshness, by reading the cache")
    common(sp)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("check", help="screen one name")
    sp.add_argument("name")
    sp.add_argument("--dob", default="", help="1975-03-02, 02/03/1975 or 1975")
    sp.add_argument("--nationality", "--country", dest="nationality", default="")
    sp.add_argument("--type", default="any")
    sp.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    sp.add_argument("--limit", type=int, default=40)
    sp.add_argument("--include-delisted", action="store_true")
    sp.add_argument("--verbose", "-v", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--report", help="write the screening record to this path")
    sp.add_argument("--report-dir", help="write the screening record into this directory")
    sp.add_argument("--client", default="")
    sp.add_argument("--matter", default="")
    sp.add_argument("--strict", action="store_true",
                    help="(kept for compatibility; an incomplete search always exits 3)")
    common(sp)
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("batch", help="screen a CSV (name,dob,nationality,type,client,matter)")
    sp.add_argument("file")
    sp.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--default-type", default="any")
    sp.add_argument("--include-delisted", action="store_true")
    sp.add_argument("--report-dir")
    sp.add_argument("--strict", action="store_true")
    sp.add_argument("--verbose", "-v", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--client", default="")
    sp.add_argument("--matter", default="")
    common(sp)
    sp.set_defaults(func=cmd_batch)

    args = p.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        # Every exit from this program reports whether the search can be relied
        # on. An unhandled fault is the one case where it plainly cannot, so it
        # leaves by the same door as any other incomplete search rather than as
        # a traceback and a bare exit 1. KeyboardInterrupt is not caught: an
        # interrupted run is the operator's own doing and should look like it.
        print(f"\nThe run failed ({type(exc).__name__}: {term(exc)}).\n"
              "Nothing here can be relied on as a completed search.",
              file=sys.stderr)
        return EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
