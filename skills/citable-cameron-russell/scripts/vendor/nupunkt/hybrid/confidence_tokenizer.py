"""
Confidence-based hybrid sentence tokenizer.

This module implements a confidence-scoring approach to sentence boundary
detection that enhances the base Punkt algorithm while maintaining its
core principles (zero dependencies, deterministic behavior).
"""

from dataclasses import dataclass
from typing import TypedDict

from nupunkt.core.parameters import PunktParameters
from nupunkt.core.tokens import PunktToken
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer


@dataclass
class ConfidenceScore:
    """Container for confidence scoring components."""

    total: float
    components: dict[str, float]
    decision_threshold: float
    is_boundary: bool


class ConfidenceCalculator:
    """Calculate confidence scores for sentence boundaries."""

    def __init__(self, params: PunktParameters):
        self.params = params

        # Default component weights (user-configurable)
        self.weights = {
            "punkt_base": 0.4,  # Original Punkt decision
            "punctuation": 0.2,  # Type of punctuation
            "orthographic": 0.15,  # Capitalization patterns
            "length": 0.1,  # Token length heuristics
            "context": 0.15,  # Surrounding context
        }

    def calculate_confidence(
        self, token: PunktToken, next_token: PunktToken | None = None
    ) -> dict[str, float]:
        """Calculate individual confidence components."""
        scores = {}

        # Punkt base score - original algorithm's decision
        scores["punkt_base"] = self._punkt_base_score(token)

        # Punctuation type score
        scores["punctuation"] = self._punctuation_score(token)

        # Orthographic score - capitalization patterns
        scores["orthographic"] = self._orthographic_score(token, next_token)

        # Length heuristic - short tokens with periods often abbreviations
        scores["length"] = self._length_score(token)

        # Context score - patterns around the token
        scores["context"] = self._context_score(token, next_token)

        return scores

    def _punkt_base_score(self, token: PunktToken) -> float:
        """Score based on original Punkt algorithm decision."""
        if token.sentbreak:
            return 1.0
        elif token.abbr:
            return 0.0  # Abbreviations are not sentence breaks
        elif token.ellipsis:
            return 0.3  # Ellipsis might be sentence break
        else:
            return 0.5  # Neutral

    def _punctuation_score(self, token: PunktToken) -> float:
        """Score based on punctuation type."""
        tok = token.tok

        # Strong sentence-ending punctuation
        if tok.endswith("!") or tok.endswith("?"):
            return 0.95

        # Period is common sentence ender but also in abbreviations
        elif tok.endswith("."):
            # Multiple periods (ellipsis) handled separately
            if tok.endswith("..."):
                return 0.4
            # Check for common patterns that are NOT sentence ends
            elif any(tok.endswith(p) for p in [".com", ".org", ".net", ".edu"]):
                return 0.1
            else:
                return 0.7

        # Semicolon sometimes ends sentences
        elif tok.endswith(";"):
            return 0.3

        # Colon rarely ends sentences
        elif tok.endswith(":"):
            return 0.2

        else:
            return 0.0

    def _orthographic_score(self, token: PunktToken, next_token: PunktToken | None) -> float:
        """Score based on capitalization patterns."""
        if not next_token:
            return 0.5  # Neutral if no next token

        # Strong indicator: next token starts with capital
        if next_token.first_upper:
            # But check if it's a known sentence starter
            if next_token.type_no_period.lower() in self.params.sent_starters:
                return 0.9
            else:
                return 0.7

        # Next token is lowercase - less likely sentence boundary
        elif next_token.first_lower:
            return 0.2

        # Next token has no case (number, punctuation)
        else:
            return 0.5

    def _length_score(self, token: PunktToken) -> float:
        """Score based on token length - short tokens with periods often abbreviations."""
        if not token.period_final:
            return 0.5  # Neutral if no period

        tok_len = len(token.type_no_period)

        # Very short (1-2 chars) - likely abbreviation
        if tok_len <= 2:
            return 0.1
        # Short (3-4 chars) - possibly abbreviation
        elif tok_len <= 4:
            return 0.3
        # Medium (5-10 chars) - less likely abbreviation
        elif tok_len <= 10:
            return 0.6
        # Long - unlikely to be abbreviation
        else:
            return 0.8

    def _context_score(self, token: PunktToken, next_token: PunktToken | None) -> float:
        """Score based on surrounding context patterns."""
        score = 0.5  # Start neutral

        # Check for quote patterns
        if token.tok.endswith('."') or token.tok.endswith('?"') or token.tok.endswith('!"'):
            score += 0.3  # More likely sentence end

        # Check for parenthesis patterns
        if token.tok.endswith(".)"):
            score -= 0.2  # Less likely sentence end

        # Check for list patterns (1. 2. etc.)
        if token.type_no_period.isdigit() or (
            len(token.type_no_period) == 1 and token.type_no_period.isalpha()
        ):
            score -= 0.3  # Likely a list item

        # Check for common non-sentence-ending patterns
        if next_token:
            next_lower = next_token.type_no_period.lower()
            # Common continuations
            if next_lower in {"and", "or", "but", "which", "that", "who", "where", "when"}:
                score -= 0.2

        return max(0.0, min(1.0, score))  # Clamp to [0, 1]

    def get_total_confidence(self, scores: dict[str, float]) -> float:
        """Calculate weighted total confidence score."""
        total = sum(
            scores.get(component, 0.0) * self.weights.get(component, 0.0)
            for component in self.weights
        )
        # Normalize by sum of weights
        weight_sum = sum(self.weights.values())
        return total / weight_sum if weight_sum > 0 else 0.5


