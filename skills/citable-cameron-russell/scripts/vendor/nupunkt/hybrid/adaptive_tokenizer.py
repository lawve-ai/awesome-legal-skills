"""
Adaptive confidence-based sentence tokenizer.

This tokenizer enhances the base Punkt algorithm by:
1. Dynamically identifying likely abbreviations
2. Using confidence scoring to adaptively refine base decisions
3. Maintaining compatibility with the core algorithm
"""

import re
from dataclasses import dataclass
from typing import Any, TypedDict

from nupunkt.core.parameters import PunktParameters
from nupunkt.core.tokens import PunktToken
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer

# Confidence scoring weights for sentence boundary detection
# These constants control how different features contribute to the confidence score

# Base algorithm decision weights
SCORE_BASE_DECISION_YES = 0.5  # Weight when base algorithm decides it's a boundary
SCORE_BASE_DECISION_NO = 0.0  # Starting score when base says no boundary

# Punctuation weights
SCORE_STRONG_PUNCTUATION = 0.3  # Weight for ! or ? endings
SCORE_QUOTE_ENDING = 0.2  # Weight for ." ?" !" endings

# Abbreviation penalties
SCORE_KNOWN_ABBREVIATION = -0.4  # Penalty for known abbreviations
SCORE_LIKELY_ABBREVIATION = -0.3  # Penalty for likely abbreviations

# Next token weights - when uppercase follows
SCORE_SENTENCE_STARTER_FOLLOWS = 0.4  # Strong evidence for boundary
SCORE_UPPERCASE_FOLLOWS = 0.2  # Moderate evidence for boundary

# Next token weights - when lowercase follows
SCORE_CONTINUATION_WORD_FOLLOWS = -0.3  # Strong evidence against boundary
SCORE_LOWERCASE_FOLLOWS = -0.15  # Moderate evidence against boundary

# Special pattern penalties
SCORE_LIST_ITEM_PATTERN = -0.2  # Penalty for single digits/letters


@dataclass
class BoundaryDecision:
    """Container for detailed boundary decision information."""

    token: str
    next_token: str | None
    base_decision: bool
    final_decision: bool
    confidence: float
    reasons: list[str]
    overridden: bool


