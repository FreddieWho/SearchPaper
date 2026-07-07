"""Shared async HTTP helpers for SearchPaper source adapters."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from searchpaper.config import default_user_agent


class HTTPClient:
    """Thin wrapper around httpx.AsyncClient with retry and rate-limit helpers."""

    def __init__(
        self,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        api_key: str | None = None,
        key_header: str = "x-api-key",
    ):
        merged_headers = {"User-Agent": default_user_agent()}
        if headers:
            merged_headers.update(headers)
        if api_key:
            merged_headers[key_header] = api_key
        self.client = httpx.AsyncClient(
            base_url=base_url or "",
            timeout=timeout,
            headers=merged_headers,
        )

    async def aclose(self) -> None:
        await self.client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        max_retries: int = 1,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        **kwargs: Any,
    ) -> httpx.Response:
        last_exception: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                resp = await self.client.request(method, url, **kwargs)
                if resp.status_code != 429 and resp.status_code < 500:
                    return resp
                if attempt == max_retries:
                    return resp
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                last_exception = exc
                if attempt == max_retries:
                    raise
            delay = min(base_delay * (2**attempt) + random.uniform(0, 1), max_delay)
            await asyncio.sleep(delay)
        if last_exception:
            raise last_exception
        raise httpx.HTTPError("Max retries exceeded")

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
