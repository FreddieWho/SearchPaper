"""Unpaywall adapter for open-access availability enrichment.

Unpaywall is not a general literature search source; it enforces DOI-based
lookups. It is registered as an enrichment source and is not included in the
default search source list.
"""

from __future__ import annotations

from typing import Any

from searchpaper.config import load_config
from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_doi
from searchpaper.schemas import SearchFilters, SourceRecord, SourceState, SourceStatus, WorkIdentifier
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso
from searchpaper.sources.registry import register

UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
UNPAYWALL_SOURCE = "unpaywall"
UNPAYWALL_TERMS_URL = "https://unpaywall.org/products/api"


def _normalize_oa_record(doi: str, raw: dict[str, Any]) -> dict[str, Any]:
    best = raw.get("best_oa_location") or {}
    return {
        "doi": doi,
        "is_oa": raw.get("is_oa"),
        "oa_status": raw.get("oa_status"),
        "oa_url": best.get("url"),
        "oa_pdf_url": best.get("url_for_pdf"),
        "host_type": best.get("host_type"),
        "license": best.get("license"),
        "version": best.get("version"),
    }


def _make_record(doi: str, raw: dict[str, Any]) -> SourceRecord:
    normalized = _normalize_oa_record(doi, raw)
    return SourceRecord(
        source=UNPAYWALL_SOURCE,
        source_record_id=doi,
        retrieved_at=now_iso(),
        query_or_identifier=doi,
        raw_record=raw,
        normalized_fields=normalized,
        identifiers={"doi": doi},
        source_terms_url=UNPAYWALL_TERMS_URL,
        usage_note="Unpaywall enriches DOIs with OA status. Provide email for polite pool.",
    )


@register(UNPAYWALL_SOURCE)
class UnpaywallAdapter(SourceAdapter):
    """Enrich DOIs with open-access metadata from Unpaywall."""

    name = UNPAYWALL_SOURCE
    source_terms_url = UNPAYWALL_TERMS_URL
    usage_note = "Unpaywall is DOI-only; provide email for polite pool."

    def __init__(self, email: str | None = None):
        cfg = load_config()
        self.email = email or cfg.get("unpaywall_email") or cfg.get("crossref_email") or "searchpaper@localhost"
        self.http = HTTPClient(timeout=30.0)

    async def aclose(self) -> None:
        await self.http.aclose()

    def _params(self) -> dict[str, Any]:
        return {"email": self.email}

    async def _fetch(self, doi: str) -> SourceRecord | None:
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        resp = await self.http.get(f"{UNPAYWALL_BASE}/{normalized}", params=self._params())
        if resp.status_code >= 400:
            return None
        try:
            data = resp.json()
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return _make_record(normalized, data)

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        # Unpaywall does not support free-text search.
        return []

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        if identifier.type.value == "doi":
            return await self._fetch(identifier.value)
        return None

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            # Probe with a well-known DOI.
            resp = await self.http.get(f"{UNPAYWALL_BASE}/10.1038/nature12373", params=self._params())
            if resp.status_code == 200:
                return self._make_status(
                    SourceState.AVAILABLE,
                    message="Unpaywall API responded to a probe query.",
                )
            return self._make_status(
                SourceState.DEGRADED,
                message=f"Unpaywall probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                message=f"Unpaywall probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
