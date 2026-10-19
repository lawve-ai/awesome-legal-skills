"""
Hyperparameter optimization and algorithm discovery for nupunkt.

This module provides tools for automatically optimizing tokenizer parameters
and discovering new algorithmic improvements.
"""

from nupunkt.optimization.discovery import (
    AlgorithmVariant,
    discover_improvements,
    test_algorithm_variant,
)
from nupunkt.optimization.hyperparameter import (
    HyperparameterSpace,
    grid_search,
    optimize_hyperparameters,
    random_search,
)

__all__ = [
    # Hyperparameter optimization
    "HyperparameterSpace",
    "optimize_hyperparameters",
    "grid_search",
    "random_search",
    # Algorithm discovery
    "AlgorithmVariant",
    "discover_improvements",
    "test_algorithm_variant",
]
