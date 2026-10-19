"""
Core training functionality for nupunkt.

This module provides the main training workflow logic for creating
Punkt tokenizer models.
"""

import gzip
import json
from pathlib import Path
from typing import Any, Callable

from nupunkt.trainers.base_trainer import PunktTrainer
from nupunkt.training.hyperparameters import PRESETS, PunktHyperparameters

# Optional imports for HuggingFace datasets (not a runtime dependency of nupunkt;
# only needed if the caller wants to train from "hf:org/dataset" sources).
try:
    from datasets import load_dataset  # ty: ignore[unresolved-import]
    from tokenizers import Tokenizer  # ty: ignore[unresolved-import]

    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


def load_abbreviations(file_path: str | Path) -> list[str]:
    """
    Load abbreviations from a JSON file.

    Args:
        file_path: Path to the JSON file containing abbreviations

    Returns:
        List of cleaned abbreviations (lowercase, without trailing periods)
    """
    file_path = Path(file_path)
    with open(file_path, encoding="utf-8") as f:
        abbreviations = json.load(f)

    # Convert abbreviations to lowercase and remove trailing periods
    cleaned_abbrevs = []
    for abbr in abbreviations:
        # Remove trailing period if present
        if abbr.endswith("."):
            abbr = abbr[:-1]
        # Convert to lowercase
        cleaned_abbrevs.append(abbr.lower())

    return cleaned_abbrevs


