"""Base agent integration utilities."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MARKER_START = "<!-- searchpaper:start -->"
MARKER_END = "<!-- searchpaper:end -->"


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def backup_path(path: Path) -> Path:
    suffix = now_iso().replace(":", "-")
    return Path(f"{path}.{suffix}.backup")


def ensure_managed_block(content: str, block: str) -> str:
    """Insert or replace a marker-delimited managed block in text content."""
    start = content.find(MARKER_START)
    end = content.find(MARKER_END)
    if start != -1 and end != -1:
        return content[:start] + block + content[end + len(MARKER_END) :]
    if content and not content.endswith("\n"):
        content += "\n"
    return content + block + "\n"


def remove_managed_block(content: str) -> str:
    """Remove a marker-delimited managed block from text content."""
    start = content.find(MARKER_START)
    end = content.find(MARKER_END)
    if start == -1 or end == -1:
        return content
    return content[:start] + content[end + len(MARKER_END) :]


def safe_write(path: Path, content: str, dry_run: bool = False) -> dict[str, Any]:
    """Write content to path, backing up existing files."""
    action = "would write" if dry_run else "wrote"
    backup: str | None = None
    if path.exists() and path.stat().st_size > 0:
        backup = str(backup_path(path))
        if not dry_run:
            shutil.copy2(path, backup)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {"path": str(path), "action": action, "backup": backup}


def safe_remove(path: Path, dry_run: bool = False) -> dict[str, Any]:
    action = "would remove" if dry_run else "removed"
    existed = path.exists()
    if not dry_run and existed:
        path.unlink()
    return {"path": str(path), "action": action, "existed": existed}
