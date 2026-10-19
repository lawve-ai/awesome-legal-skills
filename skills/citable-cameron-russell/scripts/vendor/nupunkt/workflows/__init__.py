"""
Automated workflows for nupunkt.

This module provides pre-built workflows for common tasks like
training, evaluation, and optimization.
"""

from nupunkt.workflows.automated_training import (
    AutomatedWorkflow,
    run_automated_experiment,
)

__all__ = [
    "AutomatedWorkflow",
    "run_automated_experiment",
]
