"""
Layout-aware segmentation for nupunkt.

Punkt decides sentence boundaries at sentence-ending punctuation. Real documents
also mark boundaries with layout: a blank line between paragraphs, a heading on
its own line, a list item per line. None of those carry a period, so Punkt alone
merges a heading into the sentence that follows it. On the bundled legal gold set
94% of the boundaries Punkt misses have no terminal punctuation at all.

This module adds two deterministic layout rules that run *before* Punkt, on top
of it rather than inside it:

``paragraph_breaks``
    A blank line (a newline, optional horizontal whitespace, another newline) is a
    hard sentence boundary. Sentences never cross it. Measured on gold sets that
    keep paragraph structure (UD EWT, UD GUM, the legal set with paragraph
    markers) this raises recall by 9-35 points at unchanged precision, so it is
    the default of the segmentation interface. The legacy ``sent_tokenize`` family
    keeps Punkt-only behaviour.

``line_breaks``
    Additionally, a single newline ends a unit when the line before it looks like
    a heading (short, no terminal punctuation) or the line after it starts with a
    list marker (``-``, ``*``, ``1.``, ``(a)``, ``iv)`` ...). This is opt-in: it
    helps on structured documents and hurts on hard-wrapped plain text, where lines
    end mid-sentence without punctuation.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator

from nupunkt.segmentation import Segment, tight

# A blank line: newline, optional horizontal whitespace, newline
BLANK_LINE = re.compile(r"\n[ \t\r\f\v]*\n")

# A line that starts with a list marker followed by whitespace
LIST_MARKER = re.compile(
    r"[ \t]*(?:[-*•–—·]|\(?\d{1,3}[.)]|\(?[A-Za-z][.)]|\(?[ivxlIVXL]{1,5}[.)])[ \t]"
)

# Characters that mark a line as *not* heading-like when they end it
_LINE_CONTINUES_IF_ENDS_WITH = frozenset(".!?:;,\"')]}…”’»")

# Headings are short; longer punctuation-free lines are usually wrapped prose
HEADING_MAX_WORDS = 8


def is_heading_line(line: str) -> bool:
    """
    Whether a line looks like a heading or label rather than wrapped prose.

    A heading is non-empty, has at most :data:`HEADING_MAX_WORDS` words, and does
    not end with punctuation that would normally end or continue a sentence.

    Args:
        line: One line of text, without its trailing newline
    """
    stripped = line.strip()
    if not stripped or stripped[-1] in _LINE_CONTINUES_IF_ENDS_WITH:
        return False
    return stripped.count(" ") < HEADING_MAX_WORDS


def iter_blocks(
    text: str, paragraph_breaks: bool = True, line_breaks: bool = False
) -> Iterator[tuple[int, int]]:
    """
    Yield ``(start, end)`` of the layout blocks of ``text``.

    Blocks are separated by blank lines when ``paragraph_breaks`` is set and, when
    ``line_breaks`` is also set, by single newlines after heading-like lines or
    before list-marker lines. Whitespace-only blocks are skipped. With both flags
    off the whole text is one block.

    Args:
        text: The text to split
        paragraph_breaks: Split at blank lines
        line_breaks: Also split at heading and list-item line breaks
    """
    if not paragraph_breaks and not line_breaks:
        if text.strip():
            yield (0, len(text))
        return
    paragraphs: Iterable[tuple[int, int]]
    if paragraph_breaks:
        cuts = [
            (m.start(), m.end())
            for m in BLANK_LINE.finditer(text)
            if not continues_across(text, m.start(), m.end())
        ]
        paragraphs = _spans_between(cuts, len(text))
    else:
        paragraphs = [(0, len(text))]
    for start, end in paragraphs:
        if not text[start:end].strip():
            continue
        if line_breaks:
            yield from _line_blocks(text, start, end)
        else:
            yield (start, end)


def continues_across(text: str, gap_start: int, gap_end: int) -> bool:
    """
    Whether a sentence runs across the blank line ``text[gap_start:gap_end]``.

    This is the page-break case of scanned or OCR'd documents, where a sentence
    continues on the next page after a blank line. The blank line is *not* a
    boundary when the last line before it has no terminal punctuation and either
    ends with a hyphen (a word split across the break) or the text after the gap
    starts with a lowercase letter. Punctuation before the gap, or an uppercase
    start after it, keeps the blank line as a boundary. A heading followed by a
    lowercase paragraph start is therefore merged with it; that shape is rare.

    Args:
        text: The source text
        gap_start: Start of the blank-line match
        gap_end: End of the blank-line match
    """
    before = _last_nonblank_line_before(text, gap_start)
    if not before or before[-1] in _LINE_CONTINUES_IF_ENDS_WITH:
        return False
    if PAGE_FURNITURE.fullmatch(before):
        # A bare page number never continues into the next block
        return False
    if before.endswith("-") and before.count(" ") >= 1:
        return True
    i = gap_end
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    return i < n and text[i].islower()


def _last_nonblank_line_before(text: str, pos: int) -> str:
    """The last line before ``pos`` that has non-whitespace content, stripped."""
    end = pos
    while end > 0:
        start = text.rfind("\n", 0, end) + 1
        line = text[start:end].strip()
        if line:
            return line
        end = start - 1
        if end < 0:
            break
    return ""


# Page furniture: a line holding only a page number ("12", "- 12 -", "[12]",
# "Page 12", "Page 12 of 30", "p. 12") or a form feed
PAGE_FURNITURE = re.compile(
    r"(?im)^[ \t]*(?:\f|[-\u2013\u2014\[(]*\s*(?:page|p\.|pg\.?)?\s*\d{1,5}\s*(?:of\s*\d{1,5})?\s*[-\u2013\u2014\])]*)[ \t]*$"
)


def blank_page_furniture(text: str) -> str:
    """
    Replace page-number lines and form feeds with spaces, keeping every offset.

    Scanned and OCR'd documents carry a page number (or "Page 3 of 10") on its own
    line at each page break, often in the middle of a sentence. Blanking those
    lines with the same number of spaces leaves the character offsets of all other
    text unchanged, so spans from :func:`layout_segments` still index the original
    string, and lets :func:`continues_across` join the two halves of the sentence.
    Running headers and footers with words in them are not recognised; strip
    those with a document-specific pattern in the same offset-preserving way.

    Args:
        text: The text to clean

    Returns:
        The text with furniture lines replaced by spaces
    """
    return PAGE_FURNITURE.sub(lambda m: " " * len(m.group(0)), text)


def _spans_between(cuts: list[tuple[int, int]], length: int) -> Iterator[tuple[int, int]]:
    pos = 0
    for cut_start, cut_end in cuts:
        yield (pos, cut_start)
        pos = cut_end
    yield (pos, length)


def _line_blocks(text: str, start: int, end: int) -> Iterator[tuple[int, int]]:
    """Split ``text[start:end]`` at heading and list-item line breaks."""
    block_start = start
    line_start = start
    while True:
        nl = text.find("\n", line_start, end)
        if nl == -1:
            break
        line = text[line_start:nl]
        next_nl = text.find("\n", nl + 1, end)
        next_line = text[nl + 1 : next_nl if next_nl != -1 else end]
        # The next line with content, for the lowercase-continuation check
        probe = nl + 1
        while probe < end and text[probe].isspace():
            probe += 1
        stripped_next = text[probe : probe + 1]
        # A heading-like line is a boundary unless the text plainly continues it
        heading_cut = (
            is_heading_line(line)
            and not line.rstrip().endswith("-")
            and not (stripped_next and stripped_next[0].islower())
        )
        if heading_cut or LIST_MARKER.match(next_line):
            if text[block_start:nl].strip():
                yield (block_start, nl)
            block_start = nl + 1
        line_start = nl + 1
    if text[block_start:end].strip():
        yield (block_start, end)


def layout_segments(
    text: str,
    span_tokenize: Callable[[str], Iterable[tuple[int, int]]],
    paragraph_breaks: bool = True,
    line_breaks: bool = False,
) -> Iterator[Segment]:
    """
    Run a span tokenizer inside each layout block and yield tight segments.

    Args:
        text: The text to segment
        span_tokenize: ``text -> iterable of (start, end)``, e.g. Punkt's ``span_tokenize``
        paragraph_breaks: Blank lines are hard boundaries
        line_breaks: Heading and list-item line breaks are hard boundaries too
    """
    for block_start, block_end in iter_blocks(text, paragraph_breaks, line_breaks):
        block = text[block_start:block_end]
        raw = (
            Segment(block[s:e], block_start + s, block_start + e) for s, e in span_tokenize(block)
        )
        yield from tight(raw, text)


__all__ = [
    "BLANK_LINE",
    "HEADING_MAX_WORDS",
    "LIST_MARKER",
    "is_heading_line",
    "PAGE_FURNITURE",
    "blank_page_furniture",
    "continues_across",
    "iter_blocks",
    "layout_segments",
]
