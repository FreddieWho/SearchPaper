"""Smoke benchmark using the curated biomedical query set.

Usage:
    uv run python scripts/smoke_benchmark.py --query-set examples/biomedical_query_set.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


async def call_tool(session: ClientSession, tool: str, params: dict[str, Any]) -> dict[str, Any]:
    result = await session.call_tool(tool, arguments=params)
    for content in result.content:
        if isinstance(content, TextContent):
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return {"raw": content.text[:500]}
    return {}


async def run_queries(query_set_path: Path, output_path: Path) -> None:
    query_set = json.loads(query_set_path.read_text(encoding="utf-8"))
    queries = query_set.get("queries", [])

    cache_fd, cache_path = tempfile.mkstemp(prefix="smoke_bench_cache_", suffix=".db")
    os.close(cache_fd)
    env = os.environ.copy()
    env["SEARCHPAPER_CACHE"] = cache_path

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "searchpaper", "serve", "--mcp"],
        env=env,
    )

    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "query_set": query_set.get("description", ""),
        "results": [],
    }

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                for item in queries:
                    name = item["name"]
                    query = item["query"]
                    print(f"[smoke] {name}: '{query}'")
                    start = time.perf_counter()
                    result = await call_tool(session, "search_literature", {"query": query, "limit": 5})
                    latency_ms = (time.perf_counter() - start) * 1000
                    data = result.get("data", {})
                    trace = data.get("trace", {})
                    entry = {
                        "name": name,
                        "query": query,
                        "domain": item.get("domain"),
                        "latency_ms": round(latency_ms, 2),
                        "work_count": len(data.get("works", [])),
                        "sources_succeeded": trace.get("sources_succeeded", []),
                        "sources_failed": trace.get("sources_failed", []),
                        "warnings": data.get("warnings", []),
                    }
                    report["results"].append(entry)
                    print(
                        f"[smoke] {name}: {entry['work_count']} works, "
                        f"succeeded={entry['sources_succeeded']}, "
                        f"latency={entry['latency_ms']:.0f}ms"
                    )
    finally:
        try:
            os.unlink(cache_path)
        except FileNotFoundError:
            pass

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport saved to {output_path}")

    total = len(report["results"])
    with_results = sum(1 for r in report["results"] if r["work_count"] > 0)
    print(f"Queries with results: {with_results}/{total}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke benchmark biomedical query set")
    parser.add_argument("--query-set", default="examples/biomedical_query_set.json", help="Query set JSON")
    parser.add_argument(
        "--output",
        default=f"reports/smoke_query_set_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json",
        help="Output report path",
    )
    args = parser.parse_args()
    asyncio.run(run_queries(Path(args.query_set), Path(args.output)))


if __name__ == "__main__":
    main()
