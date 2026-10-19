"""
Paragraph tokenizer module for nupunkt.

This module provides tokenizer classes for paragraph boundary detection.
"""

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from nupunkt.core.language_vars import PunktLanguageVars
from nupunkt.core.tokens import PunktToken
from nupunkt.layout import iter_blocks
from nupunkt.segmentation import Segment, SegmenterMixin, tight
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer

# Precompiled regex pattern for two or more consecutive newlines
# This will efficiently detect paragraph breaks
PARAGRAPH_BREAK_PATTERN = re.compile(r"\n\s*\n+")


class PunktParagraphTokenizer(SegmenterMixin):
    """
    Paragraph tokenizer using sentence boundaries and newlines.

    This tokenizer identifies paragraph breaks ONLY at sentence boundaries that are
    immediately followed by two or more newlines.
    """

    def __init__(
        self,
        sentence_tokenizer: PunktSentenceTokenizer | None = None,
        lang_vars: PunktLanguageVars | None = None,
        token_cls: type[PunktToken] = PunktToken,
    ) -> None:
        """
        Initialize the paragraph tokenizer.

        Args:
            sentence_tokenizer: The sentence tokenizer to use (if None, a default model will be loaded)
            lang_vars: Language-specific variables
            token_cls: The token class to use
        """
        self._lang_vars = lang_vars or PunktLanguageVars()
        self._Token = token_cls

        # Initialize the sentence tokenizer
        if sentence_tokenizer is None:
            # Use the singleton pattern to avoid reloading the model
            self._sentence_tokenizer = self._get_default_model()
        else:
            self._sentence_tokenizer = sentence_tokenizer

    # Class-level variable for caching the default model
    _default_model = None

    @staticmethod
    def _get_default_model():
        """Get the default model, with caching using a class-level variable."""
        # Use class-level caching for the default model
        if PunktParagraphTokenizer._default_model is None:
            from nupunkt.models import load_default_model

            PunktParagraphTokenizer._default_model = load_default_model()
        return PunktParagraphTokenizer._default_model

    def iter_segments(self, text: str, **options: Any) -> Iterator[Segment]:
        """
        Yield each paragraph of ``text`` with its tight character span.

        With ``paragraph_breaks`` (default: the sentence tokenizer's setting, ``True``)
        every blank line separates paragraphs, matching the sentence-level layout
        rule. With it off, paragraphs are the legacy ones of ``tokenize_with_spans``:
        a Punkt sentence boundary followed by a blank line. Either way the spans
        exclude surrounding whitespace.
        """
        paragraph_breaks = options.pop("paragraph_breaks", None)
        if options:
            raise TypeError(f"unexpected options: {sorted(options)}")
        if paragraph_breaks is None:
            paragraph_breaks = getattr(self._sentence_tokenizer, "paragraph_breaks", True)
        if paragraph_breaks:
            raw = (Segment(text[s:e], s, e) for s, e in iter_blocks(text, True, False))
        else:
            raw = (
                Segment(para, start, end) for para, (start, end) in self.tokenize_with_spans(text)
            )
        yield from tight(raw, text)

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into paragraphs.

        Args:
            text: The text to tokenize

        Returns:
            A list of paragraphs
        """
        return [paragraph for paragraph, _ in self.tokenize_with_spans(text)]

    def tokenize_with_spans(self, text: str) -> list[tuple[str, tuple[int, int]]]:
        """
        Tokenize text into paragraphs with their character spans.

        Each span is a tuple of (start_idx, end_idx) where start_idx is inclusive
        and end_idx is exclusive (following Python's slicing convention).
        The spans are guaranteed to cover the entire input text without gaps.

        Args:
            text: The text to tokenize

        Returns:
            List of tuples containing (paragraph, (start_index, end_index))
        """
        # Quick return for empty text
        if not text:
            return []

        # Get all sentence boundary positions
        spans = list(self._sentence_tokenizer.span_tokenize(text))
        boundary_positions = [span[1] for span in spans]

        # If no boundaries, treat the whole text as one paragraph
        if not boundary_positions:
            return [(text, (0, len(text)))]

        # Find paragraph boundaries (sentence boundaries followed by 2+ newlines)
        paragraph_boundaries = []

        for pos in boundary_positions:
            # Look for 2+ newlines right after this boundary
            window_end = min(pos + 10, len(text))  # 10 char window is enough for newlines

            if pos < len(text):
                # Get the text slice to check
                window = text[pos:window_end]

                # Search for 2+ newlines in the window using the precompiled pattern
                match = PARAGRAPH_BREAK_PATTERN.search(window)

                # Only consider it a match if the newlines appear near the start of the window
                if match and match.start() <= 3:  # Allow for a few whitespace chars after sentence
                    paragraph_boundaries.append(pos)

        # Always include the end of text as a paragraph boundary
        if not paragraph_boundaries or paragraph_boundaries[-1] != len(text):
            paragraph_boundaries.append(len(text))

        # Create paragraph spans from boundaries
        result = []
        start_idx = 0

        for end_idx in paragraph_boundaries:
            # Get the paragraph text (without stripping to maintain all whitespace)
            paragraph_text = text[start_idx:end_idx]

            # Include all paragraphs to ensure contiguity
            result.append((paragraph_text, (start_idx, end_idx)))
            start_idx = end_idx

        return result

    def span_tokenize(self, text: str) -> list[tuple[int, int]]:
        """
        Tokenize text into paragraph spans.

        Each span is a tuple of (start_idx, end_idx) where start_idx is inclusive
        and end_idx is exclusive (following Python's slicing convention).
        The spans are guaranteed to cover the entire input text without gaps.

        Args:
            text: The text to tokenize

        Returns:
            List of paragraph spans (start_index, end_index)
        """
        return [span for _, span in self.tokenize_with_spans(text)]

    def save(
        self, file_path: str | Path, compress: bool = True, compression_level: int = 1
    ) -> None:
        """
        Save the tokenizer to a file.

        This saves the underlying sentence tokenizer.

        Args:
            file_path: The path to save the file to
            compress: Whether to compress the file using LZMA (default: True)
            compression_level: LZMA compression level (0-9), lower is faster but less compressed
        """
        self._sentence_tokenizer.save(file_path, compress, compression_level)

    @classmethod
    def load(
        cls,
        file_path: str | Path,
        lang_vars: PunktLanguageVars | None = None,
        token_cls: type[PunktToken] | None = None,
    ) -> "PunktParagraphTokenizer":
        """
        Load a PunktParagraphTokenizer from a file.

        Args:
            file_path: The path to load the file from
            lang_vars: Optional language variables
            token_cls: Optional token class

        Returns:
            A new PunktParagraphTokenizer instance
        """
        sentence_tokenizer = PunktSentenceTokenizer.load(file_path, lang_vars, token_cls)
        return cls(sentence_tokenizer, lang_vars, token_cls or PunktToken)
