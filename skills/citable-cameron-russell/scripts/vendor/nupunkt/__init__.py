"""
nupunkt is a Python library for sentence and paragraph boundary detection based on the Punkt algorithm.

It learns to identify sentence boundaries in text, even when periods are used for
abbreviations, ellipses, and other non-sentence-ending contexts. It also supports
paragraph detection based on sentence boundaries and newlines.
"""

# Core classes
from functools import lru_cache
from pathlib import Path

# Import for type annotations
from typing import Any, Literal, overload

from nupunkt._version import __version__
from nupunkt.core.language_vars import PunktLanguageVars
from nupunkt.core.parameters import PunktParameters
from nupunkt.core.tokens import PunktToken
from nupunkt.document import Document, Paragraph, Sentence

# Models
from nupunkt.layout import blank_page_furniture
from nupunkt.models import load_default_model
from nupunkt.segmentation import Segment, Segmenter, WordSegmenter, contiguous
from nupunkt.tokenizers.paragraph_tokenizer import PunktParagraphTokenizer

# Tokenizers
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer

# Trainers
from nupunkt.trainers.base_trainer import PunktTrainer


@lru_cache(maxsize=64)  # Increased 8x from 8
def load(model: str) -> PunktSentenceTokenizer:
    """
    Load a Punkt model by name or path.

    Args:
        model: Either:
            - "default" for the built-in model
            - A file path to a model (.bin, .json, .json.xz)
            - A model name to search in standard locations

    Returns:
        A PunktSentenceTokenizer initialized with the model

    Model Search Paths:
        When loading by name, models are searched in order:
        1. Package models directory (built-in models)
        2. Platform-specific user data directory:
           - Linux: $XDG_DATA_HOME/nupunkt/models or ~/.local/share/nupunkt/models
           - macOS: ~/Library/Application Support/nupunkt/models
           - Windows: %LOCALAPPDATA%\\nupunkt\\models
        3. Legacy ~/.nupunkt/models (for backward compatibility)
        4. Current working directory/models

    Raises:
        FileNotFoundError: If the model file doesn't exist
        ValueError: If the model format is unsupported

    Note:
        Results are cached, so repeated calls with the same argument return the
        same tokenizer instance. Calling ``add_abbreviation`` or
        ``remove_abbreviation`` on it therefore also affects ``sent_tokenize``
        and every other caller using that model name. Construct a
        ``PunktSentenceTokenizer`` directly if you need an independent instance.
    """
    # Handle default model
    if model == "default":
        return load_default_model()

    # Try as direct file path first
    path = Path(model)
    if path.is_file():
        return PunktSentenceTokenizer.load(path)

    # Search for model by name using platform-specific paths
    from nupunkt.utils.paths import get_model_search_paths

    search_paths = get_model_search_paths()
    for search_dir in search_paths:
        for ext in (".json.gz", ".json.xz", ".bin", ".json"):
            model_path = search_dir / f"{model}{ext}"
            if model_path.exists():
                return PunktSentenceTokenizer.load(model_path)

    # Build helpful error message
    searched_locations = "\n  - ".join(str(p) for p in search_paths)
    raise FileNotFoundError(
        f"Model '{model}' not found. Searched in:\n  - {searched_locations}\n"
        f"To install a model, place it in one of these directories."
    )


# Backward compatibility - keep the old internal functions
@lru_cache(maxsize=8)  # Increased 8x from 1
def _get_default_model():
    """Get the default model, loading it only once."""
    return load("default")


@lru_cache(maxsize=8)  # Increased 8x from 1
def _get_paragraph_tokenizer():
    """Get the paragraph tokenizer with the default model, loading it only once."""
    return PunktParagraphTokenizer(_get_default_model())


