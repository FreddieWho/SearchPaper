"""OpenAlex adapter for SearchPaper."""

from __future__ import annotations

from typing import Any

from searchpaper.config import default_user_agent, load_config
from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_doi, normalize_openalex
from searchpaper.schemas import Author, SearchFilters, SourceRecord, SourceState, SourceStatus, WorkIdentifier
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso
from searchpaper.sources.registry import register

OPENALEX_BASE = "https://api.openalex.org"
OPENALEX_SOURCE = "openalex"
OPENALEX_TERMS_URL = "https://openalex.org/about"


def _parse_authors(authorships: list[dict[str, Any]]) -> list[Author]:
    authors: list[Author] = []
    for auth in authorships:
        if not isinstance(auth, dict):
            continue
        author_obj = auth.get("author") or {}
        name = author_obj.get("display_name") or ""
        if not name:
            continue
        authors.append(
            Author(
                name=name,
                orcid=author_obj.get("orcid"),
                affiliations=[
                    inst.get("display_name", "") for inst in auth.get("institutions", []) if isinstance(inst, dict)
                ],
            )
        )
    return authors


def _extract_identifiers(work: dict[str, Any]) -> dict[str, str]:
    ids: dict[str, str] = {}
    doi = work.get("doi")
    if doi:
        ids["doi"] = normalize_doi(doi) or doi.lower().strip()
    ids["openalex"] = work.get("id", "").rsplit("/", 1)[-1]
    pmid_val = work.get("ids", {}).get("pmid")
    if pmid_val:
        ids["pmid"] = str(pmid_val).rsplit("/", 1)[-1]
    pmcid_val = work.get("ids", {}).get("pmcid")
    if pmcid_val:
        ids["pmcid"] = str(pmcid_val).rsplit("/", 1)[-1]
    return ids


def _parse_work(work: dict[str, Any]) -> SourceRecord:
    ids = _extract_identifiers(work)
    authors = _parse_authors(work.get("authorships", []))
    year = work.get("publication_year")

    normalized = {
        "title": work.get("display_title") or work.get("title"),
        "year": year,
        "publication_date": work.get("publication_date"),
        "venue": work.get("primary_location", {}).get("source", {}).get("display_name")
        if isinstance(work.get("primary_location"), dict)
        else None,
        "authors": [a.model_dump(mode="json") for a in authors],
        "abstract": work.get("abstract"),
        "identifiers": ids,
        "citation_count": work.get("cited_by_count"),
        "publication_types": [work.get("type")] if work.get("type") else [],
        "concepts": [c.get("display_name") for c in work.get("concepts", []) if isinstance(c, dict)],
    }

    return SourceRecord(
        source=OPENALEX_SOURCE,
        source_record_id=ids.get("openalex") or work.get("id", ""),
        retrieved_at=now_iso(),
        raw_record=work,
        normalized_fields=normalized,
        identifiers=ids,
        source_terms_url=OPENALEX_TERMS_URL,
        usage_note="OpenAlex API is no-key usable; provide email for polite pool.",
    )


@register(OPENALEX_SOURCE)
class OpenAlexAdapter(SourceAdapter):
    """Search and retrieve works from OpenAlex."""

    name = OPENALEX_SOURCE
    source_terms_url = OPENALEX_TERMS_URL
    usage_note = "OpenAlex API is no-key usable; set OPENALEX_EMAIL for polite pool."

    def __init__(self, email: str | None = None):
        cfg = load_config()
        self.email = email or cfg.get("openalex_email")
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

    def _safe_json(self, resp: Any) -> dict[str, Any] | None:
        try:
            data = resp.json()
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        limit = min(max(filters.limit, 1), 200)
        params = self._params({"search": query, "per-page": limit})
        if filters.year:
            params["filter"] = f"publication_year:{filters.year}"
        resp = await self.http.get(f"{OPENALEX_BASE}/works", params=params)
        resp.raise_for_status()
        data = self._safe_json(resp)
        if data is None:
            raise ValueError("OpenAlex returned non-JSON response")
        results = data.get("results", []) or []
        return [_parse_work(w) for w in results if isinstance(w, dict)]

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        url: str | None = None
        if identifier.type.value == "openalex":
            oa_id = normalize_openalex(identifier.value)
            url = f"{OPENALEX_BASE}/works/{oa_id}"
        elif identifier.type.value == "doi":
            doi = normalize_doi(identifier.value)
            url = f"{OPENALEX_BASE}/works/doi:{doi}"
        else:
            return None

        if not url:
            return None
        resp = await self.http.get(url, params=self._params())
        resp.raise_for_status()
        data = self._safe_json(resp)
        if data is None:
            raise ValueError("OpenAlex returned non-JSON response")
        return _parse_work(data)

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            resp = await self.http.get(f"{OPENALEX_BASE}/works", params=self._params({"per-page": 1}))
            if resp.status_code == 200:
                return self._make_status(
                    SourceState.AVAILABLE,
                    key_configured=bool(self.email),
                    message="OpenAlex API responded to a probe query.",
                )
            return self._make_status(
                SourceState.DEGRADED,
                key_configured=bool(self.email),
                message=f"OpenAlex probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                key_configured=bool(self.email),
                message=f"OpenAlex probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
