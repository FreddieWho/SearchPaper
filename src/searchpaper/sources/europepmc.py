"""Europe PMC adapter for SearchPaper.

Europe PMC provides life-science literature enrichment. The adapter is
implemented with the full contract and fixture-backed tests; if the live
endpoint is unstable during a run it reports ``degraded`` and does not block
multi-source search.
"""

from __future__ import annotations

from typing import Any

from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_doi, normalize_pmcid, normalize_pmid
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

EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
EUROPEPMC_SOURCE = "europepmc"
EUROPEPMC_TERMS_URL = "https://europepmc.org/Libraries"


def _parse_result(item: dict[str, Any]) -> SourceRecord:
    ids: dict[str, str] = {}
    if item.get("doi"):
        ids["doi"] = normalize_doi(item["doi"]) or item["doi"].lower().strip()
    if item.get("pmid"):
        ids["pmid"] = str(item["pmid"])
    if item.get("pmcid"):
        ids["pmcid"] = normalize_pmcid(str(item["pmcid"])) or str(item["pmcid"])
    if item.get("id"):
        ids["europepmc"] = str(item["id"])

    authors_raw = item.get("authorString", "")
    if isinstance(authors_raw, str):
        authors = [Author(name=n.strip()) for n in authors_raw.split(",") if n.strip()]
    else:
        authors = []

    year = item.get("pubYear")
    if isinstance(year, str) and year.isdigit():
        year = int(year)

    normalized = {
        "title": item.get("title"),
        "year": year,
        "publication_date": item.get("firstPublicationDate") or item.get("pubYear"),
        "venue": item.get("journalTitle") or item.get("journal"),
        "authors": [a.model_dump(mode="json") for a in authors],
        "abstract": item.get("abstractText"),
        "identifiers": ids,
        "publication_types": [item.get("pubType")] if item.get("pubType") else [],
        "open_access": bool(item.get("isOpenAccess") == "Y"),
    }

    return SourceRecord(
        source=EUROPEPMC_SOURCE,
        source_record_id=ids.get("europepmc") or ids.get("pmid") or ids.get("pmcid") or item.get("id", ""),
        retrieved_at=now_iso(),
        raw_record=item,
        normalized_fields=normalized,
        identifiers=ids,
        source_terms_url=EUROPEPMC_TERMS_URL,
        usage_note="Europe PMC REST API; no API key required for search.",
    )


@register(EUROPEPMC_SOURCE)
class EuropePMCAdapter(SourceAdapter):
    """Search and retrieve records from Europe PMC."""

    name = EUROPEPMC_SOURCE
    source_terms_url = EUROPEPMC_TERMS_URL
    usage_note = "Europe PMC REST API; no API key required."

    def __init__(self) -> None:
        self.http = HTTPClient(timeout=30.0)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        limit = min(max(filters.limit, 1), 100)
        params: dict[str, Any] = {"query": query, "format": "json", "pageSize": limit}
        if filters.year:
            params["query"] = f"{query} AND FIRST_PDATE:{filters.year}"
        resp = await self.http.get(f"{EUROPEPMC_BASE}/search", params=params)
        if resp.status_code >= 400:
            return []
        data = resp.json()
        return [_parse_result(r) for r in data.get("resultList", {}).get("result", [])]

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        if identifier.type.value == "pmid":
            pmid = normalize_pmid(identifier.value)
            url = f"{EUROPEPMC_BASE}/MED/{pmid}"
        elif identifier.type.value == "pmcid":
            pmcid = normalize_pmcid(identifier.value)
            url = f"{EUROPEPMC_BASE}/PMC/{pmcid}"
        elif identifier.type.value == "doi":
            doi = normalize_doi(identifier.value)
            url = f"{EUROPEPMC_BASE}/DOI/{doi}"
        else:
            return None

        resp = await self.http.get(url, params={"format": "json"})
        if resp.status_code >= 400:
            return None
        data = resp.json()
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return None
        return _parse_result(results[0])

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            resp = await self.http.get(
                f"{EUROPEPMC_BASE}/search",
                params={"query": "test", "format": "json", "pageSize": 1},
            )
            if resp.status_code == 200:
                return self._make_status(
                    SourceState.AVAILABLE,
                    message="Europe PMC API responded to a probe query.",
                )
            return self._make_status(
                SourceState.DEGRADED,
                message=(
                    f"Europe PMC probe returned HTTP {resp.status_code}; "
                    "fixture-backed adapter contract is preserved."
                ),
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                message=(
                    f"Europe PMC probe failed: {exc}; "
                    "fixture-backed adapter contract is preserved."
                ),
                last_error_class=classify_http_error(0, exc),
            )