@lru_cache(maxsize=64)  # Increased 8x from 8
def _get_adaptive_tokenizer(
    model: str, confidence_threshold: float, enable_dynamic_abbrev: bool
) -> Any:  # Returns AdaptiveTokenizer but avoid import at module level
    """Get an adaptive tokenizer with caching based on parameters."""
    from nupunkt.hybrid import AdaptiveTokenizer

    # Load base model - always use load() to get cached version
    base_model = load(model)

    return AdaptiveTokenizer(
        model_or_text=base_model._params,
        confidence_threshold=confidence_threshold,
        enable_dynamic_abbrev=enable_dynamic_abbrev,
        debug=False,  # Don't cache debug mode
    )


# Function for quick and easy sentence tokenization
def sent_tokenize(
    text: str,
    model: str = "default",
    adaptive: bool = False,
    confidence_threshold: float = 0.7,
    dynamic_abbrev: bool = True,
    return_confidence: bool = False,
    debug: bool = False,
) -> list[str] | list[tuple[str, float]]:
    """
    Tokenize text into sentences.

    Args:
        text: The text to tokenize
        model: Model to use - "default", a file path, or a model name
        adaptive: Enable adaptive tokenization with dynamic pattern recognition
        confidence_threshold: Decision threshold for adaptive mode (0.0-1.0)
                            Higher = more sentence breaks, Lower = fewer breaks
        dynamic_abbrev: Discover abbreviation patterns at runtime (M.I.T., Ph.D.)
        return_confidence: Return (sentence, confidence) tuples instead of just sentences
        debug: Enable debug output showing decision reasoning

    Returns:
        List of sentences, or list of (sentence, confidence) tuples if return_confidence=True

    Examples:
        >>> sent_tokenize("Hello world. How are you?")
        ['Hello world.', 'How are you?']

        >>> # Adaptive mode - dynamically recognizes patterns
        >>> sent_tokenize("She studied at M.I.T. in Cambridge.", adaptive=True)
        ['She studied at M.I.T. in Cambridge.']

        >>> # Get confidence scores
        >>> sent_tokenize("Dr. Smith arrived.", adaptive=True, return_confidence=True)
        [('Dr. Smith arrived.', 0.92)]

        >>> # Tune for high precision (fewer breaks)
        >>> sent_tokenize(text, adaptive=True, confidence_threshold=0.85)

        >>> # Tune for high recall (more breaks)
        >>> sent_tokenize(text, adaptive=True, confidence_threshold=0.5)
    """
    if adaptive:
        # Get cached tokenizer if not in debug mode
        if debug:
            # Debug mode creates a new instance each time
            from nupunkt.hybrid import AdaptiveTokenizer

            base_model = load(model) if model != "default" else None
            tokenizer = AdaptiveTokenizer(
                model_or_text=base_model._params if base_model else None,
                confidence_threshold=confidence_threshold,
                enable_dynamic_abbrev=dynamic_abbrev,
                debug=True,
            )
        else:
            # Use cached tokenizer for better performance
            tokenizer = _get_adaptive_tokenizer(
                model=model,
                confidence_threshold=confidence_threshold,
                enable_dynamic_abbrev=dynamic_abbrev,
            )

        if return_confidence:
            return tokenizer.tokenize_with_confidence(text)
        else:
            return list(tokenizer.tokenize(text))
    else:
        # Standard mode
        if return_confidence:
            raise ValueError("return_confidence is only available in adaptive mode")
        tokenizer = load(model)
        return list(tokenizer.tokenize(text))


