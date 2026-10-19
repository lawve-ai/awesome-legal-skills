"""
Command-line interface for nupunkt.

This module provides CLI commands for training, optimizing, and converting
Punkt tokenizer models using only Python standard library.
"""

import argparse
import sys
from pathlib import Path

from nupunkt._version import __version__
from nupunkt.evaluation.evaluator import compare_models, evaluate_model
from nupunkt.optimization.hyperparameter import HyperparameterSpace, optimize_hyperparameters
from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer
from nupunkt.training import convert_model_format, optimize_model, train_model
from nupunkt.training.core import get_training_stats
from nupunkt.training.optimizer import get_model_info


def train_command(args):
    """Handle the train command."""
    print("=== Training Punkt Model ===")

    # Convert paths (but keep HuggingFace dataset strings)
    training_paths = []
    for f in args.training_files:
        if f.startswith("hf:"):
            training_paths.append(f)  # Keep as string for HF datasets
        else:
            training_paths.append(Path(f))  # Convert to Path for files
    abbreviation_files = [Path(f) for f in args.abbreviations] if args.abbreviations else None

    # Handle hyperparameters
    hyperparameters = None
    if args.hyperparameters:
        # Check if it's a preset or a file
        if args.hyperparameters in ["conservative", "balanced", "aggressive"]:
            hyperparameters = args.hyperparameters
        elif Path(args.hyperparameters).exists() and args.hyperparameters.endswith(".json"):
            # Load from JSON file
            import json

            with open(args.hyperparameters) as f:
                hyperparameters = json.load(f)
        else:
            print(f"Warning: Unknown hyperparameter preset or file: {args.hyperparameters}")

    # Apply individual overrides if specified
    if hyperparameters is None and (
        args.abbrev_threshold or args.sent_starter_threshold or args.collocation_threshold
    ):
        hyperparameters = {}

    if isinstance(hyperparameters, dict):
        if args.abbrev_threshold:
            hyperparameters["abbrev_threshold"] = args.abbrev_threshold
        if args.sent_starter_threshold:
            hyperparameters["sent_starter_threshold"] = args.sent_starter_threshold
        if args.collocation_threshold:
            hyperparameters["collocation_threshold"] = args.collocation_threshold

    # Progress callback
    def progress_callback(stage: str, current: int, total: int):
        if stage == "abbreviations":
            print(f"\rAdding abbreviations: {current + 1}/{total}", end="", flush=True)
            if current == total - 1:
                print(" ✓")
        elif stage == "loading":
            path_str = str(training_paths[current])
            if path_str.startswith("hf:"):
                print(f"Loading HuggingFace dataset {current + 1}/{total}: {path_str[3:]}")
            else:
                print(f"Loading file {current + 1}/{total}: {Path(path_str).name}")
        elif stage == "hf_loading":
            print(
                f"\r  Processing samples: {current + 1}/{total if total else '?'}",
                end="",
                flush=True,
            )
            if total and current == total - 1:
                print(" ✓")
        elif stage == "training":
            print(f"Training batch {current + 1}/{total}")

    try:
        # Train the model
        trainer = train_model(
            training_texts=training_paths,
            abbreviation_files=abbreviation_files,
            output_path=args.output,
            max_samples=args.max_samples,
            format_type=args.format,
            compression_method=args.compression,
            compression_level=args.level,
            memory_efficient=not args.no_memory_efficient,
            batch_size=args.batch_size,
            prune_freq=args.prune_freq,
            min_type_freq=args.min_type_freq,
            min_starter_freq=args.min_starter_freq,
            min_colloc_freq=args.min_colloc_freq,
            use_batches=not args.no_batches,
            verbose=False,
            progress_callback=progress_callback,
            use_default_abbreviations=not args.no_default_abbreviations,
            tokenizer_name=args.tokenizer if hasattr(args, "tokenizer") else None,
            hyperparameters=hyperparameters,
        )

        # Print statistics
        stats = get_training_stats(trainer)
        print("\n=== Training Statistics ===")
        print(f"Abbreviations: {stats['num_abbreviations']}")
        print(f"Sentence starters: {stats['num_sentence_starters']}")
        print(f"Collocations: {stats['num_collocations']}")
        print(f"Orthographic contexts: {stats['num_ortho_contexts']}")

        if args.output:
            print(f"\nModel saved to: {args.output}")

        # Test the model if requested
        if args.test:
            print("\n=== Testing Model ===")
            tokenizer = PunktSentenceTokenizer(trainer.get_params())

            test_cases = [
                "Dr. Smith went to Washington, D.C. He was very excited.",
                "The company (Ltd.) was founded in 1997. It has grown since.",
                "This has an ellipsis... And this is a new sentence.",
                "The meeting is at 3 p.m. Don't be late!",
            ]

            for i, text in enumerate(test_cases, 1):
                print(f"\nTest {i}: {text}")
                sentences = tokenizer.tokenize(text)
                for j, sent in enumerate(sentences, 1):
                    print(f"  Sentence {j}: {sent.strip()}")

        print("\n✓ Training completed successfully!")

    except Exception as e:
        print(f"\n✗ Error during training: {e}", file=sys.stderr)
        sys.exit(1)


