"""
Fixed confidence-based hybrid sentence tokenizer.

This module implements a confidence-scoring approach that properly integrates
with the base Punkt algorithm instead of replacing it.
"""

from dataclasses import dataclass
from typing import Any, TypedDict

from nupunkt.core.parameters import PunktParameters
from nupunkt.core.tokens import PunktToken
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer


@dataclass
class ConfidenceScore:
    """Container for confidence scoring components."""

    value: float
    components: dict[str, float]
    base_decision: bool  # What the base Punkt algorithm decided
    final_decision: bool  # What we decided after confidence adjustment
    category: str  # Description of the decision


class ConfidenceCalculator:
    """Calculate confidence scores for sentence boundaries."""

    def __init__(self, params: PunktParameters):
        self.params = params

        # Refined component weights based on analysis
        self.weights = {
            "punkt_base": 0.6,  # High weight - base algorithm is good
            "punctuation": 0.1,  # Lower weight - base handles this
            "orthographic": 0.1,  # Lower weight - base handles this
            "length": 0.1,  # Token length heuristics
            "context": 0.1,  # Surrounding context
        }

    def calculate_confidence(
        self, token: PunktToken, next_token: PunktToken | None, base_sentbreak: bool
    ) -> dict[str, float]:
        """Calculate individual confidence components."""
        scores = {}

        # Base Punkt decision - this is the most important signal
        scores["punkt_base"] = 1.0 if base_sentbreak else 0.0

        # Only calculate other scores if we might override the base decision
        scores["punctuation"] = self._punctuation_score(token)
        scores["orthographic"] = self._orthographic_score(token, next_token)
        scores["length"] = self._length_score(token)
        scores["context"] = self._context_score(token, next_token)

        return scores

    def _punctuation_score(self, token: PunktToken) -> float:
        """Score based on punctuation type."""
        tok = token.tok

        # Strong sentence-ending punctuation
        if tok.endswith("!") or tok.endswith("?"):
            return 0.95
        elif tok.endswith("."):
            # Check for URLs/emails
            if any(tok.endswith(p) for p in [".com", ".org", ".net", ".edu", ".gov"]):
                return 0.0
            # Ellipsis is handled by base algorithm
            elif tok.endswith("..."):
                return 0.5
            else:
                return 0.7
        else:
            return 0.3

    def _orthographic_score(self, token: PunktToken, next_token: PunktToken | None) -> float:
        """Score based on capitalization patterns."""
        if not next_token:
            return 0.5

        # Next token starts with capital
        if next_token.first_upper:
            # Check if it's a known sentence starter
            if next_token.type_no_period.lower() in self.params.sent_starters:
                return 0.9
            # Check if it's commonly lowercase
            elif next_token.type_no_period in self.params.ortho_context:
                ortho_context = self.params.ortho_context[next_token.type_no_period]
                # If we've seen it lowercase, less likely to be sentence start
                if ortho_context & 1:  # ORTHO_LC flag
                    return 0.3
                else:
                    return 0.7
            else:
                return 0.6
        elif next_token.first_lower:
            return 0.1
        else:
            return 0.5

    def _length_score(self, token: PunktToken) -> float:
        """Score based on token length."""
        if not token.period_final:
            return 0.5

        # If base algorithm marked it as abbreviation, trust that
        if token.abbr:
            return 0.0

        tok_len = len(token.type_no_period)

        # Very short tokens are usually abbreviations
        if tok_len <= 2:
            return 0.1
        elif tok_len <= 4:
            return 0.3
        elif tok_len <= 10:
            return 0.6
        else:
            return 0.8

    def _context_score(self, token: PunktToken, next_token: PunktToken | None) -> float:
        """Score based on surrounding context patterns."""
        score = 0.5

        # Quote patterns - these are usually sentence ends
        if token.tok.endswith('."') or token.tok.endswith('?"') or token.tok.endswith('!"'):
            score += 0.3

        # Parenthesis patterns - these are usually NOT sentence ends
        if token.tok.endswith(".)"):
            score -= 0.3

        # Check for list patterns
        if token.type_no_period.isdigit():
            # Numeric list item like "1."
            score -= 0.4
        elif len(token.type_no_period) == 1 and token.type_no_period.isalpha():
            # Letter list item like "a."
            score -= 0.4

        # Check for common abbreviation patterns we might have missed
        type_lower = token.type_no_period.lower()
        if type_lower in {"dr", "mr", "mrs", "ms", "prof", "sr", "jr"}:
            score -= 0.5
        elif type_lower in {"inc", "ltd", "corp", "llc", "co"} or type_lower in {
            "jan",
            "feb",
            "mar",
            "apr",
            "jun",
            "jul",
            "aug",
            "sep",
            "sept",
            "oct",
            "nov",
            "dec",
        }:
            score -= 0.4

        return max(0.0, min(1.0, score))

    def get_total_confidence(self, scores: dict[str, float]) -> float:
        """Calculate weighted total confidence score."""
        total = sum(
            scores.get(component, 0.0) * self.weights.get(component, 0.0)
            for component in self.weights
        )
        weight_sum = sum(self.weights.values())
        return total / weight_sum if weight_sum > 0 else 0.5