# Convenience function for adaptive tokenization
def sent_tokenize_adaptive(
    text: str,
    threshold: float = 0.7,
    model: str = "default",
    return_confidence: bool = False,
    debug: bool = False,
    **kwargs,
) -> list[str] | list[tuple[str, float]]:
    """
    Adaptive sentence tokenization with confidence scoring.

    This is a convenience wrapper for sent_tokenize with adaptive=True.

    Args:
        text: Text to tokenize
        threshold: Confidence threshold (0.0-1.0)
        model: Model to use - "default", a file path, or a model name
        return_confidence: Return (sentence, confidence) tuples
        debug: Enable debug output
        **kwargs: Additional arguments passed to sent_tokenize

    Returns:
        List of sentences, or list of (sentence, confidence) tuples if return_confidence=True

    Examples:
        >>> # Adaptively handle abbreviations
        >>> sent_tokenize_adaptive("She got her Ph.D. at M.I.T. yesterday.")
        ['She got her Ph.D. at M.I.T. yesterday.']

        >>> # Tune for your use case
        >>> sent_tokenize_adaptive(legal_text, threshold=0.5)   # Fewer breaks (more conservative)
        >>> sent_tokenize_adaptive(tweets, threshold=0.85)      # More breaks
    """
    return sent_tokenize(
        text,
        model=model,
        adaptive=True,
        confidence_threshold=threshold,
        return_confidence=return_confidence,
        debug=debug,
        **kwargs,
    )


# Function for paragraph tokenization
def para_tokenize(text: str) -> list[str]:
    """
    Tokenize text into paragraphs using the default pre-trained model.

    Paragraph breaks are identified at sentence boundaries that are
    immediately followed by two or more newlines.

    Args:
        text: The text to tokenize

    Returns:
        A list of paragraphs
    """
    paragraph_tokenizer = _get_paragraph_tokenizer()
    return list(paragraph_tokenizer.tokenize(text))


# Function for getting sentence spans
def sent_spans(text: str) -> list[tuple[int, int]]:
    """
    Get sentence spans (start, end character positions) using the default pre-trained model.

    This is a convenience function for getting sentence spans without having
    to explicitly load a model. The spans are guaranteed to be contiguous,
    covering the entire input text without gaps.

    Args:
        text: The text to segment

    Returns:
        A list of sentence spans as (start_index, end_index) tuples
    """
    tokenizer = _get_default_model()
    return [span for _, span in tokenizer.tokenize_with_spans(text)]


# Function for getting sentence spans with text
def sent_spans_with_text(text: str) -> list[tuple[str, tuple[int, int]]]:
    """
    Get sentences with their spans using the default pre-trained model.

    This is a convenience function for getting sentences with their character spans
    without having to explicitly load a model. The spans are guaranteed to be
    contiguous, covering the entire input text without gaps.

    Args:
        text: The text to segment

    Returns:
        A list of tuples containing (sentence, (start_index, end_index))
    """
    tokenizer = _get_default_model()
    return tokenizer.tokenize_with_spans(text)


# Function for getting paragraph spans
def para_spans(text: str) -> list[tuple[int, int]]:
    """
    Get paragraph spans (start, end character positions) using the default pre-trained model.

    This is a convenience function for getting paragraph spans without having
    to explicitly load a model. The spans are guaranteed to be contiguous,
    covering the entire input text without gaps.

    Args:
        text: The text to segment

    Returns:
        A list of paragraph spans as (start_index, end_index) tuples
    """
    paragraph_tokenizer = _get_paragraph_tokenizer()
    return list(paragraph_tokenizer.span_tokenize(text))


# Function for getting paragraph spans with text
def para_spans_with_text(text: str) -> list[tuple[str, tuple[int, int]]]:
    """
    Get paragraphs with their spans using the default pre-trained model.

    This is a convenience function for getting paragraphs with their character spans
    without having to explicitly load a model. The spans are guaranteed to be
    contiguous, covering the entire input text without gaps.

    Args:
        text: The text to segment

    Returns:
        A list of tuples containing (paragraph, (start_index, end_index))
    """
    paragraph_tokenizer = _get_paragraph_tokenizer()
    return list(paragraph_tokenizer.tokenize_with_spans(text))


