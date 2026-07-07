"""OpenCode integration for SearchPaper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from searchpaper.integrations.base import (
    MARKER_END,
    MARKER_START,
    ensure_managed_block,
    remove_managed_block,
    safe_remove,
    safe_write,
)


def config_path() -> Path:
    return Path.home() / ".config" / "opencode" / "opencode.jsonc"


def skills_dir() -> Path:
    return Path.home() / ".config" / "opencode" / "skills"


def skill_path() -> Path:
    return skills_dir() / "literature-search" / "SKILL.md"


def skill_content() -> str:
    from searchpaper.integrations.skill_template import literature_search_skill

    return literature_search_skill()


def mcp_config_block() -> str:
    return (
        f"{MARKER_START}\n"
        "  // SearchPaper MCP server (managed by searchpaper install --target opencode)\n"
        "  \"mcpServers\": {\n"
        "    \"searchpaper\": {\n"
        "      \"command\": \"searchpaper\",\n"
        "      \"args\": [\"serve\", \"--mcp\"]\n"
        "    }\n"
        "  }\n"
        f"{MARKER_END}"
    )


def detect() -> bool:
    return config_path().exists() or skills_dir().exists()


def install(dry_run: bool = False) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    cfg = config_path()
    if cfg.exists():
        content = cfg.read_text(encoding="utf-8")
    else:
        content = "{\n}\n"
    new_content = ensure_managed_block(content, mcp_config_block())
    changes.append(safe_write(cfg, new_content, dry_run=dry_run))

    skill = skill_path()
    changes.append(safe_write(skill, skill_content(), dry_run=dry_run))
    return {"target": "opencode", "detected": detect(), "changes": changes}


def uninstall(dry_run: bool = False) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    cfg = config_path()
    if cfg.exists():
        content = cfg.read_text(encoding="utf-8")
        new_content = remove_managed_block(content)
        changes.append(safe_write(cfg, new_content, dry_run=dry_run))
    skill = skill_path()
    if skill.exists():
        changes.append(safe_remove(skill, dry_run=dry_run))
        if dry_run:
            pass
        else:
            parent = skill.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
    return {"target": "opencode", "changes": changes}


def doctor() -> dict[str, Any]:
    issues: list[str] = []
    if not detect():
        issues.append("OpenCode config directory not found.")
    cfg = config_path()
    has_block = cfg.exists() and MARKER_START in cfg.read_text(encoding="utf-8")
    skill = skill_path()
    return {
        "target": "opencode",
        "detected": detect(),
        "has_managed_block": has_block,
        "has_skill": skill.exists(),
        "issues": issues,
    }
