"""Benchmark SearchPaper MCP server against live APIs.

Usage:
    uv run python scripts/benchmark_mcp.py --output reports/mcp_benchmark.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


@dataclass
class CallRecord:
    tool: str
    params: dict[str, Any]
    start: float
    end: float
    latency_ms: float
    success: bool
    result_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


SINGLE_TOOL_CASES: list[dict[str, Any]] = [
    {
        "name": "search_literature",
        "params": {"query": "HCC TACE PD-1", "limit": 5},
    },
    {
        "name": "plan_literature_search",
        "params": {"query": "immunotherapy biomarkers", "profile": "default"},
    },
    {
        "name": "get_work",
        "params": {"identifier": "10.1038/s41586-021-03819-2"},
    },
    {
        "name": "resolve_identifiers",
        "params": {"identifiers": ["10.1038/s41586-021-03819-2"]},
    },
    {
        "name": "get_source_status",
        "params": {"include_catalog": True},
    },
    {
        "name": "lookup_mesh",
        "params": {"term": "hepatocellular carcinoma", "limit": 5},
    },
    {
        "name": "find_related_articles",
        "params": {"pmid": "12345678", "limit": 5},
    },
    {
        "name": "convert_identifiers",
        "params": {"identifiers": ["10.1038/s41586-021-03819-2"]},
    },
    {
        "name": "search_literature_signals",
        "params": {"entity1": "PDCD1", "entity2_type": "chemical", "limit": 5},
    },
    {
        "name": "expand_from_work",
        "params": {"identifier": "10.1038/s41586-021-03819-2", "by": ["citations"]},
    },
    {
        "name": "export_records",
        "params": {
            "works": [
                {
                    "work_id": "w1",
                    "title": "Example Paper One",
                    "year": 2024,
                    "authors": [{"name": "Alice"}],
                    "identifiers": {"doi": "10.1000/one"},
                },
                {
                    "work_id": "w2",
                    "title": "Example Paper Two",
                    "year": 2023,
                    "authors": [{"name": "Bob"}],
                    "identifiers": {"doi": "10.1000/two"},
                },
            ],
            "format": "bibtex",
        },
    },
]

SEARCH_QUERIES = [
    "HCC TACE PD-1",
    "immunotherapy biomarkers",
    "single-cell RNA-seq",
    "CRISPR screening cancer",
    "hepatocellular carcinoma immunotherapy",
    "PD-L1 expression",
    "tumor microenvironment",
    "CAR-T therapy",
    "immune checkpoint inhibitors",
    "cancer vaccine",
]


def _extract_text(result: Any) -> str:
    for content in result.content:
        if isinstance(content, TextContent):
            return content.text
    return ""


def _summarize(tool: str, data: dict[str, Any]) -> dict[str, Any]:
    """Extract summary from ResponseEnvelope (data -> SearchResult -> works/signals)."""
    summary: dict[str, Any] = {}
    inner = data.get("data", {})
    if tool == "search_literature":
        summary["work_count"] = len(inner.get("works", []))
    elif tool == "plan_literature_search":
        summary["selected_sources"] = inner.get("selected_sources", [])
    elif tool == "get_work" or tool == "resolve_identifiers" or tool == "expand_from_work":
        summary["work_count"] = len(inner.get("works", []))
    elif tool == "get_source_status":
        summary["status_count"] = len(inner)
        summary["available_count"] = sum(1 for s in inner if s.get("state") == "available")
    elif tool == "lookup_mesh":
        summary["mesh_count"] = len(inner)
    elif tool == "find_related_articles":
        summary["pmid_count"] = len(inner)
    elif tool == "convert_identifiers":
        summary["converted_count"] = len(inner)
    elif tool == "search_literature_signals":
        summary["signal_count"] = len(inner.get("signals", []))
    elif tool == "export_records":
        summary["content_length"] = len(inner.get("content", ""))
    return summary


async def _call_tool(
    session: ClientSession,
    tool: str,
    params: dict[str, Any],
) -> CallRecord:
    start = time.perf_counter()
    record = CallRecord(tool=tool, params=params, start=start, end=start, latency_ms=0.0, success=False)
    try:
        result = await session.call_tool(tool, arguments=params)
        end = time.perf_counter()
        record.end = end
        record.latency_ms = (end - start) * 1000

        if getattr(result, "isError", False):
            text = _extract_text(result)
            record.error = f"MCP tool error: {text[:500]}"
            return record

        text = _extract_text(result)
        if not text:
            record.error = "Empty response content"
            return record

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            record.error = f"Non-JSON response: {text[:500]}"
            return record

        record.result_summary = _summarize(tool, data)
        record.warnings = data.get("warnings", [])
        record.trace = data.get("trace", {})
        # Treat explicit error object_type as failure.
        record.success = data.get("object_type") != "error" and data.get("error") is None
        if data.get("object_type") == "error":
            record.error = data.get("data", {}).get("error") or "error object"
    except Exception as exc:  # noqa: BLE001
        end = time.perf_counter()
        record.end = end
        record.latency_ms = (end - start) * 1000
        record.error = f"{type(exc).__name__}: {exc}"
    return record


async def run_smoke_tests(session: ClientSession) -> list[CallRecord]:
    records: list[CallRecord] = []
    for case in SINGLE_TOOL_CASES:
        print(f"[smoke] {case['name']} ...")
        record = await _call_tool(session, case["name"], case["params"])
        records.append(record)
        status = "OK" if record.success else "FAIL"
        print(f"[smoke] {case['name']}: {status} ({record.latency_ms:.0f}ms)")
    return records


async def run_repeated_search(session: ClientSession, query: str, n: int) -> list[CallRecord]:
    records: list[CallRecord] = []
    for i in range(n):
        record = await _call_tool(session, "search_literature", {"query": query, "limit": 5})
        records.append(record)
        print(f"[repeat {i+1}/{n}] latency={record.latency_ms:.0f}ms success={record.success}")
    return records


async def run_multi_query_search(session: ClientSession, queries: list[str]) -> list[CallRecord]:
    records: list[CallRecord] = []
    for i, query in enumerate(queries):
        record = await _call_tool(session, "search_literature", {"query": query, "limit": 5})
        records.append(record)
        print(f"[multi {i+1}/{len(queries)}] '{query}' latency={record.latency_ms:.0f}ms")
    return records


async def run_degradation_tests(session: ClientSession) -> list[CallRecord]:
    records: list[CallRecord] = []
    sources_list = [
        ["pubmed"],
        ["crossref"],
        ["openalex"],
        ["pubmed", "crossref"],
        ["pubmed", "crossref", "openalex", "semantic_scholar"],
    ]
    for sources in sources_list:
        record = await _call_tool(
            session,
            "search_literature",
            {"query": "HCC TACE PD-1", "sources": sources, "limit": 5},
        )
        records.append(record)
        trace = record.trace
        print(
            f"[degradation] sources={sources} "
            f"succeeded={trace.get('sources_succeeded', [])} "
            f"failed={trace.get('sources_failed', [])} "
            f"degraded={trace.get('sources_degraded', [])}"
        )
    return records


async def run_concurrent_calls(session: ClientSession, concurrency: int, rounds: int) -> list[CallRecord]:
    records: list[CallRecord] = []
    for r in range(rounds):
        print(f"[concurrent] round {r+1}/{rounds}")
        tasks = [
            _call_tool(session, "search_literature", {"query": SEARCH_QUERIES[i % len(SEARCH_QUERIES)], "limit": 5})
            for i in range(concurrency)
        ]
        round_records = await asyncio.gather(*tasks, return_exceptions=False)
        records.extend(round_records)
        ok = sum(1 for rec in round_records if rec.success)
        print(f"[concurrent] round {r+1}: {ok}/{concurrency} succeeded")
    return records


async def run_long_session(session: ClientSession, n: int) -> list[CallRecord]:
    records: list[CallRecord] = []
    tools = ["search_literature", "lookup_mesh", "plan_literature_search", "export_records"]
    params_map = {
        "search_literature": {"query": "HCC TACE PD-1", "limit": 3},
        "lookup_mesh": {"term": "carcinoma", "limit": 3},
        "plan_literature_search": {"query": "biomarkers", "profile": "default"},
        "export_records": {
            "works": [
                {
                    "work_id": "w1",
                    "title": "Example Paper",
                    "year": 2024,
                    "authors": [{"name": "Alice"}],
                    "identifiers": {"doi": "10.1000/one"},
                }
            ],
            "format": "ris",
        },
    }
    for i in range(n):
        tool = tools[i % len(tools)]
        record = await _call_tool(session, tool, params_map[tool])
        records.append(record)
        if (i + 1) % 10 == 0:
            ok = sum(1 for rec in records[-10:] if rec.success)
            print(f"[long] {i+1}/{n} done, last 10: {ok}/10 succeeded")
    return records


async def run_invalid_inputs(session: ClientSession) -> list[CallRecord]:
    records: list[CallRecord] = []
    cases = [
        ("get_work", {"identifier": "not-a-real-id"}),
        ("search_literature", {"query": ""}),
        ("search_literature", {"query": "HCC", "sources": ["nonexistent"]}),
        ("search_literature", {"query": "HCC", "limit": 500}),
    ]
    for tool, params in cases:
        record = await _call_tool(session, tool, params)
        records.append(record)
        summary = record.result_summary
        warnings = record.warnings
        print(
            f"[invalid] {tool}({params}) success={record.success} "
            f"summary={summary} warnings={warnings[:2]} error={record.error}"
        )
    return records


def _latency_stats(records: list[CallRecord]) -> dict[str, float]:
    latencies = [r.latency_ms for r in records if r.latency_ms > 0]
    if not latencies:
        return {}
    latencies.sort()
    n = len(latencies)
    return {
        "count": n,
        "mean": round(statistics.mean(latencies), 2),
        "min": round(latencies[0], 2),
        "max": round(latencies[-1], 2),
        "p50": round(latencies[n // 2], 2),
        "p95": round(latencies[int(n * 0.95)], 2) if n >= 20 else round(latencies[-1], 2),
        "p99": round(latencies[int(n * 0.99)], 2) if n >= 100 else round(latencies[-1], 2),
    }


def build_report(records: list[CallRecord]) -> dict[str, Any]:
    by_tool: dict[str, list[CallRecord]] = {}
    for rec in records:
        by_tool.setdefault(rec.tool, []).append(rec)

    tool_summary = {}
    for tool, recs in by_tool.items():
        ok = sum(1 for r in recs if r.success)
        tool_summary[tool] = {
            "count": len(recs),
            "success": ok,
            "failure": len(recs) - ok,
            "success_rate": round(ok / len(recs), 4) if recs else 0,
            "latency_ms": _latency_stats(recs),
        }

    total_ok = sum(1 for r in records if r.success)
    return {
        "run_at": datetime.now(UTC).isoformat(),
        "total_calls": len(records),
        "total_success": total_ok,
        "total_failure": len(records) - total_ok,
        "overall_success_rate": round(total_ok / len(records), 4) if records else 0,
        "overall_latency_ms": _latency_stats(records),
        "by_tool": tool_summary,
        "raw_records": [asdict(r) for r in records],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SearchPaper MCP server")
    parser.add_argument("--output", default="reports/mcp_benchmark.json", help="Output JSON file")
    parser.add_argument("--skip-stress", action="store_true", help="Skip stress scenarios")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cache_fd, cache_path = tempfile.mkstemp(prefix="mcp_bench_cache_", suffix=".db")
    os.close(cache_fd)

    env = os.environ.copy()
    env["SEARCHPAPER_CACHE"] = cache_path

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "searchpaper", "serve", "--mcp"],
        env=env,
    )

    all_records: list[CallRecord] = []
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("=== Smoke tests ===")
                all_records.extend(await run_smoke_tests(session))

                if not args.skip_stress:
                    print("\n=== Repeated search (cache test) ===")
                    all_records.extend(await run_repeated_search(session, "HCC TACE PD-1", 20))

                    print("\n=== Multi-query search ===")
                    all_records.extend(await run_multi_query_search(session, SEARCH_QUERIES))

                    print("\n=== Degradation tests ===")
                    all_records.extend(await run_degradation_tests(session))

                    print("\n=== Concurrent calls ===")
                    all_records.extend(await run_concurrent_calls(session, concurrency=5, rounds=3))

                    print("\n=== Long session ===")
                    all_records.extend(await run_long_session(session, n=50))

                print("\n=== Invalid input tests ===")
                all_records.extend(await run_invalid_inputs(session))
    finally:
        try:
            os.unlink(cache_path)
        except FileNotFoundError:
            pass

    report = build_report(all_records)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport saved to {output_path}")

    print("\n=== Summary ===")
    print(f"Total calls: {report['total_calls']}")
    print(f"Success: {report['total_success']}")
    print(f"Failure: {report['total_failure']}")
    print(f"Overall success rate: {report['overall_success_rate']:.2%}")
    latency = report["overall_latency_ms"]
    if latency:
        print(f"Latency (ms): mean={latency['mean']} p50={latency['p50']} p95={latency['p95']}")


if __name__ == "__main__":
    asyncio.run(main())
