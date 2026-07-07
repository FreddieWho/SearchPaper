"""arXiv adapter using the official Atom API."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_arxiv
from searchpaper.schemas import Author, SearchFilters, SourceRecord, SourceState, SourceStatus, WorkIdentifier
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso
from searchpaper.sources.registry import register

ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_SOURCE = "arxiv"
ARXIV_TERMS_URL = "https://info.arxiv.org/help/api/tou.html"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def _text(parent: ET.Element, name: str) -> str | None:
    element = parent.find(name)
    return element.text.strip() if element is not None and element.text else None


def _arxiv_id(entry_id: str | None) -> str:
    if not entry_id:
        return ""
    raw = entry_id.rsplit("/", 1)[-1]
    raw = re.sub(r"v\d+$", "", raw)
    return raw.lower()


def _parse_entry(entry: ET.Element) -> SourceRecord:
    entry_id = _text(entry, f"{ATOM}id")
    arxiv_id = _arxiv_id(entry_id)
    published = _text(entry, f"{ATOM}published")
    title = re.sub(r"\s+", " ", _text(entry, f"{ATOM}title") or "").strip()
    authors = [Author(name=_text(author, f"{ATOM}name") or "") for author in entry.findall(f"{ATOM}author")]
    doi = _text(entry, f"{ARXIV}doi")
    categories = [cat.attrib.get("term", "") for cat in entry.findall(f"{ATOM}category") if cat.attrib.get("term")]
    ids = {"arxiv": arxiv_id}
    if doi:
        ids["doi"] = doi.lower().strip()
    normalized: dict[str, Any] = {
        "title": title,
        "year": int(published[:4]) if published and published[:4].isdigit() else None,
        "publication_date": published[:10] if published else None,
        "venue": "arXiv",
        "authors": [author.model_dump(mode="json") for author in authors if author.name],
        "abstract": re.sub(r"\s+", " ", _text(entry, f"{ATOM}summary") or "").strip(),
        "identifiers": ids,
        "fields_of_study": categories,
        "publication_types": ["preprint"],
    }
    return SourceRecord(
        source=ARXIV_SOURCE,
        source_record_id=arxiv_id,
        retrieved_at=now_iso(),
        query_or_identifier=arxiv_id,
        raw_record={"entry_id": entry_id},
        normalized_fields=normalized,
        identifiers=ids,
        source_terms_url=ARXIV_TERMS_URL,
        usage_note="arXiv Atom API; no API key required. Respect arXiv rate limits.",
    )


@register(ARXIV_SOURCE)
class ArxivAdapter(SourceAdapter):
    name = ARXIV_SOURCE
    source_terms_url = ARXIV_TERMS_URL
    usage_note = "arXiv Atom API; no API key required. Respect arXiv rate limits."

    def __init__(self) -> None:
        self.http = HTTPClient(timeout=30.0)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _query(self, params: dict[str, Any]) -> list[SourceRecord]:
        resp = await self.http.get(ARXIV_API, params=params)
        root = ET.fromstring(resp.text)
        return [_parse_entry(entry) for entry in root.findall(f"{ATOM}entry")]

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        params = {"search_query": f"all:{query}", "start": 0, "max_results": min(filters.limit, 100)}
        return await self._query(params)

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        if identifier.type.value != "arxiv":
            return None
        arxiv_id = normalize_arxiv(identifier.value)
        if not arxiv_id:
            return None
        records = await self._query({"id_list": arxiv_id})
        return records[0] if records else None

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        record = await self.get(identifier)
        return [record] if record else []

    async def status(self) -> SourceStatus:
        try:
            resp = await self.http.get(ARXIV_API, params={"search_query": "all:test", "max_results": 1})
            if resp.status_code == 200:
                return self._make_status(SourceState.AVAILABLE, message="arXiv API responded to a probe query.")
            return self._make_status(
                SourceState.DEGRADED,
                message=f"arXiv probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.OFFLINE,
                message=f"arXiv probe failed: {exc}",
                last_error_class=classify_http_error(0, exc),
            )