class FixedConfidenceSentenceTokenizer(PunktSentenceTokenizer):
    """
    Fixed confidence-based tokenizer that properly integrates with base Punkt.

    This tokenizer enhances rather than replaces the base algorithm.
    """

    def __init__(
        self,
        model_or_text: Any = None,
        confidence_threshold: float = 0.5,
        override_threshold_high: float = 0.8,  # Only override if very confident
        override_threshold_low: float = 0.2,  # Only override if very unconfident
        component_weights: dict[str, float] | None = None,
        debug: bool = False,
        **kwargs,
    ):
        """
        Initialize fixed confidence-based tokenizer.

        Args:
            model_or_text: Same as base PunktSentenceTokenizer
            confidence_threshold: Not used for decisions, just for categorization
            override_threshold_high: Only override base decision if confidence > this
            override_threshold_low: Only override base decision if confidence < this
            component_weights: Custom weights for confidence components
            debug: Enable debug mode
            **kwargs: Additional arguments for base tokenizer
        """
        # If no model specified, use the default model
        if model_or_text is None:
            from nupunkt import load_default_model

            # Get the default model's parameters
            default_tokenizer = load_default_model()
            model_or_text = default_tokenizer._params

        super().__init__(model_or_text, **kwargs)
        self.confidence_threshold = confidence_threshold
        self.override_threshold_high = override_threshold_high
        self.override_threshold_low = override_threshold_low
        self.debug = debug
        self.debug_decisions = []

        # Initialize confidence calculator
        self.confidence_calc = ConfidenceCalculator(self._params)
        if component_weights:
            self.confidence_calc.weights.update(component_weights)

    def _second_pass_annotation(self, token1: PunktToken, token2: PunktToken | None) -> None:
        """
        Enhance second-pass annotation with confidence scoring.

        This properly calls the parent method first, then applies refinements.
        """
        # Store original decision (not used but kept for potential debugging)

        # Call parent's second pass annotation - this does all the heavy lifting
        super()._second_pass_annotation(token1, token2)

        # Now we have the base Punkt decision
        base_sentbreak = token1.sentbreak
        base_abbr = token1.abbr

        # Only apply confidence scoring to tokens that could be sentence boundaries
        if not (token1.period_final or token1.tok.endswith("!") or token1.tok.endswith("?")):
            return

        # Calculate confidence scores
        scores = self.confidence_calc.calculate_confidence(token1, token2, base_sentbreak)
        total_confidence = self.confidence_calc.get_total_confidence(scores)

        # Decision logic: only override base decision if we're very confident
        final_sentbreak = base_sentbreak
        category = "accepted_base"

        if base_sentbreak and total_confidence < self.override_threshold_low:
            # Base said yes, but we're very confident it's wrong
            final_sentbreak = False
            category = "overrode_yes_to_no"
        elif not base_sentbreak and total_confidence > self.override_threshold_high:
            # Base said no, but we're very confident it's wrong
            # BUT: never override if base marked it as abbreviation
            if not base_abbr:
                final_sentbreak = True
                category = "overrode_no_to_yes"
            else:
                category = "respected_abbreviation"

        # Apply final decision
        token1.sentbreak = final_sentbreak

        # Store debug information
        if self.debug:
            self.debug_decisions.append(
                {
                    "token": token1.tok,
                    "next_token": token2.tok if token2 else None,
                    "base_decision": base_sentbreak,
                    "base_abbr": base_abbr,
                    "confidence": total_confidence,
                    "final_decision": final_sentbreak,
                    "category": category,
                    "scores": scores,
                }
            )

    def get_boundary_confidence(self, text: str, position: int) -> ConfidenceScore:
        """
        Get confidence score for a specific boundary position.

        Args:
            text: The full text
            position: Character position of potential boundary

        Returns:
            ConfidenceScore with details
        """
        # This would need to tokenize up to the position and return the confidence
        # For now, return a placeholder
        return ConfidenceScore(
            value=0.5,
            components={},
            base_decision=True,
            final_decision=True,
            category="not_implemented",
        )


