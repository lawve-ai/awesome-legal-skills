"""Relevance and integrity gate for search hits.

Vendored copy, carried by the skill so it works against any version of the
engine. Prefer `core.quality` upstream where it exists; xsearch.py falls back
to this one.

The engine asks ~50 national databases for anything matching extradition
vocabulary. They differ wildly in how literally they take that: several sort
by date rather than relevance and stem aggressively, so a low per-source limit
returns "the newest thing that loosely matched" — which is how a competition
appeal and an asylum judgment reach an extradition sweep.

Nothing here fetches anything. It judges only the metadata the source already
gave us, and it is deliberately conservative: a hit is demoted, not deleted,
unless its link is unusable. The caller decides what to show. A search result
was never an authority — but it should at least be about extradition.

Verdicts
    broken     the link cannot reach a decision (bare domain, search page)
    on_topic   extradition/surrender vocabulary present in the metadata
    unverified the source returned too little text to judge either way
    off_topic  enough text to judge, and the vocabulary is absent
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from core.terms import TERM_PACKS  # from the installed engine

# Placeholder titles adapters emit when their extraction fails.
_PLACEHOLDER = {"text", "untitled", "document", "dokument", "judgment",
                "decision", "(untitled)", "-", "—"}

_WS = re.compile(r"\s+")
_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)


def _stems() -> frozenset[str]:
    """Stems of every term the engine actually searches with.

    Built from the term packs rather than a hand-written list, so the gate
    stays honest to what was asked for: if a new language is added to the
    packs, its vocabulary is recognised here automatically.
    """
    out: set[str] = set()
    for pack in TERM_PACKS.values():
        for mode in ("extradition", "eaw"):
            for term in pack.get(mode, []):
                for word in _WORD.findall(term.lower()):
                    # 6 chars is enough to be distinctive and short enough to
                    # survive inflection (Auslieferung/Auslieferungshaft,
                    # uitlevering/uitleveringsdetentie, extradare/extrădare).
                    out.add(word[:6])
    return frozenset(out)


STEMS = _stems()

# Docket markers that identify an extradition matter even with no prose:
# NRW's 'OAus' register, and the German constitutional senate that hears
# extradition complaints.
_DOCKET = re.compile(r"\bO\s?Aus\b|\bAusl\b|\b2\s?BvR\b", re.I)


def clean_title(hit: dict) -> str:
    """Readable title, or the best identifier available instead."""
    title = _WS.sub(" ", html.unescape(hit.get("title") or "")).strip()
    if title.lower().strip(" .:-") in _PLACEHOLDER or len(title) < 4:
        for key in ("ecli", "ref", "court"):
            if alt := (hit.get(key) or "").strip():
                return html.unescape(alt)
        return "(no title given by the source)"
    return title


def link_problem(url: str) -> str | None:
    """Why this URL cannot be a decision, or None if it looks like one."""
    if not url:
        return "no link"
    try:
        p = urlparse(url)
    except ValueError:
        return "malformed link"
    if not p.scheme.startswith("http"):
        return "malformed link"
    if not p.path or p.path == "/":
        return "links to the site's front page, not a decision"
    low = p.path.lower()
    if "/search" in low or low.endswith("/search") or p.query.startswith("q="):
        return "links to a search page, not a decision"
    return None


def assess(hit: dict) -> dict:
    """Return {'verdict', 'reason', 'rank'} for one hit. Never raises."""
    if problem := link_problem(hit.get("url") or ""):
        return {"verdict": "broken", "reason": problem, "rank": 3}

    title = clean_title(hit)
    haystack = " ".join(filter(None, [
        title, hit.get("snippet"), hit.get("court"), hit.get("ref"),
        hit.get("ecli"), " ".join(str(v) for v in (hit.get("extra") or {}).values()),
    ])).lower()

    if _DOCKET.search(haystack):
        return {"verdict": "on_topic",
                "reason": "extradition docket reference", "rank": 0}

    words = {w[:6] for w in _WORD.findall(haystack)}
    if hits := (words & STEMS):
        return {"verdict": "on_topic",
                "reason": "matched " + ", ".join(sorted(hits)[:3]), "rank": 0}

    # Enough prose to have expected the vocabulary if it were relevant.
    prose = len(hit.get("snippet") or "") + len(title)
    if prose >= 40:
        return {"verdict": "off_topic",
                "reason": "no extradition vocabulary in the text returned",
                "rank": 2}
    return {"verdict": "unverified",
            "reason": "source returned too little text to judge", "rank": 1}


def annotate(hits: list[dict]) -> list[dict]:
    """Attach `quality` and a cleaned `title` to each hit, best first."""
    for h in hits:
        h["quality"] = assess(h)
        h["title"] = clean_title(h)
    return sorted(hits, key=lambda h: (h["quality"]["rank"],
                                       h.get("date") or "", ), reverse=False)
