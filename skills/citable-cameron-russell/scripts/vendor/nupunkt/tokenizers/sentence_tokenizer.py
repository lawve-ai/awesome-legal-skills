"""
Sentence tokenizer module for nupunkt.

This module provides the main tokenizer class for sentence boundary detection.
"""

import re
from pathlib import Path
from typing import Any, Callable, Iterator

from nupunkt.core.base import PunktBase, is_abbreviation
from nupunkt.core.constants import (
    DOC_TOKENIZE_CACHE_SIZE,
    ORTHO_BEG_LC,
    ORTHO_CACHE_SIZE,
    ORTHO_LC,
    ORTHO_MID_UC,
    ORTHO_UC,
    PARA_TOKENIZE_CACHE_SIZE,
    SENT_STARTER_CACHE_SIZE,
    WHITESPACE_CACHE_SIZE,
)
from nupunkt.core.language_vars import PunktLanguageVars
from nupunkt.core.parameters import PunktParameters
from nupunkt.core.tokens import PunktToken, _check_is_ellipsis, _check_is_initial, _derived
from nupunkt.layout import layout_segments
from nupunkt.segmentation import Segment, SegmenterMixin
from nupunkt.trainers.base_trainer import PunktTrainer
from nupunkt.utils.iteration import pair_iter


def ortho_heuristic(ortho_context: int, first_upper: bool, first_lower: bool) -> bool | str:
    """
    Decide from orthographic context whether a token starts a sentence.

    Args:
        ortho_context: The orthographic context flags for the token type
        first_upper: Whether the token's first character is uppercase
        first_lower: Whether the token's first character is lowercase

    Returns:
        True if the token starts a sentence, False if not, "unknown" if uncertain
    """
    if first_upper and (ortho_context & ORTHO_LC) and not (ortho_context & ORTHO_MID_UC):
        return True
    if first_lower and ((ortho_context & ORTHO_UC) or not (ortho_context & ORTHO_BEG_LC)):
        return False
    return "unknown"


def _looks_like_model_path(value: str) -> bool:
    """Return True if a string names an existing file (never raises for long text)."""
    if len(value) > 4096 or "\n" in value:
        return False
    try:
        return Path(value).is_file()
    except (OSError, ValueError):
        return False


# First-pass outcomes of a token string, as computed by ``PunktBase._first_pass_annotation``
_FP_NONE = 0  # not a candidate (no sentence-final punctuation)
_FP_BREAK = 1  # sentence break
_FP_ABBR = 2  # known abbreviation
_FP_ELLIPSIS = 3  # ellipsis (decided by the second pass)

# Closing quotes, brackets and markdown emphasis that may trail a sentence end
_CLOSING_CHARS = frozenset("\"')]}\u201d\u2019\u00bb*")
_CLOSING_CHARS_RE = re.escape("".join(sorted(_CLOSING_CHARS)))

# A candidate context: the chunk holding the sentence-ending character (plus any
# glued closing punctuation) and the whitespace and chunk that follow it.
Context = tuple[str, str]

# ``period_context_pattern`` -> candidate pattern used by ``_match_potential_end_contexts``
_CANDIDATE_PATTERNS: dict[re.Pattern, re.Pattern] = {}
# Tokenizer class -> whether the string-level decision engine reproduces its annotation
_ENGINE_CLASSES: dict[type, bool] = {}


def _candidate_pattern(period_context: re.Pattern) -> re.Pattern:
    """
    Extend a period-context pattern for single-pass candidate scanning.

    The extension skips periods that continue a spaced ellipsis (". . .", only the
    last period is a candidate) and captures two groups that delimit the context
    handed to the annotation passes: ``_tail``, any closing punctuation glued to
    the sentence-ending character (it belongs to the token before the boundary),
    and ``_nw``, the whitespace and the whole next whitespace-delimited chunk.
    """
    pattern = _CANDIDATE_PATTERNS.get(period_context)
    if pattern is None:
        pattern = re.compile(
            f"(?:{period_context.pattern})"
            + r"(?!(?<=\.)\s+\.)(?=(?P<_tail>["
            + _CLOSING_CHARS_RE
            + r"]*)(?P<_nw>\s*\S*))",
            period_context.flags,
        )
        _CANDIDATE_PATTERNS[period_context] = pattern
    return pattern


