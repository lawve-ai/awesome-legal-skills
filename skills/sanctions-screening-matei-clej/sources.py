#!/usr/bin/env python3
"""
Source registry and parsers for the open-source sanctions screening skill.

Every source here is an official publication of the designating authority, or
(where flagged) an open-data aggregator. Nothing is scraped from a commercial
screening vendor and nothing needs an account.

A parser returns (records, meta). A record is a normalised dict:

    source        source id
    uid           the authority's own reference for the designation group
    type          individual | entity | vessel | aircraft | unknown
    name          primary name as published
    aliases       [str]                 all further name variants, Latin script
    nonlatin      [str]                 names in non-Latin script, kept SEPARATE
    dob           [str]                 ISO date or bare year, as published
    nationality   [str]
    regime        str                   the sanctions regime / programme
    measures      str                   asset freeze, travel ban, arms embargo...
    listed_on     str
    ids           [str]                 passport / national ID / registration
    address       str
    notes         str                   statement of reasons, truncated
    ref           str                   published designation reference
    status        active | delisted
    delisted_on   the date the publisher took it off, where the file gives one (Swiss)

Two traps are handled here rather than left to the caller, because either would
silently corrupt every record from that source:

  * both UK CSVs open with a preamble line BEFORE the header row;
  * the Swiss whole-list file ships de-listed targets alongside live ones.
"""

from __future__ import annotations

import csv
import functools
import gzip
import hashlib
import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zlib
import fcntl
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Callable

import matching as M

csv.field_size_limit(10_000_000)

DATA = Path(os.environ.get("SANCTIONS_DATA", Path.home() / ".claude" / "sanctions-data"))
RAW = DATA / "raw"
NORM = DATA / "norm"
META = DATA / "meta.json"

UA = "sanctions-screening/1.0 (open-source sanctions due diligence tooling)"

# ONE number for the cache, written into both fields below.
#
# ENGINE_VERSION was introduced to stop the 07.09.2026 drift and only half did.
# It stops NEW code reading an OLD cache. The incident was the reverse — a
# four-round-stale install reading a CURRENT cache — and old code cannot check a
# field it has never heard of. The eighth review proved it: a build from
# `df2e980` read a manifest declaring engine_version 999 and returned complete,
# exit 0. That install failed closed today only because PARSER_VERSION happened
# to move 3 -> 4 for an unrelated Canadian parser change.
#
# So there is one generation, and it is written into `parser_version` — the
# field every build back to the first one already validates. Bump it for ANY
# change to parsing, matching, indexing, the exactness rules, the completeness
# gate or the ledger. A cache is then refused by old code and new code alike.
CACHE_GENERATION = 7

PARSER_VERSION = CACHE_GENERATION

# What produced the RESULT, as distinct from what produced the parsed file.
#
# PARSER_VERSION binds a cache to the code that wrote it. It says nothing about
# the matcher, the completeness gate or the ledger — and on 07.09.2026 that gap
# was not theoretical: an installed copy of this tool four rounds out of date
# shared this cache at the same PARSER_VERSION, did not fail closed, and
# reported "Lists searched: 6 of 6 — No candidate", exit 0, on names that were
# on the lists. Nothing in the record it produced could have told anyone which
# code had produced it.
#
# Bump this for ANY change to matching, indexing, the exactness rules, the
# completeness gate or the ledger — not only for a parser change. A cache
# written under a different engine generation is refused, exactly as a
# differently-parsed one is.
ENGINE_VERSION = CACHE_GENERATION


@functools.lru_cache(maxsize=1)
def code_fingerprint() -> dict:
    """Digests of the three modules that decide what a screening result says.

    Recorded on the manifest and on the screening record, so that a result can
    be tied to the code that produced it after the fact. This is auditability,
    not a gate: ENGINE_VERSION is the gate."""
    out = {}
    for mod in ("screen.py", "sources.py", "matching.py"):
        try:
            out[mod] = hashlib.sha256((Path(__file__).parent / mod).read_bytes()).hexdigest()[:16]
        except OSError:
            out[mod] = "unreadable"
    return MappingProxyType(out)
"""Bumped whenever a parser changes what it emits. A cache written by a
different version is not read: its record count would still match, and a
count is not evidence that the contents are what this code expects."""
TRUNC = 600


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

@dataclass
class Source:
    id: str
    title: str
    authority: str
    url: str
    filename: str
    parser: str
    licence: str
    coverage: str
    default: bool = True
    aux: dict = field(default_factory=dict)
    notes: str = ""


SOURCES: list[Source] = [
    Source(
        id="uk-sanctions-list",
        title="UK Sanctions List",
        authority="Foreign, Commonwealth & Development Office",
        url="https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv",
        filename="uk-sanctions-list.csv",
        parser="parse_uksl",
        licence="Open Government Licence v3.0",
        coverage="Every person designated under UK autonomous regimes, with the "
                 "measures actually imposed (asset freeze, travel ban, arms, "
                 "trade, transport).",
        notes="The legal list. Broader than the OFSI list, which carries only "
              "financial-sanctions targets.",
    ),
    Source(
        id="ofsi",
        title="OFSI Consolidated List of Financial Sanctions Targets",
        authority="HM Treasury, Office of Financial Sanctions Implementation",
        url="https://ofsistorage.blob.core.windows.net/publishlive/2022format/ConList.csv",
        filename="ofsi.csv",
        parser="parse_ofsi",
        licence="Open Government Licence v3.0",
        coverage="Asset-freeze targets under all UK regimes, UK-implemented UN "
                 "designations included.",
        notes="Endpoint 404s on HEAD and serves on GET; do not read a HEAD "
              "failure as a dead source.",
    ),
    Source(
        id="un",
        title="UN Security Council Consolidated List",
        authority="United Nations Security Council",
        url="https://scsanctions.un.org/resources/xml/en/consolidated.xml",
        filename="un.xml",
        parser="parse_un",
        licence="United Nations, free to reproduce",
        coverage="All individuals and entities designated by the Security "
                 "Council sanctions committees.",
    ),
    Source(
        id="eu",
        title="EU Consolidated Financial Sanctions List",
        authority="European Commission (FSF)",
        url="https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw",
        filename="eu.xml",
        parser="parse_eu",
        licence="European Commission reuse policy",
        coverage="Persons, groups and entities subject to EU financial "
                 "sanctions.",
    ),
    Source(
        id="ofac-sdn",
        title="OFAC Specially Designated Nationals list",
        authority="US Treasury, Office of Foreign Assets Control",
        url="https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
        filename="ofac-sdn.csv",
        parser="parse_ofac",
        licence="US Government work, public domain",
        coverage="SDNs and blocked persons.",
        aux={"alt": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ALT.CSV",
             "alt_filename": "ofac-sdn-alt.csv"},
    ),
    Source(
        id="ofac-cons",
        title="OFAC Consolidated (non-SDN) list",
        authority="US Treasury, Office of Foreign Assets Control",
        url="https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONS_PRIM.CSV",
        filename="ofac-cons.csv",
        parser="parse_ofac",
        licence="US Government work, public domain",
        coverage="Sectoral, non-SDN programmes: SSI, FSE, NS-PLC, CAPTA and "
                 "others.",
        aux={"alt": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONS_ALT.CSV",
             "alt_filename": "ofac-cons-alt.csv"},
    ),
    Source(
        id="canada",
        title="Consolidated Canadian Autonomous Sanctions List",
        authority="Global Affairs Canada",
        url="https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/sanctions/sema-lmes.xml",
        filename="canada.xml",
        parser="parse_canada",
        licence="Open Government Licence – Canada",
        coverage="Designations under the Special Economic Measures Act and the "
                 "Justice for Victims of Corrupt Foreign Officials Act.",
        default=False,
    ),
    Source(
        id="swiss",
        title="SECO Swiss sanctions list",
        authority="State Secretariat for Economic Affairs (SECO)",
        url="https://www.sesam.search.admin.ch/sesam-search-web/pages/downloadXmlGesamtliste.xhtml?lang=en&action=downloadXmlGesamtlisteAction",
        filename="swiss.xml",
        parser="parse_swiss",
        licence="Swiss Confederation, free reuse",
        coverage="All Swiss ordinance designations, individuals, entities and "
                 "objects.",
        default=False,
        notes="The whole-list file includes DE-LISTED targets. Parsed as "
              "status=delisted and excluded unless asked for.",
    ),
    Source(
        id="opensanctions-sanctions",
        title="OpenSanctions consolidated sanctioned entities",
        authority="OpenSanctions Datenbanken GmbH (aggregator)",
        url="https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv",
        filename="opensanctions-sanctions.csv",
        parser="parse_opensanctions",
        licence="CC BY-NC 4.0 — NON-COMMERCIAL. Fee-earning use needs a licence "
                "from OpenSanctions.",
        coverage="~90 sanctions sources deduplicated, including states this "
                 "skill does not fetch directly.",
        default=False,
        notes="Licence-gated: set SANCTIONS_OPENSANCTIONS_LICENCE to 'noncommercial' "
              "or to your commercial licence reference before it will refresh.",
    ),
    Source(
        id="opensanctions-peps",
        title="OpenSanctions Politically Exposed Persons",
        authority="OpenSanctions Datenbanken GmbH (aggregator)",
        url="https://data.opensanctions.org/datasets/latest/peps/targets.simple.csv",
        filename="opensanctions-peps.csv",
        parser="parse_opensanctions",
        licence="CC BY-NC 4.0 — NON-COMMERCIAL. Fee-earning use needs a licence "
                "from OpenSanctions.",
        coverage="Political office-holders, their family members and known close "
                 "associates. This is the only PEP source here.",
        default=False,
        notes="Licence-gated, and large (~180 MB). PEP status is an EDD trigger "
              "under MLR 2017 reg 33(1)(d) and reg 35, not a prohibition.",
    ),
]

MIN_RECORDS = {
    "uk-sanctions-list": 2000, "ofsi": 2000, "un": 300, "eu": 2000,
    "ofac-sdn": 5000, "ofac-cons": 100, "canada": 1000, "swiss": 2000,
    "opensanctions-sanctions": 5000, "opensanctions-peps": 5000,
}
"""Fewest designations a list can plausibly hold. A download truncated at a line
boundary parses cleanly and would otherwise be committed as the whole list, with
its own count recorded as the expected count — a circular check that proves
nothing. These floors are an order of magnitude below current sizes."""

SHRINK_TOLERANCE = 0.20
"""A refresh that loses more than this share of the previous list is quarantined
rather than committed. Real lists do not shrink by a fifth overnight; a truncated
or partially-served download does."""


