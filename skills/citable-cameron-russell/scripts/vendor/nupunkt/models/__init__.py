"""
Model package for nupunkt.

This module provides functionality for loading and optimizing the default pre-trained model.
"""

from pathlib import Path

from nupunkt.tokenizers.sentence_tokenizer import PunktSentenceTokenizer
from nupunkt.utils.compression import (
    compare_formats,
    load_compressed_json,
    save_binary_model,
    save_compressed_json,
)


def get_default_model_path() -> Path:
    """
    Get the path to the default pre-trained model.

    The function searches for models in priority order:
    1. Gzipped JSON (.json.gz)
    2. Compressed JSON (.json.xz)
    3. Binary format (.bin)
    4. Uncompressed JSON (.json)

    Returns:
        Path: The path to the default model file
    """
    base_dir = Path(__file__).parent

    # Check for gzipped JSON first (best balance of size and features)
    gz_path = base_dir / "default_model.json.gz"
    if gz_path.exists():
        return gz_path

    # Check for xz compressed model next
    xz_path = base_dir / "default_model.json.xz"
    if xz_path.exists():
        return xz_path

    # Check for binary model (legacy format)
    binary_path = base_dir / "default_model.bin"
    if binary_path.exists():
        return binary_path

    # Fall back to uncompressed model
    return base_dir / "default_model.json"


def load_default_model() -> PunktSentenceTokenizer:
    """
    Load the default pre-trained model.

    Returns:
        PunktSentenceTokenizer: A tokenizer initialized with the default model
    """
    model_path = get_default_model_path()
    return PunktSentenceTokenizer.load(model_path)


def optimize_default_model(
    output_path: str | Path | None = None,
    format_type: str = "binary",
    compression_method: str = "lzma",
    compression_level: int = 6,
) -> Path:
    """
    Optimize the default model using the specified format and compression.

    Args:
        output_path: Optional path to save the optimized model. If None,
                    saves to the default location based on format_type.
        format_type: Format to use ("binary", "json_xz", or "json")
        compression_method: For binary format, the compression method to use
                           ("none", "zlib", "lzma", "gzip")
        compression_level: Compression level (0-9). Higher means better
                          compression but slower operation.

    Returns:
        Path: The path to the optimized model file
    """
    # Get the current model data (from whatever format it's currently in)
    current_model_path = get_default_model_path()
    data = load_compressed_json(current_model_path)

    # Determine output path and extension based on format
    base_dir = Path(__file__).parent
    if output_path is None:
        if format_type == "binary":
            output_path = base_dir / "default_model.bin"
        elif format_type == "json_xz":
            output_path = base_dir / "default_model.json.xz"
        else:
            output_path = base_dir / "default_model.json"
    else:
        output_path = Path(output_path)

    # Save in the requested format
    if format_type == "binary":
        save_binary_model(
            data, output_path, compression_method=compression_method, level=compression_level
        )
    else:
        save_compressed_json(
            data, output_path, level=compression_level, use_compression=(format_type == "json_xz")
        )

    return output_path


def compare_model_formats(output_dir: str | Path | None = None) -> dict[str, int]:
    """
    Compare different storage formats for the default model and output their file sizes.

    This function creates multiple versions of the default model in different formats
    and compression settings and returns their file sizes.

    Args:
        output_dir: Directory to save test files (if None, uses temp directory)

    Returns:
        Dictionary mapping format names to file sizes in bytes
    """
    # Load the current model data
    current_model_path = get_default_model_path()
    data = load_compressed_json(current_model_path)

    # Compare formats and return results
    return compare_formats(data, output_dir)
