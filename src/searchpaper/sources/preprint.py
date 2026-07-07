"""bioRxiv/medRxiv adapters."""

from __future__ import annotations

from typing import Any

from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_doi
from searchpaper.schemas import Author, SearchFilters, SourceRecord, SourceState, SourceStatus, WorkIdentifier
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso

PREPRINT_BASE = "https://api.biorxiv.org/details"
PREPRINT_TERMS_URL = "https://api.biorxiv.org/"


def _parse_authors(raw: str) -> list[Author]:
    return [Author(name=name.strip()) for name in raw.split(";") if name.strip()]


def _parse_item(item: dict[str, Any], source: str, query: str | None = None) -> SourceRecord:
    doi = normalize_doi(item.get("doi", "")) or item.get("doi", "").lower().strip()
    date = item.get("date") or item.get("version")
    ids = {"doi": doi} if doi else {}
    normalized = {
        "title": item.get("title"),
        "year": int(date[:4]) if isinstance(date, str) and date[:4].isdigit() else None,
        "publication_date": date,
        "venue": source,
        "authors": [author.model_dump(mode="json") for author in _parse_authors(item.get("authors", ""))],
        "abstract": item.get("abstract"),
        "identifiers": ids,
        "fields_of_study": [item.get("category")] if item.get("category") else [],
        "publication_types": ["preprint"],
    }
    return SourceRecord(
        source=source,
        source_record_id=doi or item.get("title", ""),
        retrieved_at=now_iso(),
        query_or_identifier=query,
        raw_record=item,
        normalized_fields=normalized,
        identifiers=ids,
        source_terms_url=PREPRINT_TERMS_URL,
        usage_note=f"{source} API; no API key required.",
    )


class PreprintAdapter(SourceAdapter):
    name: str
    server: str
    source_terms_url = PREPRINT_TERMS_URL

    def __init__(self) -> None:
        self.http = HTTPClient(timeout=30.0)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        resp = await self.http.get(f"{PREPRINT_BASE}/{self.server}/2020-01-01/3000-01-01")
        items = resp.json().get("collection", [])
        lowered = query.lower()
        records = [_parse_item(item, self.name, query=query) for item in items]
        filtered = [
            record
            for record in records
            if lowered in (record.normalized_fields.get("title") or "").lower()
            or lowered in (record.normalized_fields.get("abstract") or "").lower()
        ]
        return (filtered or records)[: filters.limit]

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        if identifier.type.value != "doi":
            return None
        resp = await self.http.get(f"{PREPRINT_BASE}/{self.server}/{identifier.value}")
        items = resp.json().get("collection", [])
        return _parse_item(items[0], self.name, query=identifier.value) if items else None

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        record = await self.get(identifier)
        return [record] if record else []

    async def status(self) -> SourceStatus:
        try:
            resp = await self.http.get(f"{PREPRINT_BASE}/{self.server}/2020-01-01/2020-01-02")
            if resp.status_code == 200:
                return self._make_status(SourceState.AVAILABLE, message=f"{self.name} API responded.")
            return self._make_status(
                SourceState.DEGRADED,
                message=f"{self.name} probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.OFFLINE,
                message=f"{self.name} probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
