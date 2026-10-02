#!/usr/bin/env python3
"""
Name matching. Standard library only — no third-party dependency, so the whole
of what runs can be read here.

Three ideas do the work:

1. **Per-token Jaro-Winkler**, not whole-string similarity, because names arrive
   reordered, with patronymics, and with parts missing. Coverage is measured in
   both directions: how much of the query the listing accounts for, and how much
   of the listing the query accounts for.

2. **First-and-last anchoring.** Where the first and last parts of the query both
   match strongly, the parts in between are discounted — a client who gives a
   patronymic the list does not hold is still the same person. Without this,
   "Ivan Sergeyevich Petrov" fails to find the listing for "Ivan Petrov".

3. **Asymmetry damping.** A listing holding the bare alias "John" would otherwise
   score 100 against "John Smith", because everything the listing knows is
   matched. Where the listing is shorter than the query and the ends are not
   anchored, its coverage is damped by how much of the query it accounts for.

The prefilter is a character-bigram mask per designation. It is a speed
optimisation only, and `tests/benchmark.py --no-prefilter` re-measures whether it
costs any recall. See PREFILTER_FRACTION for the measurement it is set from.
"""

from __future__ import annotations

import functools
import math
import re
import unicodedata

# --------------------------------------------------------------- constants

# Personal titles, stripped from people only. "LADY" is a courtesy title in
# front of a person and the first word of the designated tanker LADY R
# (UK RUS2185, OFAC 37095); stripping it from every record type left "R", which
# is capped as a bare initial, so an exact designation on two lists returned a
# clean nil and exit 0.
TITLES = {"MR", "MRS", "MS", "MISS", "DR", "PROF", "SIR", "LORD", "LADY", "HON",
          "REV", "SHEIKH", "SHAYKH", "HAJI", "COL", "GEN", "CAPT", "LT", "MAJ",
          "BRIG", "ADM", "JUDGE", "MAJOR"}
ARTICLES = {"THE"}   # an article, not a title: dropped whatever is designated
CORP = {"LTD", "LIMITED", "LLC", "LLP", "PLC", "INC", "CORP", "CORPORATION",
        "CO", "COMPANY", "GMBH", "AG", "SA", "SAS", "SRL", "SPA", "BV", "NV",
        "OOO", "OAO", "PAO", "ZAO", "PJSC", "JSC", "OJSC", "AB", "OY", "SP",
        "ZOO", "SL", "LDA", "PTE", "PTY", "KFT", "DOO", "AD", "EOOD", "OOD",
        "SARL", "TOO", "FZE", "FZCO", "GROUP", "HOLDING", "HOLDINGS"}

INITIAL_CREDIT = 88.0   # an initial corroborates a name; it never proves one
STRONG = 88.0           # where two full tokens count as the same name
MIDDLE_WEIGHT = 0.35    # weight of middle names once the ends are anchored
UNCORROBORATED_CAP = 70.0   # ceiling where nothing but initials matched
RUN_TOGETHER_RATIO = 0.8    # how close in length two strings must be to be the
                            # same name with its spaces removed

# Cyrillic and Greek letters drawn like Latin ones. Published lists mix them into
# otherwise-Latin names — "ROMASHKІN" on the EU list carries a Cyrillic І — and
# stripping them instead of folding them breaks the surname in two.
HOMOGLYPHS = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "У": "Y", "Х": "X", "І": "I", "Ѕ": "S", "Ј": "J", "Ї": "I",
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "о": "o", "р": "p", "с": "c",
    "т": "t", "у": "y", "х": "x", "і": "i", "ѕ": "s", "ј": "j", "ї": "i",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
})

MAX_NAME_CHARS = 1000
"""Longest input considered. The longest name published on any of these lists is
about 140 characters."""

MAX_TOKENS = 40
"""Most name parts considered. The longest published name has 34 parts (a
Portuguese research institute on the EU list), so this cannot truncate a real
one. Without a cap, a 5,000-character input scores 700 parts against every
designation on every list and the run never returns."""

_NONALNUM = re.compile(r"[^A-Z0-9 ]+")
_WS = re.compile(r"\s+")

