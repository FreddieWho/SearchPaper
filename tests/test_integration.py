"""Tests for agent integration manager."""

from pathlib import Path

import pytest

from searchpaper.integrations import claude, codex, opencode
from searchpaper.integrations.manager import IntegrationManager


@pytest.mark.asyncio
async def test_integration_dry_run_opencode(tmp_path, monkeypatch):
    from searchpaper.integrations import manager

    monkeypatch.setattr(manager, "STATE_PATH", tmp_path / "integrations.json")
    mgr = IntegrationManager()
    result = await mgr.install("opencode", dry_run=True)
    assert result["dry_run"] is True
    assert any(r["target"] == "opencode" for r in result["results"])
    # State should not be written on dry-run.
    assert not (tmp_path / "integrations.json").exists()


@pytest.mark.asyncio
async def test_integration_state_records_config_path(tmp_path, monkeypatch):
    from searchpaper.integrations import manager

    monkeypatch.setattr(manager, "STATE_PATH", tmp_path / "integrations.json")
    mgr = IntegrationManager()
    await mgr.install("opencode")
    state = manager._load_state()
    opencode_state = state["installed_targets"]["opencode"]
    assert "config_path" in opencode_state
    assert "opencode.jsonc" in opencode_state["config_path"]


@pytest.mark.asyncio
async def test_integration_migration_updates_state_version(tmp_path, monkeypatch):
    from searchpaper.integrations import manager

    monkeypatch.setattr(manager, "STATE_PATH", tmp_path / "integrations.json")
    mgr = IntegrationManager()

    # Simulate an older installation.
    state_path = tmp_path / "integrations.json"
    state_path.write_text(
        '{"schema_version": "0.2", "searchpaper_version": "0.1.0", "installed_targets": {"opencode": {}}}',
        encoding="utf-8",
    )

    migration_check = mgr.needs_migration()
    assert migration_check["needs_migration"] is True
    assert "opencode" in migration_check["outdated_targets"]

    result = await mgr.migrate("opencode", dry_run=True)
    assert any(r["target"] == "opencode" and r.get("migrated") for r in result["results"])


def test_agent_instruction_content_contains_required_safety_rules():
    for content in [opencode.skill_content(), codex.instructions_content(), claude.instructions_content()]:
        assert "search_literature" in content
        assert "DOI/PMID/PMCID" in content
        assert "Do not hide degraded or failed sources" in content


@pytest.mark.asyncio
async def test_integration_dry_run_codex_and_claude(monkeypatch, tmp_path):
    from searchpaper.integrations import manager

    monkeypatch.setattr(manager, "STATE_PATH", tmp_path / "integrations.json")
    mgr = IntegrationManager()

    codex_result = await mgr.install("codex", dry_run=True)
    claude_result = await mgr.install("claude", dry_run=True)

    codex_paths = {change["path"] for change in codex_result["results"][0]["changes"]}
    claude_paths = {change["path"] for change in claude_result["results"][0]["changes"]}

    assert any(path.endswith(".codex/searchpaper-mcp.json") for path in codex_paths)
    assert any(path.endswith(".codex/instructions/searchpaper.md") for path in codex_paths)
    assert any(path.endswith(".claude/instructions/searchpaper.md") for path in claude_paths)
    assert any(path.endswith(".claude/searchpaper-mcp.json") for path in claude_paths)
    assert not (tmp_path / "integrations.json").exists()


def test_repository_skill_templates_cover_writable_agent_targets():
    paths = [
        Path(".agents/skills/literature-search/SKILL.md"),
        Path(".opencode/skills/literature-search/SKILL.md"),
        Path(".claude/skills/literature-search/SKILL.md"),
    ]

    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "search_literature" in content
        assert "DOI/PMID/PMCID" in content
        assert "Do not hide degraded or failed sources" in content


@pytest.mark.asyncio
async def test_integration_custom_tool_install(tmp_path, monkeypatch):
    from searchpaper.integrations import manager

    monkeypatch.setattr(manager, "STATE_PATH", tmp_path / "integrations.json")
    mgr = IntegrationManager()
    result = await mgr.install("opencode", modes=["custom_tool"])
    assert result["results"][0]["modes"] == ["custom_tool"]
    wrapper_change = next(
        (c for c in result["results"][0]["changes"] if "searchpaper_wrapper.py" in c["path"]),
        None,
    )
    assert wrapper_change is not None
    tools_change = next(
        (c for c in result["results"][0]["changes"] if "searchpaper_tools.json" in c["path"]),
        None,
    )
    assert tools_change is not None


def test_opencode_custom_tool_wrapper_functions():
    from searchpaper.integrations.opencode_custom_tool import (
        search,
        tool_definitions,
        wrapper_script_content,
    )

    assert "searchpaper.integrations.opencode_custom_tool" in wrapper_script_content()
    defs = tool_definitions("/tmp/searchpaper_wrapper.py")
    assert any(t["name"] == "searchpaper_search" for t in defs["tools"])
    assert any(t["name"] == "searchpaper_signals" for t in defs["tools"])
    # Search with empty query should invoke CLI and return an envelope/error.
    result = search("")
    assert "schema_version" in result or "error" in result