class PunktSentenceTokenizer(SegmenterMixin, PunktBase):
    """
    Sentence tokenizer using the Punkt algorithm.

    This class uses trained parameters to tokenize text into sentences,
    handling abbreviations, collocations, and other special cases.
    """

    # Pre-compiled regex patterns
    # Everything up to and including the last whitespace character (match with endpos)
    _RE_LAST_WS = re.compile(r".*\s", re.DOTALL)
    # A period that starts or continues a spaced ellipsis (". . .")
    _RE_SPACED_ELLIPSIS_AT = re.compile(r"\.(?:\s+\.)+")
    # "!" or "?" followed by whitespace and an uppercase letter: a certain break
    _RE_EXCL_QUEST_BREAK = re.compile(r"[!?]\s(?=[^\W\d_])")

    # Set of common punctuation marks for fast lookup
    _PUNCT_CHARS = frozenset([";", ":", ",", ".", "!", "?"])

    # Common sentence-ending punctuation as a frozenset for O(1) lookups
    _SENT_END_CHARS = frozenset([".", "!", "?", "\u2026"])

    # A line-start list enumerator ("1.", "(a).", "IV.") is not a sentence by itself
    _RE_LINE_ENUMERATOR = re.compile(r"[ \t]*\(?(?:\d{1,3}|[A-Za-z]|[ivxlcIVXLC]{1,6})\)?\.")
    # Closing punctuation that may trail a sentence-ending character
    _CLOSING_CHARS = _CLOSING_CHARS
    # Per-abbreviation break rates (``PunktParameters.abbrev_break_rates``): an
    # abbreviation seen at least BREAK_RATE_MIN_COUNT times before a capitalized word
    # ends the sentence when it did so in at least BREAK_RATE_HIGH of those cases. With
    # BREAK_RATE_LOW set, a rate at or below it vetoes the sentence-starter heuristic;
    # it is off by default because the abbreviation's rate ignores the follower
    # ("U.S. Government" vs. "U.S. He"). Instances may override these attributes.
    BREAK_RATE_HIGH: float = 0.8
    BREAK_RATE_LOW: float | None = None
    BREAK_RATE_MIN_COUNT: int = 20

    # Prenominal titles: never sentence-final before a capitalized name
    _TITLE_ABBREVS = frozenset(
        [
            "mr",
            "mrs",
            "ms",
            "dr",
            "prof",
            "hon",
            "rev",
            "gen",
            "lt",
            "col",
            "capt",
            "sgt",
            "gov",
            "sen",
            "rep",
            "messrs",
            "mme",
            "mlle",
        ]
    )

    # Opt-in: treat "!" or "?" followed by a lowercase word as sentence-internal ("Yahoo! in").
    # Off by default: it costs recall on informal web text where sentences start lowercase.
    EXCL_QUEST_LOWERCASE_CONTINUES: bool = False

    # Words that continue a sentence after an ellipsis despite being capitalized
    _ELLIPSIS_CONTINUERS = frozenset(
        ["I", "I'm", "I'll", "I'd", "I've", "I\u2019m", "I\u2019ll", "I\u2019d", "I\u2019ve"]
    )

    # Bounds of the string-level decision memos (see ``_decision_state``)
    _DECISION_MEMO_SIZE = 32768
    _DECISION_CONTEXT_MAX_LEN = 200
    # Methods the string-level decision engine re-implements; a subclass overriding
    # any of them (e.g. AdaptiveTokenizer) is decided on PunktToken objects instead.
    _ENGINE_HOOKS = (
        "text_contains_sentbreak",
        "_annotate_tokens",
        "_annotate_first_pass",
        "_annotate_second_pass",
        "_first_pass_annotation",
        "_second_pass_annotation",
        "_ortho_heuristic",
        "_is_sent_starter",
        "_break_rate_decision",
        "_tokenize_words",
    )

    @staticmethod
    def _is_next_char_uppercase(text: str, pos: int, text_len: int) -> bool:
        """
        Check if the next non-whitespace character after a position is uppercase.

        Args:
            text: The text to check
            pos: The position to start checking from
            text_len: The length of the text

        Returns:
            True if the next non-whitespace character is uppercase
        """
        i = pos
        while i < text_len and text[i].isspace():
            i += 1
        return i < text_len and text[i].isupper()

    @property
    def abbreviations(self) -> frozenset[str]:
        """
        The abbreviations this tokenizer knows, lowercased and without trailing periods.

        This is a read-only snapshot; use ``add_abbreviation`` / ``remove_abbreviation``
        to change the set. Multi-part abbreviations keep their internal periods
        (``"u.s.c"``), and ``"..."`` stands for the ellipsis.
        """
        return frozenset(self._params.abbrev_types)

    @property
    def parameters(self) -> PunktParameters:
        """
        The trained parameters backing this tokenizer.

        Mutating the returned object changes this tokenizer (and any other tokenizer
        sharing it). After in-place edits that keep every collection's size, call
        ``clear_decision_cache()``.
        """
        return self._params

    def add_abbreviation(self, abbrev: str) -> None:
        """Add a single abbreviation to the tokenizer.

        Args:
            abbrev: The abbreviation to add (with or without trailing period)
        """
        if abbrev.endswith("."):
            abbrev = abbrev[:-1]
        self._params.abbrev_types.add(abbrev.lower())
        self.clear_decision_cache()

    def add_abbreviations(self, abbrevs: list[str]) -> None:
        """Add multiple abbreviations to the tokenizer.

        Args:
            abbrevs: List of abbreviations to add
        """
        for abbrev in abbrevs:
            self.add_abbreviation(abbrev)

    def remove_abbreviation(self, abbrev: str) -> None:
        """Remove an abbreviation from the tokenizer.

        Args:
            abbrev: The abbreviation to remove
        """
        if abbrev.endswith("."):
            abbrev = abbrev[:-1]
        self._params.abbrev_types.discard(abbrev.lower())
        self.clear_decision_cache()

    def clear_decision_cache(self) -> None:
        """
        Forget memoized boundary decisions.

        Decisions are memoized per parameter set and dropped automatically when the
        parameters are replaced, when a parameter collection is replaced or changes
        size, and on ``add_abbreviation``/``remove_abbreviation`` (on any tokenizer
        sharing the parameters). Call this after editing ``_params`` in place in a
        way that keeps every collection's size, e.g. changing an ``ortho_context``
        value.
        """
        generation = self._params.__dict__.get("_decision_generation", 0)
        self._params.__dict__["_decision_generation"] = generation + 1

    def __init__(
        self,
        model_or_text: Any | None = None,
        verbose: bool = False,
        lang_vars: PunktLanguageVars | None = None,
        token_cls: type[PunktToken] = PunktToken,
        include_common_abbrevs: bool = True,  # Whether to include common abbreviations
        cache_size: int = DOC_TOKENIZE_CACHE_SIZE,  # Size of the sentence tokenization cache
        paragraph_cache_size: int = PARA_TOKENIZE_CACHE_SIZE,  # Size of the paragraph-level cache
        enable_paragraph_caching: bool = False,  # Whether to enable paragraph-level caching
        ortho_cache_size: int = ORTHO_CACHE_SIZE,  # Deprecated: no longer used
        sent_starter_cache_size: int = SENT_STARTER_CACHE_SIZE,  # Deprecated: no longer used
        whitespace_cache_size: int = WHITESPACE_CACHE_SIZE,  # Deprecated: no longer used
    ) -> None:
        """
        Initialize the tokenizer with a model, training text, or parameters.

        Args:
            model_or_text: Can be:
                - None: Initialize with empty parameters
                - str: Either training text or a path to a model file
                - PunktParameters: Pre-trained parameters to use
            verbose: Whether to show verbose training information
            lang_vars: Language-specific variables
            token_cls: The token class to use
            include_common_abbrevs: Whether to include common abbreviations
            cache_size: Size of the document-level tokenization cache
            paragraph_cache_size: Size of the paragraph-level cache
            enable_paragraph_caching: Whether to enable paragraph-level caching
            ortho_cache_size: Deprecated and ignored (kept for API compatibility)
            sent_starter_cache_size: Deprecated and ignored (kept for API compatibility)
            whitespace_cache_size: Deprecated and ignored (kept for API compatibility)
        """
        super().__init__(lang_vars, token_cls)

        # Store cache sizes
        self._cache_size = cache_size
        self._paragraph_cache_size = paragraph_cache_size
        self._enable_paragraph_caching = enable_paragraph_caching

        # Handle different input types
        if model_or_text:
            if isinstance(model_or_text, str):
                # Check if it's a file path (long or multi-line strings are text)
                path = Path(model_or_text)
                if _looks_like_model_path(model_or_text) and (
                    path.suffix in (".bin", ".json", ".xz") or str(path).endswith(".json.xz")
                ):
                    # Load from file
                    self._params = PunktParameters.load(path)
                    if verbose:
                        print(f"Loaded model from {path}")
                else:
                    # Treat as training text
                    trainer = PunktTrainer(
                        model_or_text,
                        verbose=verbose,
                        lang_vars=self._lang_vars,
                        token_cls=self._Token,
                        include_common_abbrevs=include_common_abbrevs,
                    )
                    self._params = trainer.get_params()
            else:
                # Assume it's PunktParameters
                self._params = model_or_text

        # Add common abbreviations if using an existing parameter set
        if (
            include_common_abbrevs
            and not (isinstance(model_or_text, str) and not _looks_like_model_path(model_or_text))
            and hasattr(PunktTrainer, "COMMON_ABBREVS")
        ):
            for abbr in PunktTrainer.COMMON_ABBREVS:
                self._params.abbrev_types.add(abbr)
            if verbose:
                print(
                    f"Added {len(PunktTrainer.COMMON_ABBREVS)} common abbreviations to tokenizer."
                )

    def to_json(self) -> dict[str, Any]:
        """
        Convert the tokenizer to a JSON-serializable dictionary.

        Returns:
            A JSON-serializable dictionary
        """
        # Create a trainer to handle serialization
        trainer = PunktTrainer(lang_vars=self._lang_vars, token_cls=self._Token)

        # Set the parameters
        trainer._params = self._params
        trainer._finalized = True

        return trainer.to_json()

    @classmethod
    def from_json(
        cls,
        data: dict[str, Any],
        lang_vars: PunktLanguageVars | None = None,
        token_cls: type[PunktToken] | None = None,
    ) -> "PunktSentenceTokenizer":
        """
        Create a PunktSentenceTokenizer from a JSON dictionary.

        Args:
            data: The JSON dictionary
            lang_vars: Optional language variables
            token_cls: Optional token class

        Returns:
            A new PunktSentenceTokenizer instance
        """
        # First create a trainer from the JSON data
        trainer = PunktTrainer.from_json(data, lang_vars, token_cls)

        # Then create a tokenizer with the parameters
        return cls(trainer.get_params(), lang_vars=lang_vars, token_cls=token_cls or PunktToken)

    def save(
        self, file_path: str | Path, compress: bool = True, compression_level: int = 1
    ) -> None:
        """
        Save the tokenizer to a JSON file, optionally with LZMA compression.

        Args:
            file_path: The path to save the file to
            compress: Whether to compress the file using LZMA (default: True)
            compression_level: LZMA compression level (0-9), lower is faster but less compressed
        """
        from nupunkt.utils.compression import save_compressed_json

        save_compressed_json(
            self.to_json(), file_path, level=compression_level, use_compression=compress
        )

    @classmethod
    def load(
        cls,
        file_path: str | Path,
        lang_vars: PunktLanguageVars | None = None,
        token_cls: type[PunktToken] | None = None,
    ) -> "PunktSentenceTokenizer":
        """
        Load a PunktSentenceTokenizer from a JSON file, which may be compressed with LZMA.

        Args:
            file_path: The path to load the file from
            lang_vars: Optional language variables
            token_cls: Optional token class

        Returns:
            A new PunktSentenceTokenizer instance
        """
        from nupunkt.utils.compression import load_compressed_json

        data = load_compressed_json(file_path)
        return cls.from_json(data, lang_vars, token_cls)

    def reconfigure(self, config: dict[str, Any]) -> None:
        """
        Reconfigure the tokenizer with new settings.

        Args:
            config: A dictionary with configuration settings
        """
        # Create a temporary trainer
        trainer = PunktTrainer.from_json(config, self._lang_vars, self._Token)

        # If parameters are present in the config, use them
        if "parameters" in config:
            self._params = PunktParameters.from_json(config["parameters"])
        else:
            # Otherwise just keep our current parameters
            trainer._params = self._params
            trainer._finalized = True

    # Layout defaults for the segmentation interface (``iter_segments`` and the
    # methods derived from it). The legacy ``tokenize`` / ``span_tokenize`` methods
    # never apply layout rules. See :mod:`nupunkt.layout`.
    paragraph_breaks: bool = True
    line_breaks: bool = False

    def iter_segments(self, text: str, **options: Any) -> Iterator[Segment]:
        """
        Yield each sentence of ``text`` with its tight character span.

        This is the primitive behind ``segments``, ``texts``, ``spans`` and their
        ``iter_*`` forms (see :mod:`nupunkt.segmentation`). Unlike ``span_tokenize``,
        the spans never include surrounding whitespace, and layout rules apply.

        Args:
            text: The text to segment
            paragraph_breaks: Blank lines are hard sentence boundaries (default:
                the instance attribute, ``True``)
            line_breaks: Heading and list-item line breaks are boundaries too
                (default: the instance attribute, ``False``)
        """
        paragraph_breaks = options.pop("paragraph_breaks", None)
        line_breaks = options.pop("line_breaks", None)
        if options:
            raise TypeError(f"unexpected options: {sorted(options)}")
        if paragraph_breaks is None:
            paragraph_breaks = self.paragraph_breaks
        if line_breaks is None:
            line_breaks = self.line_breaks
        yield from layout_segments(text, self.span_tokenize, paragraph_breaks, line_breaks)

    def tokenize(self, text: str, realign_boundaries: bool = True) -> list[str]:
        """
        Tokenize text into sentences.

        Args:
            text: The text to tokenize
            realign_boundaries: Whether to realign sentence boundaries

        Returns:
            A list of sentences
        """
        return list(self.sentences_from_text(text, realign_boundaries))

    def span_tokenize(
        self, text: str, realign_boundaries: bool = True
    ) -> Iterator[tuple[int, int]]:
        """
        Tokenize text into sentence spans.

        Args:
            text: The text to tokenize
            realign_boundaries: Whether to realign sentence boundaries

        Yields:
            Tuples of (start, end) character offsets for each sentence
        """
        slices = list(self._slices_from_text(text))
        if realign_boundaries:
            slices = list(self._realign_boundaries(text, slices))
        for s in slices:
            yield (s.start, s.stop)

    def sentences_from_text(self, text: str, realign_boundaries: bool = True) -> list[str]:
        """
        Extract sentences from text.

        Args:
            text: The text to tokenize
            realign_boundaries: Whether to realign sentence boundaries

        Returns:
            A list of sentences
        """
        return [text[start:stop] for start, stop in self.span_tokenize(text, realign_boundaries)]

    def tokenize_with_spans(
        self, text: str, realign_boundaries: bool = True
    ) -> list[tuple[str, tuple[int, int]]]:
        """
        Tokenize text into sentences with their character spans.

        Each span is a tuple of (start_idx, end_idx) where start_idx is inclusive
        and end_idx is exclusive (following Python's slicing convention).
        The spans are guaranteed to be contiguous, covering the entire input text without gaps.

        Args:
            text: The text to tokenize
            realign_boundaries: Whether to realign sentence boundaries

        Returns:
            List of tuples containing (sentence, (start_index, end_index))
        """
        if not text:
            return []

        # Get the raw sentence spans
        spans = list(self.span_tokenize(text, realign_boundaries))
        if not spans:
            return [(text, (0, len(text)))]

        # Make spans contiguous by extending each span to the start of the next
        result = []
        for i, (start, _) in enumerate(spans):
            if i < len(spans) - 1:
                # Extend this span to the start of the next sentence
                next_start = spans[i + 1][0]
                result.append((text[start:next_start], (start, next_start)))
            else:
                # Last span extends to the end of text
                result.append((text[start : len(text)], (start, len(text))))

        return result

    @staticmethod
    def _get_last_whitespace_index(text: str) -> int:
        """
        Find the index of the last whitespace character in a string.

        Args:
            text: The text to search

        Returns:
            The index of the last whitespace character, or 0 if none
        """
        for i in range(len(text) - 1, -1, -1):
            if text[i].isspace():
                return i
        return 0

    def _match_potential_end_contexts(self, text: str) -> list[tuple[re.Match, Context]]:
        """
        Find potential sentence end contexts in text.

        Each context is a pair ``(before, after)``: ``before`` runs from the start
        of the word holding the sentence-ending character through any closing
        punctuation glued to it, and ``after`` is the whitespace and the whole next
        word. The annotation passes decide the tokens of ``before``; the first token
        of ``after`` only provides context. Candidates within one whitespace-free
        chunk share a context; the last of them is reported.

        Args:
            text: The text to search

        Returns:
            A list of (match, (before, after)) tuples for potential sentence ends
        """
        matches: list[tuple[re.Match, Context]] = []
        if len(text) < 2:
            return matches

        # Quick check for any sentence-ending characters
        if not any(end_char in text for end_char in self._SENT_END_CHARS):
            return matches

        last_ws = self._RE_LAST_WS.match
        prev_start = 0
        prev_stop = 0
        prev_split = 0
        prev_end = 0
        previous: re.Match | None = None

        for match in _candidate_pattern(self._lang_vars.period_context_pattern).finditer(text):
            match_pos = match.start()
            # The word starts after the last whitespace since the previous candidate;
            # without one, this candidate shares the previous candidate's context.
            m = last_ws(text, prev_stop, match_pos)
            word_start = m.end() if m and m.end() > prev_stop + 1 else prev_start
            if match_pos > 1 and text[match_pos - 1].isspace():
                # Last period of a spaced ellipsis: start the context before the run
                # so it tokenizes as one ellipsis token.
                run_start = match_pos
                while True:
                    i = run_start - 1
                    while i >= 0 and text[i].isspace():
                        i -= 1
                    if i >= 0 and i < run_start - 1 and text[i] == ".":
                        run_start = i
                    else:
                        break
                if run_start < match_pos:
                    m = last_ws(text[prev_stop:run_start].rstrip())
                    run_word = prev_stop + m.end() if m and m.end() > 1 else prev_start
                    word_start = min(word_start, run_word)
            if previous is not None and prev_stop <= word_start:
                matches.append((previous, (text[prev_start:prev_split], text[prev_split:prev_end])))
            previous = match
            prev_start = word_start
            prev_stop = match_pos
            prev_split = match.end("_tail")
            prev_end = match.end("_nw")

        if previous is not None:
            matches.append((previous, (text[prev_start:prev_split], text[prev_split:prev_end])))

        return matches

    def _slices_from_text(self, text: str) -> Iterator[slice]:
        """
        Find slices of sentences in text.

        Args:
            text: The text to slice

        Yields:
            slice objects for each sentence
        """
        # Find the last non-whitespace character index directly without creating a copy
        text_len = len(text)
        text_end = text_len - 1
        while text_end >= 0 and text[text_end].isspace():
            text_end -= 1
        # Add 1 to include the non-whitespace character itself
        if text_end >= 0:
            text_end += 1
        else:
            text_end = 0

        last_break = 0
        closing = self._CLOSING_CHARS
        # Decide on strings (memoized per context) unless a subclass customizes the
        # token-level annotation, in which case every context goes through it.
        if self._uses_decision_engine():
            contains_sentbreak = self._decision_state()[3]
        else:
            contains_sentbreak = self._context_contains_sentbreak
        # Get all potential sentence breaks in one go
        for match, context in self._match_potential_end_contexts(text):
            pos = match.start()
            if text[pos] == "." and self._is_line_start_enumerator(text, pos):
                continue
            pos = match.end()
            # A run of terminal punctuation ("?!", "!!!", "! ! !") ends the sentence at
            # its last character
            if pos < text_len and text[pos] in "!?":
                continue
            k = pos
            while k < text_len and text[k] in " \t":
                k += 1
            if (
                k > pos
                and k < text_len
                and text[k] in "!?"
                and (k + 1 == text_len or text[k + 1].isspace() or text[k + 1] in "!?")
            ):
                continue
            # "!" or "?" followed by a lowercase word on the same line is not a break
            # ("Yahoo! in 1995", "he asked, what? and left")
            if (
                self.EXCL_QUEST_LOWERCASE_CONTINUES
                and text[pos - 1] in "!?"
                and k < text_len
                and text[k].islower()
            ):
                continue
            if pos < text_len and text[pos] in closing:
                # End char followed by closing punctuation, then a lowercase word on the
                # same line: the quotation continues the sentence ("Is it?" he asked.)
                while pos < text_len and text[pos] in closing:
                    pos += 1
                while pos < text_len and text[pos] in " \t":
                    pos += 1
                if pos < text_len and text[pos].islower():
                    continue
            if contains_sentbreak(context):
                yield slice(last_break, match.end())
                # Skip whitespace when setting the next break position
                if match.group("next_tok"):
                    # next_tok already points to the non-whitespace character
                    last_break = match.start("next_tok")
                else:
                    # No next_tok captured, need to skip whitespace manually
                    pos = match.end()
                    while pos < text_len and text[pos].isspace():
                        pos += 1
                    last_break = pos

        # Final slice
        if last_break < text_end:
            yield slice(last_break, text_end)

    def _is_line_start_enumerator(self, text: str, pos: int) -> bool:
        """Check if the period at ``pos`` ends a list enumerator that starts its line."""
        lo = max(0, pos - 12)
        nl = text.rfind("\n", lo, pos)
        if nl == -1 and lo:
            return False
        return self._RE_LINE_ENUMERATOR.fullmatch(text, nl + 1, pos + 1) is not None

    def _realign_boundaries(self, text: str, slices: list[slice]) -> Iterator[slice]:
        """
        Realign sentence boundaries to handle trailing punctuation.

        Args:
            text: The text
            slices: The sentence slices

        Yields:
            Realigned sentence slices
        """
        realign = 0
        realignment_match = self._lang_vars.re_boundary_realignment.match
        for slice1, slice2 in pair_iter(iter(slices)):
            start = slice1.start + realign
            if slice2 is None:
                if slice1.stop > start:
                    yield slice(start, slice1.stop)
                continue
            m = realignment_match(text, slice2.start, slice2.stop)
            if m:
                yield slice(start, slice2.start + len(m.group(0).rstrip()))
                realign = m.end() - slice2.start
            else:
                realign = 0
                if slice1.stop > start:
                    yield slice(start, slice1.stop)

    def text_contains_sentbreak(self, text: str) -> bool:
        """
        Check if text contains a sentence break.

        Args:
            text: The text to check

        Returns:
            True if the text contains a sentence break
        """
        if not text:
            return False

        # "!" or "?" followed by whitespace and a letter is always a break
        if ("!" in text or "?" in text) and self._RE_EXCL_QUEST_BREAK.search(text):
            return True

        if self._uses_decision_engine():
            return self._strings_contain_sentbreak(text, "", self._decision_state()[1])

        # Tokenize and annotate; the second pass already resolves ellipses, so the
        # first annotated token with ``sentbreak`` decides.
        return any(t.sentbreak for t in self._annotate_tokens(self._tokenize_words(text)))

    def _context_contains_sentbreak(self, context: Context) -> bool:
        """
        Token-level decision for a candidate context (see ``_match_potential_end_contexts``).

        Only tokens of the ``before`` part can be reported as breaks; the first token
        of ``after`` is annotated so it can inform the second pass but its own
        first-pass result is not a decision about this candidate.
        """
        before, after = context
        if ("!" in before or "?" in before) and self._RE_EXCL_QUEST_BREAK.search(before + after):
            return True
        n_before = sum(len(self._lang_vars.word_tokenize(line)) for line in before.split("\n"))
        tokens = list(self._annotate_tokens(self._tokenize_words(before + after)))
        return any(t.sentbreak for t in tokens[:n_before])

    # ------------------------------------------------------------------
    # String-level decision engine
    #
    # ``text_contains_sentbreak`` on a candidate context used to build PunktToken
    # objects and run both annotation passes over them. The methods below compute
    # the same result from token strings: the first pass depends only on the token
    # string, and the second pass on the pair (token, next token, whether the next
    # token starts a paragraph). Results are memoized per context string.
    # ------------------------------------------------------------------

    def _uses_decision_engine(self) -> bool:
        """Return True if the string-level engine reproduces this tokenizer's annotation."""
        cls = type(self)
        supported = _ENGINE_CLASSES.get(cls)
        if supported is None:
            supported = all(
                getattr(cls, name) is getattr(PunktSentenceTokenizer, name)
                for name in self._ENGINE_HOOKS
            )
            _ENGINE_CLASSES[cls] = supported
        return supported and self._Token is PunktToken

    def _decision_state(
        self,
    ) -> tuple[tuple, dict[str, int], dict[Context, bool], Callable[[Context], bool]]:
        """
        Return ``(signature, first_pass_memo, context_memo, decide)`` for the parameters.

        ``decide(context)`` is the memoized equivalent of ``text_contains_sentbreak``.

        The memos are rebuilt whenever the signature changes: a different parameter
        object or language variables, a replaced or resized parameter collection, or
        an explicit ``clear_decision_cache`` on any tokenizer sharing the parameters.
        """
        params = self._params
        signature = (
            params,
            self._lang_vars,
            params.__dict__.get("_decision_generation", 0),
            params.abbrev_types,
            len(params.abbrev_types),
            params.collocations,
            len(params.collocations),
            params.sent_starters,
            len(params.sent_starters),
            params.ortho_context,
            len(params.ortho_context),
            params.abbrev_break_rates,
            len(params.abbrev_break_rates),
            self.BREAK_RATE_HIGH,
            self.BREAK_RATE_LOW,
            self.BREAK_RATE_MIN_COUNT,
        )
        state = self.__dict__.get("_decision_memo")
        if state is None or state[0] != signature:
            first_memo: dict[str, int] = {}
            context_memo: dict[Context, bool] = {}
            decide = self._context_decider(first_memo, context_memo)
            state = (signature, first_memo, context_memo, decide)
            self.__dict__["_decision_memo"] = state
        return state

    def _context_decider(
        self, first_memo: dict[str, int], context_memo: dict[Context, bool]
    ) -> Callable[[Context], bool]:
        """Build a memoized ``context -> contains a sentence break`` function."""
        get = context_memo.get
        excl_quest = self._RE_EXCL_QUEST_BREAK.search
        strings_contain_sentbreak = self._strings_contain_sentbreak
        max_size = self._DECISION_MEMO_SIZE
        max_len = self._DECISION_CONTEXT_MAX_LEN

        def contains_sentbreak(context: Context) -> bool:
            result = get(context)
            if result is None:
                before, after = context
                if ("!" in before or "?" in before) and excl_quest(before + after):
                    result = True
                else:
                    result = strings_contain_sentbreak(before, after, first_memo)
                if len(before) + len(after) <= max_len:
                    if len(context_memo) >= max_size:
                        context_memo.clear()
                    context_memo[context] = result
            return result

        return contains_sentbreak

    def _strings_contain_sentbreak(
        self, before: str, after: str, first_memo: dict[str, int]
    ) -> bool:
        """
        String-level equivalent of ``_context_contains_sentbreak``.

        Tokens made only of closing punctuation (``"``, ``)``, ``\u201d`` ...) never decide
        and are transparent when pairing, so an abbreviation followed by a closing
        quote sees the word after the quote as its successor.

        Args:
            before: The chunk holding the candidate (decided token by token)
            after: The whitespace and next chunk (its first token is context only)
            first_memo: Memo of first-pass outcomes by token string

        Returns:
            True if any token of ``before`` would be annotated as a sentence break
        """
        word_tokenize = self._lang_vars.word_tokenize
        first_pass = self._first_pass_outcome
        second_pass = self._second_pass_outcome
        memo_size = self._DECISION_MEMO_SIZE
        closing = _CLOSING_CHARS

        def outcome_of(tok: str) -> int:
            outcome = first_memo.get(tok)
            if outcome is None:
                outcome = first_pass(tok)
                if len(first_memo) < memo_size:
                    first_memo[tok] = outcome
            return outcome

        n_before = sum(len(word_tokenize(line)) for line in before.split("\n"))
        if not n_before:
            return False
        # (token, starts a paragraph, belongs to ``before``), closers dropped, and at
        # most one token from ``after``; tokenized line by line like ``_tokenize_words``
        seq: list[tuple[str, bool, bool]] = []
        parastart = False
        seen = 0
        done = False
        for line in (before + after).split("\n"):
            if not line.strip():
                parastart = True
                continue
            for tok in word_tokenize(line):
                is_before = seen < n_before
                seen += 1
                if all(c in closing for c in tok):
                    continue
                seq.append((tok, parastart, is_before))
                parastart = False
                if not is_before:
                    done = True
                    break
            if done:
                break

        last = len(seq) - 1
        for i, (tok, _, is_before) in enumerate(seq):
            if not is_before:
                break
            outcome = outcome_of(tok)
            if not outcome:
                continue
            if i < last:
                tok2, parastart2, _ = seq[i + 1]
                if second_pass(tok, outcome, tok2, outcome_of(tok2), parastart2):
                    return True
            elif outcome == _FP_BREAK:
                # The last token keeps its first-pass annotation
                return True
        return False

    def _first_pass_outcome(self, tok: str) -> int:
        """String-level ``_first_pass_annotation``: one of the ``_FP_*`` outcomes."""
        if tok in self._lang_vars.sent_end_chars:
            return _FP_BREAK
        if _check_is_ellipsis(tok):
            return _FP_ELLIPSIS
        period_final, _, valid_abbrev_candidate, _, _ = _derived(tok)
        if not period_final or tok.endswith(".."):
            return _FP_NONE
        if valid_abbrev_candidate and is_abbreviation(self._params.abbrev_types, tok[:-1].lower()):
            return _FP_ABBR
        return _FP_BREAK

    def _second_pass_outcome(
        self, tok1: str | None, outcome1: int, tok2: str, outcome2: int, parastart2: bool
    ) -> bool:
        """
        String-level ``_second_pass_annotation``: the final ``sentbreak`` of ``tok1``.

        Args:
            tok1: The token being decided (non-None whenever ``outcome1`` is set)
            outcome1: First-pass outcome of ``tok1``
            tok2: The following token
            outcome2: First-pass outcome of ``tok2``
            parastart2: Whether ``tok2`` starts a paragraph
        """
        _, type2, _, first_upper2, first_lower2 = _derived(tok2)
        if outcome1 == _FP_ELLIPSIS:
            return first_upper2 and tok2 not in self._ELLIPSIS_CONTINUERS
        assert tok1 is not None
        period_final1, type1, _, _, _ = _derived(tok1)
        if not period_final1:
            return outcome1 == _FP_BREAK
        typ = type1[:-1] if type1.endswith(".") and len(type1) > 1 else type1
        if outcome2 == _FP_BREAK and type2.endswith(".") and len(type2) > 1:
            next_typ = type2[:-1]
        else:
            next_typ = type2

        if parastart2 and first_upper2:
            return True
        is_abbr = outcome1 == _FP_ABBR
        if is_abbr and typ in self._TITLE_ABBREVS and first_upper2:
            return False
        params = self._params
        if (typ, next_typ) in params.collocations:
            return False
        is_initial = _check_is_initial(tok1)
        if is_abbr and not is_initial:
            if first_upper2 and params.abbrev_break_rates:
                rate_break = self._break_rate_decision(typ)
                if rate_break is not None:
                    return rate_break
            if tok2 not in self._PUNCT_CHARS and (
                ortho_heuristic(params.ortho_context.get(next_typ, 0), first_upper2, first_lower2)
                is True
            ):
                return True
            if first_upper2 and next_typ in params.sent_starters:
                return True
        if is_initial or typ == "##number##":
            if tok2 in self._PUNCT_CHARS:
                return False
            ortho = params.ortho_context.get(next_typ, 0)
            is_sent_starter = ortho_heuristic(ortho, first_upper2, first_lower2)
            if is_sent_starter is False:
                return False
            if (
                is_sent_starter == "unknown"
                and is_initial
                and first_upper2
                and not (ortho & ORTHO_LC)
            ):
                return False
        return outcome1 == _FP_BREAK

    def _annotate_tokens(self, tokens: Iterator[PunktToken]) -> Iterator[PunktToken]:
        """
        Perform full annotation on tokens.

        Args:
            tokens: The tokens to annotate

        Yields:
            Fully annotated tokens
        """
        tokens = self._annotate_first_pass(tokens)
        tokens = self._annotate_second_pass(tokens)
        return tokens

    def _annotate_second_pass(self, tokens: Iterator[PunktToken]) -> Iterator[PunktToken]:
        """
        Perform second-pass annotation on tokens.

        This applies collocational and orthographic heuristics.

        Args:
            tokens: The tokens to annotate

        Yields:
            Tokens with second-pass annotation
        """
        # Closing-punctuation tokens are transparent when pairing (see the
        # string-level engine), so look past them for the successor.
        closing = _CLOSING_CHARS
        items = list(tokens)
        n = len(items)
        for i, token1 in enumerate(items):
            j = i + 1
            while j < n and all(c in closing for c in items[j].tok):
                j += 1
            self._second_pass_annotation(token1, items[j] if j < n else None)
            yield token1

    def _second_pass_annotation(self, token1: PunktToken, token2: PunktToken | None) -> str | None:
        """
        Perform second-pass annotation on a token.

        Args:
            token1: The current token
            token2: The next token

        Returns:
            A string describing the decision, or None
        """
        if token2 is None:
            return None

        # Special handling for ellipsis - check this before period_final check
        if token1.is_ellipsis:
            # If next token starts with uppercase and is a known sentence starter,
            # or has strong orthographic evidence of being a sentence starter,
            # then mark this as a sentence break
            is_sent_starter = self._ortho_heuristic(token2)
            next_typ = token2.type_no_sentperiod

            # Default behavior: ellipsis followed by uppercase letter is a sentence break
            if token2.first_upper and token2.tok not in self._ELLIPSIS_CONTINUERS:
                token1.sentbreak = True
                if is_sent_starter is True:
                    return "Ellipsis followed by orthographic sentence starter"
                # Use cached lookup for sentence starters
                elif self._is_sent_starter(next_typ):
                    return "Ellipsis followed by known sentence starter"
                else:
                    return "Ellipsis followed by uppercase word"
            else:
                token1.sentbreak = False
                return "Ellipsis not followed by sentence starter"

        # For tokens with periods but not ellipsis
        if not token1.period_final:
            return None

        typ = token1.type_no_period
        next_typ = token2.type_no_sentperiod
        tok_is_initial = token1.is_initial

        # A period-final token followed by a paragraph break and a capitalized word
        if token2.parastart and token2.first_upper:
            token1.sentbreak = True
            return "Paragraph break before uppercase word"

        # A prenominal title ("Dr.", "Mr.") before a capitalized word never ends a sentence
        if token1.abbr and typ in self._TITLE_ABBREVS and token2.first_upper:
            token1.sentbreak = False
            return "Title before capitalized word"

        # Collocation heuristic: if the pair is known, mark token as abbreviation.
        if (typ, next_typ) in self._params.collocations:
            token1.sentbreak = False
            token1.abbr = True
            return "Known collocation"

        # If token is marked as an abbreviation, decide based on orthographic evidence.
        if token1.abbr and (not tok_is_initial):
            if token2.first_upper:
                rate_break = self._break_rate_decision(typ)
                if rate_break is not None:
                    token1.sentbreak = rate_break
                    return f"Abbreviation with {'high' if rate_break else 'low'} break rate"
            is_sent_starter = self._ortho_heuristic(token2)
            if is_sent_starter is True:
                token1.sentbreak = True
                return "Abbreviation with orthographic heuristic"
            # Use cached lookup for sentence starters
            if token2.first_upper and self._is_sent_starter(next_typ):
                token1.sentbreak = True
                return "Abbreviation with sentence starter"

        # Check for initials or ordinals.
        if tok_is_initial or typ == "##number##":
            is_sent_starter = self._ortho_heuristic(token2)
            if is_sent_starter is False:
                token1.sentbreak = False
                token1.abbr = True
                return "Initial with orthographic heuristic"
            if (
                is_sent_starter == "unknown"
                and tok_is_initial
                and token2.first_upper
                and not (self._params.ortho_context.get(next_typ, 0) & ORTHO_LC)
            ):
                token1.sentbreak = False
                token1.abbr = True
                return "Initial with special orthographic heuristic"
        return None

    def _break_rate_decision(self, typ: str) -> bool | None:
        """
        Decide a break after abbreviation ``typ`` before a capitalized word from its rate.

        Args:
            typ: The abbreviation type (lowercase, without the trailing period)

        Returns:
            True (break) or False (no break) when the learned break rate is decisive,
            None to fall back to orthographic and sentence-starter evidence
        """
        counts = self._params.abbrev_break_rates.get(typ)
        if counts is None or counts[0] < self.BREAK_RATE_MIN_COUNT:
            return None
        rate = counts[1] / counts[0]
        if rate >= self.BREAK_RATE_HIGH:
            return True
        if self.BREAK_RATE_LOW is not None and rate <= self.BREAK_RATE_LOW:
            return False
        return None

    def _ortho_heuristic(self, token: PunktToken) -> bool | str:
        """
        Apply orthographic heuristics to determine if a token starts a sentence.

        Args:
            token: The token to check

        Returns:
            True if the token starts a sentence, False if not, "unknown" if uncertain
        """
        if token.tok in self._PUNCT_CHARS:
            return False
        ortho = self._params.ortho_context.get(token.type_no_sentperiod, 0)
        return ortho_heuristic(ortho, token.first_upper, token.first_lower)

    def _is_sent_starter(self, token_type: str) -> bool:
        """
        Check if a token type is a known sentence starter.

        Args:
            token_type: The token type to check

        Returns:
            True if the token type is a known sentence starter, False otherwise
        """
        return token_type in self._params.sent_starters
