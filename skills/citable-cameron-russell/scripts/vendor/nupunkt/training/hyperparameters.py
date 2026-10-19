"""
Hyperparameter configuration for Punkt training.

This module provides a clean interface for configuring training hyperparameters
with sensible defaults and domain-specific presets.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from nupunkt.trainers.base_trainer import PunktTrainer


@final
@dataclass
class PunktHyperparameters:
    """
    Hyperparameters for Punkt sentence tokenizer training.

    All thresholds control the statistical significance required for
    learning various patterns from the training text.
    """

    # Abbreviation detection thresholds
    abbrev_threshold: float = 0.3
    """Log-likelihood threshold for abbreviation detection (default: 0.3)"""

    abbrev_backoff: int = 5
    """Minimum frequency for rare abbreviations (default: 5)"""

    abbrev_colloc_freq_threshold: float = 0.95
    """Frequency threshold for abbreviation collocations (default: 0.95)"""

    max_abbrev_length: int = 20
    """Maximum length for abbreviation detection (default: 20)"""

    # Sentence starter detection
    sent_starter_threshold: float = 25.0
    """Log-likelihood threshold for sentence starters (default: 25.0 - VERY HIGH!)"""

    sent_starter_min_freq: int = 5
    """Minimum frequency for sentence starters (default: 5)"""

    # Collocation detection
    collocation_threshold: float = 7.88
    """Log-likelihood threshold for collocations (default: 7.88)"""

    min_colloc_freq: int = 1
    """Minimum frequency for collocations (default: 1)"""

    include_all_collocs: bool = False
    """Whether to include all collocations (default: False)"""

    include_abbrev_collocs: bool = False
    """Whether to include abbreviation collocations (default: False)"""

    # Memory efficiency settings
    type_fdist_min_freq: int = 2
    """Minimum frequency to keep a type in frequency distribution (default: 2)"""

    colloc_fdist_min_freq: int = 3
    """Minimum frequency to keep a collocation (default: 3)"""

    prune_interval: int = 10000
    """How often to prune frequency distributions (default: 10000 tokens)"""

    @classmethod
    def conservative(cls) -> "PunktHyperparameters":
        """
        Conservative sentence splitting - learns fewer boundary indicators.

        Results in more under-segmentation (keeping sentences together).
        Good for formal text where precision is more important than recall.
        """
        return cls(
            abbrev_threshold=0.05,  # Low - learn many abbreviations
            sent_starter_threshold=30.0,  # Very high - learn few starters
            sent_starter_min_freq=10,
            collocation_threshold=10.0,  # High - learn few collocations
            min_colloc_freq=5,
        )

    @classmethod
    def balanced(cls) -> "PunktHyperparameters":
        """
        Balanced thresholds - reasonable middle ground.

        Good balance between precision and recall.
        Recommended for most use cases.
        """
        return cls(
            abbrev_threshold=0.1,  # Moderate - default threshold
            sent_starter_threshold=15.0,  # Moderate threshold
            sent_starter_min_freq=5,
            collocation_threshold=7.88,  # Default threshold
            min_colloc_freq=3,
        )

    @classmethod
    def aggressive(cls) -> "PunktHyperparameters":
        """
        Aggressive sentence splitting - learns many boundary indicators.

        Results in more over-segmentation (splitting more frequently).
        Good for informal text where recall is more important than precision.
        """
        return cls(
            abbrev_threshold=0.3,  # High - learn few abbreviations
            sent_starter_threshold=5.0,  # Low - learn many starters
            sent_starter_min_freq=2,
            collocation_threshold=3.0,  # Low - learn many collocations
            min_colloc_freq=2,
        )

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "PunktHyperparameters":
        """Create hyperparameters from a dictionary."""
        # Filter to only valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_config = {k: v for k, v in config.items() if k in valid_fields}
        return cls(**filtered_config)

    def to_dict(self) -> dict[str, Any]:
        """Convert hyperparameters to dictionary."""
        return {
            "abbrev_threshold": self.abbrev_threshold,
            "abbrev_backoff": self.abbrev_backoff,
            "abbrev_colloc_freq_threshold": self.abbrev_colloc_freq_threshold,
            "max_abbrev_length": self.max_abbrev_length,
            "sent_starter_threshold": self.sent_starter_threshold,
            "sent_starter_min_freq": self.sent_starter_min_freq,
            "collocation_threshold": self.collocation_threshold,
            "min_colloc_freq": self.min_colloc_freq,
            "include_all_collocs": self.include_all_collocs,
            "include_abbrev_collocs": self.include_abbrev_collocs,
            "type_fdist_min_freq": self.type_fdist_min_freq,
            "colloc_fdist_min_freq": self.colloc_fdist_min_freq,
            "prune_interval": self.prune_interval,
        }

    def apply_to_trainer(self, trainer: "PunktTrainer") -> None:
        """
        Apply these hyperparameters to a PunktTrainer instance.

        Args:
            trainer: The trainer to configure
        """
        # Abbreviation parameters
        trainer.ABBREV = self.abbrev_threshold
        trainer.ABBREV_BACKOFF = self.abbrev_backoff
        # trainer.ABBREV_COLLOC_FREQ_THRESHOLD = self.abbrev_colloc_freq_threshold  # Not used in trainer
        trainer.MAX_ABBREV_LENGTH = self.max_abbrev_length

        # Sentence starter parameters
        trainer.SENT_STARTER = self.sent_starter_threshold
        trainer.SENT_STARTER_MIN_FREQ = self.sent_starter_min_freq

        # Collocation parameters
        trainer.COLLOCATION = self.collocation_threshold
        trainer.MIN_COLLOC_FREQ = self.min_colloc_freq
        trainer.INCLUDE_ALL_COLLOCS = self.include_all_collocs
        trainer.INCLUDE_ABBREV_COLLOCS = self.include_abbrev_collocs

        # Memory efficiency parameters
        trainer.TYPE_FDIST_MIN_FREQ = self.type_fdist_min_freq
        trainer.COLLOC_FDIST_MIN_FREQ = self.colloc_fdist_min_freq
        trainer.PRUNE_INTERVAL = self.prune_interval


# Preset configurations for easy access
PRESETS = {
    "conservative": PunktHyperparameters.conservative(),
    "balanced": PunktHyperparameters.balanced(),
    "aggressive": PunktHyperparameters.aggressive(),
}