class _DomainPreset(TypedDict):
    """Per-domain preset for :func:`create_fixed_domain_tokenizer`."""

    confidence_threshold: float
    override_threshold_high: float
    override_threshold_low: float
    component_weights: dict[str, float] | None


# Updated domain presets with better thresholds
DOMAIN_PRESETS: dict[str, _DomainPreset] = {
    "general": {
        "confidence_threshold": 0.5,
        "override_threshold_high": 0.8,
        "override_threshold_low": 0.2,
        "component_weights": None,  # Use defaults
    },
    "legal": {
        "confidence_threshold": 0.5,
        "override_threshold_high": 0.85,  # More conservative
        "override_threshold_low": 0.15,  # More conservative
        "component_weights": {
            "punkt_base": 0.7,  # Trust base more for legal
            "punctuation": 0.05,
            "orthographic": 0.05,
            "length": 0.1,
            "context": 0.1,
        },
    },
    "scientific": {
        "confidence_threshold": 0.5,
        "override_threshold_high": 0.82,
        "override_threshold_low": 0.18,
        "component_weights": {
            "punkt_base": 0.65,
            "punctuation": 0.08,
            "orthographic": 0.08,
            "length": 0.09,
            "context": 0.1,
        },
    },
}


def create_fixed_domain_tokenizer(
    domain: str = "general", model_or_text: Any = None, debug: bool = False, **kwargs
) -> FixedConfidenceSentenceTokenizer:
    """
    Create a fixed tokenizer configured for a specific domain.

    Args:
        domain: One of 'general', 'legal', 'scientific'
        model_or_text: Same as PunktSentenceTokenizer (defaults to default model)
        debug: Enable debug mode
        **kwargs: Additional arguments for tokenizer

    Returns:
        Configured FixedConfidenceSentenceTokenizer
    """
    if domain not in DOMAIN_PRESETS:
        raise ValueError(f"Unknown domain: {domain}. Choose from {list(DOMAIN_PRESETS.keys())}")

    # If no model specified, use the default model
    if model_or_text is None:
        from nupunkt import load_default_model

        default_tokenizer = load_default_model()
        model_or_text = default_tokenizer._params

    preset = DOMAIN_PRESETS[domain]
    return FixedConfidenceSentenceTokenizer(
        model_or_text=model_or_text,
        confidence_threshold=preset["confidence_threshold"],
        override_threshold_high=preset["override_threshold_high"],
        override_threshold_low=preset["override_threshold_low"],
        component_weights=preset.get("component_weights"),
        debug=debug,
        **kwargs,
    )
