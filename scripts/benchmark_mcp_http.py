"""Stress benchmark for the HTTP/SSE MCP server.

Starts a local HTTP MCP server and runs concurrent tool calls to measure
latency percentiles and throughput. `plan_literature_search` is used as the
fast local workload; `get_source_status` and `search_literature` are sampled
separately because they depend on live source APIs.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import subprocess
import time
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

HOST = "127.0.0.1"
PORT = 18765
PATH = "/mcp"
URL = f"http://{HOST}:{PORT}{PATH}/sse"
FAST_TIMEOUT = 10.0
SLOW_TIMEOUT = 60.0


@asynccontextmanager
async def mcp_session():
    async with sse_client(URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=10.0)
            yield session


async def call_tool(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any],
    timeout: float = FAST_TIMEOUT,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            session.call_tool(name, arguments=arguments),
            timeout=timeout,
        )
    except TimeoutError:
        return {"latency": time.perf_counter() - start, "content": [], "is_error": True, "error": "timeout"}
    latency = time.perf_counter() - start
    content = []
    for item in result.content:
        if hasattr(item, "text"):
            content.append(item.text)
    return {"latency": latency, "content": content, "is_error": result.isError}


async def run_fast_workload(session: ClientSession, n: int) -> list[dict[str, Any]]:
    results = []
    args = {"query": "CRISPR cancer immunotherapy", "profile": "auto"}
    for _ in range(n):
        result = await call_tool(session, "plan_literature_search", args)
        results.append({"tool": "plan_literature_search", **result})
    return results


async def benchmark(concurrent_clients: int, requests_per_client: int) -> dict[str, Any]:
    async def client_runner() -> list[dict[str, Any]]:
        async with mcp_session() as session:
            return await run_fast_workload(session, requests_per_client)

    start = time.perf_counter()
    client_results = await asyncio.gather(*[client_runner() for _ in range(concurrent_clients)])
    total_time = time.perf_counter() - start

    all_calls: list[dict[str, Any]] = []
    for client in client_results:
        all_calls.extend(client)

    latencies = [c["latency"] for c in all_calls]
    errors = [c for c in all_calls if c.get("is_error")]
    sorted_lat = sorted(latencies)

    def percentile(p: float) -> float:
        idx = int(len(sorted_lat) * p / 100)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    return {
        "concurrent_clients": concurrent_clients,
        "requests_per_client": requests_per_client,
        "total_calls": len(all_calls),
        "errors": len(errors),
        "error_rate": round(len(errors) / len(all_calls), 4) if all_calls else 0,
        "total_time_seconds": round(total_time, 3),
        "throughput_rps": round(len(all_calls) / total_time, 2),
        "latency_ms": {
            "min": round(min(latencies) * 1000, 2),
            "p50": round(percentile(50) * 1000, 2),
            "p95": round(percentile(95) * 1000, 2),
            "p99": round(percentile(99) * 1000, 2),
            "max": round(max(latencies) * 1000, 2),
            "mean": round(statistics.mean(latencies) * 1000, 2),
        },
        "sample_error": errors[0] if errors else None,
    }


async def sample_slow_tool(name: str, arguments: dict[str, Any], timeout: float) -> dict[str, Any]:
    async with mcp_session() as session:
        result = await call_tool(session, name, arguments, timeout=timeout)
        return {
            "tool": name,
            "latency_ms": round(result["latency"] * 1000, 2),
            "is_error": result["is_error"],
            "work_count": _work_count(result["content"]) if name == "search_literature" else None,
        }


def _work_count(content: list[str]) -> int:
    if not content:
        return 0
    try:
        data = json.loads(content[0]).get("data", {})
        return len(data.get("works", []))
    except Exception:
        return 0


async def main(output_path: str | None = None):
    server = subprocess.Popen(
        [
            "uv",
            "run",
            "python",
            "-m",
            "searchpaper",
            "serve",
            "--mcp",
            "--transport",
            "http",
            "--host",
            HOST,
            "--port",
            str(PORT),
            "--path",
            PATH,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    for _ in range(30):
        if server.poll() is not None:
            stdout, stderr = server.communicate(timeout=2)
            raise RuntimeError(
                f"Server exited early (code {server.returncode}):\n"
                f"stdout:\n{stdout.decode()}\nstderr:\n{stderr.decode()}"
            )
        try:
            import httpx

            resp = httpx.head(f"http://{HOST}:{PORT}{PATH}/sse", timeout=2.0)
            if resp.status_code in (200, 405):
                break
        except Exception:
            pass
        await asyncio.sleep(0.5)
    else:
        server.terminate()
        try:
            stdout, stderr = server.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = b"", b""
        raise RuntimeError(f"Server did not start in time:\nstdout:\n{stdout.decode()}\nstderr:\n{stderr.decode()}")

    report: dict[str, Any] = {
        "url": URL,
        "slow_tool_samples": {},
        "fast_workload": [],
    }
    try:
        print(f"Benchmarking HTTP MCP at {URL}\n")

        print("Sample slow-tool latencies (live source APIs):")
        status_sample = await sample_slow_tool("get_source_status", {"include_catalog": False}, SLOW_TIMEOUT)
        report["slow_tool_samples"]["get_source_status"] = status_sample
        print(json.dumps(status_sample, indent=2))
        search_sample = await sample_slow_tool(
            "search_literature",
            {"query": "PD-1 hepatocellular carcinoma", "sources": ["pubmed"], "limit": 3},
            SLOW_TIMEOUT,
        )
        report["slow_tool_samples"]["search_literature"] = search_sample
        print(json.dumps(search_sample, indent=2))
        print()

        print("Fast local workload throughput (`plan_literature_search`):")
        for clients, requests in [(1, 10), (2, 10), (4, 10)]:
            bench_report = await benchmark(clients, requests)
            report["fast_workload"].append(bench_report)
            print(json.dumps(bench_report, indent=2))
            print()

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"JSON report written to {output_path}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark HTTP MCP server")
    parser.add_argument("--output", default=None, help="Path to write JSON report")
    args = parser.parse_args()
    asyncio.run(main(output_path=args.output))