# Control characters, terminal escape sequences and bidi formatting. A
# designation is a string somebody else chose. On the way INTO the index, an
# ESC-wrapped "LADY R" was indexed as the parts 32MLADY, 0M and R: the
# sequence's own digits and letters became searchable name and the real one
# did not. On the way OUT, to the terminal a fee earner reads, the same bytes
# recolour a line, move the cursor back over a candidate, or rewrite REFUSED as
# clean after it was printed. Stripped in both directions, and consumed WHOLE:
# an 8-bit CSI (0x9B) whose introducer alone was removed left "31mLADY0m R",
# which scores 70 against the name it was hiding. Every bidi format control
# goes — overrides, embeddings, isolates and marks (U+061C, U+200E-F,
# U+202A-E, U+2066-9): a terminal honours all of them, and none is a letter.
# The UK, OFSI and EU lists do carry embeddings around Arabic script; the
# Arabic survives, the formatting does not, and normalise() never kept it.
# Whitespace (\t \n \v \f \r) stays: both consumers fold it to a space.
CONTROL = re.compile(
    r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?"           # OSC ... BEL/ST: titles, hyperlinks
    r"|\x9d[^\x07\x9c\x1b]*(?:\x07|\x9c|\x1b\\)?"   # 8-bit OSC
    r"|\x1b\[[0-?]*[ -/]*[@-~]"                     # CSI: colour, cursor, erase
    r"|\x9b[0-?]*[ -/]*[@-~]"                       # 8-bit CSI, parameters included
    r"|\x1b[@-Z\\-_]"                               # any other two-byte escape
    r"|[\x00-\x08\x0e-\x1f\x7f-\x9f"                # C0, DEL, C1
    r"\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]"  # every bidi format control
)


def strip_control(s: str) -> str:
    """Remove control characters, escape sequences and bidi overrides."""
    return CONTROL.sub("", s or "")


def normalise(name: str) -> str:
    s = unicodedata.normalize("NFKD", strip_control((name or "")[:MAX_NAME_CHARS]))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.translate(LATIN_FOLD).translate(HOMOGLYPHS).upper().replace("&", " AND ")
    return _WS.sub(" ", _NONALNUM.sub(" ", s)).strip()


def tokens_from_normalised(normalised: str, kind: str = "individual") -> list[str]:
    drop = ARTICLES | (TITLES if kind == "individual" else CORP)
    plain = normalised.split()
    out = [t for t in plain if t not in drop] or plain
    # A repeated name part carries no further information, and deduplicating is
    # what stops "Ivanov" typed 700 times from being scored 700 times against
    # every designation held.
    seen, unique = set(), []
    for tok in out:
        if tok not in seen:
            seen.add(tok)
            unique.append(tok)
    return unique[:MAX_TOKENS]


def tokens(name: str, kind: str = "individual") -> list[str]:
    return tokens_from_normalised(normalise(name), kind)


# --------------------------------------------------------- Jaro-Winkler

def jaro(a: str, b: str) -> float:
    la, lb = len(a), len(b)
    if not la or not lb:
        return 0.0
    if a == b:
        return 1.0
    window = max(la, lb) // 2 - 1
    if window < 0:
        window = 0
    a_flags = [False] * la
    b_flags = [False] * lb
    matches = 0
    for i, ch in enumerate(a):
        lo = max(0, i - window)
        hi = min(i + window + 1, lb)
        for j in range(lo, hi):
            if not b_flags[j] and b[j] == ch:
                a_flags[i] = b_flags[j] = True
                matches += 1
                break
    if not matches:
        return 0.0
    k = transpositions = 0
    for i, ch in enumerate(a):
        if a_flags[i]:
            while not b_flags[k]:
                k += 1
            if ch != b[k]:
                transpositions += 1
            k += 1
    transpositions //= 2
    return (matches / la + matches / lb + (matches - transpositions) / matches) / 3.0


def jaro_winkler(a: str, b: str, p: float = 0.1, max_prefix: int = 4) -> float:
    j = jaro(a, b)
    if j <= 0.7:
        return j
    prefix = 0
    for x, y in zip(a[:max_prefix], b[:max_prefix]):
        if x != y:
            break
        prefix += 1
    return j + prefix * p * (1 - j)


# ------------------------------------------------------------- scoring

def _jw_upper_bound(la: int, lb: int) -> float:
    """Highest Jaro-Winkler two strings of these lengths can reach.

    Every matched character is bounded by the shorter string, so
    jaro <= (m/la + m/lb + 1)/3 with m = min(la, lb), and Winkler adds at most
    0.4 of the remainder. Exact, so it can be used to skip work without changing
    any result."""
    m = min(la, lb)
    j = (m / la + m / lb + 1.0) / 3.0
    return (j + 0.4 * (1.0 - j)) * 100.0