class ConfidenceSentenceTokenizer(PunktSentenceTokenizer):
    """
    Enhanced sentence tokenizer with confidence scoring.

    This tokenizer extends the base Punkt algorithm with a confidence-based
    scoring system that considers multiple factors when making sentence
    boundary decisions.
    """

    def __init__(
        self,
        params: PunktParameters | None = None,
        confidence_threshold: float = 0.5,
        component_weights: dict[str, float] | None = None,
        debug: bool = False,
    ):
        """
        Initialize confidence-based tokenizer.

        Args:
            params: Punkt parameters (uses default if None)
            confidence_threshold: Minimum confidence to declare sentence boundary
            component_weights: Custom weights for confidence components
            debug: Enable debug mode for decision inspection
        """
        super().__init__(params)
        self.confidence_threshold = confidence_threshold
        self.debug = debug
        self.debug_decisions = []

        # Initialize confidence calculator
        self.confidence_calc = ConfidenceCalculator(self._params)
        if component_weights:
            self.confidence_calc.weights.update(component_weights)

    def _second_pass_annotation(self, token1: PunktToken, token2: PunktToken | None) -> None:
        """
        Override second-pass annotation to use confidence scoring.

        This method is called for each token pair during the second pass.
        """
        # Only process tokens that could be sentence boundaries
        if (
            not token1.period_final
            and not token1.tok.endswith("!")
            and not token1.tok.endswith("?")
        ):
            return

        # Calculate confidence scores
        scores = self.confidence_calc.calculate_confidence(token1, token2)
        total_confidence = self.confidence_calc.get_total_confidence(scores)

        # Make decision based on confidence
        is_boundary = total_confidence >= self.confidence_threshold

        # Store debug information
        if self.debug:
            self.debug_decisions.append(
                ConfidenceScore(
                    total=total_confidence,
                    components=scores,
                    decision_threshold=self.confidence_threshold,
                    is_boundary=is_boundary,
                )
            )

        # Apply decision - but respect abbreviation status
        if is_boundary and not token1.abbr:
            token1.sentbreak = True
        elif not is_boundary:
            token1.sentbreak = False

    def tokenize_with_confidence(self, text: str) -> list[tuple[str, ConfidenceScore]]:
        """
        Tokenize text and return sentences with confidence scores.

        This method is useful for debugging and threshold tuning.

        Returns:
            List of (sentence, confidence_score) tuples
        """
        # Enable debug mode temporarily
        old_debug = self.debug
        self.debug = True
        self.debug_decisions = []

        # Tokenize
        sentences = self.tokenize(text)

        # Match sentences with decisions
        results = []
        for i, sent in enumerate(sentences):
            if i < len(self.debug_decisions):
                results.append((sent, self.debug_decisions[i]))
            else:
                # Shouldn't happen, but handle gracefully
                results.append((sent, ConfidenceScore(0.5, {}, self.confidence_threshold, True)))

        # Restore debug mode
        self.debug = old_debug

        return results

    def set_confidence_threshold(self, threshold: float) -> None:
        """Adjust the confidence threshold."""
        self.confidence_threshold = threshold

    def set_component_weight(self, component: str, weight: float) -> None:
        """Adjust individual component weight."""
        self.confidence_calc.weights[component] = weight


class _DomainPreset(TypedDict):
    """Per-domain preset for :func:`create_domain_tokenizer`."""

    confidence_threshold: float
    component_weights: dict[str, float]


# Preset configurations for different domains
DOMAIN_PRESETS: dict[str, _DomainPreset] = {
    "general": {
        "confidence_threshold": 0.5,
        "component_weights": {
            "punkt_base": 0.4,
            "punctuation": 0.2,
            "orthographic": 0.15,
            "length": 0.1,
            "context": 0.15,
        },
    },
    "legal": {
        "confidence_threshold": 0.55,  # Slightly higher threshold
        "component_weights": {
            "punkt_base": 0.3,  # Less weight on base
            "punctuation": 0.2,
            "orthographic": 0.15,
            "length": 0.15,  # More weight on length (legal has many abbrevs)
            "context": 0.2,  # More weight on context
        },
    },
    "scientific": {
        "confidence_threshold": 0.52,
        "component_weights": {
            "punkt_base": 0.35,
            "punctuation": 0.2,
            "orthographic": 0.15,
            "length": 0.12,
            "context": 0.18,
        },
    },
}


def create_domain_tokenizer(
    domain: str = "general", params: PunktParameters | None = None, debug: bool = False
) -> ConfidenceSentenceTokenizer:
    """
    Create a tokenizer configured for a specific domain.

    Args:
        domain: One of 'general', 'legal', 'scientific'
        params: Custom Punkt parameters (uses default if None)
        debug: Enable debug mode

    Returns:
        Configured ConfidenceSentenceTokenizer
    """
    if domain not in DOMAIN_PRESETS:
        raise ValueError(f"Unknown domain: {domain}. Choose from {list(DOMAIN_PRESETS.keys())}")

    preset = DOMAIN_PRESETS[domain]
    return ConfidenceSentenceTokenizer(
        params=params,
        confidence_threshold=preset["confidence_threshold"],
        component_weights=preset["component_weights"],
        debug=debug,
    )