BY_ID = {s.id: s for s in SOURCES}
DEFAULT_IDS = [s.id for s in SOURCES if s.default]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _clean(v) -> str:
    if v is None:
        return ""
    v = str(v).strip()
    return "" if v in {"-0-", "-0-", "n/a", "N/A", "None"} else v


def _join_names(*parts) -> str:
    return " ".join(p for p in (_clean(x) for x in parts) if p)


def _trunc(s: str, n: int = TRUNC) -> str:
    s = re.sub(r"\s+", " ", _clean(s))
    return s if len(s) <= n else s[: n - 1] + "…"


def _dedupe(seq) -> list:
    seen, out = set(), []
    for x in seq:
        x = _clean(x)
        if x and x.upper() not in seen:
            seen.add(x.upper())
            out.append(x)
    return out


LATIN = re.compile(r"[A-Za-z]")
LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def _is_nonlatin(s: str) -> bool:
    """True where the name is written predominantly outside the Latin script.

    A "contains no Latin letter" test is not enough: the EU list publishes each
    name in every official language, and Cyrillic names routinely carry a stray
    Latin homoglyph (Ольга Валерiївна — that "i" is Latin). Those were landing
    in the Latin display name."""
    letters = LETTER.findall(s or "")
    if not letters:
        return False
    latin = sum(1 for ch in letters if LATIN.match(ch))
    return latin * 2 < len(letters)


def _sniff_header(path: Path, marker: str) -> int:
    """UK CSVs carry a preamble line before the header. Return rows to skip."""
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for i, line in enumerate(fh):
            if marker.lower() in line.lower():
                return i
            if i > 5:
                break
    return 0


def _first_line(path: Path) -> str:
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.readline().strip()


def download(src: Source, timeout: int = 600) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    out = {}
    targets = [(src.url, RAW / src.filename)]
    if "alt" in src.aux:
        targets.append((src.aux["alt"], RAW / src.aux["alt_filename"]))
    for url, dest in targets:
        tmp = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as fh:
            while chunk := resp.read(1 << 20):
                fh.write(chunk)
        tmp.replace(dest)
        out[str(dest)] = dest.stat().st_size
    return out


def raw_fingerprints(src: "Source") -> dict:
    """Digest, size and line count of EVERY file the parse reads.

    Only the primary file's digest was recorded. OFAC's aliases live in a second
    file, and a truncated or empty one leaves the primary intact, so every alias
    could be lost while the manifest, the validator and `complete` all reported
    success — and the exact published alias AVIA IMPORT then returned a clean nil.
    A list is only as whole as the least whole file behind it."""
    out = {}
    names = [src.filename] + ([src.aux["alt_filename"]] if "alt" in src.aux else [])
    for fn in names:
        path = RAW / fn
        if not path.exists():
            out[fn] = {"missing": True}
            continue
        blob = path.read_bytes()
        out[fn] = {"sha256": hashlib.sha256(blob).hexdigest()[:16],
                   "bytes": len(blob), "lines": blob.count(b"\n")}
    return out


def alias_floor(src: "Source", records: list, previous: dict | None) -> None:
    """Aliases come from the auxiliary file for the OFAC sources, so the count of
    records CARRYING one is the measure of whether that file arrived."""
    with_alias = sum(1 for r in records if r.get("aliases"))
    floor = MIN_ALIASED.get(src.id)
    if floor is not None and with_alias < floor:
        raise CacheError(
            f"only {with_alias:,} designations carry an alias, fewer than the "
            f"{floor:,} this list must hold — the alias file did not arrive whole")
    was = (previous or {}).get("aliased") or (previous or {}).get("last_good_aliased") or 0
    if was and with_alias < was * (1 - SHRINK_TOLERANCE):
        raise CacheError(
            f"designations carrying an alias fell from {was:,} to {with_alias:,} "
            f"(>{int(SHRINK_TOLERANCE * 100)}%) — quarantined; the auxiliary file "
            "is probably truncated")


def last_good_count(previous: dict | None) -> int:
    """The last count this list was known good at, which is not the same as the
    last count recorded. One failed refresh writes ok=false with records=0, and
    reading the shrink baseline off that entry silently retires the rule just
    when it is most needed."""
    if not previous:
        return 0
    if previous.get("ok") and previous.get("records"):
        return int(previous["records"])
    return int(previous.get("last_good_records") or 0)


# What each list must hold that CARRIES AN ALIAS. Measured against the live files
# on 02.09.2026: OFAC SDN 8,811 of 19,321, OFAC consolidated 411 of 481. The
# floors sit about a third below those, far enough under to survive ordinary
# movement and high enough to catch an auxiliary file that arrived truncated or
# not at all. The 20% shrink rule above catches the slower erosion.
MIN_ALIASED = {"ofac-sdn": 6_000, "ofac-cons": 250}

# ALT ROWS, not designations carrying an alias. Measured 03.09.2026: OFAC SDN
# 20,147 rows for 8,811 aliased designations, consolidated 1,110 for 411. The
# fourth review kept the first row for every aliased designation and dropped
# the other 11,336 — 56% of the file — and every floor and shrink rule above
# passed, because they count designations with AT LEAST ONE alias. The exact
# published alias CUBAN FREIGHT ENTERPRISE then returned a clean nil, complete,
# exit 0. A list is only as whole as the least whole file behind it, and that
# file is measured in rows. Floors sit about a third under the live counts.
MIN_ALIAS_ROWS = {"ofac-sdn": 13_000, "ofac-cons": 700}


def _last_good(previous: dict | None, key: str) -> int:
    """The last value of a manifest figure the list was known GOOD at."""
    if not previous:
        return 0
    if previous.get("ok") and previous.get(key):
        return int(previous[key])
    return int(previous.get(f"last_good_{key}") or 0)


def alias_delta(src: "Source", extra: dict, previous: dict | None) -> None:
    """Refuse an auxiliary file that has lost rows or aliases, whatever the
    count of designations still carrying one."""
    rows = extra.get("alias_rows")
    if rows is None:            # this parser reads no auxiliary file
        return
    floor = MIN_ALIAS_ROWS.get(src.id)
    if floor is not None and rows < floor:
        raise CacheError(f"the alias file holds {rows:,} rows, fewer than the {floor:,} "
                         "it must hold — it did not arrive whole")
    was = _last_good(previous, "alias_rows")
    if was and rows < was * (1 - SHRINK_TOLERANCE):
        raise CacheError(f"alias rows fell from {was:,} to {rows:,} "
                         f"(>{int(SHRINK_TOLERANCE * 100)}%) — quarantined; the auxiliary "
                         "file is probably truncated")
    total, was_total = extra.get("alias_total"), _last_good(previous, "alias_total")
    if total is not None and was_total and total < was_total * (1 - SHRINK_TOLERANCE):
        raise CacheError(f"aliases emitted fell from {was_total:,} to {total:,} "
                         f"(>{int(SHRINK_TOLERANCE * 100)}%) — quarantined")


# Lists whose aliases come mechanically out of an auxiliary file, where a name
# leaving a designation that is still listed means the file or the parse failed,
# not that the publisher changed its mind. Every list gets an inventory written;
# these are the ones a removal blocks. Widen it as each publisher's real
# alias churn is measured.
# Every default list. Two of six was a guarantee about six lists enforced on
# two, and the seventh review answered its own standing question with it:
# removing "Černé září" from otherwise valid EU raw XML passed a real parser and
# a real refresh, ledger present and unenforced, and returned exit 0.
#
# ⚠ Four of these publishers have never been replayed across consecutive
# snapshots under this rule. Ordinary churn that this rule reads as a loss will
# REFUSE a refresh rather than accept it. That is the intended direction of
# failure, and SANCTIONS_ALLOW_ALIAS_REMOVAL=1 — which now records itself in the
# manifest — is the release valve. See TESTING.md.
ALIAS_INVENTORY_ENFORCED = set(DEFAULT_IDS)


# Bumped whenever the shape of a ledger entry changes, so that a ledger written
# by an older build is treated as ABSENT rather than trusted. Version 1 held
# aliases only: OFAC UID 424's entry was literally [], and its primary name
# BOUTIQUE LA MAISON could therefore be substituted through a refresh that
# passed every check, complete, exit 0, with no override and nothing corrupted.
INVENTORY_VERSION = 4

# The fields a designation keeps when only its NAME is changed. A substitution in
# place rewrites the name and leaves these alone, which is what makes them useful
# for telling a de-listing from a replacement. They are never used for matching.
STABLE_FIELDS = ("type", "regime", "measures", "dob", "nationality", "ids",
                 "address", "listed_on")

# A fingerprint shared by more designations than this identifies a CLASS, not a
# designation. It cannot then be used to show that a vanished designation was
# genuinely de-listed rather than replaced in place, and the vanishing is refused.
FINGERPRINT_SPECIFIC = 3


def designation_axes(r: dict) -> set:
    """The values that identify a designation ONE AT A TIME.

    The fingerprint is a digest over every stable field at once, so restating any
    single one of them defeats it — and that was enough to walk a substitution
    straight through: rename, renumber, append "-RESTATED" to a programme code,
    and the successor no longer matches on any ground the rule tests. Restating a
    programme code is cosmetic. Restating a passport number is not. These are
    compared separately so that an edit to one leaves the others still speaking.

    A date of birth alone identifies nobody — thousands share 1968 — so it is
    carried only in company. Values that turn out not to be distinguishing are
    filtered later, against the ledger, where their frequency is known."""
    out = set()
    for v in (r.get("ids") or []):
        v = str(v).strip()
        if len(v) >= 4:
            out.add("id:" + v.upper())
    addr = str(r.get("address") or "").strip()
    if len(addr) >= 8:
        out.add("addr:" + " ".join(addr.upper().split()))
    dobs = [str(x).strip() for x in (r.get("dob") or []) if str(x).strip()]
    nats = [str(x).strip() for x in (r.get("nationality") or []) if str(x).strip()]
    for dv in dobs:
        for nv in nats:
            out.add(f"dob+nat:{dv.upper()}|{nv.upper()}")
        # A date on its own, where it is a DATE and not a bare year. Requiring a
        # nationality alongside meant a designation carrying a full date of birth
        # and no stated nationality had no axis at all, and the eleventh review
        # used exactly that record. How identifying any given date is, is a
        # question the frequency filter answers; it is not a reason to refuse to
        # look.
        if sum(ch.isdigit() for ch in dv) >= 6:
            out.add("dob:" + dv.upper())
    return out


def designation_fingerprint(r: dict) -> str:
    parts = []
    for f in STABLE_FIELDS:
        v = r.get(f)
        if isinstance(v, (list, tuple)):
            v = "|".join(sorted(str(x) for x in v))
        parts.append(f"{f}={v or ''}")
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]