def _sim(a: str, b: str) -> float:
    """Similarity of two name parts. An initial scores as corroboration only."""
    if len(a) == 1 or len(b) == 1:
        return INITIAL_CREDIT if a[0] == b[0] else 0.0
    return jaro_winkler(a, b) * 100.0


def _best_sim(t: str, others: list[str]) -> tuple[float, float]:
    """Best similarity of t against any of others, and the best achieved against
    a full token rather than an initial. Pairs whose lengths put them out of
    reach of the best already found are skipped, which is exact."""
    best = best_full = 0.0
    lt = len(t)
    for o in others:
        lo = len(o)
        if lt == 1 or lo == 1:
            s = INITIAL_CREDIT if t[0] == o[0] else 0.0
            if s > best:
                best = s
            continue
        if _jw_upper_bound(lt, lo) <= best and best >= best_full:
            continue
        s = jaro_winkler(t, o) * 100.0
        if s > best:
            best = s
        if s > best_full:
            best_full = s
    return best, best_full


def score(query: str, candidate: str, kind: str = "individual") -> float:
    return score_tokens(tokens(query, kind), tokens(candidate, kind))


def score_tokens(q: list[str], c: list[str], exact: bool = False) -> float:
    """Scoring over already-tokenised names, so a screening run tokenises each
    designation once rather than once per query.

    `exact` says the caller has established that the query and the candidate are
    the SAME STRING once normalised. That is not a similarity judgment to be
    capped or damped: it is the published name. Scoring it through the ordinary
    path capped 54 published designations below the threshold — every one of
    them a name that reduces to initials, such as "E. S. Co.", "T.R.O.S" and the
    tanker "LADY R" — so that they could not find themselves."""
    if exact:
        return 100.0
    if not q or not c:
        return 0.0

    # A name typed without its spaces is one token where the listing has
    # several, or the reverse. Compared token by token it scores as a fragment —
    # "JieShun" reached 37.5% recall against "Jie Shun" — although the two
    # strings are the same name with one keystroke missing. Compare the runs
    # together as well, and treat the result as a full-token match, because
    # matching an entire concatenated name is not an uncorroborated initial.
    # Guarded on length. Without it "John Smith" against a listing holding the
    # bare forename "John" concatenates to JOHNSMITH vs JOHN and scores 88.9 on
    # the prefix bonus alone — the subset inflation this matcher already refuses
    # elsewhere. A name missing its spaces is very nearly the same LENGTH as the
    # name that has them; a fragment is not.
    joined = 0.0
    if len(q) == 1 and len(c) > 1:
        a, b = q[0], "".join(c)
    elif len(c) == 1 and len(q) > 1:
        a, b = "".join(q), c[0]
    elif len(q) != len(c):
        # Both sides multi-token, tokenised DIFFERENTLY — which is what happens
        # every time a name carries initials. The UK publishes "P.K.T. MUNGMEE
        # CO., LTD"; that normalises to six tokens, and a person types "PKT
        # MUNGMEE CO LTD", which is four. Token by token the initials score as
        # fragments and the whole name reached 79.9 against a threshold of 88 —
        # a complete nil, exit 0, on a healthy cache, for the ordinary spelling
        # of a designated company. The branch above already knew to compare the
        # runs together; it only ever looked when ONE side was a single token.
        # The length-ratio guard below is what keeps this from inflating a
        # fragment: a name missing its punctuation is very nearly as long as the
        # name that has it, and "ABC LTD" against "ABC HOLDINGS LTD" is not.
        a, b = "".join(q), "".join(c)
    else:
        a = b = ""
    if a and b and min(len(a), len(b)) / max(len(a), len(b)) >= RUN_TOGETHER_RATIO:
        joined = jaro_winkler(a, b) * 100.0

    best_q, best_full = [], 0.0
    for qt in q:
        b, bf = _best_sim(qt, c)
        best_q.append(b)
        if bf > best_full:
            best_full = bf
    best_c = [_best_sim(ct, q)[0] for ct in c]

    if len(q) == 1:                       # a deliberate one-name search
        # A query that is nothing but an initial identifies nobody, and is capped
        # like any other uncorroborated initial rather than returning everyone
        # whose name begins with that letter.
        result = max(best_q[0], joined)
        if joined >= STRONG:
            return result
        return result if best_full >= STRONG else min(result, UNCORROBORATED_CAP)

    anchored = best_q[0] >= STRONG and best_q[-1] >= STRONG
    weights = [1.0] * len(q)
    if anchored:
        for i in range(1, len(q) - 1):
            weights[i] = MIDDLE_WEIGHT
    cov_q = sum(b * w for b, w in zip(best_q, weights)) / sum(weights)
    cov_c = sum(best_c) / len(best_c)
    if len(c) < len(q) and not anchored:
        cov_c *= 0.5 + 0.5 * (len(c) / len(q))

    result = max(0.7 * max(cov_q, cov_c) + 0.3 * min(cov_q, cov_c), joined)
    if joined >= STRONG:
        return result
    # nothing but initials matched: corroboration without identification
    return result if best_full >= STRONG else min(result, UNCORROBORATED_CAP)


