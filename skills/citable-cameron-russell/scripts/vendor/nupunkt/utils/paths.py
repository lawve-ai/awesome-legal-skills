"""
Cross-platform path utilities for nupunkt.

This module provides functions to get platform-specific directories for
storing user data and cache files, following platform conventions without
external dependencies.
"""

import os
import sys
from pathlib import Path


def get_user_data_dir() -> Path:
    """
    Get the platform-specific user data directory for nupunkt.

    Returns:
        Path: The user data directory path

    Platform behavior:
        - Linux: $XDG_DATA_HOME/nupunkt or ~/.local/share/nupunkt
        - macOS: ~/Library/Application Support/nupunkt
        - Windows: %LOCALAPPDATA%\\nupunkt or %APPDATA%\\nupunkt
    """
    if sys.platform == "win32":
        # Windows
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = str(Path.home())
        return Path(base) / "nupunkt"
    elif sys.platform == "darwin":
        # macOS
        return Path.home() / "Library" / "Application Support" / "nupunkt"
    else:
        # Linux and other Unix-like systems
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / "nupunkt"
        else:
            return Path.home() / ".local" / "share" / "nupunkt"


def get_user_cache_dir() -> Path:
    """
    Get the platform-specific user cache directory for nupunkt.

    Returns:
        Path: The user cache directory path

    Platform behavior:
        - Linux: $XDG_CACHE_HOME/nupunkt or ~/.cache/nupunkt
        - macOS: ~/Library/Caches/nupunkt
        - Windows: %LOCALAPPDATA%\\nupunkt\\Cache or %TEMP%\\nupunkt
    """
    if sys.platform == "win32":
        # Windows
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "nupunkt" / "Cache"
        else:
            temp = os.environ.get("TEMP", str(Path.home()))
            return Path(temp) / "nupunkt"
    elif sys.platform == "darwin":
        # macOS
        return Path.home() / "Library" / "Caches" / "nupunkt"
    else:
        # Linux and other Unix-like systems
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            return Path(xdg_cache_home) / "nupunkt"
        else:
            return Path.home() / ".cache" / "nupunkt"


def get_legacy_user_dir() -> Path:
    """
    Get the legacy user directory (~/.nupunkt) for backward compatibility.

    Returns:
        Path: The legacy user directory path
    """
    return Path.home() / ".nupunkt"


def get_model_search_paths() -> list[Path]:
    """
    Get all directories where models should be searched, in priority order.

    Returns:
        List[Path]: List of paths to search for models, in order of priority

    Search order:
        1. Package models directory (built-in models)
        2. User data directory / models
        3. Legacy ~/.nupunkt/models (for backward compatibility)
        4. Current working directory / models
    """
    paths = []

    # 1. Package models directory
    package_dir = Path(__file__).parent.parent / "models"
    if package_dir.exists():
        paths.append(package_dir)

    # 2. User data directory
    user_data = get_user_data_dir() / "models"
    if user_data.exists():
        paths.append(user_data)

    # 3. Legacy directory for backward compatibility
    legacy_dir = get_legacy_user_dir() / "models"
    if legacy_dir.exists():
        paths.append(legacy_dir)

    # 4. Current working directory
    cwd_models = Path.cwd() / "models"
    if cwd_models.exists() and cwd_models not in paths:
        paths.append(cwd_models)

    return paths


def ensure_user_directories() -> None:
    """
    Create user directories if they don't exist.

    This creates both the data and cache directories with appropriate
    permissions (700 on Unix-like systems).
    """
    for dir_func in (get_user_data_dir, get_user_cache_dir):
        directory = dir_func()
        models_dir = directory / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        # Set appropriate permissions on Unix-like systems
        if sys.platform != "win32":
            try:
                directory.chmod(0o700)
                models_dir.chmod(0o700)
            except (OSError, PermissionError):
                pass  # Ignore permission errors


def migrate_legacy_models() -> None:
    """
    Migrate models from legacy ~/.nupunkt directory to new platform-specific location.

    This function checks if models exist in the legacy location and copies them
    to the new user data directory if they don't already exist there.
    """
    legacy_dir = get_legacy_user_dir() / "models"
    if not legacy_dir.exists():
        return

    new_dir = get_user_data_dir() / "models"
    new_dir.mkdir(parents=True, exist_ok=True)

    # Copy models that don't already exist in the new location
    for model_file in legacy_dir.glob("*"):
        if model_file.is_file():
            new_path = new_dir / model_file.name
            if not new_path.exists():
                try:
                    new_path.write_bytes(model_file.read_bytes())
                except (OSError, PermissionError):
                    pass  # Skip files we can't copy