class AdaptiveTokenizer(PunktSentenceTokenizer):
    """
    Adaptive tokenizer that enhances the base Punkt algorithm.

    Key features:
    1. Dynamic abbreviation detection for tokens not in the training data
    2. Confidence-based adaptive refinement of edge cases
    3. Preservation of base algorithm strengths
    """

    # Generic abbreviation format templates
    ABBREV_PATTERNS = [
        # Pattern for multi-part abbreviations with dots (e.g., i.e., e.g., Ph.D.)
        re.compile(r"^[a-z][a-z]*(\.[a-z][a-z]*)+\.?$", re.I),
        # Pattern for capitalized single-word abbreviations (e.g., Fig., Vol.)
        re.compile(r"^[A-Z][a-z]*\.$"),
        # Pattern for lowercase single-word abbreviations (e.g., etc., vs.)
        re.compile(r"^[a-z]{2,}\.$"),
        # Pattern for all-caps acronyms with dots (e.g., U.S.A., M.I.T.)
        re.compile(r"^[A-Z](\.[A-Z])+\.?$"),
    ]

    # Closing quotes and brackets that end a quoted or parenthetical sentence
    _CLOSING_TOKENS = frozenset(['"', "'", ")", "]", "}", "\u201d", "\u2019", "\u00bb"])

    # Tokens that often follow abbreviations (not sentence starters)
    CONTINUATION_WORDS = {
        "of",
        "in",
        "at",
        "on",
        "for",
        "and",
        "or",
        "but",
        "with",
        "to",
        "from",
        "by",
        "as",
        "than",
        "that",
        "which",
        "who",
        "whom",
        "whose",
        "where",
        "when",
        "why",
        "how",
    }

    def __init__(
        self,
        model_or_text: Any = None,
        enable_dynamic_abbrev: bool = True,
        confidence_threshold: float = 0.7,
        debug: bool = False,
        **kwargs,
    ):
        """
        Initialize improved tokenizer.

        Args:
            model_or_text: Model/parameters or training text
            enable_dynamic_abbrev: Whether to detect abbreviations dynamically
            confidence_threshold: Threshold for overriding base decisions
            debug: Enable debug mode
            **kwargs: Additional arguments for base tokenizer
        """
        # Load default model if none specified
        if model_or_text is None:
            from nupunkt import load

            default_tokenizer = load("default")
            model_or_text = default_tokenizer._params

        super().__init__(model_or_text, **kwargs)

        self.enable_dynamic_abbrev = enable_dynamic_abbrev
        self.confidence_threshold = confidence_threshold
        self.debug = debug
        self.decisions = []

        # Track dynamically identified abbreviations for this session
        self.dynamic_abbrevs: set[str] = set()

        # PERFORMANCE FIX: If we loaded from the same model, preserve the original
        # frozenset objects to maintain LRU cache efficiency
        if isinstance(model_or_text, PunktParameters):
            # We're sharing the same parameters object, so the frozensets
            # should already be the same. But if not, preserve them.
            if hasattr(model_or_text, "_frozen_abbrev_types"):
                self._params._frozen_abbrev_types = model_or_text._frozen_abbrev_types
            if hasattr(model_or_text, "_frozen_collocations"):
                self._params._frozen_collocations = model_or_text._frozen_collocations
            if hasattr(model_or_text, "_frozen_sent_starters"):
                self._params._frozen_sent_starters = model_or_text._frozen_sent_starters

    def _is_likely_abbreviation(
        self, token: PunktToken, next_token: PunktToken | None
    ) -> tuple[bool, list[str]]:
        """
        Check if a token is likely an abbreviation using patterns and context.

        Returns:
            Tuple of (is_likely_abbrev, reasons)
        """
        if not token.period_final or not token.type_no_period:
            return False, []

        reasons = []
        type_no_period = token.type_no_period

        # Check against patterns
        for pattern in self.ABBREV_PATTERNS:
            if pattern.match(token.tok):
                reasons.append(f"Matches pattern: {pattern.pattern}")

                # For single-word lowercase abbreviations, check if it's known
                if (
                    pattern.pattern == r"^[a-z]{2,}\.$"
                    and type_no_period.lower() not in self._params.abbrev_types
                ):
                    # Unknown lowercase abbreviation - likely NOT an abbreviation
                    return False, ["Matches lowercase pattern but not in known abbreviations"]
                break

        # Check token characteristics
        if len(type_no_period) <= 4 and type_no_period[0].isupper():
            reasons.append("Short uppercase token")

        # Check for internal periods (like M.I.T.)
        if token.tok.count(".") > 1:
            reasons.append("Multiple internal periods")

        # Context checks
        if next_token:
            # A closing quote or bracket right after a capitalized word ("Stop.")
            # means the period ended a quoted sentence, not an abbreviation.
            if next_token.tok in self._CLOSING_TOKENS and token.first_upper:
                return False, ["Followed by closing punctuation"]

            # Check if followed by lowercase continuation word
            if next_token.first_lower and next_token.tok.lower() in self.CONTINUATION_WORDS:
                reasons.append(f"Followed by continuation word: {next_token.tok}")

            # Check if followed by comma or other punctuation
            elif next_token.tok in {",", ";", ":", "(", "-", "–", "—"}:
                reasons.append(f"Followed by punctuation: {next_token.tok}")

            # Negative evidence - followed by uppercase sentence starter
            elif (
                next_token.first_upper
                and next_token.type_no_period.lower() in self._params.sent_starters
            ):
                reasons.append(f"Followed by sentence starter: {next_token.tok}")
                return False, reasons  # Strong evidence against

        return len(reasons) > 0, reasons

    def _calculate_boundary_confidence(
        self, token: PunktToken, next_token: PunktToken | None, base_decision: bool
    ) -> tuple[float, list[str]]:
        """
        Calculate confidence in sentence boundary decision.

        Returns:
            Tuple of (confidence, contributing_factors)
        """
        factors = []
        score = 0.0

        # Start with base decision weight
        if base_decision:
            score += SCORE_BASE_DECISION_YES
            factors.append("Base algorithm: yes")
        else:
            score = SCORE_BASE_DECISION_NO
            factors.append("Base algorithm: no")

        # Token ending analysis
        if token.tok.endswith("!") or token.tok.endswith("?"):
            score += SCORE_STRONG_PUNCTUATION
            factors.append("Strong punctuation")
        elif token.tok.endswith('."') or token.tok.endswith('?"') or token.tok.endswith('!"'):
            score += SCORE_QUOTE_ENDING
            factors.append("Quote ending")

        # Abbreviation analysis
        if token.abbr:
            score += SCORE_KNOWN_ABBREVIATION
            factors.append("Known abbreviation")
        elif self.enable_dynamic_abbrev:
            is_likely_abbrev, abbrev_reasons = self._is_likely_abbreviation(token, next_token)
            if is_likely_abbrev:
                score += SCORE_LIKELY_ABBREVIATION
                factors.extend([f"Likely abbrev: {r}" for r in abbrev_reasons[:2]])

        # Next token analysis
        if next_token:
            if next_token.first_upper:
                if next_token.type_no_period.lower() in self._params.sent_starters:
                    score += SCORE_SENTENCE_STARTER_FOLLOWS
                    factors.append("Known sentence starter follows")
                else:
                    score += SCORE_UPPERCASE_FOLLOWS
                    factors.append("Uppercase follows")
            elif next_token.first_lower:
                if next_token.tok.lower() in self.CONTINUATION_WORDS:
                    score += SCORE_CONTINUATION_WORD_FOLLOWS
                    factors.append("Continuation word follows")
                else:
                    score += SCORE_LOWERCASE_FOLLOWS
                    factors.append("Lowercase follows")

        # Special patterns
        if token.type_no_period.isdigit() or (
            len(token.type_no_period) == 1 and token.type_no_period.isalpha()
        ):
            score += SCORE_LIST_ITEM_PATTERN
            factors.append("List item pattern")

        # Normalize to [0, 1]
        confidence = max(0.0, min(1.0, score))

        return confidence, factors

    def _second_pass_annotation(self, token1: PunktToken, token2: PunktToken | None) -> None:
        """
        Enhanced second-pass annotation that refines base decisions.
        """
        # Store original state (not used but kept for potential debugging)

        # Call parent's second pass - this is crucial!
        super()._second_pass_annotation(token1, token2)

        # Now we have the base Punkt decision
        base_decision = token1.sentbreak

        # Only consider refinements for period-ending tokens
        if not (token1.period_final or token1.tok.endswith("!") or token1.tok.endswith("?")):
            return

        # Calculate confidence in the decision
        confidence, factors = self._calculate_boundary_confidence(token1, token2, base_decision)

        # Decide whether to override
        final_decision = base_decision
        overridden = False

        if base_decision and confidence < (1.0 - self.confidence_threshold):
            # Base said yes, but we're confident it's wrong
            final_decision = False
            overridden = True
            factors.append("OVERRIDE: High confidence NOT boundary")

            # Also mark as abbreviation if appropriate
            if token1.period_final and not token1.abbr:
                is_likely_abbrev, _ = self._is_likely_abbreviation(token1, token2)
                if is_likely_abbrev:
                    token1.abbr = True
                    self.dynamic_abbrevs.add(token1.type_no_period.lower())

        elif not base_decision and confidence > self.confidence_threshold:
            # Base said no, but we're confident it's wrong
            # However, respect known abbreviations
            if not token1.abbr:
                final_decision = True
                overridden = True
                factors.append("OVERRIDE: High confidence IS boundary")

        # Apply final decision
        token1.sentbreak = final_decision

        # Store decision info for debugging
        if self.debug:
            self.decisions.append(
                BoundaryDecision(
                    token=token1.tok,
                    next_token=token2.tok if token2 else None,
                    base_decision=base_decision,
                    final_decision=final_decision,
                    confidence=confidence,
                    reasons=factors,
                    overridden=overridden,
                )
            )

    def tokenize(self, text: str, realign_boundaries: bool = True, **kwargs) -> list[str]:
        """
        Tokenize with optional debug output.
        """
        # Clear debug info
        if self.debug:
            self.decisions = []

        # Tokenize
        sentences = super().tokenize(text, realign_boundaries, **kwargs)

        # Show debug info if requested
        if self.debug and self.decisions:
            print("\n=== Tokenization Decisions ===")
            for decision in self.decisions:
                if decision.overridden or decision.confidence > 0.8 or decision.confidence < 0.2:
                    print(f"\nToken: '{decision.token}' -> '{decision.next_token}'")
                    print(f"  Base: {decision.base_decision}, Final: {decision.final_decision}")
                    print(
                        f"  Confidence: {decision.confidence:.2f}, Overridden: {decision.overridden}"
                    )
                    print(f"  Reasons: {', '.join(decision.reasons[:3])}")

        return sentences

    def tokenize_with_confidence(self, text: str, **kwargs) -> list[tuple[str, float]]:
        """
        Tokenize text and return sentences with confidence scores.

        Args:
            text: The text to tokenize
            **kwargs: Additional arguments passed to base tokenizer

        Returns:
            List of (sentence, confidence) tuples where confidence is the
            average confidence of all boundary decisions for that sentence.
        """
        # Clear debug info and enable decision tracking
        self.decisions = []
        original_debug = self.debug
        self.debug = True  # Temporarily enable to collect decisions

        # Tokenize to get sentences
        sentences = super().tokenize(text, **kwargs)

        # Restore original debug setting
        self.debug = original_debug

        # If no decisions were made, return sentences with default confidence
        if not self.decisions:
            return [(sent, 1.0) for sent in sentences]

        # Calculate average confidence for each sentence
        # We need to map decisions to sentences
        results = []
        decision_idx = 0

        for sent in sentences:
            # Find all decisions that contributed to this sentence
            sent_confidences = []

            # Look for decisions until we've processed all tokens in this sentence
            while decision_idx < len(self.decisions):
                decision = self.decisions[decision_idx]

                # If this decision's token is in the current sentence
                if decision.token in sent:
                    sent_confidences.append(decision.confidence)
                    decision_idx += 1

                    # If this was a sentence break, we're done with this sentence
                    if decision.final_decision:
                        break
                else:
                    # This decision belongs to the next sentence
                    break

            # Calculate average confidence for this sentence
            if sent_confidences:
                avg_confidence = sum(sent_confidences) / len(sent_confidences)
            else:
                avg_confidence = 1.0  # Default high confidence if no decisions

            results.append((sent, avg_confidence))

        return results


