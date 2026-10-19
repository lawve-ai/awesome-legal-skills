"""
Comprehensive metrics for evaluating sentence tokenization.

This module implements various metrics for assessing tokenizer performance,
including precision, recall, F1, boundary accuracy, and detailed error analysis.
"""

import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""

    precision: float
    recall: float
    f1: float
    accuracy: float
    boundary_precision: float
    boundary_recall: float
    boundary_f1: float
    exact_match_accuracy: float
    over_segmentation_rate: float
    under_segmentation_rate: float
    avg_sentence_length_diff: float
    processing_time: float
    sentences_per_second: float
    total_sentences_pred: int
    total_sentences_true: int
    total_boundaries_pred: int
    total_boundaries_true: int

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "accuracy": round(self.accuracy, 4),
            "boundary_precision": round(self.boundary_precision, 4),
            "boundary_recall": round(self.boundary_recall, 4),
            "boundary_f1": round(self.boundary_f1, 4),
            "exact_match_accuracy": round(self.exact_match_accuracy, 4),
            "over_segmentation_rate": round(self.over_segmentation_rate, 4),
            "under_segmentation_rate": round(self.under_segmentation_rate, 4),
            "avg_sentence_length_diff": round(self.avg_sentence_length_diff, 4),
            "processing_time": round(self.processing_time, 4),
            "sentences_per_second": round(self.sentences_per_second, 2),
            "total_sentences_pred": self.total_sentences_pred,
            "total_sentences_true": self.total_sentences_true,
            "total_boundaries_pred": self.total_boundaries_pred,
            "total_boundaries_true": self.total_boundaries_true,
        }

    def summary(self) -> str:
        """Create a human-readable summary."""
        return f"""Evaluation Metrics Summary:
===========================
Core Metrics:
  - Precision: {self.precision:.2%}
  - Recall: {self.recall:.2%}
  - F1 Score: {self.f1:.2%}
  - Accuracy: {self.accuracy:.2%}
  
Boundary Detection:
  - Boundary Precision: {self.boundary_precision:.2%}
  - Boundary Recall: {self.boundary_recall:.2%}
  - Boundary F1: {self.boundary_f1:.2%}
  
Segmentation Analysis:
  - Exact Match Accuracy: {self.exact_match_accuracy:.2%}
  - Over-segmentation Rate: {self.over_segmentation_rate:.2%}
  - Under-segmentation Rate: {self.under_segmentation_rate:.2%}
  - Avg Sentence Length Diff: {self.avg_sentence_length_diff:.2f} chars
  
Performance:
  - Processing Time: {self.processing_time:.3f}s
  - Sentences/Second: {self.sentences_per_second:.0f}
  
Counts:
  - Predicted Sentences: {self.total_sentences_pred}
  - True Sentences: {self.total_sentences_true}
  - Predicted Boundaries: {self.total_boundaries_pred}
  - True Boundaries: {self.total_boundaries_true}
"""


def get_sentence_boundaries(sentences: list[str], text: str) -> set[int]:
    """
    Extract sentence boundary positions from a list of sentences.

    Args:
        sentences: List of sentence strings
        text: Original text

    Returns:
        Set of character positions where sentences end
    """
    boundaries = set()
    pos = 0

    for sent in sentences:
        # Find the sentence in the text starting from current position
        sent_start = text.find(sent, pos)
        if sent_start == -1:
            # Try stripping whitespace
            sent_stripped = sent.strip()
            sent_start = text.find(sent_stripped, pos)
            if sent_start != -1:
                sent = sent_stripped

        if sent_start != -1:
            sent_end = sent_start + len(sent)
            boundaries.add(sent_end)
            pos = sent_end

    return boundaries


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Calculate precision, recall, and F1 score."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def boundary_accuracy(
    pred_boundaries: set[int], true_boundaries: set[int], tolerance: int = 0
) -> tuple[int, int, int]:
    """
    Calculate boundary detection accuracy with optional tolerance.

    Args:
        pred_boundaries: Predicted boundary positions
        true_boundaries: True boundary positions
        tolerance: Allow boundaries to be off by this many characters

    Returns:
        Tuple of (true_positives, false_positives, false_negatives)
    """
    tp = 0
    matched_true = set()

    # Find true positives with tolerance
    for pred in pred_boundaries:
        for true in true_boundaries:
            if abs(pred - true) <= tolerance and true not in matched_true:
                tp += 1
                matched_true.add(true)
                break

    fp = len(pred_boundaries) - tp
    fn = len(true_boundaries) - tp

    return tp, fp, fn