# --------------------------------------------------- native (non-Latin) script

_LATIN_RE = re.compile(r"[A-Za-z]")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)


# Latin letters whose mark is part of the glyph and so survives NFKD: they were
# being cut to spaces by the non-alphanumeric sweep, turning "Međunarodna" into
# "ME UNARODNA", and were then read by the script gate as letters this tool
# cannot romanise.
LATIN_FOLD = str.maketrans({
    "đ": "d", "Đ": "D", "ð": "d", "Ð": "D", "ø": "o", "Ø": "O",
    "ł": "l", "Ł": "L", "þ": "th", "Þ": "TH", "ß": "ss",
    "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE", "ŧ": "t", "Ŧ": "T",
    "ħ": "h", "Ħ": "H", "ı": "i", "İ": "I", "ŉ": "n", "ĸ": "k",
})


def unmappable_letters(name: str) -> list:
    """The letters in a name that this tool cannot render into Latin at all.

    `is_native` asks whether a name is MOSTLY non-Latin, which is the wrong
    question for deciding whether a search is possible: appending one ASCII
    letter to an Arabic name made it non-native, skipped the refusal, and the
    unchanged Arabic string was then reported to the reader as its
    "romanisation". What matters is whether every non-Latin letter can be
    mapped — a name is searchable against Latin lists only if all of them can.

    Letters that homoglyph folding or diacritic stripping already turn into
    Latin do not count: those are Latin names written with confusable
    characters, and they are handled."""
    out, seen = [], set()
    for ch in (name or "")[:MAX_NAME_CHARS]:
        if not _LETTER_RE.match(ch) or _LATIN_RE.match(ch):
            continue
        folded = unicodedata.normalize("NFKD", ch.translate(LATIN_FOLD)) \
            .translate(HOMOGLYPHS)
        if any(_LATIN_RE.match(c) for c in folded):
            continue                       # a Latin letter in disguise
        if ch.lower() in CYRILLIC_TO_LATIN:
            continue                       # romanisable
        try:
            if unicodedata.name(ch).startswith("LATIN"):
                continue                   # Latin script, however exotic
        except ValueError:
            pass
        if ch not in seen:
            seen.add(ch)
            out.append(ch)
    return out


def script_names(letters) -> list:
    """The Unicode script blocks a set of letters belongs to, for the refusal
    message: 'ARABIC', 'HAN', 'HEBREW' rather than a list of code points."""
    names, seen = [], set()
    for ch in letters:
        try:
            block = unicodedata.name(ch).split()[0]
        except ValueError:
            block = "UNKNOWN"
        if block not in seen:
            seen.add(block)
            names.append(block)
    return names


@functools.lru_cache(maxsize=8192)
def is_latin_letter(ch: str) -> bool:
    """True where a character is a letter of the LATIN script.

    ASCII membership is not a script test, and using it as one cost real
    recall. `is_native()` counted only [A-Za-z], so the EU's Latin-script
    "Černé září" was classified as written outside Latin, was kept out of the
    Latin index, and the ordinary folded query "Cerne zari" — the spelling
    anyone without a Czech keyboard would type — returned nothing on a healthy
    list. Unicode already knows the answer: every Latin letter, however
    accented, is named LATIN SOMETHING. Cached, because this runs per character
    over about 100,000 published names."""
    if _LATIN_RE.match(ch):            # ASCII fast path
        return True
    if not _LETTER_RE.match(ch):
        return False
    # Ask the question of the form MATCHING uses, not of the codepoint as typed.
    # normalise() decomposes with NFKD before it does anything else, so a
    # fullwidth "Ａ" is already an "A" by the time any name is compared —
    # but its own Unicode name is FULLWIDTH LATIN CAPITAL LETTER A, which does
    # not BEGIN "LATIN", so asking the codepoint filed it outside the Latin
    # script and kept "ＡＣＭＥ" out of the Latin index while an
    # ordinary "ACME" query looked for it there. The same holds for the
    # letterlike and mathematical alphanumerics: "ℂ", "𝐀", "Ⅻ".
    # Decomposing first and asking of the pieces classifies the spelling the
    # way the matcher will actually read it. Cyrillic is untouched by NFKD and
    # stays native, which is the distinction that matters.
    for probe in (ch, unicodedata.normalize("NFKD", ch)):
        for c in probe:
            if _LATIN_RE.match(c):
                return True
            try:
                if unicodedata.name(c).startswith("LATIN"):
                    return True
            except ValueError:         # unnamed character: it says nothing
                continue
    return False