# Function for getting sentence spans with adaptive tokenization
def sent_spans_adaptive(
    text: str,
    threshold: float = 0.7,
    model: str = "default",
    dynamic_abbrev: bool = True,
    **kwargs,
) -> list[tuple[int, int]]:
    """
    Get sentence spans using adaptive tokenization with confidence scoring.

    This function provides character-level sentence boundary detection using
    the adaptive algorithm that dynamically recognizes abbreviation patterns.

    Args:
        text: The text to segment
        threshold: Confidence threshold (0.0-1.0)
        model: Model to use - "default", a file path, or a model name
        dynamic_abbrev: Discover abbreviation patterns at runtime
        **kwargs: Additional arguments passed to the tokenizer

    Returns:
        A list of sentence spans as (start_index, end_index) tuples

    Examples:
        >>> # Get spans for text with unknown abbreviations
        >>> spans = sent_spans_adaptive("She studied at M.I.T. in Cambridge.")
        >>> [(0, 35)]  # Single sentence preserved

        >>> # Tune for high precision
        >>> spans = sent_spans_adaptive(legal_text, threshold=0.85)
    """
    # Get cached tokenizer
    tokenizer = _get_adaptive_tokenizer(
        model=model,
        confidence_threshold=threshold,
        enable_dynamic_abbrev=dynamic_abbrev,
    )
    return [span for _, span in tokenizer.tokenize_with_spans(text)]


# Function for getting sentence spans with text using adaptive tokenization
@overload
def sent_spans_with_text_adaptive(
    text: str,
    threshold: float = 0.7,
    model: str = "default",
    dynamic_abbrev: bool = True,
    return_confidence: Literal[False] = False,
    **kwargs,
) -> list[tuple[str, tuple[int, int]]]: ...


@overload
def sent_spans_with_text_adaptive(
    text: str,
    threshold: float = 0.7,
    model: str = "default",
    dynamic_abbrev: bool = True,
    return_confidence: Literal[True] = True,
    **kwargs,
) -> list[tuple[str, tuple[int, int], float]]: ...


def sent_spans_with_text_adaptive(
    text: str,
    threshold: float = 0.7,
    model: str = "default",
    dynamic_abbrev: bool = True,
    return_confidence: bool = False,
    **kwargs,
) -> list[tuple[str, tuple[int, int]]] | list[tuple[str, tuple[int, int], float]]:
    """
    Get sentences with their spans using adaptive tokenization.

    This function provides both the sentence text and character positions using
    the adaptive algorithm. Optionally includes confidence scores.

    Args:
        text: The text to segment
        threshold: Confidence threshold (0.0-1.0)
        model: Model to use - "default", a file path, or a model name
        dynamic_abbrev: Discover abbreviation patterns at runtime
        return_confidence: Include confidence scores in the output
        **kwargs: Additional arguments passed to the tokenizer

    Returns:
        If return_confidence is False:
            List of (sentence, (start_index, end_index)) tuples
        If return_confidence is True:
            List of (sentence, (start_index, end_index), confidence) tuples

    Examples:
        >>> # Get sentences with spans
        >>> results = sent_spans_with_text_adaptive("Dr. Smith studied at M.I.T. today.")
        >>> [('Dr. Smith studied at M.I.T. today.', (0, 34))]

        >>> # With confidence scores
        >>> results = sent_spans_with_text_adaptive(text, return_confidence=True)
        >>> [('First sentence.', (0, 15), 0.92), ('Second one.', (15, 26), 0.88)]
    """
    # Get cached tokenizer
    tokenizer = _get_adaptive_tokenizer(
        model=model,
        confidence_threshold=threshold,
        enable_dynamic_abbrev=dynamic_abbrev,
    )

    if return_confidence:
        # Get sentences with confidence scores
        sentences_with_conf = tokenizer.tokenize_with_confidence(text)

        # Get spans
        spans_with_text = tokenizer.tokenize_with_spans(text)

        # Combine confidence scores with spans
        results = []
        for (sent_conf, conf), (sent_span, span) in zip(sentences_with_conf, spans_with_text):
            # Verify sentences match (they should)
            if sent_conf.strip() != sent_span.strip():
                # Handle potential whitespace differences
                conf_idx = next(
                    (
                        i
                        for i, (s, _) in enumerate(sentences_with_conf)
                        if sent_span.strip() == s.strip()
                    ),
                    None,
                )
                if conf_idx is not None:
                    conf = sentences_with_conf[conf_idx][1]
            results.append((sent_span, span, conf))
        return results
    else:
        return tokenizer.tokenize_with_spans(text)