class _DomainSettings(TypedDict):
    """Per-domain configuration for :func:`create_adaptive_tokenizer`."""

    confidence_threshold: float
    enable_dynamic_abbrev: bool


def create_adaptive_tokenizer(
    model_or_text: Any = None, domain: str = "general", debug: bool = False, **kwargs
) -> AdaptiveTokenizer:
    """
    Create an adaptive tokenizer for a specific domain.

    Args:
        model_or_text: Model/parameters or training text
        domain: One of 'general', 'legal', 'scientific'
        debug: Enable debug output
        **kwargs: Additional tokenizer arguments

    Returns:
        Configured tokenizer
    """
    # Domain-specific settings
    domain_settings: dict[str, _DomainSettings] = {
        "general": {
            "confidence_threshold": 0.7,
            "enable_dynamic_abbrev": True,
        },
        "legal": {
            "confidence_threshold": 0.75,  # More conservative
            "enable_dynamic_abbrev": True,
        },
        "scientific": {
            "confidence_threshold": 0.72,
            "enable_dynamic_abbrev": True,
        },
    }

    if domain not in domain_settings:
        raise ValueError(f"Unknown domain: {domain}. Choose from {list(domain_settings.keys())}")

    settings = domain_settings[domain]

    return AdaptiveTokenizer(
        model_or_text=model_or_text,
        confidence_threshold=settings["confidence_threshold"],
        enable_dynamic_abbrev=settings["enable_dynamic_abbrev"],
        debug=debug,
        **kwargs,
    )
