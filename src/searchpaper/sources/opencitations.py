"""OpenCitations adapter for citation relationship enrichment.

OpenCitations provides DOI-to-DOI citation links via the COCI index. This
adapter is registered as an enrichment source and is not included in the
default search source list.
"""

from __future__ import annotations

from typing import Any

from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_doi
from searchpaper.schemas import SearchFilters, SourceRecord, SourceState, SourceStatus, WorkIdentifier
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso
from searchpaper.sources.registry import register

OCOCI_BASE = "https://opencitations.net/index/coci/api/v1"
OPENCITATIONS_SOURCE = "opencitations"
OPENCITATIONS_TERMS_URL = "https://opencitations.net/"


def _parse_relation(raw: dict[str, Any], relation_type: str, subject_doi: str) -> dict[str, Any]:
    """Normalize a COCI citation/reference row into a relation record."""
    if relation_type == "citation":
        # raw cites subject_doi; citing is the source of the link.
        other = raw.get("citing")
    else:
        # subject_doi cites raw; cited is the target of the link.
        other = raw.get("cited")
    return {
        "relation_type": relation_type,
        "subject_doi": subject_doi,
        "object_doi": other,
        "oci": raw.get("oci"),
        "creation": raw.get("creation"),
        "timespan": raw.get("timespan"),
    }


@register(OPENCITATIONS_SOURCE)
class OpenCitationsAdapter(SourceAdapter):
    """Enrich DOIs with citation links from OpenCitations COCI."""

    name = OPENCITATIONS_SOURCE
    source_terms_url = OPENCITATIONS_TERMS_URL
    usage_note = "OpenCitations provides DOI-to-DOI citation links. Rate limits apply."

    def __init__(self) -> None:
        self.http = HTTPClient(timeout=30.0)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _fetch_relations(self, doi: str, endpoint: str) -> list[dict[str, Any]]:
        normalized = normalize_doi(doi)
        if not normalized:
            return []
        try:
            resp = await self.http.get(f"{OCOCI_BASE}/{endpoint}/{normalized}")
            if resp.status_code >= 400:
                return []
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception:
            return []

    async def get_citations(self, doi: str) -> list[SourceRecord]:
        """Return records representing papers that cite the given DOI."""
        rows = await self._fetch_relations(doi, "citations")
        normalized = normalize_doi(doi) or doi
        return [
            SourceRecord(
                source=OPENCITATIONS_SOURCE,
                source_record_id=row.get("oci") or f"{normalized}->cited_by->{row.get('citing')}",
                retrieved_at=now_iso(),
                query_or_identifier=normalized,
                raw_record=row,
                normalized_fields=_parse_relation(row, "citation", normalized),
                identifiers={"doi": row.get("citing", "")},
                source_terms_url=OPENCITATIONS_TERMS_URL,
                usage_note="OpenCitations citation link",
            )
            for row in rows
            if isinstance(row, dict)
        ]

    async def get_references(self, doi: str) -> list[SourceRecord]:
        """Return records representing papers cited by the given DOI."""
        rows = await self._fetch_relations(doi, "references")
        normalized = normalize_doi(doi) or doi
        return [
            SourceRecord(
                source=OPENCITATIONS_SOURCE,
                source_record_id=row.get("oci") or f"{normalized}->cites->{row.get('cited')}",
                retrieved_at=now_iso(),
                query_or_identifier=normalized,
                raw_record=row,
                normalized_fields=_parse_relation(row, "reference", normalized),
                identifiers={"doi": row.get("cited", "")},
                source_terms_url=OPENCITATIONS_TERMS_URL,
                usage_note="OpenCitations reference link",
            )
            for row in rows
            if isinstance(row, dict)
        ]

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        # COCI is DOI-only; free-text search is not supported.
        return []

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        # Return a synthetic record summarizing citation counts.
        if identifier.type.value != "doi":
            return None
        doi = normalize_doi(identifier.value)
        if not doi:
            return None
        citations = await self.get_citations(doi)
        references = await self.get_references(doi)
        return SourceRecord(
            source=OPENCITATIONS_SOURCE,
            source_record_id=doi,
            retrieved_at=now_iso(),
            query_or_identifier=doi,
            raw_record={},
            normalized_fields={
                "doi": doi,
                "citation_count": len(citations),
                "reference_count": len(references),
            },
            identifiers={"doi": doi},
            source_terms_url=OPENCITATIONS_TERMS_URL,
            usage_note="OpenCitations citation counts",
        )

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            # Probe with a well-known DOI.
            resp = await self.http.get(f"{OCOCI_BASE}/citations/10.1038/nature12373")
            if resp.status_code == 200:
                return self._make_status(SourceState.AVAILABLE, message="OpenCitations API responded to a probe query.")
            return self._make_status(
                SourceState.DEGRADED,
                message=f"OpenCitations probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                message=f"OpenCitations probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
