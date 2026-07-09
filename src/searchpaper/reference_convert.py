"""Batch reference file conversion helpers.

Supports refs.txt files with identifier lines (DOI/PMID/arXiv), query lines,
and author+title combinations. Query results are resolved through the
SearchPaper engine so that exported citation formats contain real metadata.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from searchpaper.engine import SearchEngine
from searchpaper.export import works_to_format
from searchpaper.identifiers import identify, normalize_arxiv, normalize_doi, normalize_pmid
from searchpaper.schemas import SearchFilters


def _work_from_identifier(kind: str, value: str) -> dict:
    identifiers: dict[str, str] = {}
    if kind == "doi":
        identifiers["doi"] = value
    elif kind == "pmid":
        identifiers["pmid"] = value
    elif kind == "arxiv":
        identifiers["arxiv"] = value
    return {
        "title": f"Reference {value}",
        "authors": [],
        "identifiers": identifiers,
        "publication_types": ["journal-article"],
    }


def _extract_work_from_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize a search/resolve result work into a plain dict for export."""
    if isinstance(record, dict):
        return record
    return record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record)


async def _resolve_identifier(engine: SearchEngine, kind: str, value: str) -> dict[str, Any] | None:
    """Resolve an identifier through the engine and return the first work."""
    wid = identify(value)
    if not wid:
        return None
    result = await engine.resolve(wid, sources=["pubmed", "crossref", "openalex"])
    data = result.data if hasattr(result, "data") else result.get("data", {})
    works = data.get("works", []) if isinstance(data, dict) else []
    if works:
        return _extract_work_from_record(works[0])
    return None


async def _search_query(engine: SearchEngine, query: str) -> dict[str, Any] | None:
    """Run a query through the engine and return the first work."""
    result = await engine.search(query, filters=SearchFilters(limit=1), sources=["pubmed", "crossref", "openalex"])
    data = result.data if hasattr(result, "data") else result.get("data", {})
    works = data.get("works", []) if isinstance(data, dict) else []
    if works:
        return _extract_work_from_record(works[0])
    return None


async def _parse_refs_file(path: Path, engine: SearchEngine | None = None) -> list[dict[str, Any]]:
    """Parse a refs.txt file into works, resolving queries and identifiers.

    Lines may be:
      - DOI:10.xxx
      - PMID:12345
      - ARXIV:1706.03762
      - QUERY:TB-Profiler AND Bioinformatics[Journal]
      - AUTHOR:Dheda TITLE:drug-resistant tuberculosis
      - # comments
    """
    engine = engine or SearchEngine()
    works: list[dict[str, Any]] = []
    pending_author: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        key, _, value = line.partition(":")
        key = key.lower().strip()
        value = value.strip()

        if key == "doi" and (doi := normalize_doi(value)):
            work = await _resolve_identifier(engine, "doi", doi) or _work_from_identifier("doi", doi)
            works.append(work)
        elif key == "pmid" and (pmid := normalize_pmid(value)):
            work = await _resolve_identifier(engine, "pmid", pmid) or _work_from_identifier("pmid", pmid)
            works.append(work)
        elif key == "arxiv" and (arxiv := normalize_arxiv(value)):
            work = await _resolve_identifier(engine, "arxiv", arxiv) or _work_from_identifier("arxiv", arxiv)
            works.append(work)
        elif key == "query" and value:
            work = await _search_query(engine, value)
            if work:
                works.append(work)
        elif key == "author" and value:
            pending_author = value
        elif key == "title" and value:
            query = value
            if pending_author:
                query = f"{pending_author} {query}"
                pending_author = None
            work = await _search_query(engine, query)
            if work:
                works.append(work)

    return works


def convert_refs_file(input_file: Path, format: str) -> str:
    """Convert refs.txt identifiers to citation formats with metadata enrichment."""
    works = asyncio.run(_parse_refs_file(input_file))
    return works_to_format(works, format)
