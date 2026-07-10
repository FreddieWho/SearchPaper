"""Codex integration for SearchPaper.

By default this integration writes standalone managed files and does not
overwrite the user's main ``~/.codex/settings.json``.
Use ``inject_config_snippet(dry_run=False)`` to add a marker-delimited block to
that file when the user explicitly asks for direct integration.
"""

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
    return Path.home() / ".codex" / "settings.json"


def instructions_path() -> Path:
    return Path.home() / ".codex" / "instructions" / "searchpaper.md"


def mcp_snippet_path() -> Path:
    return Path.home() / ".codex" / "searchpaper-mcp.json"


def instructions_content() -> str:
    from searchpaper.integrations.skill_template import literature_search_instructions

    return literature_search_instructions()


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


def mcp_config_block() -> str:
    """Marker-delimited block for injection into ~/.codex/settings.json."""
    return (
        f"{MARKER_START}\n"
        "  // SearchPaper MCP server (managed by searchpaper install --target codex)\n"
        '  "mcpServers": {\n'
        '    "searchpaper": {\n'
        '      "command": "searchpaper",\n'
        '      "args": ["serve", "--mcp"]\n'
        "    }\n"
        "  }\n"
        f"{MARKER_END}"
    )


def detect() -> bool:
    return config_path().parent.exists() or instructions_path().parent.exists()


def install(dry_run: bool = False) -> dict[str, Any]:
    """Default install writes standalone snippet files only."""
    changes: list[dict[str, Any]] = []
    changes.append(safe_write(mcp_snippet_path(), mcp_config_snippet(), dry_run=dry_run))
    changes.append(safe_write(instructions_path(), instructions_content(), dry_run=dry_run))
    return {
        "target": "codex",
        "detected": detect(),
        "message": (
            "Codex support scaffolded. Merge ~/.codex/searchpaper-mcp.json into "
            "your Codex MCP settings manually, or use inject_config_snippet()."
        ),
        "changes": changes,
    }


def inject_config_snippet(dry_run: bool = True) -> dict[str, Any]:
    """Inject a marker-delimited SearchPaper block into ~/.codex/settings.json."""
    changes: list[dict[str, Any]] = []
    cfg = config_path()
    if cfg.exists():
        content = cfg.read_text(encoding="utf-8")
    else:
        content = "{\n}\n"
    new_content = ensure_managed_block(content, mcp_config_block())
    changes.append(safe_write(cfg, new_content, dry_run=dry_run))
    return {
        "target": "codex",
        "dry_run": dry_run,
        "message": "Injected SearchPaper block into ~/.codex/settings.json. Run with dry_run=False to apply.",
        "changes": changes,
    }


def uninstall(dry_run: bool = False) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    changes.append(safe_remove(mcp_snippet_path(), dry_run=dry_run))
    changes.append(safe_remove(instructions_path(), dry_run=dry_run))

    cfg = config_path()
    if cfg.exists():
        content = cfg.read_text(encoding="utf-8")
        new_content = remove_managed_block(content)
        changes.append(safe_write(cfg, new_content, dry_run=dry_run))

    return {"target": "codex", "changes": changes}


def doctor() -> dict[str, Any]:
    cfg = config_path()
    has_managed_block = cfg.exists() and MARKER_START in cfg.read_text(encoding="utf-8")
    issues: list[str] = []
    if not detect():
        issues.append("Codex config directory not found.")
    if not has_managed_block and not mcp_snippet_path().exists():
        issues.append("No SearchPaper MCP config found. Run install or inject_config_snippet().")
    if not instructions_path().exists():
        issues.append("No SearchPaper instructions found. Run install.")

    return {
        "target": "codex",
        "detected": detect(),
        "has_managed_block": has_managed_block,
        "has_mcp_snippet": mcp_snippet_path().exists(),
        "has_instructions": instructions_path().exists(),
        "issues": issues,
        "manual_merge_instructions": [
            "1. Open ~/.codex/searchpaper-mcp.json and copy the mcpServers block.",
            "2. Paste it into your Codex MCP settings.",
            "3. Review ~/.codex/instructions/searchpaper.md for agent behavior rules.",
        ],
    }
