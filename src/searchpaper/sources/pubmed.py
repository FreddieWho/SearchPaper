"""PubMed / NCBI E-utilities adapter for SearchPaper."""

from __future__ import annotations

from typing import Any

from searchpaper.config import load_config
from searchpaper.http import HTTPClient
from searchpaper.identifiers import (
    normalize_pmid,
)
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

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_SOURCE = "pubmed"
PUBMED_TERMS_URL = "https://www.ncbi.nlm.nih.gov/home/about/policies/"


def _extract_authors(authors: list[dict[str, Any]]) -> list[Author]:
    result: list[Author] = []
    for a in authors:
        if not isinstance(a, dict):
            continue
        name = a.get("Name") or a.get("name") or ""
        if not name:
            continue
        result.append(
            Author(
                name=name,
                first_name=a.get("ForeName"),
                last_name=a.get("LastName"),
                affiliations=[a["Affiliation"]] if a.get("Affiliation") else [],
            )
        )
    return result


def _extract_identifiers(articleids: list[dict[str, Any]]) -> dict[str, str]:
    ids: dict[str, str] = {}
    for item in articleids:
        if not isinstance(item, dict):
            continue
        idtype = item.get("idtype", "").lower()
        value = item.get("value")
        if not value:
            continue
        if idtype == "doi":
            ids["doi"] = value.lower().strip()
        elif idtype == "pubmed":
            ids["pmid"] = value
        elif idtype == "pmc":
            ids["pmcid"] = f"PMC{value.replace('PMC', '').upper()}"
    return ids


def _parse_summary(uid: str, doc: dict[str, Any]) -> SourceRecord:
    ids = _extract_identifiers(doc.get("articleids", []))
    ids.setdefault("pmid", uid)
    title = doc.get("title") or ""
    # PubMed titles often end with a period; keep original but normalize separately.
    authors_raw = doc.get("authors", [])
    authors = _extract_authors(authors_raw)
    mesh = doc.get("meshterms") or []
    if isinstance(mesh, str):
        mesh = [m.strip() for m in mesh.split(";") if m.strip()]

    normalized = {
        "title": title,
        "year": doc.get("pubdate", "")[:4] if doc.get("pubdate") else None,
        "publication_date": doc.get("pubdate"),
        "venue": doc.get("fulljournalname") or doc.get("source"),
        "authors": [a.model_dump(mode="json") for a in authors],
        "abstract": doc.get("abstracttext") or doc.get("abstract"),
        "identifiers": ids,
        "keywords": doc.get("keywords") or [],
        "mesh_terms": mesh,
        "publication_types": doc.get("pubtype") if isinstance(doc.get("pubtype"), list) else [],
    }

    return SourceRecord(
        source=PUBMED_SOURCE,
        source_record_id=uid,
        retrieved_at=now_iso(),
        raw_record=doc,
        normalized_fields=normalized,
        identifiers=ids,
        source_terms_url=PUBMED_TERMS_URL,
        usage_note="NCBI E-utilities; no API key required, but an NCBI API key increases rate limits.",
    )


@register(PUBMED_SOURCE)
class PubMedAdapter(SourceAdapter):
    """Search and retrieve records from PubMed via NCBI E-utilities."""

    name = PUBMED_SOURCE
    source_terms_url = PUBMED_TERMS_URL
    usage_note = "NCBI E-utilities; no API key required. Respect NCBI rate limits."

    def __init__(self, api_key: str | None = None, email: str | None = None):
        cfg = load_config()
        self.api_key = api_key or cfg.get("ncbi_api_key")
        self.email = email or cfg.get("ncbi_email")
        self.http = HTTPClient(timeout=30.0)

    async def aclose(self) -> None:
        await self.http.aclose()

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"retmode": "json"}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        if extra:
            params.update(extra)
        return params

    async def _esearch(self, term: str, retmax: int = 20) -> dict[str, Any]:
        params = self._params({"db": "pubmed", "term": term, "retmax": retmax, "sort": "relevance"})
        resp = await self.http.get(f"{NCBI_BASE}/esearch.fcgi", params=params)
        return resp.json()

    async def _esummary(self, ids: list[str]) -> dict[str, Any]:
        params = self._params({"db": "pubmed", "id": ",".join(ids)})
        resp = await self.http.get(f"{NCBI_BASE}/esummary.fcgi", params=params)
        return resp.json()

    async def _do_search(self, term: str, limit: int) -> list[SourceRecord]:
        search_data = await self._esearch(term, retmax=limit)
        idlist = search_data.get("esearchresult", {}).get("idlist", [])
        if not idlist:
            return []
        summary_data = await self._esummary(idlist)
        result = summary_data.get("result", {})
        records: list[SourceRecord] = []
        for uid in idlist:
            doc = result.get(uid)
            if not doc:
                continue
            rec = _parse_summary(uid, doc)
            rec.query_or_identifier = term
            records.append(rec)
        return records

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        limit = min(max(filters.limit, 1), 200)
        return await self._do_search(query, limit)

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        if identifier.type.value == "pmid":
            pmid = normalize_pmid(identifier.value)
        elif identifier.type.value == "doi":
            # PubMed supports DOI search via ESearch; fetch the first matching PMID.
            data = await self._esearch(f"{identifier.value}[doi]", retmax=1)
            idlist = data.get("esearchresult", {}).get("idlist", [])
            if not idlist:
                return None
            pmid = idlist[0]
        else:
            return None

        if not pmid:
            return None
        summary = await self._esummary([pmid])
        doc = summary.get("result", {}).get(pmid)
        if not doc:
            return None
        rec = _parse_summary(pmid, doc)
        rec.query_or_identifier = identifier.value
        return rec

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            data = await self._esearch("test", retmax=1)
            if "esearchresult" in data:
                return self._make_status(
                    SourceState.AVAILABLE,
                    key_configured=bool(self.api_key),
                    message="PubMed E-utilities responded to a probe query.",
                )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                key_configured=bool(self.api_key),
                message=f"PubMed probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
        return self._make_status(
            SourceState.DEGRADED,
            key_configured=bool(self.api_key),
            message="PubMed returned an unexpected probe response.",
        )
