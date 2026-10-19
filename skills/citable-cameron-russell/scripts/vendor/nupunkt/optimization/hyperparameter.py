"""
Hyperparameter optimization for Punkt tokenizers.

This module provides tools for optimizing training and tokenization parameters
to achieve better performance on specific datasets.
"""

import itertools
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nupunkt.evaluation.evaluator import evaluate_on_dataset
from nupunkt.evaluation.metrics import EvaluationMetrics
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer
from nupunkt.trainers.base_trainer import PunktTrainer
from nupunkt.training.core import train_model


@dataclass
class HyperparameterSpace:
    """Define the hyperparameter search space."""

    # Training parameters
    abbrev_threshold: list[float] | None = None
    colloc_threshold: list[float] | None = None
    sent_starter_threshold: list[float] | None = None
    min_colloc_freq: list[int] | None = None
    min_sent_starter_freq: list[int] | None = None

    # Memory efficiency parameters
    batch_size: list[int] | None = None
    prune_freq: list[int] | None = None
    min_type_freq: list[int] | None = None

    # Feature toggles
    include_default_abbrevs: list[bool] | None = None
    use_memory_efficient: list[bool] | None = None

    def __post_init__(self):
        """Set default search spaces."""
        if self.abbrev_threshold is None:
            self.abbrev_threshold = [1.5, 2.0, 2.5, 3.0, 3.5]
        if self.colloc_threshold is None:
            self.colloc_threshold = [6.0, 7.0, 7.46, 8.0, 9.0]
        if self.sent_starter_threshold is None:
            self.sent_starter_threshold = [25, 30, 35, 40]
        if self.min_colloc_freq is None:
            self.min_colloc_freq = [1, 2, 3, 5]
        if self.min_sent_starter_freq is None:
            self.min_sent_starter_freq = [1, 2, 3]
        if self.batch_size is None:
            self.batch_size = [100000, 500000, 1000000]
        if self.prune_freq is None:
            self.prune_freq = [10000, 50000, 100000]
        if self.min_type_freq is None:
            self.min_type_freq = [1, 2, 3]
        if self.include_default_abbrevs is None:
            self.include_default_abbrevs = [True, False]
        if self.use_memory_efficient is None:
            self.use_memory_efficient = [True]

    def get_param_grid(self) -> list[dict[str, Any]]:
        """Get all parameter combinations for grid search."""
        # __post_init__ always populates these with non-None lists; assert to
        # narrow the `List[X] | None` field types for the type checker.
        assert self.abbrev_threshold is not None
        assert self.colloc_threshold is not None
        assert self.sent_starter_threshold is not None
        assert self.min_colloc_freq is not None
        assert self.min_sent_starter_freq is not None
        assert self.batch_size is not None
        assert self.prune_freq is not None
        assert self.min_type_freq is not None
        assert self.include_default_abbrevs is not None
        assert self.use_memory_efficient is not None

        param_dict: dict[str, list[Any]] = {
            "abbrev_threshold": self.abbrev_threshold,
            "colloc_threshold": self.colloc_threshold,
            "sent_starter_threshold": self.sent_starter_threshold,
            "min_colloc_freq": self.min_colloc_freq,
            "min_sent_starter_freq": self.min_sent_starter_freq,
            "batch_size": self.batch_size,
            "prune_freq": self.prune_freq,
            "min_type_freq": self.min_type_freq,
            "include_default_abbrevs": self.include_default_abbrevs,
            "use_memory_efficient": self.use_memory_efficient,
        }

        # Create all combinations
        keys = list(param_dict.keys())
        values = [param_dict[k] for k in keys]

        param_combinations = []
        for combo in itertools.product(*values):
            param_combinations.append(dict(zip(keys, combo)))

        return param_combinations

    def sample_random(self, n_samples: int) -> list[dict[str, Any]]:
        """Sample random parameter combinations."""
        # __post_init__ always populates these with non-None lists; assert to
        # narrow the `List[X] | None` field types for the type checker.
        assert self.abbrev_threshold is not None
        assert self.colloc_threshold is not None
        assert self.sent_starter_threshold is not None
        assert self.min_colloc_freq is not None
        assert self.min_sent_starter_freq is not None
        assert self.batch_size is not None
        assert self.prune_freq is not None
        assert self.min_type_freq is not None
        assert self.include_default_abbrevs is not None
        assert self.use_memory_efficient is not None

        samples = []

        for _ in range(n_samples):
            sample = {
                "abbrev_threshold": random.choice(self.abbrev_threshold),
                "colloc_threshold": random.choice(self.colloc_threshold),
                "sent_starter_threshold": random.choice(self.sent_starter_threshold),
                "min_colloc_freq": random.choice(self.min_colloc_freq),
                "min_sent_starter_freq": random.choice(self.min_sent_starter_freq),
                "batch_size": random.choice(self.batch_size),
                "prune_freq": random.choice(self.prune_freq),
                "min_type_freq": random.choice(self.min_type_freq),
                "include_default_abbrevs": random.choice(self.include_default_abbrevs),
                "use_memory_efficient": random.choice(self.use_memory_efficient),
            }
            samples.append(sample)

        return samples


