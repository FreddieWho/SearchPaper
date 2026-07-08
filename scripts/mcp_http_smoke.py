"""Minimal smoke test for HTTP MCP client."""

import asyncio
import subprocess
import time

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

HOST = "127.0.0.1"
PORT = 18767
PATH = "/mcp"
URL = f"http://{HOST}:{PORT}{PATH}/sse"


def server_cmd() -> list[str]:
    return [
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
    ]


async def main():
    server = subprocess.Popen(
        server_cmd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    for _ in range(30):
        if server.poll() is not None:
            break
        try:
            resp = httpx.head(URL, timeout=2.0)
            if resp.status_code in (200, 405):
                print("Server ready")
                break
        except Exception:
            pass
        await asyncio.sleep(0.5)
    else:
        server.terminate()
        raise RuntimeError("Server not ready")

    try:
        print("Connecting SSE client...")
        async with sse_client(URL) as (read_stream, write_stream):
            print("SSE connected, creating session...")
            async with ClientSession(read_stream, write_stream) as session:
                print("Initializing...")
                await asyncio.wait_for(session.initialize(), timeout=10.0)
                print("Calling get_source_status...")
                start = time.perf_counter()
                result = await asyncio.wait_for(
                    session.call_tool("get_source_status", arguments={}),
                    timeout=30.0,
                )
                print(f"Call took {time.perf_counter() - start:.2f}s")
                print("Result content:")
                for item in result.content:
                    print(item.text[:500])
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    asyncio.run(main())
