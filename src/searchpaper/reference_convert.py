"""Batch reference file conversion helpers."""

from __future__ import annotations

from pathlib import Path

from searchpaper.export import works_to_format
from searchpaper.identifiers import normalize_arxiv, normalize_doi, normalize_pmid


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


def parse_refs_file(path: Path) -> list[dict]:
    """Parse a simple refs.txt file into placeholder works for citation export."""
    works: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        key = key.lower().strip()
        value = value.strip()
        if key == "doi" and (doi := normalize_doi(value)):
            works.append(_work_from_identifier("doi", doi))
        elif key == "pmid" and (pmid := normalize_pmid(value)):
            works.append(_work_from_identifier("pmid", pmid))
        elif key == "arxiv" and (arxiv := normalize_arxiv(value)):
            works.append(_work_from_identifier("arxiv", arxiv))
    return works


def convert_refs_file(input_file: Path, format: str) -> str:
    return works_to_format(parse_refs_file(input_file), format)
