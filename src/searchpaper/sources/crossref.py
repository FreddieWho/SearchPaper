"""Crossref adapter for SearchPaper."""

from __future__ import annotations

from typing import Any

from searchpaper.config import default_user_agent, load_config
from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_doi
from searchpaper.schemas import (
    Author,
    SearchFilters,
    SourceRecord,
    SourceState,
    SourceStatus,
    WorkIdentifier,
)
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso
from searchpaper.sources.registry import register

CROSSREF_BASE = "https://api.crossref.org"
CROSSREF_SOURCE = "crossref"
CROSSREF_TERMS_URL = "https://www.crossref.org/documentation/researchers/"


def _parse_author(a: dict[str, Any]) -> Author:
    given = a.get("given", "")
    family = a.get("family", "")
    name = f"{given} {family}".strip() or a.get("name", "")
    return Author(
        name=name,
        first_name=given or None,
        last_name=family or None,
        orcid=a.get("ORCID"),
        affiliations=[aff.get("name", "") for aff in a.get("affiliation", []) if isinstance(aff, dict)],
    )


def _extract_identifiers(item: dict[str, Any]) -> dict[str, str]:
    ids: dict[str, str] = {}
    doi = item.get("DOI")
    if doi:
        ids["doi"] = doi.lower().strip()
    if item.get("PMID"):
        ids["pmid"] = str(item["PMID"])
    if item.get("PMCID"):
        ids["pmcid"] = str(item["PMCID"])
    return ids


def _parse_message(item: dict[str, Any]) -> SourceRecord:
    ids = _extract_identifiers(item)
    authors_raw = item.get("author", [])
    authors = [_parse_author(a) for a in authors_raw if isinstance(a, dict)]
    published = item.get("published-print") or item.get("published") or item.get("published-online")
    year: int | None = None
    if isinstance(published, dict):
        date_parts = published.get("date-parts", [[]])[0]
        if date_parts:
            year = int(date_parts[0]) if str(date_parts[0]).isdigit() else None

    title_list = item.get("title", [])
    title = title_list[0] if isinstance(title_list, list) and title_list else item.get("title", "")

    published_print = item.get("published-print")
    if isinstance(published_print, dict):
        date_parts = published_print.get("date-parts", [[]])[0]
    else:
        date_parts = None
    publication_date = "-".join(str(p) for p in date_parts) if isinstance(date_parts, list) and date_parts else None

    normalized = {
        "title": title,
        "year": year,
        "publication_date": publication_date,
        "venue": item.get("container-title", [""])[0]
        if isinstance(item.get("container-title"), list)
        else item.get("container-title"),
        "authors": [a.model_dump(mode="json") for a in authors],
        "abstract": item.get("abstract"),
        "identifiers": ids,
        "publication_types": [item.get("type")] if item.get("type") else [],
        "keywords": item.get("subject", []),
    }

    return SourceRecord(
        source=CROSSREF_SOURCE,
        source_record_id=ids.get("doi") or item.get("URL", ""),
        retrieved_at=now_iso(),
        raw_record=item,
        normalized_fields=normalized,
        identifiers=ids,
        source_terms_url=CROSSREF_TERMS_URL,
        usage_note="Crossref polite pool recommended; set CROSSREF_EMAIL for higher reliability.",
    )


@register(CROSSREF_SOURCE)
class CrossrefAdapter(SourceAdapter):
    """Search and retrieve works from Crossref."""

    name = CROSSREF_SOURCE
    source_terms_url = CROSSREF_TERMS_URL
    usage_note = "Crossref API is no-key usable; polite pool with email is recommended."

    def __init__(self, email: str | None = None):
        cfg = load_config()
        self.email = email or cfg.get("crossref_email")
        headers = {"User-Agent": default_user_agent()}
        if self.email:
            headers["User-Agent"] = f"{default_user_agent()} (mailto:{self.email})"
        self.http = HTTPClient(timeout=30.0, headers=headers)

    async def aclose(self) -> None:
        await self.http.aclose()

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.email:
            params["mailto"] = self.email
        if extra:
            params.update(extra)
        return params

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        limit = min(max(filters.limit, 1), 100)
        params = self._params({"query": query, "rows": limit, "sort": "relevance", "order": "desc"})
        if filters.year:
            params["filter"] = f"from_pub_date:{filters.year},until_pub_date:{filters.year}"
        resp = await self.http.get(f"{CROSSREF_BASE}/works", params=params)
        if resp.status_code >= 400:
            return []
        data = resp.json()
        items = data.get("message", {}).get("items", [])
        return [_parse_message(item) for item in items]

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        if identifier.type.value == "doi":
            doi = identifier.normalized or normalize_doi(identifier.value)
        else:
            return None
        if not doi:
            return None
        resp = await self.http.get(f"{CROSSREF_BASE}/works/{doi}", params=self._params())
        if resp.status_code >= 400:
            return None
        item = resp.json().get("message", {})
        if not item:
            return None
        return _parse_message(item)

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            resp = await self.http.get(f"{CROSSREF_BASE}/works", params=self._params({"rows": 1}))
            if resp.status_code == 200:
                return self._make_status(
                    SourceState.AVAILABLE,
                    key_configured=bool(self.email),
                    message="Crossref API responded to a probe query.",
                )
            return self._make_status(
                SourceState.DEGRADED,
                key_configured=bool(self.email),
                message=f"Crossref probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                key_configured=bool(self.email),
                message=f"Crossref probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
