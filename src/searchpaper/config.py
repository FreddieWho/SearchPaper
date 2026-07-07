"""User-level configuration for SearchPaper.

Configuration is read from ``~/.config/searchpaper/config.json``.
Environment variables always take precedence over file values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "searchpaper"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "searchpaper"
DEFAULT_CACHE_PATH = DEFAULT_CACHE_DIR / "cache.db"
DEFAULT_PROJECT_DIR = Path(".searchpaper")

ENV_MAPPINGS: dict[str, tuple[str, type]] = {
    "SEARCHPAPER_CACHE": ("cache_path", Path),
    "SEARCHPAPER_CONFIG": ("config_path", Path),
    "SEMANTIC_SCHOLAR_API_KEY": ("semantic_scholar_api_key", str),
    "CROSSREF_EMAIL": ("crossref_email", str),
    "OPENALEX_EMAIL": ("openalex_email", str),
    "NCBI_API_KEY": ("ncbi_api_key", str),
    "EUROPEPMC_API_KEY": ("europepmc_api_key", str),
}


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

    for env_var, (cfg_key, coerce_type) in ENV_MAPPINGS.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            cfg[cfg_key] = _coerce(env_value, coerce_type)

    # Defaults
    cfg.setdefault("cache_path", DEFAULT_CACHE_PATH)
    cfg.setdefault("config_path", DEFAULT_CONFIG_PATH)
    return cfg


def ensure_config_dir() -> Path:
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def get_cache_path(config: dict[str, Any] | None = None) -> Path:
    cfg = config or load_config()
    path = cfg.get("cache_path", DEFAULT_CACHE_PATH)
    return Path(path).expanduser()


def default_user_agent() -> str:
    from searchpaper import __version__

    return f"SearchPaper/{__version__} (https://github.com/freddiewho/paperSearch)"