def alias_inventory(recs: list) -> dict:
    """EVERY published spelling each designation carries, keyed by UID.

    The primary name is a published spelling. Leaving it out made the ledger a
    guard over aliases while it was described as a guard over names, and the
    difference was a clean nil on an exact published name.

    Normalised, because that is the form a search actually reaches: a change of
    punctuation or case is not a lost name and must not read as one.

    Each entry also carries the PUBLISHER's own reference and a fingerprint of
    the fields a designation keeps when only its name is changed. Neither is used
    for matching. Both exist to answer the one question the record counts kept
    getting wrong: when a designation's key disappears, has the designation gone,
    or has it been replaced in place?"""
    inv: dict = {}
    for r in recs:
        uid = str(r.get("uid") or "")
        if not uid:
            continue
        d = inv.setdefault(uid, {"names": set(), "ref": str(r.get("ref") or ""),
                                 "fp": designation_fingerprint(r),
                                 "axes": designation_axes(r)})
        for cand in ([r.get("name", "")] + list(r.get("aliases", []))
                     + list(r.get("nonlatin", []))):
            if not cand:
                continue
            # EXACTLY the representations screen._index() derives, because the
            # question this ledger answers is "can a search still reach this
            # name", and a ledger that tracks a form the index never builds is
            # answering a different question. `normalise() or native_key()` took
            # the first that was non-empty, and for a Cyrillic spelling
            # normalise() is non-empty — it is homoglyph residue — so the native
            # key the index actually searches was never recorded.
            before = len(d["names"])
            if not M.is_native(cand):
                k = M.normalise(cand)
                if k:
                    d["names"].add(k)
            if M.has_native_letters(cand):
                k = M.native_key(cand)
                if k:
                    d["names"].add(k)
            if len(d["names"]) == before:      # neither representation survived
                k = M.normalise(cand) or M.native_key(cand)
                if k:
                    d["names"].add(k)
    return {uid: {"names": sorted(d["names"]), "ref": d["ref"], "fp": d["fp"],
                  "axes": sorted(d["axes"])}
            for uid, d in inv.items()}


def inv_dir() -> Path:
    """Where the ledger lives: beside the cache it describes.

    Resolved at CALL time, not bound at import. `DATA` is redirected in-process
    — the suites do it to keep their refreshes off the live cache — and a path
    computed once at import does not follow. Bound at import, the integrity
    suite's isolated round-trip refresh of OFSI wrote its two-record test list
    into the LIVE ledger, which is the exact failure the ledger exists to
    prevent: the next comparison baselined on names this machine never
    published."""
    return DATA / "inventory"


