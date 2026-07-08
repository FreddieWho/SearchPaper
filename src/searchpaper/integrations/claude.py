"""Claude integration for SearchPaper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from searchpaper.integrations.base import safe_write


def config_path() -> Path:
    return Path.home() / ".claude" / "CLAUDE.md"


def mcp_config_path() -> Path:
    return Path.home() / ".claude" / "mcp.json"


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
    return config_path().parent.exists() or mcp_config_path().parent.exists()


def install(dry_run: bool = False) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    changes.append(safe_write(config_path(), instructions_content(), dry_run=dry_run))
    changes.append(safe_write(mcp_config_path(), mcp_config_snippet(), dry_run=dry_run))
    return {
        "target": "claude",
        "detected": detect(),
        "message": "Claude support scaffolded. Review ~/.claude/mcp.json and enable the searchpaper server.",
        "changes": changes,
    }


def uninstall(dry_run: bool = False) -> dict[str, Any]:
    from searchpaper.integrations.base import safe_remove

    changes: list[dict[str, Any]] = []
    changes.append(safe_remove(config_path(), dry_run=dry_run))
    changes.append(safe_remove(mcp_config_path(), dry_run=dry_run))
    return {"target": "claude", "changes": changes}


def doctor() -> dict[str, Any]:
    return {
        "target": "claude",
        "detected": detect(),
        "has_instructions": config_path().exists(),
        "has_mcp_config": mcp_config_path().exists(),
        "issues": [],
    }