def load_jsonl_text(
    file_path: str | Path,
    max_samples: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> str:
    """
    Load text from a compressed JSONL file.

    Args:
        file_path: Path to the JSONL.gz file
        max_samples: Maximum number of samples to load (None for all)
        progress_callback: Optional callback for progress reporting (current, total)

    Returns:
        Combined text from all loaded samples
    """
    file_path = Path(file_path)
    combined_text = ""
    sample_count = 0

    # Get total line count for progress tracking
    if not max_samples:
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            total = sum(1 for _ in f)
    else:
        total = max_samples

    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if progress_callback:
                progress_callback(i, total)

            try:
                data = json.loads(line)
                if "text" in data:
                    combined_text += data["text"] + "\n\n"
                    sample_count += 1
                    if max_samples and sample_count >= max_samples:
                        break
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    return combined_text


def load_huggingface_text(
    dataset_name: str,
    tokenizer_name: str | None = None,
    max_samples: int | None = None,
    split: str = "train",
    text_field: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> str:
    """
    Load text from a HuggingFace dataset.

    Args:
        dataset_name: Name of the HuggingFace dataset
        tokenizer_name: Optional tokenizer to decode 'tokens' field
        max_samples: Maximum number of samples to load
        split: Dataset split to use (default: "train")
        text_field: Field name containing text (auto-detected if None)
        progress_callback: Optional callback for progress reporting

    Returns:
        Combined text from the dataset
    """
    if not HF_AVAILABLE:
        raise ImportError(
            "HuggingFace datasets not available. "
            "Install with: pip install nupunkt[training] or uv sync --extra training"
        )

    # Load dataset in streaming mode for efficiency
    dataset = load_dataset(dataset_name, streaming=True, split=split)

    # Load tokenizer if specified
    tokenizer = None
    if tokenizer_name:
        tokenizer = Tokenizer.from_pretrained(tokenizer_name)

    combined_text = ""
    sample_count = 0

    # Get total count if not streaming (for progress)
    total = max_samples if max_samples else None

    for i, record in enumerate(dataset):
        if progress_callback and total:
            progress_callback(i, total)

        # Determine which field to use
        if text_field and text_field in record:
            text = record[text_field]
        elif "text" in record:
            text = record["text"]
        elif "tokens" in record and tokenizer:
            # Decode tokens if we have a tokenizer
            text = tokenizer.decode(record["tokens"])
        else:
            # Try to find a text-like field
            for field in ["content", "document", "sentence", "paragraph"]:
                if field in record:
                    text = record[field]
                    break
            else:
                # Skip if no text field found
                continue

        combined_text += text + "\n\n"
        sample_count += 1

        if max_samples and sample_count >= max_samples:
            break

    return combined_text


def train_model(
    training_texts: str | list[str | Path],
    abbreviations: list[str] | None = None,
    abbreviation_files: list[str | Path] | None = None,
    output_path: str | Path | None = None,
    max_samples: int | None = None,
    format_type: str = "binary",
    compression_method: str = "zlib",
    compression_level: int = 6,
    memory_efficient: bool = True,
    batch_size: int = 1000000,
    prune_freq: int = 10000,
    min_type_freq: int = 3,
    min_starter_freq: int = 5,
    min_colloc_freq: int = 3,
    use_batches: bool = True,
    verbose: bool = False,
    progress_callback: Callable[[str, int, int], None] | None = None,
    use_default_abbreviations: bool = True,
    tokenizer_name: str | None = None,
    hyperparameters: str | dict[str, Any] | PunktHyperparameters | None = None,
) -> PunktTrainer:
    """
    Train a Punkt sentence tokenizer model.

    Args:
        training_texts: Either a string of text, list of text strings, file paths,
                       or HuggingFace dataset names (format: "hf:org/dataset")
        abbreviations: Optional list of abbreviations to include
        abbreviation_files: Optional list of JSON files containing abbreviations
        output_path: Optional path to save the trained model
        max_samples: Maximum number of samples to use from JSONL files or HF datasets
        format_type: Model format ("binary", "json", "json_xz")
        compression_method: Compression method for binary format
        compression_level: Compression level (0-9)
        memory_efficient: Whether to use memory-efficient training mode
        batch_size: Batch size in characters for batch training
        prune_freq: How often to prune distributions (token count)
        min_type_freq: Minimum frequency to keep a type
        min_starter_freq: Minimum frequency to keep a sentence starter
        min_colloc_freq: Minimum frequency to keep a collocation
        use_batches: Whether to use batch training mode
        verbose: Whether to print detailed training information
        progress_callback: Optional callback for progress reporting (stage, current, total)
        use_default_abbreviations: Whether to load default abbreviations from data/ folder
        tokenizer_name: Optional tokenizer name for decoding HuggingFace datasets with 'tokens' field
        hyperparameters: Training hyperparameters - can be:
            - None: Use default hyperparameters
            - str: Preset name ('default', 'balanced', 'legal', 'academic', 'informal')
            - dict: Custom hyperparameter values
            - PunktHyperparameters: Hyperparameter object

    Returns:
        The trained PunktTrainer instance

    Examples:
        # Train from text file
        trainer = train_model(["corpus.txt"])

        # Train from HuggingFace dataset
        trainer = train_model(
            ["hf:alea-institute/kl3m-data-edgar-agreements"],
            tokenizer_name="alea-institute/kl3m-004-128k-cased",
            max_samples=1000
        )
    """
    # Initialize trainer
    trainer = PunktTrainer(verbose=False, memory_efficient=memory_efficient)

    # Apply hyperparameters
    if hyperparameters is not None:
        if isinstance(hyperparameters, str):
            # Use preset
            if hyperparameters not in PRESETS:
                raise ValueError(
                    f"Unknown hyperparameter preset: {hyperparameters}. "
                    f"Available presets: {list(PRESETS.keys())}"
                )
            hp = PRESETS[hyperparameters]
        elif isinstance(hyperparameters, dict):
            # Create from dict
            hp = PunktHyperparameters.from_dict(hyperparameters)
        elif isinstance(hyperparameters, PunktHyperparameters):
            # Use directly
            hp = hyperparameters
        else:
            raise TypeError(f"Invalid hyperparameters type: {type(hyperparameters)}")

        # Apply to trainer
        hp.apply_to_trainer(trainer)

    # Configure memory optimization parameters (override if specified)
    if memory_efficient:
        trainer.TYPE_FDIST_MIN_FREQ = min_type_freq
        trainer.SENT_STARTER_MIN_FREQ = min_starter_freq
        trainer.COLLOC_FDIST_MIN_FREQ = min_colloc_freq
        trainer.PRUNE_INTERVAL = prune_freq

    # Load abbreviations from files
    all_abbreviations = abbreviations or []

    # Load default abbreviations if requested
    if use_default_abbreviations:
        # Bundled with the package so they are available in installed distributions
        data_dir = Path(__file__).parent.parent / "data"

        # Default abbreviation files
        default_abbrev_files = [
            data_dir / "general_abbreviations.json",
            data_dir / "legal_abbreviations.json",
        ]

        # Add default files to the beginning of abbreviation_files list
        if abbreviation_files:
            abbreviation_files = default_abbrev_files + list(abbreviation_files)
        else:
            abbreviation_files = default_abbrev_files

    if abbreviation_files:
        for abbr_file in abbreviation_files:
            if Path(abbr_file).exists():
                all_abbreviations.extend(load_abbreviations(abbr_file))

    # Add abbreviations to trainer
    if all_abbreviations:
        for i, abbr in enumerate(all_abbreviations):
            if progress_callback:
                progress_callback("abbreviations", i, len(all_abbreviations))
            trainer._params.abbrev_types.add(abbr.lower())

    # Process training texts
    if isinstance(training_texts, str):
        # Single text string
        combined_text = training_texts
    else:
        # List of texts or file paths
        combined_text = ""
        for i, text_or_path in enumerate(training_texts):
            if progress_callback:
                progress_callback("loading", i, len(training_texts))

            if isinstance(text_or_path, str | Path):
                text_str = str(text_or_path)

                # Check if it's a HuggingFace dataset (format: hf:org/dataset)
                if text_str.startswith("hf:") and "/" in text_str:
                    dataset_name = text_str[3:]  # Remove 'hf:' prefix
                    if progress_callback:
                        progress_callback("loading", i, len(training_texts))
                    text = load_huggingface_text(
                        dataset_name,
                        tokenizer_name=tokenizer_name,
                        max_samples=max_samples,
                        progress_callback=lambda curr, total: (
                            progress_callback("hf_loading", curr, total)
                            if progress_callback
                            else None
                        ),
                    )
                    combined_text += text + "\n\n"
                else:
                    path = Path(text_or_path)
                    if path.exists() and path.suffix == ".gz":
                        # Load from JSONL.gz file
                        text = load_jsonl_text(path, max_samples=max_samples)
                        combined_text += text + "\n\n"
                    elif path.exists():
                        # Load from text file
                        with open(path, encoding="utf-8") as f:
                            combined_text += f.read() + "\n\n"
                    else:
                        # Treat as text string
                        combined_text += str(text_or_path) + "\n\n"

    # Train the model
    if use_batches and len(combined_text) > batch_size:
        # Use batch training
        batches = list(PunktTrainer.text_to_batches(combined_text, batch_size=batch_size))

        for i, batch in enumerate(batches):
            if progress_callback:
                progress_callback("training", i, len(batches))
            trainer.train(batch, verbose=False, finalize=(i == len(batches) - 1))
    else:
        # Train in one pass
        if progress_callback:
            progress_callback("training", 1, 1)
        trainer.train(combined_text, verbose=verbose)

    # Save the model if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        trainer.get_params().save(
            output_path,
            format_type=format_type,
            compression_level=compression_level,
            compression_method=compression_method,
        )

    return trainer


def get_training_stats(trainer: PunktTrainer) -> dict[str, Any]:
    """
    Get statistics about a trained model.

    Args:
        trainer: The trained PunktTrainer instance

    Returns:
        Dictionary containing training statistics
    """
    params = trainer.get_params()

    return {
        "num_abbreviations": len(params.abbrev_types),
        "num_sentence_starters": len(params.sent_starters),
        "num_collocations": len(params.collocations),
        "num_ortho_contexts": len(params.ortho_context),
        "hyperparameters": {
            "abbrev_threshold": trainer.ABBREV,
            "abbrev_backoff": trainer.ABBREV_BACKOFF,
            "collocation_threshold": trainer.COLLOCATION,
            "sent_starter_threshold": trainer.SENT_STARTER,
            "min_colloc_freq": trainer.MIN_COLLOC_FREQ,
        },
    }