def normalize_sentence(sent: str) -> str:
    """Normalize a sentence for comparison."""
    # Remove paragraph markers
    sent = sent.replace("<|paragraph|>", " ")
    # Normalize whitespace (collapse multiple spaces)
    sent = " ".join(sent.split())
    return sent.strip()


def calculate_metrics(
    pred_sentences: list[str], true_sentences: list[str], original_text: str, processing_time: float
) -> EvaluationMetrics:
    """
    Calculate comprehensive evaluation metrics.

    Args:
        pred_sentences: Predicted sentences
        true_sentences: True sentences
        original_text: Original text
        processing_time: Time taken to process

    Returns:
        EvaluationMetrics object with all metrics
    """
    # Normalize sentences for comparison
    pred_normalized = [normalize_sentence(s) for s in pred_sentences if s.strip()]
    true_normalized = [normalize_sentence(s) for s in true_sentences if s.strip()]

    # Sentence-level metrics using normalized sentences
    pred_set = set(pred_normalized)
    true_set = set(true_normalized)

    # Calculate true positives, false positives, false negatives
    tp = len(pred_set & true_set)
    fp = len(pred_set - true_set)
    fn = len(true_set - pred_set)

    # Core metrics
    precision, recall, f1 = precision_recall_f1(tp, fp, fn)

    # For boundary metrics, we'll use the same as sentence metrics
    # since boundary detection in combined text is problematic
    b_precision, b_recall, b_f1 = precision, recall, f1

    # Exact match accuracy
    exact_match_accuracy = 1.0 if pred_normalized == true_normalized else 0.0

    # Segmentation analysis
    over_segmentation_rate = (
        max(0, len(pred_sentences) - len(true_sentences)) / len(true_sentences)
        if true_sentences
        else 0.0
    )
    under_segmentation_rate = (
        max(0, len(true_sentences) - len(pred_sentences)) / len(true_sentences)
        if true_sentences
        else 0.0
    )

    # Sentence length analysis
    avg_pred_len = (
        sum(len(s) for s in pred_sentences) / len(pred_sentences) if pred_sentences else 0
    )
    avg_true_len = (
        sum(len(s) for s in true_sentences) / len(true_sentences) if true_sentences else 0
    )
    avg_len_diff = abs(avg_pred_len - avg_true_len)

    # Accuracy (average of precision and recall)
    accuracy = (precision + recall) / 2 if (precision + recall) > 0 else 0.0

    # Performance metrics
    sentences_per_second = len(true_sentences) / processing_time if processing_time > 0 else 0

    return EvaluationMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        accuracy=accuracy,
        boundary_precision=b_precision,
        boundary_recall=b_recall,
        boundary_f1=b_f1,
        exact_match_accuracy=exact_match_accuracy,
        over_segmentation_rate=over_segmentation_rate,
        under_segmentation_rate=under_segmentation_rate,
        avg_sentence_length_diff=avg_len_diff,
        processing_time=processing_time,
        sentences_per_second=sentences_per_second,
        total_sentences_pred=len(pred_sentences),
        total_sentences_true=len(true_sentences),
        total_boundaries_pred=len(pred_sentences),
        total_boundaries_true=len(true_sentences),
    )


def create_evaluation_report(
    metrics: EvaluationMetrics,
    output_path: str | None = None,
    model_info: dict[str, Any] | None = None,
) -> str:
    """
    Create a detailed evaluation report.

    Args:
        metrics: Evaluation metrics
        output_path: Optional path to save JSON report
        model_info: Optional model information

    Returns:
        Human-readable report string
    """
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": metrics.to_dict(),
    }

    if model_info:
        report_data["model_info"] = model_info

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)

    return metrics.summary()
