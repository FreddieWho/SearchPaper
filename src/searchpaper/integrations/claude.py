"""Claude integration for SearchPaper.

By default this integration writes standalone managed files and does not
overwrite the user's main ``~/.claude/mcp.json`` or ``~/.claude/CLAUDE.md``.
Use ``inject_config_snippet(dry_run=False)`` to add marker-delimited blocks to
those files when the user explicitly asks for direct integration.
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
    return Path.home() / ".claude" / "CLAUDE.md"


def mcp_config_path() -> Path:
    return Path.home() / ".claude" / "mcp.json"


def instructions_path() -> Path:
    return Path.home() / ".claude" / "instructions" / "searchpaper.md"


def mcp_snippet_path() -> Path:
    return Path.home() / ".claude" / "searchpaper-mcp.json"


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


def mcp_config_block() -> str:
    """Marker-delimited block for injection into ~/.claude/mcp.json."""
    return (
        f"{MARKER_START}\n"
        "  // SearchPaper MCP server (managed by searchpaper install --target claude)\n"
        '  "mcpServers": {\n'
        '    "searchpaper": {\n'
        '      "command": "searchpaper",\n'
        '      "args": ["serve", "--mcp"]\n'
        "    }\n"
        "  }\n"
        f"{MARKER_END}"
    )


def instructions_block() -> str:
    """Marker-delimited block for injection into ~/.claude/CLAUDE.md."""
    return f"{MARKER_START}\n# SearchPaper Instructions\n\n{instructions_content()}\n{MARKER_END}"


def detect() -> bool:
    return config_path().parent.exists() or mcp_config_path().parent.exists()


def install(dry_run: bool = False) -> dict[str, Any]:
    """Default install writes standalone snippet files only."""
    changes: list[dict[str, Any]] = []
    changes.append(safe_write(instructions_path(), instructions_content(), dry_run=dry_run))
    changes.append(safe_write(mcp_snippet_path(), mcp_config_snippet(), dry_run=dry_run))
    return {
        "target": "claude",
        "detected": detect(),
        "message": (
            "Claude support scaffolded. Merge ~/.claude/searchpaper-mcp.json into "
            "your Claude MCP settings manually, or use inject_config_snippet()."
        ),
        "changes": changes,
    }


def inject_config_snippet(dry_run: bool = True) -> dict[str, Any]:
    """Inject marker-delimited SearchPaper blocks into Claude's main config files."""
    changes: list[dict[str, Any]] = []

    mcp_cfg = mcp_config_path()
    if mcp_cfg.exists():
        content = mcp_cfg.read_text(encoding="utf-8")
    else:
        content = "{\n}\n"
    new_content = ensure_managed_block(content, mcp_config_block())
    changes.append(safe_write(mcp_cfg, new_content, dry_run=dry_run))

    claude_md = config_path()
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
    else:
        content = ""
    new_content = ensure_managed_block(content, instructions_block())
    changes.append(safe_write(claude_md, new_content, dry_run=dry_run))

    return {
        "target": "claude",
        "dry_run": dry_run,
        "message": (
            "Injected SearchPaper blocks into ~/.claude/mcp.json and ~/.claude/CLAUDE.md. "
            "Run with dry_run=False to apply."
        ),
        "changes": changes,
    }


def uninstall(dry_run: bool = False) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    changes.append(safe_remove(instructions_path(), dry_run=dry_run))
    changes.append(safe_remove(mcp_snippet_path(), dry_run=dry_run))

    mcp_cfg = mcp_config_path()
    if mcp_cfg.exists():
        content = mcp_cfg.read_text(encoding="utf-8")
        new_content = remove_managed_block(content)
        changes.append(safe_write(mcp_cfg, new_content, dry_run=dry_run))

    claude_md = config_path()
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        new_content = remove_managed_block(content)
        changes.append(safe_write(claude_md, new_content, dry_run=dry_run))

    return {"target": "claude", "changes": changes}


def doctor() -> dict[str, Any]:
    mcp_cfg = mcp_config_path()
    claude_md = config_path()
    has_managed_mcp = mcp_cfg.exists() and MARKER_START in mcp_cfg.read_text(encoding="utf-8")
    has_managed_md = claude_md.exists() and MARKER_START in claude_md.read_text(encoding="utf-8")
    issues: list[str] = []
    if not detect():
        issues.append("Claude config directory not found.")
    if not has_managed_mcp and not mcp_snippet_path().exists():
        issues.append("No SearchPaper MCP config found. Run install or inject_config_snippet().")
    if not has_managed_md and not instructions_path().exists():
        issues.append("No SearchPaper instructions found. Run install or inject_config_snippet().")

    return {
        "target": "claude",
        "detected": detect(),
        "has_managed_mcp_block": has_managed_mcp,
        "has_managed_instructions_block": has_managed_md,
        "has_mcp_snippet": mcp_snippet_path().exists(),
        "has_instructions_snippet": instructions_path().exists(),
        "issues": issues,
        "manual_merge_instructions": [
            "1. Open ~/.claude/searchpaper-mcp.json and copy the mcpServers block.",
            "2. Paste it into your Claude MCP settings (Claude Desktop or project config).",
            "3. Review ~/.claude/instructions/searchpaper.md for agent behavior rules.",
        ],
    }
