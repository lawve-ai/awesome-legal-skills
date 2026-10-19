"""
Dataset handling for evaluation.

This module provides functionality to load and parse evaluation datasets
with various annotation formats.
"""

import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass
class TestCase:
    """Single test case for evaluation."""

    text: str
    sentences: list[str]
    metadata: dict[str, Any] | None = None


def parse_annotated_text(text: str, delimiter: str = "<|sentence|>") -> list[str]:
    """
    Parse text with sentence boundary annotations.

    Args:
        text: Text with sentence delimiters
        delimiter: Delimiter marking sentence boundaries

    Returns:
        List of sentences
    """
    # Handle paragraph markers first
    text = text.replace("<|paragraph|>", "\n\n")

    # Split by delimiter and clean up
    parts = text.split(delimiter)
    sentences = []

    for part in parts:
        # Normalize whitespace within each sentence
        part = " ".join(part.split())
        if part:
            sentences.append(part)

    return sentences


def load_jsonl_evaluation_data(
    file_path: str | Path,
    max_samples: int | None = None,
    delimiter: str = "<|sentence|>",
    show_progress: bool = False,
) -> Iterator[TestCase]:
    """
    Load evaluation data from JSONL file.

    Args:
        file_path: Path to JSONL file (can be gzipped)
        max_samples: Maximum number of samples to load
        delimiter: Sentence boundary delimiter
        show_progress: Whether to show progress bar (requires tqdm)

    Yields:
        TestCase objects
    """
    file_path = Path(file_path)

    # Determine if file is compressed
    if file_path.suffix == ".gz":
        opener = gzip.open
        mode = "rt"
    else:
        opener = open
        mode = "r"

    with opener(file_path, mode, encoding="utf-8") as f:
        # Wrap file iterator with tqdm if requested and available
        if show_progress:
            try:
                from tqdm import tqdm

                # For large files, we don't pre-count lines
                line_iter = tqdm(f, desc=f"Loading {file_path.name}", unit="lines")
            except ImportError:
                line_iter = f
        else:
            line_iter = f

        for i, line in enumerate(line_iter):
            if max_samples and i >= max_samples:
                break

            line = line.strip()
            if not line:  # Skip empty lines
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                # Log warning and skip malformed lines
                import warnings

                warnings.warn(f"Skipping malformed JSON at line {i + 1}: {e}", stacklevel=2)
                continue

            # Extract text and sentences
            if "text" in data:
                text = data["text"]
                sentences = parse_annotated_text(text, delimiter)

                # Create clean text: remove delimiters and handle paragraph markers
                # Replace delimiter with single space to avoid double spaces
                clean_text = text.replace(f" {delimiter} ", " ")
                # Handle edge cases where delimiter might be at start/end
                clean_text = clean_text.replace(delimiter, "")
                clean_text = clean_text.replace("<|paragraph|>", "\n\n")

                # Extract metadata if present
                metadata = {k: v for k, v in data.items() if k != "text"}

                yield TestCase(
                    text=clean_text, sentences=sentences, metadata=metadata if metadata else None
                )


def load_evaluation_data(
    file_path: str | Path,
    format: str = "auto",
    max_samples: int | None = None,
    show_progress: bool = False,
) -> list[TestCase]:
    """
    Load evaluation data from various formats.

    Args:
        file_path: Path to evaluation data
        format: File format ("auto", "jsonl", "txt")
        max_samples: Maximum samples to load
        show_progress: Whether to show progress bar (requires tqdm)

    Returns:
        List of test cases
    """
    file_path = Path(file_path)

    # Auto-detect format
    if format == "auto":
        format = "jsonl" if file_path.suffix in (".jsonl", ".gz") else "txt"

    test_cases = []

    if format == "jsonl":
        for test_case in load_jsonl_evaluation_data(
            file_path, max_samples, show_progress=show_progress
        ):
            test_cases.append(test_case)
    elif format == "txt":
        # Simple text format: one document per line, sentences separated by delimiter
        with open(file_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if max_samples and i >= max_samples:
                    break

                line = line.strip()
                if line:
                    sentences = parse_annotated_text(line)
                    clean_text = line.replace("<|sentence|>", "")
                    test_cases.append(TestCase(text=clean_text, sentences=sentences))
    else:
        raise ValueError(f"Unknown format: {format}")

    return test_cases


def create_test_cases(
    texts: list[str], sentence_lists: list[list[str]], metadata: list[dict[str, Any]] | None = None
) -> list[TestCase]:
    """
    Create test cases from separate lists.

    Args:
        texts: List of text documents
        sentence_lists: List of sentence lists (one per document)
        metadata: Optional metadata for each document

    Returns:
        List of test cases
    """
    if len(texts) != len(sentence_lists):
        raise ValueError("Number of texts must match number of sentence lists")

    test_cases = []
    for i, (text, sentences) in enumerate(zip(texts, sentence_lists)):
        meta = metadata[i] if metadata and i < len(metadata) else None
        test_cases.append(TestCase(text=text, sentences=sentences, metadata=meta))

    return test_cases


def save_evaluation_dataset(
    test_cases: list[TestCase], output_path: str | Path, delimiter: str = "<|sentence|>"
) -> None:
    """
    Save evaluation dataset in JSONL format.

    Args:
        test_cases: List of test cases
        output_path: Output file path
        delimiter: Sentence boundary delimiter
    """
    output_path = Path(output_path)

    # Determine if we should compress
    if output_path.suffix == ".gz":
        opener = gzip.open
        mode = "wt"
    else:
        opener = open
        mode = "w"

    with opener(output_path, mode, encoding="utf-8") as f:
        for test_case in test_cases:
            # Reconstruct text with delimiters
            annotated_text = f" {delimiter} ".join(test_case.sentences)

            data = {"text": annotated_text}
            if test_case.metadata:
                data.update(test_case.metadata)

            f.write(json.dumps(data) + "\n")
