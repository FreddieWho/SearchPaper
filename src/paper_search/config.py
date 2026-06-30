"""Load user-level configuration for paperSearch.

Configuration is read from ``~/.config/paperSearch/config.json``.
Environment variables always take precedence over file values.
"""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "paperSearch"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"


def _coerce(value: Any, target_type: type) -> Any:
    if value is None:
        return None
    if target_type is Path and isinstance(value, (str, os.PathLike)):
        return Path(value).expanduser()
    if target_type is str and not isinstance(value, str):
        return str(value)
    return value


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load configuration from file, then overlay environment variables."""
    cfg: dict[str, Any] = {}
    config_path = path or DEFAULT_CONFIG_PATH

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            cfg = {}

    env_mappings = {
        "SEMANTIC_SCHOLAR_API_KEY": ("semantic_scholar_api_key", str),
        "PAPER_SEARCH_CACHE": ("cache_path", Path),
    }

    for env_var, (cfg_key, coerce_type) in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            cfg[cfg_key] = _coerce(env_value, coerce_type)

    return cfg


def ensure_config_dir() -> Path:
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR
