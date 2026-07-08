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
    assert any(path.endswith(".claude/CLAUDE.md") for path in claude_paths)
    assert any(path.endswith(".claude/mcp.json") for path in claude_paths)
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