def is_native(name: str) -> bool:
    """True where the text is written predominantly outside the Latin script."""
    letters = _LETTER_RE.findall(name or "")
    if not letters:
        return False
    return sum(1 for c in letters if is_latin_letter(c)) * 2 < len(letters)


def has_native_letters(name: str) -> bool:
    """True where ANY letter falls outside A-Z.

    The test for whether a spelling is worth a native key at all. A pure ASCII
    name is not: giving all 19,321 OFAC designations a native key each would
    swell the native index with entries no native query can ever match. A name
    carrying one letter outside A-Z is worth one, whatever field it was
    published in and whichever script dominates it."""
    return any(_LETTER_RE.match(ch) and not is_latin_letter(ch)
               for ch in (name or "")[:MAX_NAME_CHARS])


def has_romanisable(name: str) -> bool:
    """True where ANY letter of the name can be romanised — in this tool, any
    Cyrillic letter. This, not is_native(), decides whether romanisations are
    searched: "Yury Viktorovich Федоров" is Latin by count and was never
    romanised, so a fresh OFAC list returned a clean nil for a name it holds."""
    return any(ch.lower() in CYRILLIC_TO_LATIN for ch in (name or "")[:MAX_NAME_CHARS])


def native_key(name: str) -> str:
    """A comparable form of a non-Latin name.

    normalise() keeps only [A-Z0-9 ], so a Cyrillic, Arabic or Chinese name
    reduces to nothing and can never match. Publishers supply these names; they
    have to be searchable in the script they are published in."""
    s = unicodedata.normalize("NFKC", strip_control((name or "")[:MAX_NAME_CHARS]))
    s = "".join(c for c in s if _LETTER_RE.match(c) or c.isdigit())
    return s.casefold()


CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "ґ": "g", "д": "d", "е": "e", "ё": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "i", "і": "i", "ї": "i", "й": "i", "к": "k",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ў": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "iu", "я": "ia",
}


# The romanisation systems the publishers actually use. One spelling is not
# enough: ФЕДОРОВ Юрий is published by OFAC as "Yury Viktorovich" and by the
# system below as "IUrii Viktorovich", which scores 87.8 against a threshold of
# 88 — an exact designation missed by two tenths of a point. Whole systems are
# used rather than a cross-product of every ambiguous letter, because a system
# is a spelling somebody really publishes, and because twelve synthetic hybrids
# cost 19 seconds a query to find nothing the four real ones miss.
#
#   iso9      the ICAO/GOST-flavoured system already used above
#   bgn       BGN/PCGN, the Anglophone standard (Yuriy, Fedorov)
#   press     BGN with ё written yo, which is how the press and many lists spell
#             it (Fyodorov, Gorbachyov)
#   scholarly the scientific/ISO transliteration (Jurij, Hodorkovskij)
#
ROMANISATION_SYSTEMS = (
    ("iso9", {}),
    ("bgn", {"й": "y", "ю": "yu", "я": "ya", "ё": "e", "ы": "y", "є": "ye", "ї": "yi"}),
    ("press", {"й": "y", "ю": "yu", "я": "ya", "ё": "yo", "ы": "y", "є": "ye",
               "ї": "yi", "ъ": ""}),
    ("scholarly", {"й": "j", "ю": "ju", "я": "ja", "ё": "jo", "х": "h", "ц": "c",
                   "ж": "zh", "щ": "shch", "є": "je", "ї": "ji"}),
)


def _romanise(name: str, overrides: dict) -> str:
    out = []
    for ch in (name or "")[:MAX_NAME_CHARS]:
        low = ch.lower()
        if low in overrides:
            mapped = overrides[low]
        elif low in CYRILLIC_TO_LATIN:
            mapped = CYRILLIC_TO_LATIN[low]
        else:
            out.append(ch)
            continue
        out.append(mapped.upper() if ch.isupper() else mapped)
    return "".join(out)


