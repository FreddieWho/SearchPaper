import asyncio
import random
from typing import Any

import httpx


def _is_retryable_status(status: int) -> bool:
    return status == 429 or status >= 500


async def fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs: Any,
) -> httpx.Response:
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            resp = await client.request(method, url, **kwargs)
            if not _is_retryable_status(resp.status_code):
                return resp
            if attempt == max_retries:
                return resp
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
            last_exception = e
            if attempt == max_retries:
                raise
        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
        await asyncio.sleep(delay)
    if last_exception:
        raise last_exception
    raise httpx.HTTPError("Max retries exceeded")
