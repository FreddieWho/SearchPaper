"""Tests for capabilities reporting."""

import json

from typer.testing import CliRunner

from searchpaper.cli import app

runner = CliRunner()


def test_capabilities_json():
    result = runner.invoke(app, ["capabilities", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "cli_commands" in data
    assert "mcp_tools" in data
    assert "sources" in data
    assert "pubmed" in data["sources"]
    assert "jsonl" in data["export_formats"]
    assert "opencode" in data["agent_integrations"]
