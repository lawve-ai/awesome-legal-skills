"""
One-pass hierarchical segmentation: paragraphs -> sentences -> words.

:func:`segment` runs the sentence tokenizer once and derives every level from
that single pass, instead of running one pass per level (``paragraph_segments``
re-runs sentence segmentation internally, so calling ``word_segments``,
``sentence_segments`` and ``paragraph_segments`` on one text segments its
sentences twice and tokenizes its words once more).

The result is a :class:`Document` tree whose nodes are :class:`Segment`
subclasses, so every node unpacks as ``(text, start, end)``, compares equal to
the plain ``Segment`` with the same values, and obeys the same invariants as
the flat functions: spans are tight, ascending and non-overlapping, and every
word lies inside a sentence that lies inside a paragraph. The flat lists are
identical to the separate calls::

    doc = nupunkt.segment(text)
    doc.paragraphs == nupunkt.paragraph_segments(text)
    doc.sentences == nupunkt.sentence_segments(text)
    doc.words == nupunkt.word_segments(text)

Words are the expensive level, so they are computed lazily, one sentence at a
time, the first time a sentence's ``words`` are read.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import TYPE_CHECKING, Any

from nupunkt.core.language_vars import PunktLanguageVars
from nupunkt.layout import iter_blocks, layout_segments
from nupunkt.segmentation import Segment, WordSegmenter
from nupunkt.tokenizers.paragraph_tokenizer import PARAGRAPH_BREAK_PATTERN

if TYPE_CHECKING:
    from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer

# Same tokenization as WordSegmenter (line by line, Punkt's word pattern), inlined
# so that words can be produced directly at their final offsets.
_WORD_FINDITER = PunktLanguageVars().word_tokenize_pattern.finditer
_LINE_FINDITER = WordSegmenter._RE_LINE.finditer


def _strip_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Shrink ``[start, end)`` past surrounding whitespace (may become empty)."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def is_paragraph_break(text: str, pos: int) -> bool:
    """
    Whether a sentence boundary at ``pos`` is also a paragraph boundary.

    This is the rule used by :class:`~nupunkt.PunktParagraphTokenizer`: a blank
    line (two or more newlines, possibly with whitespace between them) starting
    within three characters of the boundary, inside a ten-character window.

    Args:
        text: The source text
        pos: A sentence end offset (exclusive), as given by ``span_tokenize``

    Returns:
        True if a paragraph ends at ``pos``
    """
    if pos >= len(text):
        return False
    match = PARAGRAPH_BREAK_PATTERN.search(text, pos, min(pos + 10, len(text)))
    return match is not None and match.start() - pos <= 3


class Sentence(Segment):
    """
    A sentence node: a :class:`Segment` with lazily computed ``words``.

    Equality, hashing and unpacking are those of the underlying
    ``(text, start, end)`` tuple; the words are not part of the value.
    """

    _words: list[Segment] | None = None

    @property
    def words(self) -> list[Segment]:
        """The words of this sentence, computed on first access and cached."""
        words = self._words
        if words is None:
            text = self.text
            base = self.start
            words = []
            append = words.append
            for line in _LINE_FINDITER(text):
                offset = base + line.start()
                for m in _WORD_FINDITER(line.group(0)):
                    append(Segment(m.group(0), offset + m.start(), offset + m.end()))
            self._words = words
        return words

    def iter_words(self) -> Iterator[Segment]:
        """Yield the words of this sentence."""
        yield from self.words

    def to_dict(self, words: bool = True) -> dict[str, Any]:
        """
        Convert to a JSON-serializable dict.

        Args:
            words: Include the ``words`` of the sentence

        Returns:
            ``{"text", "start", "end"}`` plus ``"words"`` if requested
        """
        result: dict[str, Any] = {"text": self.text, "start": self.start, "end": self.end}
        if words:
            result["words"] = [{"text": w.text, "start": w.start, "end": w.end} for w in self.words]
        return result


class Paragraph(Segment):
    """A paragraph node: a :class:`Segment` with its ``sentences``."""

    _sentences: list[Sentence] | None = None

    @property
    def sentences(self) -> list[Sentence]:
        """The sentences of this paragraph, in order."""
        sentences = self._sentences
        if sentences is None:
            sentences = self._sentences = []
        return sentences

    @property
    def words(self) -> list[Segment]:
        """All words of the paragraph, in order."""
        return [w for s in self.sentences for w in s.words]

    def iter_sentences(self) -> Iterator[Sentence]:
        """Yield the sentences of this paragraph."""
        yield from self.sentences

    def iter_words(self) -> Iterator[Segment]:
        """Yield the words of this paragraph, one sentence at a time."""
        for sentence in self.sentences:
            yield from sentence.words

    def to_dict(self, words: bool = True) -> dict[str, Any]:
        """
        Convert to a JSON-serializable dict.

        Args:
            words: Include the ``words`` of each sentence

        Returns:
            ``{"text", "start", "end", "sentences"}``
        """
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "sentences": [s.to_dict(words) for s in self.sentences],
        }


def _build_blocks(
    text: str, span_tokenize: Callable[[str], Iterable[tuple[int, int]]], line_breaks: bool
) -> list[Paragraph]:
    """Build the tree with blank lines as paragraph (and sentence) boundaries."""
    paragraphs: list[Paragraph] = []
    for block_start, block_end in iter_blocks(text, True, False):
        start, stop = _strip_span(text, block_start, block_end)
        if stop <= start:
            continue
        block = text[block_start:block_end]
        sentences = [
            Sentence(s.text, s.start, s.end)
            for s in layout_segments(block, span_tokenize, False, line_breaks)
        ]
        # layout_segments worked on the block; shift to document offsets
        sentences = [
            Sentence(s.text, s.start + block_start, s.end + block_start) for s in sentences
        ]
        para = Paragraph(text[start:stop], start, stop)
        para._sentences = sentences
        paragraphs.append(para)
    return paragraphs


def _build(text: str, spans: Iterator[tuple[int, int]]) -> list[Paragraph]:
    """Build the paragraph/sentence tree from raw ``span_tokenize`` spans."""
    paragraphs: list[Paragraph] = []
    current: list[Sentence] = []
    para_start = 0

    def close(end: int) -> None:
        nonlocal current, para_start
        start, stop = _strip_span(text, para_start, end)
        if stop > start:
            para = Paragraph(text[start:stop], start, stop)
            para._sentences = current
            paragraphs.append(para)
        current = []
        para_start = end

    for raw_start, raw_end in spans:
        start, end = _strip_span(text, raw_start, raw_end)
        if end > start:
            current.append(Sentence(text[start:end], start, end))
        if is_paragraph_break(text, raw_end):
            close(raw_end)
    close(len(text))
    return paragraphs


class Document:
    """
    The hierarchical segmentation of a text: paragraphs -> sentences -> words.

    Build one with :func:`segment`. ``paragraphs`` and ``sentences`` are computed
    eagerly from a single sentence pass; words are computed per sentence on
    first access.

    Attributes:
        text: The source text
        paragraphs: The paragraphs, each with its ``sentences``
    """

    __slots__ = ("paragraphs", "text")

    def __init__(self, text: str, paragraphs: list[Paragraph]) -> None:
        self.text = text
        self.paragraphs = paragraphs

    @classmethod
    def from_tokenizer(
        cls,
        text: str,
        tokenizer: PunktSentenceTokenizer,
        paragraph_breaks: bool = True,
        line_breaks: bool = False,
    ) -> Document:
        """
        Segment ``text`` with a sentence tokenizer in a single pass.

        Args:
            text: The text to segment
            tokenizer: Any object with Punkt's ``span_tokenize(text)`` method
            paragraph_breaks: Blank lines separate paragraphs and end sentences
                (see :mod:`nupunkt.layout`); with ``False`` paragraphs are derived
                from Punkt boundaries followed by a blank line, as in 0.7.0
            line_breaks: Heading and list-item line breaks also end sentences

        Returns:
            The segmented document
        """
        if not paragraph_breaks:
            spans = tokenizer.span_tokenize(text)
            if line_breaks:
                spans = (
                    (s.start, s.end)
                    for s in layout_segments(text, tokenizer.span_tokenize, False, True)
                )
            return cls(text, _build(text, iter(spans)))
        return cls(text, _build_blocks(text, tokenizer.span_tokenize, line_breaks))

    @property
    def sentences(self) -> list[Sentence]:
        """All sentences, in order."""
        return [s for p in self.paragraphs for s in p.sentences]

    @property
    def words(self) -> list[Segment]:
        """All words, in order (computes any words not yet computed)."""
        return [w for p in self.paragraphs for s in p.sentences for w in s.words]

    def iter_paragraphs(self) -> Iterator[Paragraph]:
        """Yield each paragraph."""
        yield from self.paragraphs

    def iter_sentences(self) -> Iterator[Sentence]:
        """Yield each sentence."""
        for paragraph in self.paragraphs:
            yield from paragraph.sentences

    def iter_words(self) -> Iterator[Segment]:
        """Yield each word, computing words one sentence at a time."""
        for paragraph in self.paragraphs:
            for sentence in paragraph.sentences:
                yield from sentence.words

    def to_dict(self, words: bool = True) -> dict[str, Any]:
        """
        Convert to a JSON-serializable dict (``json.dumps(doc.to_dict())``).

        Args:
            words: Include the words of each sentence

        Returns:
            ``{"text", "paragraphs": [{..., "sentences": [{..., "words": [...]}]}]}``
        """
        return {"text": self.text, "paragraphs": [p.to_dict(words) for p in self.paragraphs]}

    def __len__(self) -> int:
        """The number of paragraphs."""
        return len(self.paragraphs)

    def __iter__(self) -> Iterator[Paragraph]:
        """Iterate over paragraphs."""
        return iter(self.paragraphs)

    def __repr__(self) -> str:
        n_sent = sum(len(p.sentences) for p in self.paragraphs)
        return f"Document(chars={len(self.text)}, paragraphs={len(self.paragraphs)}, sentences={n_sent})"


__all__ = ["Document", "Paragraph", "Sentence", "is_paragraph_break"]
