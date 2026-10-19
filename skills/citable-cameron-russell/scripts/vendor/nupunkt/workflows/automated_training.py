"""
Automated training and evaluation workflow for nupunkt.

This module demonstrates a complete automated pipeline for:
1. Training models with different configurations
2. Evaluating them on test data
3. Performing hyperparameter optimization
4. Generating comprehensive reports
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from nupunkt.evaluation.evaluator import evaluate_model
from nupunkt.optimization.hyperparameter import HyperparameterSpace, optimize_hyperparameters
from nupunkt.training import train_model


class AutomatedWorkflow:
    """Automated training and evaluation workflow."""

    def __init__(self, output_dir: str | Path = "workflow_outputs"):
        """Initialize workflow with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self.logger = logging.getLogger("nupunkt.workflow")
        handler = logging.FileHandler(self.output_dir / "workflow.log")
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def run_complete_pipeline(
        self,
        train_data: str | Path,
        test_data: str | Path,
        experiment_name: str = "experiment",
        optimize_params: bool = True,
        n_optimization_trials: int = 10,
    ) -> dict[str, Any]:
        """
        Run complete training and evaluation pipeline.

        Args:
            train_data: Training data path
            test_data: Test data path
            experiment_name: Name for this experiment
            optimize_params: Whether to run hyperparameter optimization
            n_optimization_trials: Number of optimization trials

        Returns:
            Dictionary with all results
        """
        self.logger.info(f"Starting experiment: {experiment_name}")
        start_time = time.time()

        results = {
            "experiment_name": experiment_name,
            "train_data": str(train_data),
            "test_data": str(test_data),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Create experiment directory
        exp_dir = self.output_dir / experiment_name
        exp_dir.mkdir(exist_ok=True)

        # Step 1: Train baseline model
        self.logger.info("Training baseline model...")
        baseline_model = exp_dir / "baseline_model.bin"
        train_model(
            training_texts=[train_data],
            output_path=baseline_model,
            format_type="binary",
            use_default_abbreviations=True,
        )

        # Evaluate baseline
        self.logger.info("Evaluating baseline model...")
        baseline_eval = evaluate_model(
            baseline_model, test_data, output_path=exp_dir / "baseline_eval.json", verbose=False
        )
        results["baseline_evaluation"] = baseline_eval.metrics.to_dict()

        # Step 2: Hyperparameter optimization (if requested)
        if optimize_params:
            self.logger.info("Running hyperparameter optimization...")
            opt_result = optimize_hyperparameters(
                HyperparameterSpace(),
                train_data,
                test_data,
                search_method="random",
                n_trials=n_optimization_trials,
                output_path=exp_dir / "optimization_results.json",
                verbose=False,
            )

            results["optimization"] = {
                "best_params": opt_result.best_params,
                "best_metrics": opt_result.best_metrics.to_dict(),
                "improvement_over_baseline": {
                    "f1": opt_result.best_metrics.f1 - baseline_eval.metrics.f1,
                    "boundary_f1": opt_result.best_metrics.boundary_f1
                    - baseline_eval.metrics.boundary_f1,
                },
            }

            # Train final model with best params
            self.logger.info("Training optimized model...")
            optimized_model = exp_dir / "optimized_model.bin"
            self._train_with_params(opt_result.best_params, train_data, optimized_model)

            # Evaluate optimized model
            optimized_eval = evaluate_model(
                optimized_model,
                test_data,
                output_path=exp_dir / "optimized_eval.json",
                verbose=False,
            )
            results["optimized_evaluation"] = optimized_eval.metrics.to_dict()

        # Step 3: Generate comprehensive report
        total_time = time.time() - start_time
        results["total_time"] = total_time

        report = self._generate_report(results)
        with open(exp_dir / "experiment_report.md", "w") as f:
            f.write(report)

        # Save all results
        with open(exp_dir / "experiment_results.json", "w") as f:
            json.dump(results, f, indent=2)

        self.logger.info(f"Experiment completed in {total_time:.1f}s")

        return results

    def _train_with_params(
        self, params: dict[str, Any], train_data: str | Path, output_path: str | Path
    ) -> None:
        """Train model with specific parameters."""
        from nupunkt.trainers.base_trainer import PunktTrainer

        # Override class variables
        original_abbrev = PunktTrainer.ABBREV
        original_colloc = PunktTrainer.COLLOCATION
        original_starter = PunktTrainer.SENT_STARTER

        try:
            PunktTrainer.ABBREV = params["abbrev_threshold"]
            PunktTrainer.COLLOCATION = params["colloc_threshold"]
            PunktTrainer.SENT_STARTER = params["sent_starter_threshold"]

            train_model(
                training_texts=[train_data],
                output_path=output_path,
                format_type="binary",
                memory_efficient=params["use_memory_efficient"],
                batch_size=params["batch_size"],
                prune_freq=params["prune_freq"],
                min_type_freq=params["min_type_freq"],
                min_starter_freq=params["min_sent_starter_freq"],
                min_colloc_freq=params["min_colloc_freq"],
                use_default_abbreviations=params["include_default_abbrevs"],
            )
        finally:
            # Restore original values
            PunktTrainer.ABBREV = original_abbrev
            PunktTrainer.COLLOCATION = original_colloc
            PunktTrainer.SENT_STARTER = original_starter

    def _generate_report(self, results: dict[str, Any]) -> str:
        """Generate a comprehensive Markdown report."""
        report = f"""# Experiment Report: {results["experiment_name"]}

## Overview
- **Date**: {results["timestamp"]}
- **Training Data**: {results["train_data"]}
- **Test Data**: {results["test_data"]}
- **Total Time**: {results["total_time"]:.1f}s

## Baseline Model Performance

| Metric | Value |
|--------|-------|
| F1 Score | {results["baseline_evaluation"]["f1"]:.2%} |
| Precision | {results["baseline_evaluation"]["precision"]:.2%} |
| Recall | {results["baseline_evaluation"]["recall"]:.2%} |
| Boundary F1 | {results["baseline_evaluation"]["boundary_f1"]:.2%} |
| Exact Match | {results["baseline_evaluation"]["exact_match_accuracy"]:.2%} |
| Speed (sent/s) | {results["baseline_evaluation"]["sentences_per_second"]:,.0f} |

"""

        if "optimization" in results:
            report += f"""## Hyperparameter Optimization

### Best Parameters Found
```json
{json.dumps(results["optimization"]["best_params"], indent=2)}
```

### Performance Improvement
- **F1 Improvement**: {results["optimization"]["improvement_over_baseline"]["f1"]:.2%}
- **Boundary F1 Improvement**: {results["optimization"]["improvement_over_baseline"]["boundary_f1"]:.2%}

### Optimized Model Performance

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| F1 Score | {results["baseline_evaluation"]["f1"]:.2%} | {results["optimized_evaluation"]["f1"]:.2%} | {results["optimized_evaluation"]["f1"] - results["baseline_evaluation"]["f1"]:.2%} |
| Precision | {results["baseline_evaluation"]["precision"]:.2%} | {results["optimized_evaluation"]["precision"]:.2%} | {results["optimized_evaluation"]["precision"] - results["baseline_evaluation"]["precision"]:.2%} |
| Recall | {results["baseline_evaluation"]["recall"]:.2%} | {results["optimized_evaluation"]["recall"]:.2%} | {results["optimized_evaluation"]["recall"] - results["baseline_evaluation"]["recall"]:.2%} |
| Boundary F1 | {results["baseline_evaluation"]["boundary_f1"]:.2%} | {results["optimized_evaluation"]["boundary_f1"]:.2%} | {results["optimized_evaluation"]["boundary_f1"] - results["baseline_evaluation"]["boundary_f1"]:.2%} |

"""

        return report


def run_automated_experiment(
    train_data: str | Path,
    test_data: str | Path,
    experiment_name: str = "automated_experiment",
    output_dir: str | Path = "experiments",
    optimize: bool = True,
) -> dict[str, Any]:
    """
    Convenience function to run an automated experiment.

    Args:
        train_data: Training data path
        test_data: Test data path
        experiment_name: Name for the experiment
        output_dir: Output directory
        optimize: Whether to run hyperparameter optimization

    Returns:
        Experiment results dictionary
    """
    workflow = AutomatedWorkflow(output_dir)
    return workflow.run_complete_pipeline(
        train_data, test_data, experiment_name, optimize_params=optimize
    )


if __name__ == "__main__":
    # Example usage
    results = run_automated_experiment(
        "data/train2.jsonl.gz", "data/test.jsonl.gz", "example_experiment"
    )
    print("Experiment completed. Results saved to: experiments/example_experiment/")
