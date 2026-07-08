"""Semantic Scholar adapter for SearchPaper."""

from __future__ import annotations

from typing import Any

from searchpaper.config import load_config
from searchpaper.http import HTTPClient
from searchpaper.identifiers import (
    identifiers_from_dict,
    normalize_doi,
)
from searchpaper.schemas import Author, SearchFilters, SourceRecord, SourceState, SourceStatus, WorkIdentifier
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso
from searchpaper.sources.registry import register

S2_GRAPH_BASE = "https://api.semanticscholar.org/graph/v1"
S2_SOURCE = "semantic_scholar"
S2_TERMS_URL = "https://www.semanticscholar.org/product/api"

DEFAULT_FIELDS = [
    "paperId",
    "title",
    "year",
    "publicationDate",
    "url",
    "venue",
    "citationCount",
    "influentialCitationCount",
    "authors",
    "externalIds",
    "openAccessPdf",
    "publicationTypes",
    "fieldsOfStudy",
]


def _normalize_paper(raw: dict[str, Any]) -> SourceRecord:
    ext = raw.get("externalIds") or {}
    authors = []
    for a in raw.get("authors") or []:
        if isinstance(a, dict):
            authors.append(Author(name=a.get("name", ""), source_ids={"s2": a.get("authorId")}))
    oa = raw.get("openAccessPdf")
    open_access_pdf: dict[str, Any] | None = None
    if isinstance(oa, dict):
        open_access_pdf = {"url": oa.get("url"), "status": oa.get("status")}
    tldr = raw.get("tldr")
    tldr_text = tldr.get("text") if isinstance(tldr, dict) else None

    ids = identifiers_from_dict(
        {
            "doi": ext.get("DOI"),
            "pmid": ext.get("PubMed"),
            "pmcid": ext.get("PMCID"),
            "arxiv": ext.get("ArXiv"),
            "semantic_scholar": raw.get("paperId"),
        }
    )

    normalized = {
        "title": raw.get("title"),
        "year": raw.get("year"),
        "publication_date": raw.get("publicationDate"),
        "venue": raw.get("venue"),
        "url": raw.get("url"),
        "authors": [a.model_dump(mode="json") for a in authors],
        "abstract": raw.get("abstract"),
        "identifiers": ids,
        "citation_count": raw.get("citationCount"),
        "influential_citation_count": raw.get("influentialCitationCount"),
        "open_access_pdf": open_access_pdf,
        "fields_of_study": raw.get("fieldsOfStudy") or [],
        "publication_types": raw.get("publicationTypes") or [],
        "tldr": tldr_text,
    }

    return SourceRecord(
        source=S2_SOURCE,
        source_record_id=raw.get("paperId", ""),
        retrieved_at=now_iso(),
        raw_record=raw,
        normalized_fields=normalized,
        identifiers=ids,
        source_terms_url=S2_TERMS_URL,
        usage_note="Semantic Scholar API is no-key usable; an API key raises rate limits.",
    )


