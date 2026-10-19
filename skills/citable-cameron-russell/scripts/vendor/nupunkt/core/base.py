"""
Base module for nupunkt.

This module provides the base class for Punkt tokenizers and trainers.
"""

from collections.abc import Collection, Iterable, Iterator

from nupunkt.core.language_vars import PunktLanguageVars
from nupunkt.core.parameters import PunktParameters
from nupunkt.core.tokens import PunktToken, create_punkt_token


def is_abbreviation(abbrev_set: Collection[str], candidate: str) -> bool:
    """
    Check if a candidate is a known abbreviation.

    The candidate is the lowercased token without its trailing period. Besides an
    exact match, the last dash-separated part (``"mid-jan"`` -> ``"jan"``) and the
    form without internal periods (``"u.s.c"`` -> ``"usc"``) are also checked.

    Args:
        abbrev_set: The known abbreviations (any container supporting ``in``)
        candidate: The candidate string to check

    Returns:
        True if the candidate is a known abbreviation, False otherwise
    """
    if candidate in abbrev_set:
        return True
    if "-" in candidate and candidate.rsplit("-", 1)[-1] in abbrev_set:
        return True
    return "." in candidate and candidate.replace(".", "") in abbrev_set


class PunktBase:
    """
    Base class for Punkt tokenizers and trainers.

    This class provides common functionality used by both the trainer and tokenizer,
    including tokenization and first-pass annotation of tokens.
    """

    def __init__(
        self,
        lang_vars: PunktLanguageVars | None = None,
        token_cls: type[PunktToken] = PunktToken,
        params: PunktParameters | None = None,
    ) -> None:
        """
        Initialize the PunktBase instance.

        Args:
            lang_vars: Language-specific variables
            token_cls: The token class to use
            params: Punkt parameters
        """
        self._lang_vars = lang_vars or PunktLanguageVars()
        self._Token = token_cls
        self._params = params or PunktParameters()

    def _tokenize_words(self, plaintext: str) -> Iterator[PunktToken]:
        """
        Tokenize text into words, maintaining paragraph and line-start information.

        Args:
            plaintext: The text to tokenize

        Yields:
            PunktToken instances for each token
        """
        # Quick check for empty text
        if not plaintext:
            return

        # ``create_punkt_token`` is the fast path for the stock token class;
        # subclasses must be instantiated directly so their overrides are honoured.
        make = create_punkt_token if self._Token is PunktToken else self._Token
        word_tokenize = self._lang_vars.word_tokenize

        parastart = False
        for line in plaintext.split("\n"):
            if line.strip():
                tokens = word_tokenize(line)
                if tokens:
                    # First token on a line gets the parastart and linestart flags
                    yield make(tokens[0], parastart=parastart, linestart=True)
                    for tok in tokens[1:]:
                        yield make(tok)
                parastart = False
            else:
                parastart = True

    def _annotate_first_pass(self, tokens: Iterable[PunktToken]) -> Iterator[PunktToken]:
        """
        Perform first-pass annotation on tokens.

        This annotates tokens with sentence breaks, abbreviations, and ellipses.

        Args:
            tokens: The tokens to annotate

        Yields:
            Annotated tokens
        """
        for token in tokens:
            self._first_pass_annotation(token)
            yield token

    def _first_pass_annotation(self, token: PunktToken) -> None:
        """
        Annotate a token with sentence breaks, abbreviations, and ellipses.

        Args:
            token: The token to annotate
        """
        if token.tok in self._lang_vars.sent_end_chars:
            token.sentbreak = True
        elif token.is_ellipsis:
            token.ellipsis = True
            # Don't mark as sentence break now - will be decided in second pass
            # based on what follows the ellipsis
            token.sentbreak = False
        elif token.period_final and not token.tok.endswith(".."):
            # Tokens that cannot be abbreviations are sentence breaks; candidates are
            # checked against the live abbreviation set so runtime additions and
            # removals take effect immediately.
            if not token.valid_abbrev_candidate:
                token.sentbreak = True
            elif is_abbreviation(self._params.abbrev_types, token.tok[:-1].lower()):
                token.abbr = True
            else:
                token.sentbreak = True

    def _is_abbreviation(self, candidate: str) -> bool:
        """
        Check if a candidate is a known abbreviation.

        This is a wrapper around the module-level cached function.

        Args:
            candidate: The candidate string to check

        Returns:
            True if the candidate is a known abbreviation, False otherwise
        """
        return is_abbreviation(self._params.abbrev_types, candidate)
