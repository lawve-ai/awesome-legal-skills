"""
Main evaluation functionality for nupunkt tokenizers.

This module provides high-level functions for evaluating tokenizers
on datasets and comparing different models.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nupunkt.evaluation.dataset import TestCase, load_evaluation_data
from nupunkt.evaluation.metrics import (
    EvaluationMetrics,
    calculate_metrics,
)
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer


@dataclass
class ModelEvaluation:
    """Container for model evaluation results."""

    model_name: str
    dataset_name: str
    metrics: EvaluationMetrics
    errors: list[dict[str, Any]]
    config: dict[str, Any] | None = None


def evaluate_single_example(
    tokenizer: PunktSentenceTokenizer, test_case: TestCase
) -> tuple[list[str], float, dict[str, Any] | None]:
    """
    Evaluate tokenizer on a single example.

    Args:
        tokenizer: Tokenizer to evaluate
        test_case: Single test case

    Returns:
        Tuple of (predicted_sentences, processing_time, error_info)
    """
    start_time = time.time()

    try:
        predicted = list(tokenizer.tokenize(test_case.text))
        processing_time = time.time() - start_time

        # Check for errors
        error_info = None
        if len(predicted) != len(test_case.sentences):
            error_info = {
                "type": "count_mismatch",
                "predicted_count": len(predicted),
                "true_count": len(test_case.sentences),
                "text_preview": test_case.text[:100] + "..."
                if len(test_case.text) > 100
                else test_case.text,
            }

        return predicted, processing_time, error_info

    except Exception as e:
        processing_time = time.time() - start_time
        error_info = {
            "type": "exception",
            "exception": str(e),
            "text_preview": test_case.text[:100] + "..."
            if len(test_case.text) > 100
            else test_case.text,
        }
        return [], processing_time, error_info


def evaluate_on_dataset(
    tokenizer: PunktSentenceTokenizer,
    dataset_path: str | Path,
    max_samples: int | None = None,
    verbose: bool = True,
) -> ModelEvaluation:
    """
    Evaluate a tokenizer on an entire dataset.

    Args:
        tokenizer: Tokenizer to evaluate
        dataset_path: Path to evaluation dataset
        max_samples: Maximum samples to evaluate
        verbose: Whether to print progress

    Returns:
        ModelEvaluation object with results
    """
    dataset_path = Path(dataset_path)

    # Load test cases
    if verbose:
        print(f"Loading evaluation data from {dataset_path}...")
    test_cases = load_evaluation_data(dataset_path, max_samples=max_samples, show_progress=verbose)

    if verbose:
        print(f"Loaded {len(test_cases)} test cases")

    # Evaluate each test case
    all_predicted = []
    all_true = []
    all_texts = []
    total_time = 0
    errors = []

    # Try to use tqdm for progress bar if available
    if verbose:
        try:
            from tqdm import tqdm

            test_case_iter = tqdm(test_cases, desc="Evaluating", unit="case")
        except ImportError:
            test_case_iter = test_cases
            print("Note: Install tqdm for progress bars during evaluation.")
    else:
        test_case_iter = test_cases

    for i, test_case in enumerate(test_case_iter):
        if verbose and not hasattr(test_case_iter, "__name__") and i % 100 == 0:
            print(f"  Processing {i}/{len(test_cases)}...")

        predicted, proc_time, error_info = evaluate_single_example(tokenizer, test_case)

        all_predicted.extend(predicted)
        all_true.extend(test_case.sentences)
        all_texts.append(test_case.text)
        total_time += proc_time

        if error_info:
            error_info["index"] = i
            errors.append(error_info)

    # Calculate aggregate metrics
    combined_text = " ".join(all_texts)
    metrics = calculate_metrics(all_predicted, all_true, combined_text, total_time)

    if verbose:
        print("\n" + metrics.summary())
        if errors:
            print(f"\nFound {len(errors)} errors during evaluation")

    return ModelEvaluation(
        model_name="PunktSentenceTokenizer",
        dataset_name=dataset_path.name,
        metrics=metrics,
        errors=errors,
    )


def evaluate_model(
    model_path: str | Path,
    dataset_path: str | Path,
    output_path: str | Path | None = None,
    max_samples: int | None = None,
    verbose: bool = True,
) -> ModelEvaluation:
    """
    Evaluate a saved model on a dataset.

    Args:
        model_path: Path to saved model
        dataset_path: Path to evaluation dataset
        output_path: Optional path to save results
        max_samples: Maximum samples to evaluate
        verbose: Whether to print progress

    Returns:
        ModelEvaluation object
    """
    if verbose:
        print(f"Loading model from {model_path}...")

    # Load tokenizer
    from nupunkt import load

    tokenizer = load(str(model_path))

    # Evaluate
    evaluation = evaluate_on_dataset(tokenizer, dataset_path, max_samples, verbose)
    evaluation.model_name = Path(model_path).stem

    # Save results if requested
    if output_path:
        save_evaluation_results(evaluation, output_path)

    return evaluation


def compare_models(
    model_paths: list[str | Path],
    dataset_path: str | Path,
    output_path: str | Path | None = None,
    max_samples: int | None = None,
    verbose: bool = True,
) -> list[ModelEvaluation]:
    """
    Compare multiple models on the same dataset.

    Args:
        model_paths: List of model paths to compare
        dataset_path: Path to evaluation dataset
        output_path: Optional path to save comparison
        max_samples: Maximum samples to evaluate
        verbose: Whether to print progress

    Returns:
        List of ModelEvaluation objects
    """
    evaluations = []

    for model_path in model_paths:
        if verbose:
            print(f"\n{'=' * 60}")
            print(f"Evaluating {model_path}")
            print("=" * 60)

        evaluation = evaluate_model(model_path, dataset_path, None, max_samples, verbose)
        evaluations.append(evaluation)

    # Print comparison
    if verbose:
        print_model_comparison(evaluations)

    # Save comparison if requested
    if output_path:
        save_comparison_results(evaluations, output_path)

    return evaluations


def run_benchmark(
    tokenizer_factory: Callable[[], PunktSentenceTokenizer],
    benchmark_name: str,
    dataset_paths: list[str | Path],
    output_dir: str | Path | None = None,
    max_samples: int | None = None,
) -> dict[str, ModelEvaluation]:
    """
    Run a comprehensive benchmark across multiple datasets.

    Args:
        tokenizer_factory: Function that creates a tokenizer instance
        benchmark_name: Name for this benchmark
        dataset_paths: List of dataset paths to evaluate on
        output_dir: Optional directory to save results
        max_samples: Maximum samples per dataset

    Returns:
        Dictionary mapping dataset names to evaluations
    """
    results = {}

    print(f"Running benchmark: {benchmark_name}")
    print("=" * 60)

    for dataset_path in dataset_paths:
        dataset_path = Path(dataset_path)
        print(f"\nEvaluating on {dataset_path.name}...")

        tokenizer = tokenizer_factory()
        evaluation = evaluate_on_dataset(tokenizer, dataset_path, max_samples, verbose=False)
        evaluation.model_name = benchmark_name

        results[dataset_path.name] = evaluation

        print(f"  F1 Score: {evaluation.metrics.f1:.2%}")
        print(f"  Boundary F1: {evaluation.metrics.boundary_f1:.2%}")
        print(f"  Exact Match: {evaluation.metrics.exact_match_accuracy:.2%}")

    # Save results if requested
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for dataset_name, evaluation in results.items():
            output_path = output_dir / f"{benchmark_name}_{dataset_name}_results.json"
            save_evaluation_results(evaluation, output_path)

    return results


def save_evaluation_results(evaluation: ModelEvaluation, output_path: str | Path) -> None:
    """Save evaluation results to JSON file."""
    output_path = Path(output_path)

    data = {
        "model_name": evaluation.model_name,
        "dataset_name": evaluation.dataset_name,
        "metrics": evaluation.metrics.to_dict(),
        "errors": evaluation.errors,
        "config": evaluation.config,
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


def save_comparison_results(evaluations: list[ModelEvaluation], output_path: str | Path) -> None:
    """Save model comparison results."""
    output_path = Path(output_path)

    data = {
        "comparison": [
            {
                "model_name": eval.model_name,
                "dataset_name": eval.dataset_name,
                "metrics": eval.metrics.to_dict(),
                "error_count": len(eval.errors),
            }
            for eval in evaluations
        ]
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


def print_model_comparison(evaluations: list[ModelEvaluation]) -> None:
    """Print a formatted comparison of model evaluations."""
    print("\n" + "=" * 80)
    print("MODEL COMPARISON")
    print("=" * 80)

    # Header
    print(f"{'Model':<30} {'F1':>8} {'Boundary F1':>12} {'Exact Match':>12} {'Speed (sent/s)':>15}")
    print("-" * 80)

    # Results
    for eval in evaluations:
        print(
            f"{eval.model_name:<30} "
            f"{eval.metrics.f1:>8.2%} "
            f"{eval.metrics.boundary_f1:>12.2%} "
            f"{eval.metrics.exact_match_accuracy:>12.2%} "
            f"{eval.metrics.sentences_per_second:>15,.0f}"
        )

    print("=" * 80)
