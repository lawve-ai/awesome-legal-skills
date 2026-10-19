"""
Evaluation module for nupunkt.

This module provides comprehensive evaluation capabilities for sentence tokenizers,
including metrics calculation, dataset management, and reporting.
"""

from nupunkt.evaluation.dataset import (
    create_test_cases,
    load_evaluation_data,
    parse_annotated_text,
)
from nupunkt.evaluation.evaluator import (
    compare_models,
    evaluate_model,
    evaluate_on_dataset,
    run_benchmark,
)
from nupunkt.evaluation.metrics import (
    boundary_accuracy,
    calculate_metrics,
    create_evaluation_report,
    precision_recall_f1,
)

__all__ = [
    # Metrics
    "calculate_metrics",
    "precision_recall_f1",
    "boundary_accuracy",
    "create_evaluation_report",
    # Dataset
    "load_evaluation_data",
    "parse_annotated_text",
    "create_test_cases",
    # Evaluator
    "evaluate_model",
    "evaluate_on_dataset",
    "compare_models",
    "run_benchmark",
]