def read_alias_inventory(source_id: str, entry: dict | None = None):
    """The ledger, or None where there is not a usable one.

    None and {} are different answers and were once the same. An unreadable
    ledger returned {}, the guard read that as "nothing to compare", the
    refresh was committed, and the successful commit then REWROTE the ledger —
    so corrupting the file both disabled the check and destroyed the evidence
    that it had been disabled. Absence is now reported as absence, and the
    caller decides whether it may proceed."""
    path = inv_dir() / f"{source_id}.aliases.json.gz"
    if not path.exists():
        return None
    try:
        blob = path.read_bytes()
        data = json.loads(gzip.decompress(blob).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("version") != INVENTORY_VERSION:
        return None            # including every version-1 ledger, which had no primary names
    uids = data.get("uids")
    if not isinstance(uids, dict) or not uids:
        # An EMPTY ledger is not a ledger, and this is the same mistake one
        # level down from the one it was written to fix. Absence was separated
        # from emptiness in the reader, and then the caller was written to test
        # only for absence — so a syntactically perfect {"uids": {}} passed as
        # data, the comparison iterated nothing, found nothing missing, and let
        # a deletion through. A source with designations has spellings.
        return None
    if entry:
        # Bound to the cache it describes. Without this a ledger is just a file
        # in a directory: a false but well-formed one passed every check and was
        # then overwritten by the refresh it had just waved through.
        recorded = entry.get("inventory_sha256")
        n = entry.get("inventory_uids")
        if not recorded or n is None:
            # An UNBOUND manifest cannot vouch for any ledger, and treating the
            # binding as optional meant that whatever was on disk was trusted
            # whenever the manifest happened not to carry the fields. A ledger
            # holding one designation was accepted on that basis and a deletion
            # passed: complete, zero hits, exit 0. No binding, no ledger.
            return None
        if recorded != hashlib.sha256(blob).hexdigest() or n != len(uids):
            return None
    return uids


def write_alias_inventory(source_id: str, inv: dict) -> dict:
    """Write the ledger and return the fields that bind it to this refresh."""
    payload = {"version": INVENTORY_VERSION, "uids": inv}
    blob = gzip.compress(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"), mtime=0)
    atomic_write_bytes(inv_dir() / f"{source_id}.aliases.json.gz", lambda fh: fh.write(blob))
    return {"inventory_sha256": hashlib.sha256(blob).hexdigest(),
            "inventory_uids": len(inv), "inventory_version": INVENTORY_VERSION}


def bootstrap_alias_inventory(source_id: str, entry: dict | None = None):
    """Rebuild the ledger from the last good normalised file already on disk.

    A machine upgrading to this build, or one whose ledger has been damaged,
    has no version-2 ledger — but it does have a normalised cache whose digest
    the manifest already verifies, and that cache IS the last good set of
    published spellings. Rebuilding from it is what lets the guard fail closed
    without making the first refresh after an upgrade impossible. Returns None
    where the cache cannot be read, and the caller then refuses."""
    # Through _load_norm, NOT load_records. load_records is expressly tolerant:
    # it verifies neither digest, nor parser version, nor recorded count, so
    # rebuilding through it accepted a readable-but-wrong cache and laundered
    # whatever loss was already baked into it into the new baseline.
    if not entry:
        return None
    if entry.get("parser_version") != PARSER_VERSION:
        return None
    path = NORM / f"{source_id}.jsonl.gz"
    if not path.exists():
        return None
    # The count to verify against is the LAST GOOD one. A failed refresh records
    # `records: 0` — the number this attempt committed, which is the truth — and
    # verifying the file on disk against nought made every rebuild fail, so one
    # refusal turned into a source that could never refresh again.
    verify = dict(entry)
    if not verify.get("records"):
        verify["records"] = entry.get("last_good_records")
    if not verify.get("records"):
        verify.pop("records", None)      # digest alone, rather than against nothing
    try:
        recs = _load_norm(path, verify)
    except Exception:
        return None
    return alias_inventory(list(recs)) or None


def alias_removals(src: "Source", recs: list, prior: dict | None,
                   entry: dict | None = None) -> None:
    """Refuse a refresh that has dropped published spellings from designations
    the list still carries.

    Row and total counters cannot see this. The fifth review deleted a single
    ALT row and, separately, substituted one name for another under the same
    UID; both preserved every aggregate the tool checked — rows, emitted
    aliases, designations carrying an alias, and even that UID's own
    cardinality — and both made the exact published alias CUBAN FREIGHT
    ENTERPRISE, UID 1287, a clean nil through the real refresh path, complete,
    exit 0. Only the SET of names per designation catches it.

    A UID that has gone from the list entirely is not counted: de-listing is
    what these publishers do every week, and the designation's disappearance is
    the record count's business, not this ledger's.

    SANCTIONS_ALLOW_ALIAS_REMOVAL=1 lets a verified publisher correction
    through. It is deliberately its own switch, and it is the ONLY one that
    reaches this check. SANCTIONS_ALLOW_SHRINK=1 nulls the `previous` manifest
    entry so that the count rules stand down, and this guard used to take that
    same nulled value and return on it — so authorising a shrink silently
    authorised every name loss with it, and deleting CUBAN FREIGHT ENTERPRISE
    under that flag committed and produced a clean nil. The prior entry is now
    passed here in full whatever the shrink flag says.

    It fails CLOSED. Where the list has a last good cache but no usable ledger,
    the ledger is rebuilt from that cache — whose digest the manifest already
    verifies — and the comparison is made against it. Only where neither exists
    is there genuinely nothing to compare, and only then does this return."""
    if src.id not in ALIAS_INVENTORY_ENFORCED:
        return
    if os.environ.get("SANCTIONS_ALLOW_ALIAS_REMOVAL", "").strip() == "1":
        # Recorded, not merely obeyed. An override that leaves no trace is
        # indistinguishable afterwards from a refresh that had nothing to
        # authorise, and the whole point of this guard is that a name leaving a
        # list should be a visible decision.
        if entry is not None:
            entry["alias_removal_override"] = True
        return
    if prior and prior.get("parser_version") not in (None, PARSER_VERSION):
        # A GENERATION CHANGE, and there is nothing comparable to compare with.
        # The last good cache was written by different code: its ledger may
        # legitimately differ from what today's parser produces, so treating it
        # as a baseline would manufacture losses that never happened — and
        # requiring it, which is what the first version of this did, made every
        # enforced list unrefreshable the moment the generation moved. The tool
        # could not upgrade itself.
        #
        # So the comparison is skipped, ONCE, and the skip is recorded on the
        # manifest rather than passed over in silence. The refresh after this one
        # has a current-generation ledger and is compared normally.
        if entry is not None:
            entry["alias_baseline"] = (
                f"not compared — the last good cache was written at generation "
                f"{prior.get('parser_version')}, this is {PARSER_VERSION}")
        return
    had_cache = bool(prior) and bool(
        (prior.get("ok") and prior.get("records")) or prior.get("last_good_records"))
    # A parsed list on disk is itself evidence that this is not a first refresh,
    # whatever the manifest says. Asking the manifest alone meant that losing or
    # refusing it turned a full cache into "nothing to compare against" and the
    # guard stood down. The bootstrap then runs, finds no digest to verify
    # against, and the refresh is REFUSED — which is the right direction.
    had_cache = had_cache or (NORM / f"{src.id}.jsonl.gz").exists()
    old = read_alias_inventory(src.id, prior)
    if old is None:
        if not had_cache:
            return             # a genuinely first refresh on this machine
        old = bootstrap_alias_inventory(src.id, prior)
        if old is None:
            raise CacheError(
                f"{src.id} has a last good cache but no readable ledger of the names it "
                "published, and the cache it would be rebuilt from cannot be read — "
                "refusing to commit a list whose names cannot be compared against "
                "anything. Refresh again once the cache is readable, or set "
                "SANCTIONS_ALLOW_ALIAS_REMOVAL=1 to proceed without the comparison")
    new = alias_inventory(recs)
    new_all: set = set()
    for d in new.values():
        new_all |= set(d["names"])
    # Every current designation is a possible successor, not only the ones whose
    # key is new. The eleventh review substituted into an EXISTING uid — one the
    # ledger already knew — and the successor maps skipped it, because they were
    # built from arrivals alone. Identity that moves onto a record already on the
    # list has moved just as surely as identity that arrives with a new one.
    carrier_ref, carrier_fp, carrier_axis = {}, {}, {}
    for uid, d in new.items():
        if d.get("ref"):
            carrier_ref.setdefault(d["ref"], []).append(uid)
        carrier_fp.setdefault(d["fp"], []).append(uid)
        for a in d.get("axes", ()):
            carrier_axis.setdefault(a, []).append(uid)
    axis_freq: dict = {}
    for d in old.values():
        if isinstance(d, dict):
            for a in d.get("axes", ()):
                axis_freq[a] = axis_freq.get(a, 0) + 1
    new_fp_freq: dict = {}
    for d in new.values():
        new_fp_freq[d["fp"]] = new_fp_freq.get(d["fp"], 0) + 1
    fp_freq: dict = {}
    for d in old.values():
        f = d.get("fp") if isinstance(d, dict) else None
        if f:
            fp_freq[f] = fp_freq.get(f, 0) + 1

    lost, names_lost, repositioned, evidenced = {}, 0, {}, {}
    for uid, entry_old in old.items():
        forms = entry_old["names"] if isinstance(entry_old, dict) else entry_old
        current = new.get(uid)
        if current is None:
            # The key has gone and so, unless they are still findable somewhere
            # on this list, have the names it carried.
            #
            # There used to be three ways to be excused: nothing arrived with the
            # same reference, nothing arrived with the same fingerprint, and the
            # designation was identifiable enough for those absences to mean
            # something. Each was an absence of evidence, and each was defeated
            # by editing one more field — the reference, then a stable field,
            # then the field that moved it out of its identity group. The
            # eleventh review put it exactly right: the absence of an eligible
            # axis must not convert an unexplained disappearance into an
            # authorised de-listing.
            #
            # So it does not. A published name that leaves a list is quarantined
            # and named, and a human authorises it. What the identity evidence
            # is still for is telling the operator WHICH of the two this is —
            # a designation that left and took its names with it, or a name
            # removed while everything that identified it stayed behind.
            orphaned = sorted(f for f in forms if f not in new_all)
            if not orphaned:
                continue                      # re-keyed, names intact
            lost[uid] = orphaned
            names_lost += len(orphaned)
            ref = entry_old.get("ref") if isinstance(entry_old, dict) else ""
            fp = entry_old.get("fp") if isinstance(entry_old, dict) else ""
            axes = entry_old.get("axes", ()) if isinstance(entry_old, dict) else ()
            if ((ref and carrier_ref.get(ref))
                    or (fp and carrier_fp.get(fp))
                    or any(carrier_axis.get(a) and axis_freq.get(a, 0) <= FINGERPRINT_SPECIFIC
                           for a in axes)):
                evidenced[uid] = True
            continue
        cur_names = current["names"] if isinstance(current, dict) else current
        missing = sorted(set(forms) - set(cur_names))
        if missing:
            lost[uid] = missing
            names_lost += len(missing)
        if isinstance(entry_old, dict) and isinstance(current, dict):
            was, now = entry_old.get("fp"), current.get("fp")
            if (was and now and was != now
                    and fp_freq.get(was, 0) > FINGERPRINT_SPECIFIC
                    and new_fp_freq.get(now, 0) <= FINGERPRINT_SPECIFIC):
                repositioned[uid] = was
    if repositioned and not lost:
        shown = ", ".join(sorted(repositioned)[:3])
        raise CacheError(
            f"{len(repositioned):,} designation(s) have been moved out of a shared "
            f"identity group without leaving the list — the one change to a designation's "
            f"non-name fields that always precedes a substitution, and never anything "
            f"else. First: {shown}. Quarantined, nothing committed. Set "
            "SANCTIONS_ALLOW_ALIAS_REMOVAL=1 if the publisher really did restate them")
    if not lost:
        return
    shown = "; ".join(f"{uid}: {', '.join(v[:3])}" for uid, v in list(sorted(lost.items()))[:3])
    still_listed = {u for u in lost if u in new}
    vanished = {u for u in lost if u not in new}
    # Both are quarantined. Which one it is decides how long the operator should
    # look before authorising it, so it goes in the sentence rather than being
    # left for them to work out.
    # Three different events, and saying which one it is decides how long the
    # operator should look. Calling them all de-listings was actively misleading:
    # the first live refusal in ordinary use was OFAC editing three alias
    # spellings on designations that were still on the list, and the message told
    # the reader they had been de-listed.
    if still_listed and not vanished:
        why = (f"Every one of those {len(still_listed):,} designation(s) is STILL ON THE "
               "LIST — nothing has been de-listed. The publisher has changed how it "
               "spells them, and anyone searching the old spelling stops finding them. "
               "Check the new spellings cover what the old ones did")
    elif evidenced:
        why = (f"{len(evidenced):,} of them left their identifying detail behind on this "
               "list — the reference, the non-name fields, or a date or identifier that "
               "belongs to a designation — which is what a substitution looks like and "
               "not what a de-listing looks like. Read those before authorising anything")
    elif still_listed:
        why = (f"{len(still_listed):,} of the designation(s) are still on the list and have "
               f"merely lost a spelling; the other {len(vanished):,} have gone from it "
               "entirely, leaving no identifying detail behind, which is what an ordinary "
               "de-listing looks like")
    else:
        why = ("None of them left identifying detail behind, and the designations have gone "
               "from the list entirely, which is what an ordinary de-listing looks like")
    raise CacheError(
        f"{names_lost:,} published name(s) across {len(lost):,} designation(s) have gone "
        f"since the last good refresh — quarantined, nothing committed. First: {shown}. "
        f"{why}. Set SANCTIONS_ALLOW_ALIAS_REMOVAL=1 to accept them")


def parse_list_date(value: str):
    """The publisher's own date as a date, or None where there is none or the
    form is not one this tool knows. UK: 02-Sep-2026. OFSI: 03/06/2026, day
    first. UN, EU and Swiss: ISO 8601, with or without a time."""
    v = (value or "").strip()
    if not v:
        return None
    for fmt in ("%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def chronology(src: "Source", list_date: str, previous: dict | None) -> None:
    """A list dated EARLIER than the last good one is a rollback, not a refresh.

    A server or proxy serving a genuine but older file resets the retrieval
    clock: `status` said fresh, ok, age 0, for an OFSI list dated 01/01/2000
    committed over one dated 03/06/2026. An older list can omit every
    designation made since it was published and then give a clean nil. The
    publisher's date was already read and recorded; it was never compared.
    SANCTIONS_ALLOW_ROLLBACK=1 lets a verified publisher correction through.
    Where the publisher dates nothing (OFAC, Canada) chronology cannot be
    established, and the manifest says so rather than pretending."""
    if os.environ.get("SANCTIONS_ALLOW_ROLLBACK", "").strip() == "1":
        return
    prev = previous or {}
    old_raw = prev.get("list_date") if prev.get("ok") else prev.get("last_good_list_date")
    new, old = parse_list_date(list_date), parse_list_date(old_raw)
    if new and old and new < old:
        raise CacheError(f"the publisher dates this list {list_date!r}, earlier than the "
                         f"{old_raw!r} last fetched — a rollback, quarantined; set "
                         "SANCTIONS_ALLOW_ROLLBACK=1 if the publisher really did this")


def validate(src: "Source", recs: list, previous: dict | None) -> None:
    """Refuse a parse that cannot be a whole list. Raises CacheError."""
    floor = MIN_RECORDS.get(src.id, 100)
    if len(recs) < floor:
        raise CacheError(f"only {len(recs):,} designations parsed, fewer than the "
                         f"{floor:,} this list must hold — treated as a partial download")
    blank = sum(1 for r in recs if not (r.get("name") or "").strip())
    if blank:
        raise CacheError(f"{blank:,} designations parsed with no name — schema has moved")
    if not any(r.get("aliases") for r in recs):
        raise CacheError("no designation carries an alias — alias columns are not being read")
    alias_floor(src, recs, previous)
    before = last_good_count(previous)
    if before:
        if len(recs) < before * (1 - SHRINK_TOLERANCE):
            raise CacheError(
                f"list shrank from {before:,} to {len(recs):,} designations "
                f"(>{int(SHRINK_TOLERANCE*100)}%) — quarantined; set "
                "SANCTIONS_ALLOW_SHRINK=1 if the publisher really did this")


def atomic_write_bytes(dest: Path, write) -> None:
    """Write through a uniquely-named temporary file in the destination
    directory, flush to disk, then rename. A fixed .part path is shared by every
    concurrent process, so two refreshes truncate each other's work."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dest.parent), prefix=f".{dest.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as fh:
            write(fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class _Lock:
    """Inter-process lock around the whole refresh-and-commit, so two refreshes
    cannot interleave a download, a parse and a manifest rewrite."""

    def __init__(self, path: Path):
        self.path = path
        self.fh = None

    # Held once per process. refresh_and_commit takes it around the whole
    # read-modify-write, and refresh() takes it again for a direct caller; the
    # depth count keeps the inner one from releasing the outer one's hold.
    _depth = 0
    _fh = None

    def __enter__(self):
        if _Lock._depth == 0:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _Lock._fh = open(self.path, "w")
            fcntl.flock(_Lock._fh, fcntl.LOCK_EX)
        _Lock._depth += 1
        return self

    def __exit__(self, *exc):
        _Lock._depth -= 1
        if _Lock._depth == 0 and _Lock._fh is not None:
            fcntl.flock(_Lock._fh, fcntl.LOCK_UN)
            _Lock._fh.close()
            _Lock._fh = None
        return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# parsers
# --------------------------------------------------------------------------

def parse_uksl(src: Source) -> tuple[list[dict], dict]:
    path = RAW / src.filename
    preamble = _first_line(path)
    skip = _sniff_header(path, "Name 1")
    groups: dict[str, dict] = {}
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for _ in range(skip):
            fh.readline()
        for row in csv.DictReader(fh):
            uid = _clean(row.get("Unique ID")) or _clean(row.get("OFSI Group ID"))
            if not uid:
                continue
            name = _join_names(row.get("Name 6"), row.get("Name 1"), row.get("Name 2"),
                               row.get("Name 3"), row.get("Name 4"), row.get("Name 5"))
            # Name 6 is the family name; the published display order puts it last
            # for individuals. Keep both readings searchable.
            alt_order = _join_names(row.get("Name 1"), row.get("Name 2"), row.get("Name 3"),
                                    row.get("Name 4"), row.get("Name 5"), row.get("Name 6"))
            g = groups.setdefault(uid, {
                "source": src.id, "uid": uid, "type": "unknown", "name": "",
                "aliases": [], "nonlatin": [], "dob": [], "nationality": [],
                "regime": _clean(row.get("Regime Name")), "measures": _clean(row.get("Sanctions Imposed")),
                "listed_on": _clean(row.get("Date Designated")), "ids": [], "address": "",
                "notes": "", "ref": "", "status": "active",
            })
            primary = _clean(row.get("Name type")).lower().startswith("primary")
            if primary and not g["name"]:
                g["name"] = name
            elif name:
                g["aliases"].append(name)
            if alt_order and alt_order != name:
                g["aliases"].append(alt_order)
            nl = _clean(row.get("Name non-latin script"))
            if nl:
                g["nonlatin"].append(nl)
            dtype = _clean(row.get("Designation Type"))
            if dtype:
                g["type"] = subject_type("uk-sanctions-list", dtype)
            g["dob"].append(_clean(row.get("D.O.B")))
            g["nationality"].append(_clean(row.get("Nationality(/ies)")))
            for k in ("National Identifier number", "Passport number",
                      "Business registration number (s)", "IMO number"):
                v = _clean(row.get(k))
                if v:
                    g["ids"].append(f"{k.split('(')[0].strip()}: {v}")
            if not g["address"]:
                g["address"] = _join_names(row.get("Address Line 1"), row.get("Address Line 2"),
                                           row.get("Address Country"))
            if not g["notes"]:
                g["notes"] = _trunc(row.get("UK Statement of Reasons"))
            if not g["ref"]:
                g["ref"] = _clean(row.get("Unique ID"))
    recs = []
    for g in groups.values():
        if not g["name"] and g["aliases"]:
            g["name"] = g["aliases"].pop(0)
        for k in ("aliases", "nonlatin", "dob", "nationality", "ids"):
            g[k] = _dedupe(g[k])
        g["aliases"] = [a for a in g["aliases"] if a.upper() != g["name"].upper()]
        recs.append(g)
    m = re.search(r"(\d{1,2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4})", preamble)
    return recs, {"list_date": m.group(1) if m else "", "preamble": preamble,
                  "list_date_source": "published in the file"}


def parse_ofsi(src: Source) -> tuple[list[dict], dict]:
    path = RAW / src.filename
    preamble = _first_line(path)
    skip = _sniff_header(path, "Name 1")
    groups: dict[str, dict] = {}
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for _ in range(skip):
            fh.readline()
        for row in csv.DictReader(fh):
            uid = _clean(row.get("Group ID"))
            if not uid:
                continue
            name = _join_names(row.get("Name 6"), row.get("Name 1"), row.get("Name 2"),
                               row.get("Name 3"), row.get("Name 4"), row.get("Name 5"))
            alt_order = _join_names(row.get("Name 1"), row.get("Name 2"), row.get("Name 3"),
                                    row.get("Name 4"), row.get("Name 5"), row.get("Name 6"))
            gtype = _clean(row.get("Group Type")).lower()
            g = groups.setdefault(uid, {
                "source": src.id, "uid": uid,
                "type": subject_type("ofsi", gtype),
                "name": "", "aliases": [], "nonlatin": [], "dob": [], "nationality": [],
                "regime": _clean(row.get("Regime")), "measures": "Asset freeze",
                "listed_on": _clean(row.get("Listed On")), "ids": [], "address": "",
                "notes": "", "ref": "", "status": "active",
            })
            if _clean(row.get("Alias Type")).lower().startswith("primary") and not g["name"]:
                g["name"] = name
            elif name:
                g["aliases"].append(name)
            if alt_order and alt_order != name:
                g["aliases"].append(alt_order)
            # Non-Latin script names live in their own column and must never be
            # concatenated into the Latin name.
            nl = _clean(row.get("Name Non-Latin Script"))
            if nl:
                g["nonlatin"].append(nl)
            g["dob"].append(_clean(row.get("DOB")))
            g["nationality"].append(_clean(row.get("Nationality")))
            for k, label in (("Passport Number", "Passport"),
                             ("National Identification Number", "National ID")):
                v = _clean(row.get(k))
                if v:
                    g["ids"].append(f"{label}: {v}")
            if not g["address"]:
                g["address"] = _join_names(row.get("Address 1"), row.get("Address 2"), row.get("Country"))
            if not g["notes"]:
                g["notes"] = _trunc(row.get("Other Information"))
            if not g["ref"]:
                mref = re.search(r"\(UK Sanctions List Ref\):\s*([A-Z0-9./-]+)", _clean(row.get("Other Information")))
                g["ref"] = mref.group(1) if mref else uid
    recs = []
    for g in groups.values():
        if not g["name"] and g["aliases"]:
            g["name"] = g["aliases"].pop(0)
        for k in ("aliases", "nonlatin", "dob", "nationality", "ids"):
            g[k] = _dedupe(g[k])
        g["aliases"] = [a for a in g["aliases"] if a.upper() != g["name"].upper()]
        recs.append(g)
    m = re.search(r"(\d{2}/\d{2}/\d{4})", preamble)
    return recs, {"list_date": m.group(1) if m else "", "preamble": preamble,
                  "list_date_source": "published in the file"}


# --------------------------------------------------------------------------
# subject type
# --------------------------------------------------------------------------
# Every publisher has its own word for what a designation is about. A ship filed
# as an entity is invisible to a vessel search and reports a clean nil, so these
# tables are exhaustive against the live files and an unrecognised value stops
# the refresh rather than defaulting quietly. Counts are what the published file
# held when the table was last checked; they are a guide to scale, not a test.

class ParseError(Exception):
    """A list could not be parsed into something safe to search."""


SUBJECT_TYPES = ("individual", "entity", "vessel", "aircraft", "unknown")

TYPE_TABLES = {
    # OFSI consolidated list, "Group Type": Individual 13,863 / Entity 5,817 / Ship 81
    "ofsi": {"individual": "individual", "entity": "entity", "ship": "vessel",
             "vessel": "vessel", "aircraft": "aircraft"},
    # UK Sanctions List, "Designation Type": Entity 30,541 / Individual 27,006 / Ship 889
    "uk-sanctions-list": {"individual": "individual", "entity": "entity",
                          "organisation": "entity", "ship": "vessel",
                          "vessel": "vessel", "aircraft": "aircraft"},
    # EU consolidated list, subjectType/@code: person 4,462 / enterprise 1,772
    "eu": {"person": "individual", "enterprise": "entity", "vessel": "vessel",
           "aircraft": "aircraft"},
    # OFAC SDN, sdn_type: -0- 9,922 / individual 7,517 / vessel 1,540 / aircraft 342
    "ofac": {"individual": "individual", "-0-": "entity", "entity": "entity",
             "vessel": "vessel", "aircraft": "aircraft"},
    # Swiss SECO, the element naming the subject
    "swiss": {"individual": "individual", "entity": "entity", "object": "vessel"},
    # OpenSanctions FollowTheMoney schemata
    "opensanctions": {"person": "individual", "company": "entity",
                      "organization": "entity", "legalentity": "entity",
                      "publicbody": "entity", "vessel": "vessel",
                      "airplane": "aircraft", "airplanes": "aircraft",
                      "security": "entity", "cryptowallet": "entity",
                      "address": "entity", "position": "entity"},
}


def subject_type(table_id: str, raw: str) -> str:
    """Map a publisher's own subject word onto ours, or refuse to parse.

    Silently defaulting an unrecognised word to "entity" is how 81 OFSI ships
    became invisible to `--type vessel` while the run still reported itself
    complete. A word this tool has never seen is a parser that has fallen behind
    its publisher, and that must stop the refresh, not the search."""
    key = (raw or "").strip().lower()
    if not key:
        return "unknown"
    table = TYPE_TABLES[table_id]
    if key not in table:
        raise ParseError(
            f"{table_id}: the publisher used the subject type {raw!r}, which this "
            f"parser does not map. Known: {', '.join(sorted(set(table)))}. "
            "Add the mapping before screening against this list — an unmapped type "
            "hides every designation carrying it from a typed search.")
    return table[key]


def _t(el) -> str:
    return _clean(el.text) if el is not None else ""


def parse_un(src: Source) -> tuple[list[dict], dict]:
    root = ET.parse(RAW / src.filename).getroot()
    recs = []
    for group, kind in (("INDIVIDUALS", "individual"), ("ENTITIES", "entity")):
        block = root.find(group)
        if block is None:
            continue
        for e in block:
            names = [_join_names(_t(e.find(f)) for f in ())]  # placeholder replaced below
            primary = " ".join(x for x in (_t(e.find("FIRST_NAME")), _t(e.find("SECOND_NAME")),
                                           _t(e.find("THIRD_NAME")), _t(e.find("FOURTH_NAME"))) if x)
            aliases, nonlatin = [], []
            for al in e.findall(".//INDIVIDUAL_ALIAS") + e.findall(".//ENTITY_ALIAS"):
                a = _t(al.find("ALIAS_NAME"))
                if not a:
                    continue
                (nonlatin if _is_nonlatin(a) else aliases).append(a)
            dobs = []
            for d in e.findall(".//INDIVIDUAL_DATE_OF_BIRTH"):
                dobs.append(_t(d.find("DATE")) or _t(d.find("YEAR")) or
                            f"{_t(d.find('FROM_YEAR'))}-{_t(d.find('TO_YEAR'))}".strip("-"))
            nat = [_t(n) for n in e.findall(".//NATIONALITY/VALUE")]
            ids = []
            for doc in e.findall(".//INDIVIDUAL_DOCUMENT"):
                ids.append(_join_names(_t(doc.find("TYPE_OF_DOCUMENT")), _t(doc.find("NUMBER"))))
            addr = []
            for a in e.findall(".//INDIVIDUAL_ADDRESS") + e.findall(".//ENTITY_ADDRESS"):
                addr.append(_join_names(_t(a.find("STREET")), _t(a.find("CITY")), _t(a.find("COUNTRY"))))
            recs.append({
                "source": src.id, "uid": _t(e.find("DATAID")), "type": kind,
                "name": primary or _t(e.find("NAME_ORIGINAL_SCRIPT")),
                "aliases": _dedupe(aliases), "nonlatin": _dedupe(nonlatin + [_t(e.find("NAME_ORIGINAL_SCRIPT"))]),
                "dob": _dedupe(dobs), "nationality": _dedupe(nat),
                "regime": _t(e.find("UN_LIST_TYPE")), "measures": "UN measures per the listing committee",
                "listed_on": _t(e.find("LISTED_ON")), "ids": _dedupe(ids),
                "address": next((a for a in addr if a), ""),
                "notes": _trunc(_t(e.find("COMMENTS1"))), "ref": _t(e.find("REFERENCE_NUMBER")),
                "status": "active",
            })
    return recs, {"list_date": root.get("dateGenerated", ""),
                  "list_date_source": "published in the file"}


def parse_eu(src: Source) -> tuple[list[dict], dict]:
    root = ET.parse(RAW / src.filename).getroot()
    s = lambda t: t.split("}")[-1]
    recs = []
    for e in root:
        if s(e.tag) != "sanctionEntity":
            continue
        subject = next((c.get("code", "") for c in e if s(c.tag) == "subjectType"), "")
        kind = subject_type("eu", subject)
        names, nonlatin = [], []
        for c in e:
            if s(c.tag) != "nameAlias":
                continue
            whole = _clean(c.get("wholeName")) or _join_names(c.get("firstName"), c.get("middleName"), c.get("lastName"))
            if whole:
                (nonlatin if _is_nonlatin(whole) else names).append(whole)
        dob, nat, ids, addr, regime, listed = [], [], [], "", "", ""
        for c in e:
            tag = s(c.tag)
            if tag == "birthdate":
                dob.append(_clean(c.get("birthdate")) or _clean(c.get("year")))
            elif tag == "citizenship":
                nat.append(_clean(c.get("countryDescription")))
            elif tag == "identification":
                ids.append(_join_names(c.get("identificationTypeDescription"), c.get("number")))
            elif tag == "address" and not addr:
                addr = _join_names(c.get("street"), c.get("city"), c.get("countryDescription"))
            elif tag == "regulation":
                regime = regime or _clean(c.get("programme"))
                listed = listed or _clean(c.get("publicationDate"))
        names = _dedupe(names)
        recs.append({
            "source": src.id, "uid": _clean(e.get("logicalId")), "type": kind,
            "name": names[0] if names else "", "aliases": names[1:], "nonlatin": _dedupe(nonlatin),
            "dob": _dedupe(dob), "nationality": _dedupe(nat), "regime": regime,
            "measures": "Asset freeze / economic resources", "listed_on": listed,
            "ids": _dedupe(ids), "address": addr,
            "notes": _trunc(next((_clean(c.text) for c in e if s(c.tag) == "remark"), "")),
            "ref": _clean(e.get("euReferenceNumber")), "status": "active",
        })
    return recs, {"list_date": root.get("generationDate", ""),
                  "list_date_source": "published in the file"}


OFAC_PRIM = ["ent_num", "name", "sdn_type", "program", "title", "call_sign",
             "vess_type", "tonnage", "grt", "vess_flag", "vess_owner", "remarks"]
OFAC_ALT = ["ent_num", "alt_num", "alt_type", "alt_name", "alt_remarks"]


def parse_ofac(src: Source) -> tuple[list[dict], dict]:
    alt: dict[str, list[str]] = {}
    alt_rows = 0
    alt_path = RAW / src.aux.get("alt_filename", "")
    if alt_path.name and alt_path.exists():
        with open(alt_path, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for row in csv.reader(fh):
                if len(row) < 4:
                    continue
                alt_rows += 1
                alt.setdefault(_clean(row[0]), []).append(_clean(row[3]))
    recs = []
    path = RAW / src.filename
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 12 or not _clean(row[0]):
                continue
            r = dict(zip(OFAC_PRIM, [_clean(c) for c in row]))
            kind = subject_type("ofac", r["sdn_type"]) if r["sdn_type"].strip() else "entity"
            names = alt.get(r["ent_num"], [])
            dob = re.findall(r"DOB\s+([0-9A-Za-z ]{4,12})", r["remarks"])
            nat = re.findall(r"nationality\s+([A-Za-z ]+?);", r["remarks"])
            ids = re.findall(r"((?:Passport|National ID No\.|Cedula No\.|Tax ID No\.)\s+[^;]+)", r["remarks"])
            recs.append({
                "source": src.id, "uid": r["ent_num"], "type": kind, "name": r["name"],
                "aliases": _dedupe([n for n in names if not _is_nonlatin(n)]),
                "nonlatin": _dedupe([n for n in names if _is_nonlatin(n)]),
                "dob": _dedupe(dob), "nationality": _dedupe(nat), "regime": r["program"],
                "measures": "Blocking (SDN)" if src.id == "ofac-sdn" else "Non-SDN programme restrictions",
                "listed_on": "", "ids": _dedupe(ids), "address": "",
                "notes": _trunc(r["remarks"]), "ref": r["ent_num"], "status": "active",
            })
    # OFAC does not stamp a publication date inside these exports. The time this
    # machine downloaded the file is not the date the list was published. The
    # alias file is measured in rows and emitted aliases, so a refresh that kept
    # one alias per designation and lost the rest is a refresh that failed.
    return recs, {"list_date": "", "list_date_source": "not published in this file",
                  "alias_rows": alt_rows,
                  "alias_total": sum(len(r["aliases"]) + len(r["nonlatin"]) for r in recs)}


def parse_canada(src: Source) -> tuple[list[dict], dict]:
    root = ET.parse(RAW / src.filename).getroot()
    s = lambda t: t.split("}")[-1]
    recs = []
    for i, rec in enumerate(root):
        f = {s(c.tag).split("-")[0]: _clean(c.text) for c in rec}
        entity = f.get("EntityOrShip", "")
        name = entity or _join_names(f.get("GivenName"), f.get("LastName"))
        if not name:
            continue
        # 731 rows carry an IMO number. Typing them as entities hid every ship
        # from a vessel search, threw the IMO away, and filed the build year as a
        # date of birth.
        imo = f.get("ShipIMONumber", "")
        ship_type = f.get("TitleOrShipType", "")
        vessel = bool(imo)
        kind = "vessel" if vessel else ("entity" if entity else "individual")
        built_or_born = f.get("DateOfBirthOrShipBuildDate", "")
        aliases = [a.strip() for a in re.split(r"[;,]", f.get("Aliases", "")) if a.strip()]
        if not entity:
            reversed_name = _join_names(f.get("LastName"), f.get("GivenName"))
            if reversed_name and reversed_name != name:
                aliases.append(reversed_name)
        notes = f"Schedule {f.get('Schedule','')} item {f.get('Item','')}"
        if vessel:
            notes += f"; ship type {ship_type}" if ship_type else ""
            notes += f"; built {built_or_born}" if built_or_born else ""
        elif ship_type:
            notes += f"; {ship_type}"
        recs.append({
            "source": src.id,
            # NOT the row index. Country-Schedule-Item is unique across this
            # file, and including the enumeration position meant that swapping
            # two otherwise untouched publisher rows changed both designations'
            # identifiers — which, to any guard keyed on the identifier, reads
            # as two designations leaving the list and two arriving.
            "uid": f"{f.get('Country','')}-{f.get('Schedule','')}-{f.get('Item','')}",
            "type": kind, "name": name,
            "aliases": _dedupe([a for a in aliases if not _is_nonlatin(a)]),
            "nonlatin": _dedupe([a for a in aliases if _is_nonlatin(a)]),
            "dob": [] if vessel else _dedupe([built_or_born]),
            "nationality": [], "regime": f.get("Country", ""),
            "measures": "Dealings prohibition (SEMA / JVCFOA)",
            "listed_on": f.get("DateOfListing", ""),
            "ids": _dedupe([f"IMO: {imo}"] if imo else []), "address": "",
            "notes": notes,
            "ref": f"{f.get('Schedule','')}/{f.get('Item','')}", "status": "active",
        })
    # This file carries no generation date. The download time is not the date the
    # list was published, and reporting it as such is a false provenance claim.
    return recs, {"list_date": "", "list_date_source": "not published in this file"}


def parse_swiss(src: Source) -> tuple[list[dict], dict]:
    root = ET.parse(RAW / src.filename).getroot()
    s = lambda t: t.split("}")[-1]
    # A target points at a <sanctions-set> by ssid, not at a <sanctions-program>.
    # Keyed on the programme's ssid, the lookup never matched and all 8,667
    # records carried an empty regime. Prefer the English text where the set is
    # published in several languages.
    programmes = {}
    for c in root.iter():
        tag = s(c.tag)
        if tag == "sanctions-set":
            ssid = c.get("ssid", "")
            if not ssid:
                continue
            text = _clean(c.text) or next((_clean(x.text) for x in c), "")
            if text and (ssid not in programmes or c.get("lang") == "eng"):
                programmes[ssid] = _trunc(text)
        elif tag == "sanctions-program":
            label = next((_clean(x.text) for x in c if s(x.tag) == "program-name"), "")
            programmes.setdefault(c.get("ssid", ""), label or _clean(c.get("ssid")))

    def whole_names(name_el) -> list[str]:
        """Rebuild complete names, one per language and script.

        Swiss publishes a name as ordered parts, each carrying its own spelling
        variants by language and script. Emitting those variants as standalone
        aliases produced "Petrov", "Oleg" and "Vladimirovich" as three separate
        names and lost every published transliteration of the full name."""
        parts = []
        for np in name_el:
            if s(np.tag) != "name-part":
                continue
            base = next((_clean(v.text) for v in np if s(v.tag) == "value"), "")
            # A part can carry SEVERAL variants under the same language and
            # script: 3,669 of the 70,283 name-parts in the live file do.
            # Keyed by (lang, script) alone, each overwrote the last and the
            # published spelling never reached the record.
            variants = {}
            for sv in np:
                if s(sv.tag) == "spelling-variant" and _clean(sv.text):
                    variants.setdefault((sv.get("lang", ""), sv.get("script", "")),
                                        []).append(_clean(sv.text))
            try:
                order = int(np.get("order", "0"))
            except ValueError:
                order = 0
            parts.append((order, base, variants))
        if not parts:
            return []
        parts.sort(key=lambda x: x[0])
        out = [" ".join(b for _, b, _ in parts if b)]
        keys = {k for _, _, v in parts for k in v}
        for key in keys:
            # Coordinate the nth variant of each part with the nth of the others,
            # then fall back to the part's own last variant, then to its base.
            depth = max((len(v.get(key) or ()) for _, _, v in parts), default=0)
            for i in range(depth):
                pieces = []
                for _, b, v in parts:
                    got = v.get(key) or []
                    pieces.append(got[i] if i < len(got) else (got[-1] if got else b))
                built = " ".join(x for x in pieces if x)
                if built:
                    out.append(built)
        return _dedupe(out)

    recs = []
    for tgt in root:
        if s(tgt.tag) != "target":
            continue
        mods = [m.get("modification-type", "") for m in tgt if s(m.tag) == "modification"]
        status = "delisted" if "de-listed" in mods else "active"
        # The listing date is on the <modification modification-type="listed">
        # where the file gives one; otherwise the earliest date recorded against
        # any modification. It was never read at all, so every record said the
        # publisher had published no date.
        dates = []
        listed_on = delisted_on = ""
        for m in tgt:
            if s(m.tag) != "modification":
                continue
            when = (m.get("enactment-date") or m.get("publication-date")
                    or m.get("effective-date") or "")
            if not when:
                continue
            dates.append(when)
            if m.get("modification-type") == "listed" and not listed_on:
                listed_on = when
            if m.get("modification-type") == "de-listed":
                delisted_on = when      # the date the publisher took it off
        if not listed_on and dates:
            listed_on = min(dates)
        body = next((c for c in tgt if s(c.tag) in ("individual", "entity", "object")), None)
        if body is None:
            continue
        kind = subject_type("swiss", s(body.tag))
        names, nonlatin, dob, ids, addr, notes = [], [], [], [], "", ""
        nat = []
        for ident in body:
            if s(ident.tag) == "identity":
                for nm in ident:
                    if s(nm.tag) == "name":
                        for whole in whole_names(nm):
                            (nonlatin if _is_nonlatin(whole) else names).append(whole)
                for dm in ident:
                    tag = s(dm.tag)
                    if tag == "day-month-year":
                        y, mo, d = dm.get("year", ""), dm.get("month", ""), dm.get("day", "")
                        dob.append(f"{y}-{int(mo):02d}-{int(d):02d}" if y and mo and d else y)
                    elif tag == "address" and not addr:
                        addr = " ".join(_clean(x.text) for x in dm if _clean(x.text))
                    elif tag in ("identification-document", "identification",
                                 "bic-number"):
                        # The live schema is <identification-document
                        # document-type="id-card"><number>…</number></…>. Looking
                        # for "identification" alone left 0 of 8,667 records with
                        # any identifier at all.
                        num = (_clean(dm.get("number"))
                               or next((_clean(c.text) for c in dm
                                        if s(c.tag) == "number"), "")
                               or _clean(dm.text))
                        if num:
                            label = (dm.get("document-type")
                                     or dm.get("identification-type") or tag)
                            issuer = next((_clean(c.text) for c in dm
                                           if s(c.tag) == "issuer"), "")
                            ids.append(f"{label}: {num}" + (f" ({issuer})" if issuer else ""))
                    elif tag == "nationality":
                        for c in dm:
                            if s(c.tag) == "country":
                                val = _clean(c.text) or _clean(c.get("iso-code"))
                                if val:
                                    nat.append(val)
            elif s(ident.tag) == "justification":
                notes = notes or _trunc(_clean(ident.text))
        names = _dedupe(names)
        recs.append({
            "source": src.id, "uid": _clean(tgt.get("ssid")), "type": kind,
            "name": names[0] if names else "", "aliases": names[1:],
            "nonlatin": _dedupe(nonlatin), "dob": _dedupe(dob),
            "nationality": _dedupe(nat),
            "regime": programmes.get(next((_clean(c.text) for c in tgt
                                           if s(c.tag) == "sanctions-set-id"), ""), ""),
            "measures": "Swiss ordinance measures", "listed_on": listed_on,
            "ids": _dedupe(ids),
            "address": addr, "notes": notes, "ref": _clean(tgt.get("ssid")), "status": status,
            "delisted_on": delisted_on,
        })
    return recs, {"list_date": root.get("date", ""), "list_date_source": "published in the file"}


def parse_opensanctions(src: Source) -> tuple[list[dict], dict]:
    path = RAW / src.filename
    recs = []
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            name = _clean(row.get("name"))
            if not name:
                continue
            aliases = [a for a in re.split(r";", _clean(row.get("aliases", ""))) if a.strip()]
            kind = subject_type("opensanctions", _clean(row.get("schema")))
            recs.append({
                "source": src.id, "uid": _clean(row.get("id")), "type": kind, "name": name,
                "aliases": _dedupe([a for a in aliases if not _is_nonlatin(a)]),
                "nonlatin": _dedupe([a for a in aliases if _is_nonlatin(a)]),
                "dob": _dedupe(re.split(r";", _clean(row.get("birth_date", "")))),
                "nationality": _dedupe(re.split(r";", _clean(row.get("countries", "")))),
                "regime": _trunc(_clean(row.get("sanctions", "")), 200) or _clean(row.get("dataset")),
                "measures": "See listing source" if "sanctions" in src.id else "PEP status (EDD trigger, not a prohibition)",
                "listed_on": _clean(row.get("first_seen", ""))[:10],
                "ids": _dedupe(re.split(r";", _clean(row.get("identifiers", "")))),
                "address": _trunc(_clean(row.get("addresses", "")), 160),
                "notes": "", "ref": _clean(row.get("id")), "status": "active",
            })
    # OFAC does not stamp a publication date inside these exports. The time this
    # machine downloaded the file is not the date the list was published.
    return recs, {"list_date": "", "list_date_source": "not published in this file"}


PARSERS: dict[str, Callable[[Source], tuple[list[dict], dict]]] = {
    "parse_uksl": parse_uksl, "parse_ofsi": parse_ofsi, "parse_un": parse_un,
    "parse_eu": parse_eu, "parse_ofac": parse_ofac, "parse_canada": parse_canada,
    "parse_swiss": parse_swiss, "parse_opensanctions": parse_opensanctions,
}


# --------------------------------------------------------------------------
# refresh / load
# --------------------------------------------------------------------------

class CacheError(Exception):
    """The cached copy of a list cannot be trusted, so it was not searched."""


def meta_path() -> Path:
    """Where the manifest is, resolved at CALL time.

    META is bound at import from DATA. Redirect DATA — which every isolated
    test does, and which is the only way to exercise refresh() without touching
    the real cache — and META goes on pointing at the live manifest, so an
    isolated refresh writes its own meta.json and then reads the real one. The
    per-UID ledger had exactly this bug and it was fixed there; the manifest
    kept it. Where META has been redirected deliberately, that wins."""
    return META if META.parent == DATA else DATA / "meta.json"


def watermark_path() -> Path:
    return DATA / ".manifest-generation"


def load_meta() -> dict:
    """A damaged meta.json means nothing is known about the cache, which must
    read as 'nothing was searched' rather than as an empty result set.

    A ROLLED-BACK meta.json means the same. Every check in this file verifies one
    artefact against what the manifest records, and nothing verified the manifest:
    replacing it wholesale with an older, internally consistent generation — whose
    digests genuinely match an older ledger and an older cache — moved a published
    name from `1 hit, exit 2` to `0 hits, exit 0` with every individual binding
    still valid. A monotonic counter is kept beside it, and a manifest older than
    the highest this machine has committed is not read.

    Restoring a whole cache directory from a backup moves the counter with it,
    which is a deliberate restore rather than a substitution; for dated feeds the
    chronology quarantine is the check that then applies."""
    path = meta_path()
    if not path.exists():
        return {}
    try:
        meta = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    if not isinstance(meta, dict):
        return {}
    try:
        high = int(watermark_path().read_text().strip())
    except (OSError, ValueError):
        high = 0
    if int(meta.get("generation") or 0) < high:
        return {}
    return meta


def save_meta(meta: dict) -> None:
    """Written through a uniquely-named temporary file and renamed, so neither an
    interrupted write nor a concurrent one can leave half a document."""
    try:
        high = int(watermark_path().read_text().strip())
    except (OSError, ValueError):
        high = 0
    gen = max(high, int(meta.get("generation") or 0)) + 1
    meta = dict(meta, generation=gen)
    payload = json.dumps(meta, indent=2, sort_keys=True).encode("utf-8")
    atomic_write_bytes(meta_path(), lambda fh: fh.write(payload))
    # After the manifest, so a crash between the two leaves the watermark BEHIND
    # the manifest — which reads as valid — rather than ahead of it, which would
    # refuse a manifest this machine had just legitimately written.
    atomic_write_bytes(watermark_path(), lambda fh: fh.write(str(gen).encode()))


def licence_ok(src: Source) -> tuple[bool, str]:
    if "CC BY-NC" not in src.licence:
        return True, ""
    ack = os.environ.get("SANCTIONS_OPENSANCTIONS_LICENCE", "").strip()
    if not ack:
        return False, ("OpenSanctions data is CC BY-NC 4.0. Set "
                       "SANCTIONS_OPENSANCTIONS_LICENCE=noncommercial, or to your "
                       "commercial licence reference, before refreshing it. "
                       "Screening fee-earning client work is commercial use.")
    return True, ack


def refresh(src: Source, meta: dict) -> dict:
    """Fetch, parse, validate and commit one list.

    Nothing is committed that has not been validated: a download truncated at a
    line boundary parses perfectly well, and its own record count would then be
    recorded as the count to expect — a check that verifies nothing. The whole
    sequence is taken under a lock so two refreshes cannot interleave."""
    started = time.time()
    entry = {"source": src.id, "url": src.url, "licence": src.licence}
    ok, note = licence_ok(src)
    if not ok:
        entry.update({"ok": False, "error": note, "records": 0})
        meta[src.id] = entry
        return entry
    if note:
        entry["licence_ack"] = note
    with _Lock(DATA / ".refresh.lock"):
        try:
            sizes = download(src)
            recs, extra = PARSERS[src.parser](src)
            # Exactly "1". Any-non-empty meant that SANCTIONS_ALLOW_SHRINK=0, or
            # =no, switched the quarantine off.
            allow = os.environ.get("SANCTIONS_ALLOW_SHRINK", "").strip() == "1"
            prior = meta.get(src.id)
            # Two baselines, deliberately. The shrink override stands the COUNT
            # rules down; it has never meant "and a published name may vanish".
            # One variable served both and so it did mean that.
            previous = None if allow else prior
            validate(src, recs, previous)
            alias_delta(src, extra, previous)
            alias_removals(src, recs, prior, entry)
            chronology(src, extra.get("list_date", ""), meta.get(src.id))
            out = NORM / f"{src.id}.jsonl.gz"
            candidate = NORM / f".{src.id}.jsonl.gz.candidate"

            def _write(fh):
                with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
                    for r in recs:
                        gz.write((json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8"))

            atomic_write_bytes(candidate, _write)
            # Read the CANDIDATE back through the reader screening uses, before
            # it replaces the last good file and before the manifest says the
            # list is good. The validator had passed 5,690 Canadian designations
            # and the writer had written them; the reader could not read the
            # file, and nothing between the two had asked it to try. The first
            # repair read back the INSTALLED file — after it had replaced the
            # last good one, so a failed readback left no good copy on disk.
            # What the manifest promises is what read_source can deliver, and
            # the old file stays until the new one has proved it.
            back = _load_norm(candidate, {"records": len(recs), "norm_sha256": sha256(candidate),
                                          "parser_version": PARSER_VERSION})
            if len(back) != len(recs):
                raise CacheError(f"the list was written with {len(recs):,} designations "
                                 f"and reads back with {len(back):,} — not committed")
            # The install is not the last thing that can fail, and until now
            # it was treated as though it were: a ledger write that raised
            # AFTER os.replace left the new file installed, the manifest not
            # written, the refresh reporting failure — and the last good file
            # gone. A hard link costs nothing and holds the old bytes until
            # everything that can still fail has not.
            backup = NORM / f".{src.id}.jsonl.gz.lastgood"
            backup.unlink(missing_ok=True)
            if out.exists():
                os.link(out, backup)
            try:
                os.replace(candidate, out)
                # The ledger is written only once the list it describes is the
                # list on disk. Written before, a refresh that failed its
                # readback would leave tomorrow's comparison baselined on names
                # this machine never committed — and the loss it is there to
                # catch would be baked into the baseline as normal.
                entry.update(write_alias_inventory(src.id, alias_inventory(recs)))
                entry.update({
                    "ok": True, "records": len(recs), "bytes": sum(sizes.values()),
                    "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "list_date": extra.get("list_date", ""),
                    "list_date_source": extra.get("list_date_source", "unknown"),
                    "sha256": sha256(RAW / src.filename)[:16],
                    "raw_files": raw_fingerprints(src),
                    "norm_sha256": sha256(out),
                    "parser_version": PARSER_VERSION,
                    "engine_version": ENGINE_VERSION,
                    "code": dict(code_fingerprint()),
                    "seconds": round(time.time() - started, 1), "error": "",
                    "last_good_records": len(recs),
                    "aliased": sum(1 for r in recs if r.get("aliases")),
                    "last_good_aliased": sum(1 for r in recs if r.get("aliases")),
                    "alias_rows": extra.get("alias_rows"), "alias_total": extra.get("alias_total"),
                    "last_good_alias_rows": extra.get("alias_rows"),
                    "last_good_alias_total": extra.get("alias_total"),
                    "last_good_list_date": extra.get("list_date", ""),
                    "chronology": ("publisher-dated" if extra.get("list_date")
                                   else "not established — the publisher does not date this file"),
                })
            except BaseException:
                # EVERYTHING after the install, not merely the ledger write. The
                # eighth review raised inside raw_fingerprints() — which sits in
                # the entry it builds after the protected region ended — and the
                # backup had already been unlinked in `finally`, so the new file
                # stayed installed on a refresh that reported failure and the
                # retry then refused for good.
                if backup.exists():
                    os.replace(backup, out)
                raise
            finally:
                backup.unlink(missing_ok=True)
        except Exception as exc:   # a failed source must never read as "no hits"
            prev = meta.get(src.id) or {}
            (NORM / f".{src.id}.jsonl.gz.candidate").unlink(missing_ok=True)
            # The last good FILE is still on disk, and these are the fields that
            # describe it. Dropping them left the cache on disk with nothing to
            # verify it against, so the next refresh could not rebuild a ledger
            # from it and refused — one failed refresh and the source could never
            # refresh again without the override. `ok: False` is what stops the
            # list being searched; it is not a reason to forget what the file is.
            for carry in ("norm_sha256", "parser_version", "engine_version", "code",
                          "inventory_sha256", "inventory_uids", "inventory_version"):
                if prev.get(carry) is not None:
                    entry[carry] = prev[carry]
            entry.update({"ok": False, "records": 0,
                          "error": f"{type(exc).__name__}: {exc}",
                          "last_good_records": last_good_count(prev),
                          "last_good_aliased": (prev.get("aliased")
                                                or prev.get("last_good_aliased") or 0),
                          "last_good_alias_rows": _last_good(prev, "alias_rows"),
                          "last_good_alias_total": _last_good(prev, "alias_total"),
                          "last_good_list_date": ((prev.get("list_date") if prev.get("ok")
                                                   else prev.get("last_good_list_date")) or ""),
                          "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        meta[src.id] = entry
        return entry


def refresh_and_commit(src: "Source") -> dict:
    """Refresh one list and commit the manifest, all under one lock.

    The manifest is re-read inside the lock and written before it is released.
    Refreshing under the lock but committing outside it lets two processes each
    load the same old manifest and then write their own whole snapshot over the
    other's — restoring stale metadata over a list that has just been rewritten,
    which the next screen rejects as a digest mismatch."""
    with _Lock(DATA / ".refresh.lock"):
        meta = load_meta()
        entry = refresh(src, meta)
        save_meta(meta)
        return entry


def load_records(source_id: str):
    """Stream a parsed list. Tolerant, for exploratory use — screening uses
    read_source, which validates."""
    path = NORM / f"{source_id}.jsonl.gz"
    if not path.exists():
        return
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def _freeze(rec: dict):
    """A read-only view of one designation. Built once per list per process, on
    the read that also verifies the digest, so it costs nothing per query."""
    return MappingProxyType({k: (tuple(v) if isinstance(v, list) else v)
                             for k, v in rec.items()})


_CACHE: dict = {}


def read_source(source_id: str, entry: dict | None = None, use_cache: bool = True) -> tuple:
    """Read a parsed list in full, or raise CacheError.

    The claim "this list was searched" is earned here and nowhere else. A file
    that is missing, unreadable, truncated, or shorter than the count recorded at
    refresh is a failed read, not an empty one — a screening record that reported
    a clean nil return against a list it never actually read would be worse than
    no screening at all."""
    entry = entry or {}
    expected = entry.get("records")
    path = NORM / f"{source_id}.jsonl.gz"
    if not path.exists():
        raise CacheError("parsed list missing from the cache — refresh it")
    if entry.get("parser_version") != PARSER_VERSION:
        raise CacheError(f"parsed by version {entry.get('parser_version')!r}, this is "
                         f"version {PARSER_VERSION} — refresh it")
    if entry.get("engine_version") != ENGINE_VERSION:
        # The gap the installed copy walked through. A four-round-stale build
        # shared this cache at the same PARSER_VERSION, because the parser was
        # all PARSER_VERSION had ever spoken for, and reported six of six lists
        # searched and no candidate on names that were on them.
        raise CacheError(f"written by engine generation {entry.get('engine_version')!r}, this "
                         f"is generation {ENGINE_VERSION} — refresh it")
    # Integrity is verified in full whenever the data is loaded. Within one
    # process the verified copy is reused while the file on disk is unchanged,
    # which is what keeps a batch run from re-reading and re-digesting every list
    # for every subject. Any change to the file forces a fresh read and a fresh
    # verification.
    try:
        st = path.stat()
    except OSError as exc:
        raise CacheError(f"parsed list unreadable ({type(exc).__name__})") from exc
    # The recorded count is part of the key, so a manifest edited after the cache
    # was primed cannot be served from it.
    fingerprint = (source_id, st.st_mtime_ns, st.st_size,
                   entry.get("norm_sha256"), expected)
    if use_cache and fingerprint in _CACHE:
        cached = _CACHE[fingerprint]
        # Re-counted on every cached return. What is handed out is immutable, but
        # a caller that has found some other way to shorten it must not then be
        # told the list was searched in full.
        if expected is not None and len(cached) != expected:
            del _CACHE[fingerprint]
            raise CacheError(f"the verified copy of this list no longer holds the "
                             f"{expected:,} designations it was verified with "
                             f"({len(cached):,} now) — it was altered in memory")
        return cached
    out = _load_norm(path, entry)
    if use_cache:
        # Keyed on file identity, so a refreshed list supersedes its own entry
        # rather than being served stale. All lists stay cached: a batch run
        # would otherwise re-read and re-index every list for every subject.
        for stale in [k for k in _CACHE if k[0] == source_id]:
            del _CACHE[stale]
        _CACHE[fingerprint] = out
    return out


def _load_norm(path: Path, entry: dict) -> tuple:
    """Read one parsed list from PATH and verify it against ENTRY — digest,
    then parse, then count — and hand it out frozen.

    read_source() calls this for the installed file; refresh() calls it for
    the candidate file BEFORE the candidate is installed, so the reader that
    screening will use is the reader that approves the file."""
    expected = entry.get("records")
    # Read once, then digest and parse the SAME bytes. Digesting the file and
    # then re-opening it leaves a window in which a concurrent writer can
    # substitute what actually gets parsed.
    try:
        blob = path.read_bytes()
    except OSError as exc:
        raise CacheError(f"parsed list unreadable ({type(exc).__name__})") from exc
    digest = hashlib.sha256(blob).hexdigest()
    if entry.get("norm_sha256") and digest != entry["norm_sha256"]:
        raise CacheError("parsed list does not match the digest recorded when it was "
                         "fetched — it has been altered or replaced; refresh it")
    if not entry.get("norm_sha256"):
        raise CacheError("no digest recorded for this list — refresh it")
    # One record per "\n", and ONLY "\n". str.splitlines() also breaks on U+2028,
    # U+2029, NEL, VT, FF and FS/GS/RS, which json.dumps(ensure_ascii=False) writes
    # raw; one Canadian designation carries a U+2028, so the reader split that
    # record in two and refused the whole list as damaged — NOT SEARCHED on every
    # Canadian screen since the fetch, and invisible on `status` because the list
    # is not a default. The writer's line ending is the only line ending.
    recs = []
    try:
        for line in gzip.decompress(blob).decode("utf-8").split("\n"):
            if line.strip():
                recs.append(json.loads(line))
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error,
            json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CacheError(f"parsed list damaged ({type(exc).__name__}) — refresh it") from exc
    if expected is not None and len(recs) != expected:
        raise CacheError(f"parsed list incomplete: {len(recs):,} of {expected:,} "
                         "designations readable — refresh it")
    # Handed out frozen, all the way down. A tuple protects only its own slots:
    # the dictionaries inside it stayed mutable, so clearing the record for
    # AN SAN 1 left the tuple its recorded length of 5,135 and the exact vessel
    # query then returned no hits, searched, complete, exit 0. Each record
    # becomes a read-only mapping and each of its lists a tuple.
    return tuple(_freeze(r) for r in recs)