def transliterate_variants(name: str) -> list:
    """Every romanisation of a Cyrillic name this tool is prepared to compare,
    the primary system first.

    Publishers romanise to different systems and none of them is the right one,
    so a single spelling is a guess dressed as an answer. Systems that produce
    the same string for a given name collapse to one."""
    out, seen = [], set()
    for _, overrides in ROMANISATION_SYSTEMS:
        form = _romanise(name, overrides)
        if form and LATIN.search(form) and form not in seen:
            seen.add(form)
            out.append(form)
    return out


def transliterate(name: str) -> str:
    """Romanise a Cyrillic name so it can be compared with Latin listings.

    Indexing publisher-supplied native names only solves half the problem: a
    client whose passport reads КАДЫРОВ must still find a listing that spells him
    KADYROV. This is deliberately one system among several — the result is a
    query spelling, offered alongside the original, never a claim about how the
    publisher romanised it."""
    out = []
    for ch in (name or "")[:MAX_NAME_CHARS]:
        low = ch.lower()
        if low in CYRILLIC_TO_LATIN:
            mapped = CYRILLIC_TO_LATIN[low]
            out.append(mapped.upper() if ch.isupper() else mapped)
        else:
            out.append(ch)
    result = "".join(out)
    return result if LATIN.search(result) else ""


LATIN = re.compile(r"[A-Za-z]")


def native_score(query_key: str, candidate_key: str) -> float:
    if not query_key or not candidate_key:
        return 0.0
    if query_key == candidate_key:
        return 100.0
    return jaro_winkler(query_key, candidate_key) * 100.0


# ------------------------------------------------------------ prefilter

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
_IDX = {ch: i for i, ch in enumerate(_ALPHABET)}
_BASE = len(_ALPHABET)

try:
    (0).bit_count
    def _popcount(x: int) -> int:
        return x.bit_count()
except AttributeError:                                     # Python < 3.10
    def _popcount(x: int) -> int:
        return bin(x).count("1")


def _bigrams(normalised: str) -> int:
    mask = 0
    prev = None
    for ch in normalised:
        i = _IDX.get(ch)
        if i is None:
            prev = None
            continue
        if prev is not None:
            mask |= 1 << (prev * _BASE + i)
        prev = i
    return mask


def bigram_mask(normalised: str) -> int:
    """A 1,369-bit set of the character bigrams in a normalised name, TOGETHER
    with the bigrams of the same name run together.

    The scorer has a branch for names whose parts have been split or joined —
    "K M A" and "KMA" score 100 against each other, and it was written for
    exactly that. The prefilter sat above it and those two strings share no
    bigram at all, so the record was discarded before the branch could run: OFAC
    SDN 48715 is a designated VESSEL published as "K M A" with no other name,
    and the query "KMA" returned "Lists searched: 6 of 6", no candidate, exit 0.
    Thirteen published spellings across nine designations went the same way, four
    of them OFAC vessels — and ten reviews missed it because every test has
    always queried a name the way the publisher spells it.

    Including the de-spaced bigrams in BOTH masks costs 2.4 points of prefilter
    pass rate and changes no score. The filter is a cheap first gate; it has no
    business excluding a name the scorer would call an exact match."""
    joined = normalised.replace(" ", "")
    if joined == normalised:
        return _bigrams(normalised)
    return _bigrams(normalised) | _bigrams(joined)


PREFILTER_FRACTION = 0.20
"""Fraction of the query's bigrams a designation must share to be scored.

Set from measurement, not taste. Across 2,292 known-true pairs — the same
designation searched under seven deformations — the lowest observed overlap was
0.30, and the first percentile 0.50. The worst case is a client who supplies a
patronymic the list does not hold. 0.20 sits a third below anything observed,
and tests/benchmark.py --no-prefilter re-measures whether it costs recall."""


PREFILTER_CEILING = 4
"""Never demand more than this many shared bigrams, however long the query.

A long entity name has many bigrams, and a proportional rule would demand so
many that a genuine listing carrying a shorter form of the same name could be
filtered out before it was ever scored. The tightest realistic margin measured
without this ceiling was one bigram."""


def prefilter_threshold(query_mask: int) -> int:
    pq = _popcount(query_mask)
    if pq < 4:                       # very short names share few bigrams
        return 1
    need = math.ceil(pq * PREFILTER_FRACTION)
    return min(max(need, 2), PREFILTER_CEILING)


def passes(query_mask: int, record_mask: int, need: int) -> bool:
    return _popcount(query_mask & record_mask) >= need