# ---------------------------------------------------------------------------
# Standard segmentation interface
#
# One shape for every level (word, sentence, paragraph):
#   <level>s(text)          -> list[str]
#   <level>_spans(text)     -> list[tuple[int, int]]
#   <level>_segments(text)  -> list[Segment]   (text, start, end)
# and ``segmenter(level)`` for a reusable object with generator forms
# (``iter_segments``, ``iter_texts``, ``iter_spans``).
#
# Spans are tight: text[start:end] == segment text, whitespace stays in the
# gaps. Use ``contiguous(segments, text)`` for gap-free coverage.
# ---------------------------------------------------------------------------

SegmentLevel = Literal["word", "sentence", "paragraph"]

_WORD_SEGMENTER = WordSegmenter()


@lru_cache(maxsize=64)
def _get_paragraph_tokenizer_for(model: str) -> PunktParagraphTokenizer:
    """Get a paragraph tokenizer for a named model, loading it only once."""
    return PunktParagraphTokenizer(load(model))


def segmenter(
    level: SegmentLevel = "sentence",
    model: str = "default",
    adaptive: bool = False,
    confidence_threshold: float = 0.7,
    dynamic_abbrev: bool = True,
) -> Segmenter:
    """
    Get a reusable segmenter for a level of segmentation.

    The returned object exposes ``segments``, ``texts`` and ``spans`` (lists) and
    ``iter_segments``, ``iter_texts`` and ``iter_spans`` (generators).

    Args:
        level: "word", "sentence" or "paragraph"
        model: Model to use for sentences and paragraphs - "default", a path or a name
        adaptive: Use the adaptive sentence tokenizer (sentence level only)
        confidence_threshold: Decision threshold for adaptive mode (0.0-1.0)
        dynamic_abbrev: Discover abbreviation patterns at runtime (adaptive mode)

    Returns:
        A segmenter for the requested level

    Examples:
        >>> seg = segmenter("sentence")
        >>> for sentence in seg.iter_segments(text):
        ...     print(sentence.start, sentence.end, sentence.text)
    """
    if level == "word":
        return _WORD_SEGMENTER
    if level == "sentence":
        if adaptive:
            return _get_adaptive_tokenizer(model, confidence_threshold, dynamic_abbrev)
        return load(model)
    if level == "paragraph":
        return _get_paragraph_tokenizer_for(model)
    raise ValueError(
        f"Unknown segmentation level {level!r}; expected 'word', 'sentence' or 'paragraph'"
    )


# --- words -----------------------------------------------------------------


def words(text: str) -> list[str]:
    """
    Split text into words using Punkt's word tokenizer.

    Trailing periods stay attached ("Dr.") and possessives are one token
    ("Smith's"); these are the tokens the sentence tokenizer reasons about.

    Args:
        text: The text to segment

    Returns:
        A list of words
    """
    return _WORD_SEGMENTER.texts(text)


def word_spans(text: str) -> list[tuple[int, int]]:
    """
    Get the (start, end) character span of each word.

    Args:
        text: The text to segment

    Returns:
        A list of (start, end) tuples; ``text[start:end]`` is the word
    """
    return _WORD_SEGMENTER.spans(text)


def word_segments(text: str) -> list[Segment]:
    """
    Get each word with its character span.

    Args:
        text: The text to segment

    Returns:
        A list of ``Segment(text, start, end)``
    """
    return _WORD_SEGMENTER.segments(text)


# --- sentences ---------------------------------------------------------------


