"""
Compression utilities for nupunkt.

This module provides functions for compressing and decompressing data using various methods.
"""

import gzip
import json
import lzma
import struct
import zlib
from pathlib import Path
from typing import Any

# Binary format version identifier (increment when format changes)
BINARY_FORMAT_VERSION = 1

# Format identifiers (used in file headers)
FORMAT_JSON = 1
FORMAT_JSON_XZ = 2
FORMAT_BINARY = 3


def save_compressed_json(
    data: dict[str, Any], file_path: str | Path, level: int = 1, use_compression: bool = True
) -> None:
    """
    Save data as a compressed JSON file using LZMA.

    Args:
        data: The data to save
        file_path: The path to save the file to
        level: Compression level (0-9), lower is faster but less compressed
        use_compression: Whether to use compression (if False, saves as regular JSON)
    """
    # Convert Path to string if needed
    if isinstance(file_path, Path):
        file_path = str(file_path)

    # Ensure the file path has the correct extension
    if use_compression and not file_path.endswith(".json.xz"):
        file_path = file_path + ".xz" if file_path.endswith(".json") else file_path + ".json.xz"
    elif not use_compression and not file_path.endswith(".json"):
        file_path = file_path + ".json"

    # Serialize the data
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    if use_compression:
        # Use LZMA compression
        filters = [{"id": lzma.FILTER_LZMA2, "preset": level}]
        with lzma.open(
            file_path, "wt", encoding="utf-8", format=lzma.FORMAT_XZ, filters=filters
        ) as f:
            f.write(json_str)
    else:
        # Save as regular JSON
        with Path(file_path).open("w", encoding="utf-8") as f:
            f.write(json_str)


def load_compressed_json(file_path: str | Path, encoding: str = "utf-8") -> dict[str, Any]:
    """
    Load data from a JSON file, which may be compressed with gzip or LZMA.

    Args:
        file_path: The path to the file
        encoding: The text encoding to use

    Returns:
        The loaded data
    """
    # If the file has a .bin extension, try loading as binary format
    if str(file_path).endswith(".bin"):
        try:
            return load_binary_model(file_path)
        except Exception as e:
            raise ValueError(f"Failed to load binary model: {e}") from e

    # Convert Path to string if needed
    if isinstance(file_path, Path):
        file_path = str(file_path)

    # Handle gzip compressed files
    if file_path.endswith(".gz"):
        with gzip.open(file_path, "rt", encoding=encoding) as f:
            return json.load(f)

    # Handle xz compressed files
    elif file_path.endswith(".xz"):
        with lzma.open(file_path, "rt", encoding=encoding) as f:
            return json.load(f)

    # Handle uncompressed JSON
    else:
        with open(file_path, encoding=encoding) as f:
            return json.load(f)


def save_binary_model(
    data: dict[str, Any],
    file_path: str | Path,
    compression_method: str = "zlib",
    level: int = 6,
) -> None:
    """
    Save data in an optimized binary format with various compression options.

    Binary format structure (v2):
    - 4 bytes: Magic bytes "NPKT"
    - 1 byte: Format version (2)
    - 1 byte: Compression method (0=none, 1=zlib, 2=lzma, 3=gzip)
    - 4 bytes: Metadata size (compressed)
    - [metadata as compressed JSON]
    - 4 bytes: Parameters data size (uncompressed)
    - 4 bytes: Number of abbreviations
    - [abbreviations data]
    - 4 bytes: Number of collocations
    - [collocations data]
    - 4 bytes: Number of sentence starters
    - [sentence starters data]
    - 4 bytes: Number of orthographic context entries
    - [orthographic context data]

    Args:
        data: The data dictionary to save (Punkt parameters)
        file_path: The path to save the file to
        compression_method: Compression method ('none', 'zlib', 'lzma', 'gzip')
        level: Compression level (0-9), higher means better compression but slower
    """
    # Ensure the file has the right extension
    if isinstance(file_path, Path):
        file_path = str(file_path)

    if not file_path.endswith(".bin"):
        file_path = file_path + ".bin"

    # Extract data from the dictionary - handle both direct format and trainer format
    params = data.get("parameters", data)

    abbrev_types = sorted(params.get("abbrev_types", []))
    collocations = sorted([[c[0], c[1]] for c in params.get("collocations", [])])
    sent_starters = sorted(params.get("sent_starters", []))
    ortho_context = dict(params.get("ortho_context", {}).items())

    # Prepare binary data
    binary_data = bytearray()

    # Abbreviations section
    binary_data.extend(struct.pack("<I", len(abbrev_types)))
    for abbr in abbrev_types:
        encoded_abbr = abbr.encode("utf-8")
        binary_data.extend(struct.pack("<H", len(encoded_abbr)))
        binary_data.extend(encoded_abbr)

    # Collocations section
    binary_data.extend(struct.pack("<I", len(collocations)))
    for w1, w2 in collocations:
        encoded_w1 = w1.encode("utf-8")
        encoded_w2 = w2.encode("utf-8")
        binary_data.extend(struct.pack("<HH", len(encoded_w1), len(encoded_w2)))
        binary_data.extend(encoded_w1)
        binary_data.extend(encoded_w2)

    # Sentence starters section
    binary_data.extend(struct.pack("<I", len(sent_starters)))
    for starter in sent_starters:
        encoded_starter = starter.encode("utf-8")
        binary_data.extend(struct.pack("<H", len(encoded_starter)))
        binary_data.extend(encoded_starter)

    # Orthographic context section
    binary_data.extend(struct.pack("<I", len(ortho_context)))
    for key, value in sorted(ortho_context.items()):
        encoded_key = key.encode("utf-8")
        binary_data.extend(struct.pack("<HI", len(encoded_key), value))
        binary_data.extend(encoded_key)

    # Apply compression if requested
    uncompressed_size = len(binary_data)
    compression_code = 0

    if compression_method == "zlib":
        binary_data_bytes = zlib.compress(binary_data, level=level)
        compression_code = 1
        binary_data = bytearray(binary_data_bytes)
    elif compression_method == "lzma":
        binary_data_bytes = lzma.compress(binary_data, preset=level)
        compression_code = 2
        binary_data = bytearray(binary_data_bytes)
    elif compression_method == "gzip":
        binary_data_bytes = gzip.compress(binary_data, compresslevel=level)
        compression_code = 3
        binary_data = bytearray(binary_data_bytes)

    # Create file header
    header = bytearray()
    header.extend(b"NPKT")  # Magic bytes
    header.extend(struct.pack("<BB", BINARY_FORMAT_VERSION, compression_code))
    header.extend(struct.pack("<I", uncompressed_size))

    # Write to file
    with Path(file_path).open("wb") as f:
        f.write(header)
        f.write(binary_data)


