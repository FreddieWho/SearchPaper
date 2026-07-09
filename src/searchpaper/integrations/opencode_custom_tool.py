"""Thin OpenCode custom tool wrapper for SearchPaper.

This module provides a tiny adapter that shells out to the ``searchpaper`` CLI
and returns parsed JSON. It does not duplicate source adapter logic, ranking,
or cache handling.

OpenCode can expose these as custom tools by pointing to the wrapper script
generated during ``searchpaper install --target opencode --mode custom_tool``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any

CLI = shutil.which("searchpaper") or "searchpaper"


def _run(args: list[str]) -> dict[str, Any]:
    """Run searchpaper with the given args and return parsed JSON."""
    result = subprocess.run(
        [CLI, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and not result.stdout.strip():
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": {},
            "warnings": [result.stderr.strip() or f"searchpaper exited with code {result.returncode}"],
            "trace": {},
        }
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": {"stdout": result.stdout, "stderr": result.stderr},
            "warnings": ["searchpaper returned non-JSON output"],
            "trace": {},
        }


def search(query: str, sources: list[str] | None = None, limit: int = 20) -> dict[str, Any]:
    """Search scholarly literature."""
    args = ["search", query, "--json", "--limit", str(limit)]
    if sources:
        args.extend(["--sources", ",".join(sources)])
    return _run(args)


def get(identifier: str, sources: list[str] | None = None) -> dict[str, Any]:
    """Get a work by DOI, PMID, PMCID, or arXiv ID."""
    wid = identifier.strip()
    args: list[str] = ["get", "--json"]
    if wid.startswith("10."):
        args.extend(["--doi", wid])
    elif wid.lower().startswith("pmc"):
        args.extend(["--pmcid", wid])
    elif "/" in wid or ":" in wid:
        # arXiv IDs may contain ':' in normalized form.
        args.extend(["--arxiv", wid])
    else:
        args.extend(["--pmid", wid])
    if sources:
        args.extend(["--sources", ",".join(sources)])
    return _run(args)


def resolve(identifier: str, sources: list[str] | None = None) -> dict[str, Any]:
    """Resolve an identifier across sources."""
    wid = identifier.strip()
    args: list[str] = ["resolve", "--json"]
    if wid.startswith("10."):
        args.extend(["--doi", wid])
    else:
        args.extend(["--pmid", wid])
    if sources:
        args.extend(["--sources", ",".join(sources)])
    return _run(args)


def signals(query: str, entity2_type: str = "chemical", limit: int = 10) -> dict[str, Any]:
    """Search biomedical literature signals via PubTator3."""
    return _run(["signals", query, "--entity2-type", entity2_type, "--json", "--limit", str(limit)])


def _dispatch(argv: list[str]) -> dict[str, Any]:
    """Dispatch command-line calls from OpenCode custom tool JSON."""
    if not argv:
        return {"error": "No command provided"}
    command = argv[0]
    rest = argv[1:]
    if command == "search" and rest:
        return search(rest[0])
    if command == "get" and rest:
        return get(rest[0])
    if command == "resolve" and rest:
        return resolve(rest[0])
    if command == "signals" and rest:
        return signals(rest[0])
    return _run(argv)


def wrapper_script_content() -> str:
    """Return the content of the standalone wrapper script."""
    return (
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from searchpaper.integrations.opencode_custom_tool import _dispatch\n"
        "print(json.dumps(_dispatch(sys.argv[1:]), ensure_ascii=False))\n"
    )


def tool_definitions(wrapper_path: str) -> dict[str, Any]:
    """Return a best-effort OpenCode custom tool definition structure."""
    return {
        "schema_version": "0.2",
        "tools": [
            {
                "name": "searchpaper_search",
                "description": "Search open scholarly literature using SearchPaper.",
                "command": f"python3 {wrapper_path} search {{query}}",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "sources": {
                        "type": "string",
                        "description": "Comma-separated source names (optional)",
                    },
                },
            },
            {
                "name": "searchpaper_get",
                "description": "Get a work by DOI, PMID, PMCID, or arXiv ID using SearchPaper.",
                "command": f"python3 {wrapper_path} get {{identifier}}",
                "parameters": {
                    "identifier": {"type": "string", "description": "DOI, PMID, PMCID, or arXiv ID"},
                },
            },
            {
                "name": "searchpaper_resolve",
                "description": "Resolve a DOI or PMID across SearchPaper sources.",
                "command": f"python3 {wrapper_path} resolve {{identifier}}",
                "parameters": {
                    "identifier": {"type": "string", "description": "DOI or PMID"},
                },
            },
            {
                "name": "searchpaper_signals",
                "description": "Search biomedical literature signals via SearchPaper.",
                "command": f"python3 {wrapper_path} signals {{query}}",
                "parameters": {
                    "query": {"type": "string", "description": "Entity or query"},
                },
            },
        ],
    }


if __name__ == "__main__":
    print(json.dumps(_dispatch(sys.argv[1:]), ensure_ascii=False))
