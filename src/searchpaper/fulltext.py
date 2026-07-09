"""Full-text download helpers (metadata + file download, no PDF parsing)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from searchpaper.http import HTTPClient
from searchpaper.sources.europepmc import EUROPEPMC_BASE


async def _download_url(client: HTTPClient, url: str, path: Path) -> dict[str, Any]:
    """Download ``url`` to ``path`` and return a status dict."""
    try:
        resp = await client.get(url, timeout=60.0, follow_redirects=True)
        if resp.status_code >= 400:
            return {
                "ok": False,
                "error": f"HTTP {resp.status_code}",
                "path": str(path),
                "url": url,
            }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
        return {
            "ok": True,
            "path": str(path),
            "url": url,
            "bytes": len(resp.content),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "path": str(path), "url": url}


async def download_full_text(
    work: dict[str, Any],
    pdf_path: Path | None = None,
    xml_path: Path | None = None,
) -> dict[str, Any]:
    """Download OA PDF and/or Europe PMC XML for a work dict.

    Returns a dict with ``pdf`` and/or ``xml`` status entries. If the
    requested asset is not available, the entry reports ``available: False``.
    """
    availability = work.get("full_text_availability") or {}
    identifiers = work.get("identifiers") or {}
    downloads: dict[str, Any] = {}

    async with _HTTPClientCtx() as client:
        if pdf_path:
            pdf_url = availability.get("oa_pdf_url")
            if pdf_url:
                downloads["pdf"] = await _download_url(client, pdf_url, pdf_path)
            else:
                downloads["pdf"] = {
                    "ok": False,
                    "available": False,
                    "error": "No open-access PDF URL available",
                    "path": str(pdf_path),
                }

        if xml_path:
            pmcid = identifiers.get("pmcid")
            if pmcid:
                url = f"{EUROPEPMC_BASE}/PMC/{pmcid}/fullTextXML"
                downloads["xml"] = await _download_url(client, url, xml_path)
            else:
                downloads["xml"] = {
                    "ok": False,
                    "available": False,
                    "error": "No PMCID available for Europe PMC XML",
                    "path": str(xml_path),
                }

    return downloads


class _HTTPClientCtx:
    """Async-context wrapper so callers do not need to manage client lifecycle."""

    def __init__(self) -> None:
        self.client = HTTPClient(timeout=60.0)

    async def __aenter__(self) -> HTTPClient:
        return self.client

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.client.aclose()
