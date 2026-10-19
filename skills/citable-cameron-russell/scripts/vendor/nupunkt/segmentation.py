"""
Standard segmentation interface for nupunkt.

Every segmenter (word, sentence, paragraph, adaptive sentence) exposes the same
surface, built from a single primitive, ``iter_segments``:

=============  =======================  ==================================
Form           List                     Generator
=============  =======================  ==================================
strings        ``texts(text)``          ``iter_texts(text)``
spans          ``spans(text)``          ``iter_spans(text)``
both           ``segments(text)``       ``iter_segments(text)``
=============  =======================  ==================================

Spans are *tight*: for every segment ``text[start:end] == segment.text`` with no
surrounding whitespace, segments are ascending and never overlap, and any
whitespace between segments is left in the gaps. Use :func:`contiguous` to
turn a list of segments into one that covers the whole input without gaps.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import Any, NamedTuple, Protocol, runtime_checkable

from nupunkt.core.language_vars import PunktLanguageVars


class Segment(NamedTuple):
    """
    A segment of text with its character span in the source string.

    ``end`` is exclusive, so ``source[start:end] == text``. The tuple unpacks as
    ``(text, start, end)``.
    """

    text: str
    start: int
    end: int

    @property
    def span(self) -> tuple[int, int]:
        """The ``(start, end)`` span as a tuple."""
        return (self.start, self.end)

    def __len__(self) -> int:  # type: ignore[override]
        """The length of the segment text in characters."""
        return self.end - self.start


@runtime_checkable
class Segmenter(Protocol):
    """The interface every segmenter provides."""

    def iter_segments(self, text: str, **options: Any) -> Iterator[Segment]: ...

    def iter_texts(self, text: str, **options: Any) -> Iterator[str]: ...

    def iter_spans(self, text: str, **options: Any) -> Iterator[tuple[int, int]]: ...

    def segments(self, text: str, **options: Any) -> list[Segment]: ...

    def texts(self, text: str, **options: Any) -> list[str]: ...

    def spans(self, text: str, **options: Any) -> list[tuple[int, int]]: ...


class SegmenterMixin:
    """
    Mixin that derives the whole segmentation interface from ``iter_segments``.

    Subclasses implement ``iter_segments`` (a generator of tight, ascending,
    non-overlapping :class:`Segment` objects) and get the other five methods.
    """

    def iter_segments(self, text: str, **options: Any) -> Iterator[Segment]:
        """Yield each segment of ``text`` with its span.

        Keyword options are segmenter-specific (for example ``paragraph_breaks``
        and ``line_breaks`` on the sentence tokenizer) and are passed through by
        the five derived methods.
        """
        raise NotImplementedError

    def iter_texts(self, text: str, **options: Any) -> Iterator[str]:
        """Yield the text of each segment."""
        for segment in self.iter_segments(text, **options):
            yield segment.text

    def iter_spans(self, text: str, **options: Any) -> Iterator[tuple[int, int]]:
        """Yield the ``(start, end)`` span of each segment."""
        for segment in self.iter_segments(text, **options):
            yield (segment.start, segment.end)

    def segments(self, text: str, **options: Any) -> list[Segment]:
        """Return all segments of ``text`` with their spans."""
        return list(self.iter_segments(text, **options))

    def texts(self, text: str, **options: Any) -> list[str]:
        """Return the text of every segment."""
        return list(self.iter_texts(text, **options))

    def spans(self, text: str, **options: Any) -> list[tuple[int, int]]:
        """Return the ``(start, end)`` span of every segment."""
        return list(self.iter_spans(text, **options))


def contiguous(segments: Iterable[Segment], source: str) -> list[Segment]:
    """
    Extend tight segments so that together they cover ``source`` without gaps.

    Each segment absorbs the whitespace that follows it, up to the start of the
    next segment; the first segment also absorbs any leading whitespace and the
    last extends to the end of the text. The result satisfies
    ``"".join(s.text for s in result) == source`` when there is at least one
    segment. Whitespace-only or empty input gives an empty list.

    Args:
        segments: Tight segments in ascending order
        source: The text the segments were taken from

    Returns:
        Contiguous segments covering all of ``source``
    """
    segs = list(segments)
    if not segs:
        return []
    result: list[Segment] = []
    length = len(source)
    for i in range(len(segs)):
        start = 0 if i == 0 else result[-1].end
        end = segs[i + 1].start if i + 1 < len(segs) else length
        result.append(Segment(source[start:end], start, end))
    return result


def tight(segments: Iterable[Segment], source: str) -> Iterator[Segment]:
    """
    Strip surrounding whitespace from segments, dropping any that become empty.

    Args:
        segments: Segments whose spans may include surrounding whitespace
        source: The text the segments were taken from

    Yields:
        Segments whose text has no leading or trailing whitespace
    """
    for seg in segments:
        start, end = seg.start, seg.end
        while start < end and source[start].isspace():
            start += 1
        while end > start and source[end - 1].isspace():
            end -= 1
        if end > start:
            yield Segment(source[start:end], start, end)


class WordSegmenter(SegmenterMixin):
    """
    Segment text into words using Punkt's word tokenizer.

    This is the tokenization the sentence tokenizer and trainer use internally:
    trailing periods stay attached (``"Dr."``), contractions and possessives are
    one token (``"Smith's"``), and most other punctuation is split off. It is
    exposed so that word spans line up with the tokens Punkt reasons about, not
    as a general-purpose word tokenizer.

    Args:
        lang_vars: Language-specific variables; defaults to :class:`PunktLanguageVars`
    """

    _RE_LINE = re.compile(r"[^\n]+")

    def __init__(self, lang_vars: PunktLanguageVars | None = None) -> None:
        self._lang_vars = lang_vars or PunktLanguageVars()

    def iter_segments(self, text: str, **options: Any) -> Iterator[Segment]:
        """Yield each word of ``text`` with its span (no options are defined)."""
        if options:
            raise TypeError(f"unexpected options for WordSegmenter: {sorted(options)}")
        finditer = self._lang_vars.word_tokenize_pattern.finditer
        # Tokenize line by line, exactly as PunktBase._tokenize_words does
        for line in self._RE_LINE.finditer(text):
            offset = line.start()
            for match in finditer(line.group(0)):
                start = offset + match.start()
                end = offset + match.end()
                yield Segment(match.group(0), start, end)


__all__ = [
    "Segment",
    "Segmenter",
    "SegmenterMixin",
    "WordSegmenter",
    "contiguous",
    "tight",
]