def sentences(
    text: str,
    model: str = "default",
    adaptive: bool = False,
    confidence_threshold: float = 0.7,
    dynamic_abbrev: bool = True,
    paragraph_breaks: bool = True,
    line_breaks: bool = False,
) -> list[str]:
    """
    Split text into sentences.

    Args:
        text: The text to segment
        model: Model to use - "default", a file path, or a model name
        adaptive: Use the adaptive tokenizer with dynamic abbreviation detection
        confidence_threshold: Decision threshold for adaptive mode (0.0-1.0)
        dynamic_abbrev: Discover abbreviation patterns at runtime (adaptive mode)
        paragraph_breaks: Blank lines are hard sentence boundaries (see ``nupunkt.layout``)
        line_breaks: Heading and list-item line breaks are boundaries too (opt-in)

    Returns:
        A list of sentences, without surrounding whitespace
    """
    return segmenter("sentence", model, adaptive, confidence_threshold, dynamic_abbrev).texts(
        text, paragraph_breaks=paragraph_breaks, line_breaks=line_breaks
    )


def sentence_spans(
    text: str,
    model: str = "default",
    adaptive: bool = False,
    confidence_threshold: float = 0.7,
    dynamic_abbrev: bool = True,
    paragraph_breaks: bool = True,
    line_breaks: bool = False,
) -> list[tuple[int, int]]:
    """
    Get the (start, end) character span of each sentence.

    Spans are tight: ``text[start:end]`` is the sentence with no surrounding
    whitespace. Use ``contiguous()`` for gap-free spans.

    Args:
        text: The text to segment
        model: Model to use - "default", a file path, or a model name
        adaptive: Use the adaptive tokenizer with dynamic abbreviation detection
        confidence_threshold: Decision threshold for adaptive mode (0.0-1.0)
        dynamic_abbrev: Discover abbreviation patterns at runtime (adaptive mode)
        paragraph_breaks: Blank lines are hard sentence boundaries (see ``nupunkt.layout``)
        line_breaks: Heading and list-item line breaks are boundaries too (opt-in)

    Returns:
        A list of (start, end) tuples
    """
    return segmenter("sentence", model, adaptive, confidence_threshold, dynamic_abbrev).spans(
        text, paragraph_breaks=paragraph_breaks, line_breaks=line_breaks
    )


def sentence_segments(
    text: str,
    model: str = "default",
    adaptive: bool = False,
    confidence_threshold: float = 0.7,
    dynamic_abbrev: bool = True,
    paragraph_breaks: bool = True,
    line_breaks: bool = False,
) -> list[Segment]:
    """
    Get each sentence with its character span.

    Args:
        text: The text to segment
        model: Model to use - "default", a file path, or a model name
        adaptive: Use the adaptive tokenizer with dynamic abbreviation detection
        confidence_threshold: Decision threshold for adaptive mode (0.0-1.0)
        dynamic_abbrev: Discover abbreviation patterns at runtime (adaptive mode)
        paragraph_breaks: Blank lines are hard sentence boundaries (see ``nupunkt.layout``)
        line_breaks: Heading and list-item line breaks are boundaries too (opt-in)

    Returns:
        A list of ``Segment(text, start, end)``
    """
    return segmenter("sentence", model, adaptive, confidence_threshold, dynamic_abbrev).segments(
        text, paragraph_breaks=paragraph_breaks, line_breaks=line_breaks
    )


# --- paragraphs --------------------------------------------------------------


def paragraphs(text: str, model: str = "default") -> list[str]:
    """
    Split text into paragraphs.

    A paragraph break is a sentence boundary followed by a blank line.

    Args:
        text: The text to segment
        model: Model to use - "default", a file path, or a model name

    Returns:
        A list of paragraphs, without surrounding whitespace
    """
    return _get_paragraph_tokenizer_for(model).texts(text)


