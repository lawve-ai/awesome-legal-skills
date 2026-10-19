"""
Language variables module for nupunkt.

This module provides language-specific variables and settings
for sentence boundary detection, which can be customized or
extended for different languages.
"""

import re


class PunktLanguageVars:
    """
    Contains language-specific variables for Punkt sentence boundary detection.

    This class encapsulates language-specific behavior, such as the
    characters that indicate sentence boundaries and the regular expressions
    used for various pattern matching tasks in the tokenization process.
    """

    # Use frozenset for O(1) membership testing instead of tuple
    sent_end_chars: frozenset = frozenset((".", "?", "!"))
    internal_punctuation: str = ",:;"
    # Closing quotes/brackets (ASCII and Unicode) and markdown emphasis that trail a sentence end
    re_boundary_realignment: re.Pattern = re.compile(
        r'[\'"\)\]}\u201d\u2019\u00bb*]+?(?:\s+|(?=--)|$)', re.MULTILINE
    )
    _re_word_start: str = r"[^\(\"\`{\[:;&\#\*@\)}\]\-,]"
    _re_multi_char_punct: str = r"(?:\-{2,}|\.{2,}|(?:\.\s+){1,}\.|\u2026)"

    def __init__(self) -> None:
        """Initialize language variables with language-specific settings."""
        self._re_period_context: re.Pattern | None = None
        self._re_word_tokenizer: re.Pattern | None = None

    @property
    def _re_sent_end_chars(self) -> str:
        """
        Returns a regex pattern string for all sentence-ending characters.

        Returns:
            str: A pattern matching any sentence ending character
        """
        return f"[{re.escape(''.join(self.sent_end_chars))}]"

    @property
    def _re_non_word_chars(self) -> str:
        """
        Returns a regex pattern for characters that can never start a word.

        Returns:
            str: A pattern matching non-word-starting characters
        """
        # Exclude characters that can never start a word
        nonword = "".join(set(self.sent_end_chars) - {"."})
        # Apostrophes only count when not followed by a letter, so "aff'd." and
        # "gov’t." stay single tokens while closing quotes still end a word.
        return rf"(?:[)\";}}\]\*:@\({{[\s{re.escape(nonword)}\u201d\u00bb]|['\u2019](?![^\W\d_]))"

    @property
    def word_tokenize_pattern(self) -> re.Pattern:
        """
        Returns a compiled regex pattern for tokenizing words.

        Returns:
            re.Pattern: The compiled regular expression for word tokenization
        """
        if self._re_word_tokenizer is None:
            pattern = rf"""(
                {self._re_multi_char_punct}
                |
                (?={self._re_word_start})\S+?
                (?=
                    \s|
                    $|
                    {self._re_non_word_chars}|
                    {self._re_multi_char_punct}|
                    ,(?=$|\s|{self._re_non_word_chars}|{self._re_multi_char_punct})
                )
                |
                \S
            )"""
            self._re_word_tokenizer = re.compile(pattern, re.UNICODE | re.VERBOSE)
        return self._re_word_tokenizer

    def word_tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into words using the word_tokenize_pattern.

        Args:
            text: The text to tokenize

        Returns:
            A list of word tokens
        """
        return self.word_tokenize_pattern.findall(text)

    @property
    def period_context_pattern(self) -> re.Pattern:
        """
        Returns a compiled regex pattern for finding periods in context.

        Returns:
            re.Pattern: The compiled regular expression for period contexts
        """
        if self._re_period_context is None:
            pattern = rf"""
                (?:{self._re_sent_end_chars}|\u2026)
                (?=(?P<after_tok>
                    {self._re_non_word_chars}|
                    \s+(?P<next_tok>\S+)
                ))
            """
            self._re_period_context = re.compile(pattern, re.UNICODE | re.VERBOSE)
        return self._re_period_context