def optimize_command(args):
    """Handle the optimize command."""
    print("=== Optimizing Model ===")

    if args.input:
        print(f"Input model: {args.input}")
    else:
        print("Using default model")

    try:
        # Get original model info
        original_info = get_model_info(args.input) if args.input else None
        if original_info:
            print(f"Original size: {original_info['file_size_kb']:.2f} KB")

        # Optimize the model
        output_path = optimize_model(
            input_path=args.input,
            output_path=args.output,
            format_type=args.format,
            compression_method=args.compression,
            compression_level=args.level,
        )

        # Get optimized model info
        new_info = get_model_info(output_path)
        print(f"Optimized size: {new_info['file_size_kb']:.2f} KB")

        if original_info:
            ratio = new_info["file_size"] / original_info["file_size"]
            print(f"Compression ratio: {ratio:.3f}")

        print(f"\n✓ Model optimized and saved to: {output_path}")

    except Exception as e:
        print(f"\n✗ Error during optimization: {e}", file=sys.stderr)
        sys.exit(1)


def convert_command(args):
    """Handle the convert command."""
    print("=== Converting Model ===")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Format: {args.format}")

    try:
        # Convert the model
        stats = convert_model_format(
            input_path=args.input,
            output_path=args.output,
            format_type=args.format,
            compression_method=args.compression,
            compression_level=args.level,
        )

        # Display statistics
        print(f"\nInput size: {stats['input_size'] / 1024:.2f} KB")
        print(f"Output size: {stats['output_size'] / 1024:.2f} KB")
        print(f"Compression ratio: {stats['compression_ratio']:.3f}")
        print(f"Load time: {stats['load_time']:.3f}s")
        print(f"Convert time: {stats['convert_time']:.3f}s")
        print(f"Verify time: {stats['verify_time']:.3f}s")

        print("\n✓ Model converted successfully!")

    except Exception as e:
        print(f"\n✗ Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)


def info_command(args):
    """Handle the info command."""
    print("=== Model Information ===")

    try:
        info = get_model_info(args.model_path)

        print(f"File: {info['file_path']}")
        print(f"Format: {info['format_type']}")
        print(f"Size: {info['file_size_kb']:.2f} KB ({info['file_size_mb']:.2f} MB)")
        print(f"Load time: {info['load_time']:.3f}s")
        print("\nModel contents:")
        print(f"  Abbreviations: {info['num_abbreviations']}")
        print(f"  Sentence starters: {info['num_sentence_starters']}")
        print(f"  Collocations: {info['num_collocations']}")
        print(f"  Orthographic contexts: {info['num_ortho_contexts']}")

    except Exception as e:
        print(f"\n✗ Error reading model: {e}", file=sys.stderr)
        sys.exit(1)


def evaluate_command(args):
    """Handle the evaluate command."""
    print("=== Model Evaluation ===")

    # Handle multiple models for comparison
    if args.compare:
        evaluations = compare_models(
            args.models,
            args.dataset,
            output_path=args.output,
            max_samples=args.max_samples,
            verbose=not args.quiet,
        )

        # Display comparison results
        print("\n=== Model Comparison Results ===")
        for eval_result in evaluations:
            print(f"\nModel: {eval_result.model_name}")
            print(f"  F1 Score: {eval_result.metrics.f1:.4f}")
            print(f"  Precision: {eval_result.metrics.precision:.4f}")
            print(f"  Recall: {eval_result.metrics.recall:.4f}")
            print(f"  Speed: {eval_result.metrics.sentences_per_second:,.0f} sent/s")

        # Find best model
        best_eval = max(evaluations, key=lambda e: e.metrics.f1)
        print(f"\nBest model: {best_eval.model_name} (F1: {best_eval.metrics.f1:.4f})")

        if args.output:
            print(f"\nDetailed comparison saved to {args.output}")
    else:
        # Single model evaluation
        model_path = args.model if args.model else "default"
        evaluation = evaluate_model(
            model_path,
            args.dataset,
            output_path=args.output,
            max_samples=args.max_samples,
            verbose=not args.quiet,
        )

        # Display evaluation results
        print(f"\n=== Evaluation Results for {evaluation.model_name} ===")
        print(f"Dataset: {evaluation.dataset_name}")
        print("\nMetrics:")
        print(f"  F1 Score: {evaluation.metrics.f1:.4f}")
        print(f"  Precision: {evaluation.metrics.precision:.4f}")
        print(f"  Recall: {evaluation.metrics.recall:.4f}")
        print(f"  Accuracy: {evaluation.metrics.accuracy:.4f}")
        print("\nPerformance:")
        print(f"  Speed: {evaluation.metrics.sentences_per_second:,.0f} sentences/second")
        print(f"  Total sentences: {evaluation.metrics.total_sentences_pred}")

        if evaluation.errors:
            print(f"\nErrors: {len(evaluation.errors)} examples had issues")

        if args.output:
            print(f"\nDetailed results saved to {args.output}")


def optimize_params_command(args):
    """Handle the optimize-params command."""
    print("=== Hyperparameter Optimization ===")

    # Create search space
    space = HyperparameterSpace()

    # Override with custom ranges if provided
    if args.abbrev_threshold:
        space.abbrev_threshold = [float(x) for x in args.abbrev_threshold.split(",")]
    if args.colloc_threshold:
        space.colloc_threshold = [float(x) for x in args.colloc_threshold.split(",")]

    # Run optimization
    result = optimize_hyperparameters(
        space,
        args.train_data,
        args.eval_data,
        search_method=args.method,
        n_trials=args.trials,
        abbrev_files=args.abbreviations,
        output_path=args.output,
        verbose=not args.quiet,
    )

    # Display optimization results
    print("\n=== Optimization Complete ===")
    print(f"Trials run: {len(result.all_results)}")
    print(f"Time taken: {result.optimization_time:.1f} seconds")

    print("\nBest parameters found:")
    for param, value in result.best_params.items():
        print(f"  {param}: {value}")

    print("\nBest model performance:")
    print(f"  F1 Score: {result.best_metrics.f1:.4f}")
    print(f"  Precision: {result.best_metrics.precision:.4f}")
    print(f"  Recall: {result.best_metrics.recall:.4f}")

    if args.output:
        print(f"\nOptimization results saved to {args.output}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="nupunkt",
        description="Nupunkt - A multilingual sentence tokenizer with zero dependencies",
    )

    # Add version argument
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Train command
    train_parser = subparsers.add_parser("train", help="Train a new Punkt sentence tokenizer model")
    train_parser.add_argument(
        "training_files",
        nargs="+",
        help="Training files (text, compressed JSONL, or HuggingFace datasets with hf: prefix)",
    )
    train_parser.add_argument("-o", "--output", help="Output path for the trained model")
    train_parser.add_argument(
        "-a", "--abbreviations", action="append", help="JSON file(s) containing abbreviations"
    )
    train_parser.add_argument(
        "--max-samples", type=int, help="Maximum number of samples to use from each JSONL file"
    )
    train_parser.add_argument(
        "--format",
        choices=["binary", "json", "json_xz"],
        default="binary",
        help="Model storage format",
    )
    train_parser.add_argument(
        "--compression",
        choices=["none", "zlib", "lzma", "gzip"],
        default="zlib",
        help="Compression method for binary format",
    )
    train_parser.add_argument("--level", type=int, default=6, help="Compression level (0-9)")
    train_parser.add_argument(
        "--batch-size",
        type=int,
        default=1000000,
        help="Batch size in characters for batch training",
    )
    train_parser.add_argument(
        "--no-memory-efficient", action="store_true", help="Disable memory-efficient training mode"
    )
    train_parser.add_argument(
        "--no-batches", action="store_true", help="Disable batch training mode"
    )
    train_parser.add_argument(
        "--min-type-freq", type=int, default=3, help="Minimum frequency to keep a type"
    )
    train_parser.add_argument(
        "--min-starter-freq",
        type=int,
        default=5,
        help="Minimum frequency to keep a sentence starter",
    )
    train_parser.add_argument(
        "--min-colloc-freq", type=int, default=3, help="Minimum frequency to keep a collocation"
    )
    train_parser.add_argument(
        "--prune-freq",
        type=int,
        default=10000,
        help="How often to prune distributions (token count)",
    )
    train_parser.add_argument(
        "--no-default-abbreviations",
        action="store_true",
        help="Do not load default abbreviations from data/ folder",
    )
    train_parser.add_argument(
        "--test", action="store_true", help="Test the trained model with sample sentences"
    )
    train_parser.add_argument(
        "--tokenizer",
        help="Tokenizer name for decoding HuggingFace datasets (e.g., alea-institute/kl3m-004-128k-cased)",
    )
    train_parser.add_argument(
        "--hyperparameters",
        help="Hyperparameter preset (conservative, balanced, aggressive) or JSON file",
    )
    train_parser.add_argument(
        "--abbrev-threshold", type=float, help="Override abbreviation threshold (default: 0.3)"
    )
    train_parser.add_argument(
        "--sent-starter-threshold",
        type=float,
        help="Override sentence starter threshold (default: 25.0)",
    )
    train_parser.add_argument(
        "--collocation-threshold", type=float, help="Override collocation threshold (default: 7.88)"
    )
    train_parser.set_defaults(func=train_command)

    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Optimize a model's storage format")
    optimize_parser.add_argument(
        "-i", "--input", help="Input model path (default: use default model)"
    )
    optimize_parser.add_argument("-o", "--output", help="Output path for optimized model")
    optimize_parser.add_argument(
        "--format", choices=["binary", "json", "json_xz"], default="binary", help="Output format"
    )
    optimize_parser.add_argument(
        "--compression",
        choices=["none", "zlib", "lzma", "gzip"],
        default="zlib",
        help="Compression method for binary format",
    )
    optimize_parser.add_argument("--level", type=int, default=6, help="Compression level (0-9)")
    optimize_parser.set_defaults(func=optimize_command)

    # Convert command
    convert_parser = subparsers.add_parser(
        "convert", help="Convert a model between different formats"
    )
    convert_parser.add_argument("input", help="Input model file path")
    convert_parser.add_argument("output", help="Output model file path")
    convert_parser.add_argument(
        "--format", choices=["binary", "json", "json_xz"], default="binary", help="Output format"
    )
    convert_parser.add_argument(
        "--compression",
        choices=["none", "zlib", "lzma", "gzip"],
        default="zlib",
        help="Compression method for binary format",
    )
    convert_parser.add_argument("--level", type=int, default=6, help="Compression level (0-9)")
    convert_parser.set_defaults(func=convert_command)

    # Info command
    info_parser = subparsers.add_parser("info", help="Display information about a model file")
    info_parser.add_argument("model_path", help="Path to the model file")
    info_parser.set_defaults(func=info_command)

    # Evaluate command
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate a model on a test dataset")
    evaluate_parser.add_argument("dataset", help="Path to evaluation dataset (JSONL format)")
    evaluate_parser.add_argument(
        "-m", "--model", default="default", help='Model to evaluate (path or "default")'
    )
    evaluate_parser.add_argument("-o", "--output", help="Output path for results JSON")
    evaluate_parser.add_argument("--max-samples", type=int, help="Maximum samples to evaluate")
    evaluate_parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress verbose output"
    )
    evaluate_parser.add_argument("--compare", action="store_true", help="Compare multiple models")
    evaluate_parser.add_argument(
        "--models", nargs="+", help="Models to compare (when using --compare)"
    )
    evaluate_parser.set_defaults(func=evaluate_command)

    # Optimize-params command
    optim_parser = subparsers.add_parser(
        "optimize-params", help="Optimize hyperparameters for a dataset"
    )
    optim_parser.add_argument("train_data", help="Training data path")
    optim_parser.add_argument("eval_data", help="Evaluation data path")
    optim_parser.add_argument("-o", "--output", help="Output path for optimization results")
    optim_parser.add_argument("-a", "--abbreviations", action="append", help="Abbreviation files")
    optim_parser.add_argument(
        "--method", choices=["grid", "random"], default="random", help="Search method"
    )
    optim_parser.add_argument(
        "--trials", type=int, default=20, help="Number of trials for random search"
    )
    optim_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress verbose output")
    optim_parser.add_argument(
        "--abbrev-threshold", help="Comma-separated abbreviation thresholds to try"
    )
    optim_parser.add_argument(
        "--colloc-threshold", help="Comma-separated collocation thresholds to try"
    )
    optim_parser.set_defaults(func=optimize_params_command)

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