def paragraph_spans(text: str, model: str = "default") -> list[tuple[int, int]]:
    """
    Get the (start, end) character span of each paragraph.

    Spans are tight: ``text[start:end]`` is the paragraph with no surrounding
    whitespace. Use ``contiguous()`` for gap-free spans.

    Args:
        text: The text to segment
        model: Model to use - "default", a file path, or a model name

    Returns:
        A list of (start, end) tuples
    """
    return _get_paragraph_tokenizer_for(model).spans(text)


def paragraph_segments(text: str, model: str = "default") -> list[Segment]:
    """
    Get each paragraph with its character span.

    Args:
        text: The text to segment
        model: Model to use - "default", a file path, or a model name

    Returns:
        A list of ``Segment(text, start, end)``
    """
    return _get_paragraph_tokenizer_for(model).segments(text)


# --- all levels in one pass ------------------------------------------------------


def segment(
    text: str,
    model: str | PunktSentenceTokenizer = "default",
    adaptive: bool = False,
    confidence_threshold: float = 0.7,
    dynamic_abbrev: bool = True,
    paragraph_breaks: bool = True,
    line_breaks: bool = False,
) -> Document:
    """
    Segment text into paragraphs, sentences and words in a single pass.

    Sentence segmentation runs once; paragraphs are derived from the same
    sentence boundaries (a boundary followed by a blank line) and words are
    computed lazily per sentence. The flat lists match the per-level functions:
    ``doc.paragraphs == paragraph_segments(text)``,
    ``doc.sentences == sentence_segments(text)`` and
    ``doc.words == word_segments(text)``.

    Args:
        text: The text to segment
        model: "default", a file path, a model name, or a ``PunktSentenceTokenizer``
        adaptive: Use the adaptive sentence tokenizer (ignored when ``model`` is a
            tokenizer object)
        confidence_threshold: Decision threshold for adaptive mode (0.0-1.0)
        dynamic_abbrev: Discover abbreviation patterns at runtime (adaptive mode)
        paragraph_breaks: Blank lines separate paragraphs and end sentences (see
            ``nupunkt.layout``); ``False`` derives paragraphs from Punkt boundaries
        line_breaks: Heading and list-item line breaks also end sentences (opt-in)

    Returns:
        A :class:`Document` with ``paragraphs`` -> ``sentences`` -> ``words``

    Examples:
        >>> doc = segment("First one. Second one.\n\nNew paragraph.")
        >>> [len(p.sentences) for p in doc.paragraphs]
        [2, 1]
        >>> doc.sentences[1].words[0]
        Segment(text='Second', start=11, end=17)
    """
    tokenizer: PunktSentenceTokenizer
    if not isinstance(model, str):
        tokenizer = model
    elif adaptive:
        tokenizer = _get_adaptive_tokenizer(model, confidence_threshold, dynamic_abbrev)
    else:
        tokenizer = load(model)
    return Document.from_tokenizer(text, tokenizer, paragraph_breaks, line_breaks)


__all__ = [
    "__version__",
    "PunktParameters",
    "PunktLanguageVars",
    "PunktToken",
    "PunktTrainer",
    "PunktSentenceTokenizer",
    "PunktParagraphTokenizer",
    "load",
    "load_default_model",
    # Standard segmentation interface
    "Segment",
    "Segmenter",
    "WordSegmenter",
    "contiguous",
    "blank_page_furniture",
    "segmenter",
    "words",
    "word_spans",
    "word_segments",
    "sentences",
    "sentence_spans",
    "sentence_segments",
    "paragraphs",
    "paragraph_spans",
    "paragraph_segments",
    "segment",
    "Document",
    "Paragraph",
    "Sentence",
    # Legacy interface (kept for backward compatibility)
    "sent_tokenize",
    "sent_tokenize_adaptive",
    "sent_spans",
    "sent_spans_with_text",
    "sent_spans_adaptive",
    "sent_spans_with_text_adaptive",
    "para_tokenize",
    "para_spans",
    "para_spans_with_text",
]
