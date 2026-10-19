"""
Training module for nupunkt.

This module provides functionality for training, optimizing, and converting
Punkt tokenizer models.
"""

from nupunkt.training.core import get_training_stats, train_model
from nupunkt.training.hyperparameters import PRESETS, PunktHyperparameters
from nupunkt.training.optimizer import convert_model_format, get_model_info, optimize_model

__all__ = [
    "train_model",
    "get_training_stats",
    "optimize_model",
    "convert_model_format",
    "get_model_info",
    "PunktHyperparameters",
    "PRESETS",
]