@register(S2_SOURCE)
class SemanticScholarAdapter(SourceAdapter):
    """Search and retrieve papers from Semantic Scholar."""

    name = S2_SOURCE
    source_terms_url = S2_TERMS_URL
    usage_note = "Semantic Scholar API is no-key usable; set SEMANTIC_SCHOLAR_API_KEY for higher rate limits."

    def __init__(self, api_key: str | None = None):
        cfg = load_config()
        self.api_key = api_key or cfg.get("semantic_scholar_api_key")
        self.http = HTTPClient(timeout=30.0, api_key=self.api_key, key_header="x-api-key")

    async def aclose(self) -> None:
        await self.http.aclose()

    def _build_fields(self, include_abstract: bool) -> str:
        fields = list(DEFAULT_FIELDS)
        if include_abstract:
            fields.append("abstract")
        return ",".join(fields)

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        limit = min(max(filters.limit, 1), 100)
        fields_str = self._build_fields(include_abstract=False)
        params: dict[str, Any] = {"query": query, "fields": fields_str, "limit": limit}
        if filters.year:
            params["year"] = filters.year
        if filters.venue:
            params["venue"] = filters.venue
        if filters.fields_of_study:
            params["fieldsOfStudy"] = ",".join(filters.fields_of_study)
        if filters.publication_types:
            params["publicationTypes"] = ",".join(filters.publication_types)
        if filters.min_citation_count is not None:
            params["minCitationCount"] = filters.min_citation_count
        if filters.open_access_only:
            params["openAccessPdf"] = "true"
        if filters.sort:
            params["sort"] = filters.sort

        resp = await self.http.get(f"{S2_GRAPH_BASE}/paper/search", params=params)
        if resp.status_code >= 400:
            return []
        data = resp.json()
        return [_normalize_paper(i) for i in data.get("data", [])]

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        paper_id: str | None = None
        if identifier.type.value == "semantic_scholar":
            paper_id = identifier.value
        elif identifier.type.value == "doi":
            paper_id = f"DOI:{normalize_doi(identifier.value)}"
        elif identifier.type.value == "pmid":
            paper_id = f"PMID:{identifier.value}"
        else:
            return None

        fields_str = self._build_fields(include_abstract=True)
        resp = await self.http.get(f"{S2_GRAPH_BASE}/paper/{paper_id}", params={"fields": fields_str})
        if resp.status_code >= 400:
            return None
        return _normalize_paper(resp.json())

    async def _resolve_paper_id(self, identifier: WorkIdentifier) -> str | None:
        """Return a canonical S2 paperId for the identifier, using S2 lookup if needed."""
        if identifier.type.value == "semantic_scholar":
            return identifier.value
        rec = await self.get(identifier)
        if rec is None:
            return None
        return rec.raw_record.get("paperId") or rec.source_record_id

    async def _fetch_paper_list(
        self, url: str, params: dict[str, Any] | None = None, nested_key: str | None = None
    ) -> list[SourceRecord]:
        """Fetch a list of papers from an S2 endpoint and normalize results."""
        try:
            resp = await self.http.get(url, params=params)
            if resp.status_code >= 400:
                return []
            data = resp.json()
            if not isinstance(data, dict):
                return []
            items: list[dict[str, Any]] = []
            if nested_key:
                for wrapper in data.get("data", []):
                    if isinstance(wrapper, dict) and isinstance(wrapper.get(nested_key), dict):
                        items.append(wrapper[nested_key])
            else:
                items = data.get("data", [])
            return [_normalize_paper(i) for i in items if isinstance(i, dict)]
        except Exception:
            return []

    async def get_citations(self, identifier: WorkIdentifier, limit: int = 20) -> list[SourceRecord]:
        paper_id = await self._resolve_paper_id(identifier)
        if not paper_id:
            return []
        return await self._fetch_paper_list(
            f"{S2_GRAPH_BASE}/paper/{paper_id}/citations",
            params={"fields": self._build_fields(include_abstract=False), "limit": limit},
            nested_key="citingPaper",
        )

    async def get_references(self, identifier: WorkIdentifier, limit: int = 20) -> list[SourceRecord]:
        paper_id = await self._resolve_paper_id(identifier)
        if not paper_id:
            return []
        return await self._fetch_paper_list(
            f"{S2_GRAPH_BASE}/paper/{paper_id}/references",
            params={"fields": self._build_fields(include_abstract=False), "limit": limit},
            nested_key="citedPaper",
        )

    async def get_recommendations(self, identifier: WorkIdentifier, limit: int = 20) -> list[SourceRecord]:
        paper_id = await self._resolve_paper_id(identifier)
        if not paper_id:
            return []
        try:
            resp = await self.http.post(
                f"{S2_GRAPH_BASE}/paper/recommendations",
                params={"fields": self._build_fields(include_abstract=False), "limit": limit},
                json={"positivePaperIds": [paper_id]},
            )
            if resp.status_code >= 400:
                return []
            data = resp.json()
            if not isinstance(data, dict):
                return []
            papers = data.get("recommendedPapers", [])
            return [_normalize_paper(p) for p in papers if isinstance(p, dict)]
        except Exception:
            return []

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            resp = await self.http.get(
                f"{S2_GRAPH_BASE}/paper/search",
                params={"query": "test", "fields": "paperId", "limit": 1},
            )
            if resp.status_code == 200:
                return self._make_status(
                    SourceState.AVAILABLE_WITH_KEY_OPTIONAL,
                    key_configured=bool(self.api_key),
                    message="Semantic Scholar API responded to a probe query.",
                )
            return self._make_status(
                SourceState.DEGRADED,
                key_configured=bool(self.api_key),
                message=f"Semantic Scholar probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                key_configured=bool(self.api_key),
                message=f"Semantic Scholar probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
