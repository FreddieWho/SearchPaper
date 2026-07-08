"""Codex integration for SearchPaper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from searchpaper.integrations.base import safe_write


def config_path() -> Path:
    return Path.home() / ".codex" / "settings.json"


def instructions_path() -> Path:
    return Path.home() / ".codex" / "instructions" / "searchpaper.md"


def instructions_content() -> str:
    from searchpaper.integrations.skill_template import literature_search_skill

    return literature_search_skill()


def mcp_config_snippet() -> str:
    return (
        "{\n"
        '  "mcpServers": {\n'
        '    "searchpaper": {\n'
        '      "command": "searchpaper",\n'
        '      "args": ["serve", "--mcp"]\n'
        "    }\n"
        "  }\n"
        "}\n"
    )


def detect() -> bool:
    return config_path().parent.exists() or instructions_path().parent.exists()


def install(dry_run: bool = False) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    snippet_path = config_path().parent / "searchpaper-mcp.json"
    changes.append(safe_write(snippet_path, mcp_config_snippet(), dry_run=dry_run))
    changes.append(safe_write(instructions_path(), instructions_content(), dry_run=dry_run))
    return {
        "target": "codex",
        "detected": detect(),
        "message": "Codex support scaffolded. Merge searchpaper-mcp.json into your Codex MCP settings manually.",
        "changes": changes,
    }


def uninstall(dry_run: bool = False) -> dict[str, Any]:
    from searchpaper.integrations.base import safe_remove

    changes: list[dict[str, Any]] = []
    snippet_path = config_path().parent / "searchpaper-mcp.json"
    changes.append(safe_remove(snippet_path, dry_run=dry_run))
    changes.append(safe_remove(instructions_path(), dry_run=dry_run))
    return {"target": "codex", "changes": changes}


def doctor() -> dict[str, Any]:
    return {
        "target": "codex",
        "detected": detect(),
        "has_mcp_snippet": (config_path().parent / "searchpaper-mcp.json").exists(),
        "has_instructions": instructions_path().exists(),
        "issues": [],
    }
