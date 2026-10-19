"""
Model optimization and conversion functionality for nupunkt.

This module provides functions for optimizing model storage and
converting between different model formats.
"""

import time
from pathlib import Path
from typing import Any

from nupunkt.utils.compression import (
    load_binary_model,
    load_compressed_json,
    save_binary_model,
    save_compressed_json,
)


def optimize_model(
    input_path: str | Path | None = None,
    output_path: str | Path | None = None,
    format_type: str = "binary",
    compression_method: str = "zlib",
    compression_level: int = 6,
) -> Path:
    """
    Optimize a model's storage format.

    Args:
        input_path: Path to the input model (None to use default model)
        output_path: Path to save the optimized model (None for automatic)
        format_type: Output format type ("binary", "json", "json_xz")
        compression_method: Compression method for binary format
        compression_level: Compression level (0-9)

    Returns:
        Path to the optimized model file
    """
    # Get input path
    if input_path is None:
        from nupunkt.models import get_default_model_path

        input_path = get_default_model_path()
    else:
        input_path = Path(input_path)

    # Load the model data
    if str(input_path).endswith(".bin"):
        data = load_binary_model(input_path)
    else:
        data = load_compressed_json(input_path)

    # Determine output path
    if output_path is None:
        # Use the same directory as input with appropriate extension
        base_name = input_path.stem.split(".")[0]  # Remove all extensions
        if format_type == "binary":
            output_path = input_path.parent / f"{base_name}.bin"
        elif format_type == "json_xz":
            output_path = input_path.parent / f"{base_name}.json.xz"
        else:
            output_path = input_path.parent / f"{base_name}.json"
    else:
        output_path = Path(output_path)

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save in the specified format
    if format_type == "binary":
        save_binary_model(
            data, output_path, compression_method=compression_method, level=compression_level
        )
    else:
        save_compressed_json(
            data, output_path, level=compression_level, use_compression=(format_type == "json_xz")
        )

    return output_path


def convert_model_format(
    input_path: str | Path,
    output_path: str | Path,
    format_type: str = "binary",
    compression_method: str = "zlib",
    compression_level: int = 6,
) -> dict[str, Any]:
    """
    Convert a model from one format to another.

    Args:
        input_path: Path to the input model file
        output_path: Path to save the converted model
        format_type: Output format type ("binary", "json", "json_xz")
        compression_method: Compression method for binary format
        compression_level: Compression level (0-9)

    Returns:
        Dictionary containing conversion statistics
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Track timing
    start_time = time.time()

    # Load the model data
    if str(input_path).endswith(".bin"):
        data = load_binary_model(input_path)
    else:
        data = load_compressed_json(input_path)

    load_time = time.time() - start_time

    # Get input file size
    input_size = input_path.stat().st_size

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert the model
    start_time = time.time()

    if format_type == "binary":
        save_binary_model(
            data, output_path, compression_method=compression_method, level=compression_level
        )
    else:
        save_compressed_json(
            data, output_path, level=compression_level, use_compression=(format_type == "json_xz")
        )

    convert_time = time.time() - start_time

    # Get output file size
    output_size = output_path.stat().st_size

    # Verify the model can be loaded
    start_time = time.time()

    if format_type == "binary":
        _ = load_binary_model(output_path)
    else:
        _ = load_compressed_json(output_path)

    verify_time = time.time() - start_time

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_size": input_size,
        "output_size": output_size,
        "compression_ratio": output_size / input_size,
        "load_time": load_time,
        "convert_time": convert_time,
        "verify_time": verify_time,
        "format_type": format_type,
        "compression_method": compression_method if format_type == "binary" else None,
        "compression_level": compression_level,
    }


def get_model_info(model_path: str | Path) -> dict[str, Any]:
    """
    Get information about a model file.

    Args:
        model_path: Path to the model file

    Returns:
        Dictionary containing model information
    """
    model_path = Path(model_path)

    # Get file info
    file_size = model_path.stat().st_size

    # Load the model to get internal info
    start_time = time.time()

    if str(model_path).endswith(".bin"):
        data = load_binary_model(model_path)
        format_type = "binary"
    else:
        data = load_compressed_json(model_path)
        format_type = "json_xz" if str(model_path).endswith(".xz") else "json"

    load_time = time.time() - start_time

    # Extract model statistics
    params = data.get("parameters", {})

    return {
        "file_path": str(model_path),
        "file_size": file_size,
        "file_size_kb": file_size / 1024,
        "file_size_mb": file_size / (1024 * 1024),
        "format_type": format_type,
        "load_time": load_time,
        "num_abbreviations": len(params.get("abbrev_types", [])),
        "num_sentence_starters": len(params.get("sent_starters", [])),
        "num_collocations": len(params.get("collocations", [])),
        "num_ortho_contexts": len(params.get("ortho_context", {})),
    }
