"""Model management utilities for nupunkt CLI."""

import sys
from pathlib import Path
from typing import Any

from nupunkt.utils.compression import load_compressed_json
from nupunkt.utils.paths import (
    ensure_user_directories,
    get_model_search_paths,
    get_user_data_dir,
    migrate_legacy_models,
)


def list_models() -> list[tuple[str, Path, dict[str, Any]]]:
    """
    List all available models.

    Returns:
        List of tuples containing (model_name, path, metadata)
    """
    models = []
    seen_names = set()

    for search_dir in get_model_search_paths():
        if not search_dir.exists():
            continue

        for model_file in search_dir.glob("*.bin"):
            name = model_file.stem
            if name not in seen_names:
                seen_names.add(name)
                metadata = _get_model_metadata(model_file)
                models.append((name, model_file, metadata))

        for model_file in search_dir.glob("*.json.xz"):
            name = model_file.stem.replace(".json", "")
            if name not in seen_names:
                seen_names.add(name)
                metadata = _get_model_metadata(model_file)
                models.append((name, model_file, metadata))

        for model_file in search_dir.glob("*.json"):
            if model_file.name.endswith(".json.xz"):
                continue
            name = model_file.stem
            if name not in seen_names:
                seen_names.add(name)
                metadata = _get_model_metadata(model_file)
                models.append((name, model_file, metadata))

    return sorted(models, key=lambda x: x[0])


def _get_model_metadata(model_path: Path) -> dict[str, Any]:
    """Extract metadata from a model file."""
    try:
        data = load_compressed_json(model_path)
        return {
            "version": data.get("version", "unknown"),
            "nupunkt_version": data.get("nupunkt_version", "unknown"),
            "size": model_path.stat().st_size,
            "abbrev_count": len(data.get("parameters", {}).get("abbrev_types", {})),
            "colloc_count": len(data.get("parameters", {}).get("collocations", {})),
        }
    except Exception:
        return {
            "version": "error",
            "nupunkt_version": "error",
            "size": model_path.stat().st_size,
            "abbrev_count": 0,
            "colloc_count": 0,
        }


def show_model_info(model_name: str) -> None:
    """Show detailed information about a model."""
    from nupunkt import load

    try:
        tokenizer = load(model_name)
        params = tokenizer._params

        print(f"Model: {model_name}")
        print(f"Abbreviations: {len(params.abbrev_types)}")
        print(f"Collocations: {len(params.collocations)}")
        print(f"Sentence starters: {len(params.sent_starters)}")
        print(f"Orthographic contexts: {len(params.ortho_context)}")

        # Show sample abbreviations
        if params.abbrev_types:
            abbrevs = sorted(params.abbrev_types)[:10]
            print(f"\nSample abbreviations: {', '.join(abbrevs)}")
            if len(params.abbrev_types) > 10:
                print(f"  ... and {len(params.abbrev_types) - 10} more")

    except FileNotFoundError:
        print(f"Model '{model_name}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        sys.exit(1)


def install_model(model_path: Path, name: str | None = None) -> None:
    """
    Install a model to the user models directory.

    Args:
        model_path: Path to the model file to install
        name: Optional name for the installed model (defaults to source filename)
    """
    if not model_path.exists():
        print(f"Model file not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure user directories exist
    ensure_user_directories()

    # Determine target path
    user_models = get_user_data_dir() / "models"
    if name:
        # Preserve extension from source
        ext = "".join(model_path.suffixes)
        target_name = name + ext
    else:
        target_name = model_path.name

    target_path = user_models / target_name

    # Check if already exists
    if target_path.exists():
        print(f"Model already exists: {target_path}", file=sys.stderr)
        print("Use a different name or remove the existing model first")
        sys.exit(1)

    # Copy the model
    print(f"Installing model to: {target_path}")
    target_path.write_bytes(model_path.read_bytes())
    print("Model installed successfully")


def main():
    """CLI entry point for model management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="nupunkt model management utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  nupunkt-models list              List all available models
  nupunkt-models info default      Show info about the default model
  nupunkt-models paths             Show model search paths
  nupunkt-models install model.bin Install a model file
  nupunkt-models migrate           Migrate models from legacy location
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List models command
    list_parser = subparsers.add_parser("list", help="List available models")
    list_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )

    # Model info command
    info_parser = subparsers.add_parser("info", help="Show model information")
    info_parser.add_argument("model", help="Model name or path")

    # Show paths command
    subparsers.add_parser("paths", help="Show model search paths")

    # Install model command
    install_parser = subparsers.add_parser("install", help="Install a model")
    install_parser.add_argument("model_file", type=Path, help="Model file to install")
    install_parser.add_argument("-n", "--name", help="Name for the installed model")

    # Migrate command
    subparsers.add_parser("migrate", help="Migrate models from legacy location")

    args = parser.parse_args()

    if args.command == "list":
        models = list_models()
        if not models:
            print("No models found")
        else:
            for name, path, metadata in models:
                if args.verbose:
                    size_mb = metadata["size"] / (1024 * 1024)
                    print(
                        f"{name:20} {str(path):50} "
                        f"{size_mb:6.1f}MB  "
                        f"abbrevs:{metadata['abbrev_count']:5}  "
                        f"nupunkt:{metadata['nupunkt_version']}"
                    )
                else:
                    print(f"{name:20} {path.parent}")

    elif args.command == "info":
        show_model_info(args.model)

    elif args.command == "paths":
        print("Model search paths (in order of priority):")
        for i, path in enumerate(get_model_search_paths(), 1):
            exists = "✓" if path.exists() else "✗"
            print(f"{i}. [{exists}] {path}")
        print(f"\nUser models directory: {get_user_data_dir() / 'models'}")

    elif args.command == "install":
        install_model(args.model_file, args.name)

    elif args.command == "migrate":
        print("Migrating models from legacy location...")
        migrate_legacy_models()
        print("Migration complete")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