def load_binary_model(file_path: str | Path) -> dict[str, Any]:
    """
    Load data from a binary format model file.

    Args:
        file_path: The path to the file

    Returns:
        The loaded data as a dictionary
    """
    with Path(file_path).open("rb") as f:
        # Read and validate header
        magic = f.read(4)
        if magic != b"NPKT":
            raise ValueError("Invalid file format: not a nupunkt binary model")

        # Read version and compression method
        version, compression_code = struct.unpack("<BB", f.read(2))
        if version != BINARY_FORMAT_VERSION:
            raise ValueError(f"Unsupported model version: {version}")

        # Read original size
        uncompressed_size = struct.unpack("<I", f.read(4))[0]

        # Read compressed data
        compressed_data = f.read()

        # Decompress data
        if compression_code == 0:
            # No compression
            binary_data = compressed_data
        elif compression_code == 1:
            # zlib
            binary_data = zlib.decompress(compressed_data)
        elif compression_code == 2:
            # lzma
            binary_data = lzma.decompress(compressed_data)
        elif compression_code == 3:
            # gzip
            binary_data = gzip.decompress(compressed_data)
        else:
            raise ValueError(f"Unknown compression method: {compression_code}")

        # Verify decompressed size
        if len(binary_data) != uncompressed_size:
            raise ValueError(
                f"Decompression error: expected {uncompressed_size} bytes, got {len(binary_data)}"
            )

        # Parse binary data
        result: dict[str, Any] = {
            "abbrev_types": [],
            "collocations": [],
            "sent_starters": [],
            "ortho_context": {},
        }
        offset = 0

        # Read abbreviations
        num_abbrevs = struct.unpack_from("<I", binary_data, offset)[0]
        offset += 4

        for _ in range(num_abbrevs):
            abbr_len = struct.unpack_from("<H", binary_data, offset)[0]
            offset += 2
            abbr = binary_data[offset : offset + abbr_len].decode("utf-8")
            offset += abbr_len
            result["abbrev_types"].append(abbr)

        # Read collocations
        num_collocs = struct.unpack_from("<I", binary_data, offset)[0]
        offset += 4

        for _ in range(num_collocs):
            w1_len, w2_len = struct.unpack_from("<HH", binary_data, offset)
            offset += 4
            w1 = binary_data[offset : offset + w1_len].decode("utf-8")
            offset += w1_len
            w2 = binary_data[offset : offset + w2_len].decode("utf-8")
            offset += w2_len
            result["collocations"].append([w1, w2])

        # Read sentence starters
        num_starters = struct.unpack_from("<I", binary_data, offset)[0]
        offset += 4

        for _ in range(num_starters):
            starter_len = struct.unpack_from("<H", binary_data, offset)[0]
            offset += 2
            starter = binary_data[offset : offset + starter_len].decode("utf-8")
            offset += starter_len
            result["sent_starters"].append(starter)

        # Read orthographic context
        num_ortho = struct.unpack_from("<I", binary_data, offset)[0]
        offset += 4

        for _ in range(num_ortho):
            key_len, value = struct.unpack_from("<HI", binary_data, offset)
            offset += 6
            key = binary_data[offset : offset + key_len].decode("utf-8")
            offset += key_len
            result["ortho_context"][key] = value

        # Return in format compatible with PunktTrainer.from_json
        return {
            "parameters": result,
            "version": "0.2.0",
            "description": "nupunkt sentence tokenizer model",
        }


def compare_formats(data: dict[str, Any], output_dir: str | Path | None = None) -> dict[str, Any]:
    """
    Compare different storage formats for the same model data.

    Args:
        data: The model data to test
        output_dir: Directory to save test files (if None, uses temp files)

    Returns:
        Dictionary with format names and their file sizes
    """
    import tempfile
    from pathlib import Path

    if output_dir is None:
        temp_dir = tempfile.mkdtemp()
        output_dir = Path(temp_dir)
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Test JSON format
    json_path = output_dir / "model_test.json"
    save_compressed_json(data, json_path, use_compression=False)
    results["json"] = json_path.stat().st_size

    # Test JSON+XZ format with different compression levels
    for level in [1, 3, 6, 9]:
        xz_path = output_dir / f"model_test_level{level}.json.xz"
        save_compressed_json(data, xz_path, level=level, use_compression=True)
        results[f"json_xz_level{level}"] = xz_path.stat().st_size

    # Test binary format with different compression methods
    for method in ["none", "zlib", "lzma", "gzip"]:
        for level in [1, 6, 9]:
            bin_path = output_dir / f"model_test_{method}_level{level}.bin"
            save_binary_model(data, bin_path, compression_method=method, level=level)
            results[f"binary_{method}_level{level}"] = bin_path.stat().st_size

    return results