@dataclass
class OptimizationResult:
    """Result from hyperparameter optimization."""

    best_params: dict[str, Any]
    best_metrics: EvaluationMetrics
    all_results: list[tuple[dict[str, Any], EvaluationMetrics]]
    optimization_time: float

    def save(self, output_path: str | Path) -> None:
        """Save optimization results."""
        data = {
            "best_params": self.best_params,
            "best_metrics": self.best_metrics.to_dict(),
            "all_results": [
                {"params": params, "metrics": metrics.to_dict()}
                for params, metrics in self.all_results
            ],
            "optimization_time": self.optimization_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def summary(self) -> str:
        """Create a summary of optimization results."""
        return f"""Hyperparameter Optimization Results
=====================================
Best F1 Score: {self.best_metrics.f1:.2%}
Best Boundary F1: {self.best_metrics.boundary_f1:.2%}
Total configurations tested: {len(self.all_results)}
Optimization time: {self.optimization_time:.1f}s

Best Parameters:
{json.dumps(self.best_params, indent=2)}

Top 5 Configurations:
"""


def train_and_evaluate(
    params: dict[str, Any],
    train_data: str | Path,
    eval_data: str | Path,
    abbrev_files: list[str | Path] | None = None,
    verbose: bool = False,
) -> tuple[dict[str, Any], EvaluationMetrics]:
    """
    Train a model with given parameters and evaluate it.

    Args:
        params: Hyperparameter configuration
        train_data: Training data path
        eval_data: Evaluation data path
        abbrev_files: Optional abbreviation files
        verbose: Whether to print progress

    Returns:
        Tuple of (params, metrics)
    """
    if verbose:
        print(f"Training with params: {params}")

    # Create a temporary model path
    temp_model = Path(f"temp_model_{hash(str(params))}.bin")

    try:
        # Override PunktTrainer class variables with our parameters
        original_abbrev = PunktTrainer.ABBREV
        original_colloc = PunktTrainer.COLLOCATION
        original_starter = PunktTrainer.SENT_STARTER

        PunktTrainer.ABBREV = params["abbrev_threshold"]
        PunktTrainer.COLLOCATION = params["colloc_threshold"]
        PunktTrainer.SENT_STARTER = params["sent_starter_threshold"]

        # Train model
        train_model(
            training_texts=[train_data],
            abbreviation_files=abbrev_files,
            output_path=temp_model,
            format_type="binary",
            memory_efficient=params["use_memory_efficient"],
            batch_size=params["batch_size"],
            prune_freq=params["prune_freq"],
            min_type_freq=params["min_type_freq"],
            min_starter_freq=params["min_sent_starter_freq"],
            min_colloc_freq=params["min_colloc_freq"],
            use_default_abbreviations=params["include_default_abbrevs"],
            progress_callback=None,
        )

        # Restore original values
        PunktTrainer.ABBREV = original_abbrev
        PunktTrainer.COLLOCATION = original_colloc
        PunktTrainer.SENT_STARTER = original_starter

        # Load and evaluate model
        tokenizer = PunktSentenceTokenizer.load(temp_model)
        evaluation = evaluate_on_dataset(tokenizer, eval_data, verbose=False)

        return params, evaluation.metrics

    finally:
        # Clean up temporary model
        if temp_model.exists():
            temp_model.unlink()


def optimize_hyperparameters(
    search_space: HyperparameterSpace,
    train_data: str | Path,
    eval_data: str | Path,
    search_method: str = "random",
    n_trials: int = 20,
    abbrev_files: list[str | Path] | None = None,
    output_path: str | Path | None = None,
    verbose: bool = True,
) -> OptimizationResult:
    """
    Optimize hyperparameters for a specific dataset.

    Args:
        search_space: Hyperparameter search space
        train_data: Training data path
        eval_data: Evaluation data path
        search_method: "grid" or "random"
        n_trials: Number of trials (for random search)
        abbrev_files: Optional abbreviation files
        output_path: Optional path to save results
        verbose: Whether to print progress

    Returns:
        OptimizationResult object
    """
    start_time = time.time()

    # Get parameter configurations
    if search_method == "grid":
        param_configs = search_space.get_param_grid()
        if verbose:
            print(f"Grid search: {len(param_configs)} configurations")
    else:
        param_configs = search_space.sample_random(n_trials)
        if verbose:
            print(f"Random search: {n_trials} configurations")

    # Evaluate each configuration
    results = []
    best_f1 = 0
    best_params = None
    best_metrics = None

    for i, params in enumerate(param_configs):
        if verbose:
            print(f"\nConfiguration {i + 1}/{len(param_configs)}")

        params_copy, metrics = train_and_evaluate(
            params, train_data, eval_data, abbrev_files, verbose
        )

        results.append((params_copy, metrics))

        if metrics.f1 > best_f1:
            best_f1 = metrics.f1
            best_params = params_copy
            best_metrics = metrics

            if verbose:
                print(f"  New best F1: {best_f1:.2%}")

    optimization_time = time.time() - start_time

    # Create result object
    if best_params is None or best_metrics is None:
        raise ValueError("No valid parameter combinations found during optimization")

    result = OptimizationResult(
        best_params=best_params,
        best_metrics=best_metrics,
        all_results=results,
        optimization_time=optimization_time,
    )

    if verbose:
        print("\n" + result.summary())

        # Print top 5 configurations
        sorted_results = sorted(results, key=lambda x: x[1].f1, reverse=True)[:5]
        for i, (params, metrics) in enumerate(sorted_results):
            print(f"\n{i + 1}. F1: {metrics.f1:.2%}, Boundary F1: {metrics.boundary_f1:.2%}")
            print(f"   Params: {json.dumps(params, indent=6)}")

    # Save results if requested
    if output_path:
        result.save(output_path)
        if verbose:
            print(f"\nResults saved to {output_path}")

    return result


def grid_search(
    search_space: HyperparameterSpace, train_data: str | Path, eval_data: str | Path, **kwargs
) -> OptimizationResult:
    """Convenience function for grid search."""
    return optimize_hyperparameters(
        search_space, train_data, eval_data, search_method="grid", **kwargs
    )


def random_search(
    search_space: HyperparameterSpace,
    train_data: str | Path,
    eval_data: str | Path,
    n_trials: int = 20,
    **kwargs,
) -> OptimizationResult:
    """Convenience function for random search."""
    return optimize_hyperparameters(
        search_space, train_data, eval_data, search_method="random", n_trials=n_trials, **kwargs
    )
