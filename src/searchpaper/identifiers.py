"""Identifier parsing and normalization for scholarly IDs."""

from __future__ import annotations

import re
from typing import Any

from searchpaper.schemas import IdentifierType, WorkIdentifier

_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s]+")
_PMID_PATTERN = re.compile(r"^\d{1,10}$")
_PMCID_PATTERN = re.compile(r"^PMC\d+$")
_ARXIV_PATTERN = re.compile(r"^\d{4}\.\d{4,5}$|^arXiv:\d{4}\.\d{4,5}(v\d+)?$", re.IGNORECASE)
_S2_PATTERN = re.compile(r"^[a-f0-9]{40}$", re.IGNORECASE)
_OPENALEX_PATTERN = re.compile(r"^W\d+$")


def _clean(value: str) -> str:
    return value.strip().lower()


def normalize_doi(value: str) -> str | None:
    """Extract and normalize a DOI string."""
    value = value.strip()
    if value.lower().startswith("doi:"):
        value = value[4:].strip()
    match = _DOI_PATTERN.search(value)
    return match.group(0).lower() if match else None


def normalize_pmid(value: str) -> str | None:
    """Normalize a PubMed ID."""
    value = value.strip()
    if value.lower().startswith("pmid:"):
        value = value[5:].strip()
    return value if _PMID_PATTERN.match(value) else None


def normalize_pmcid(value: str) -> str | None:
    """Normalize a PubMed Central ID."""
    value = value.strip().upper()
    if value.startswith("PMC") and value[3:4].isdigit():
        return value
    if value.startswith("PMCID:"):
        return "PMC" + value[6:].strip()
    return None


def normalize_arxiv(value: str) -> str | None:
    """Normalize an arXiv ID."""
    value = value.strip()
    if value.lower().startswith("arxiv:"):
        value = value[6:].strip()
    return value.lower() if _ARXIV_PATTERN.match(value) else None


def normalize_semantic_scholar(value: str) -> str | None:
    value = value.strip()
    return value if _S2_PATTERN.match(value) else None


def normalize_openalex(value: str) -> str | None:
    value = value.strip()
    return value if _OPENALEX_PATTERN.match(value) else None


def identify(value: str, source: str | None = None) -> WorkIdentifier | None:
    """Infer identifier type from a raw string."""
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    if doi := normalize_doi(value):
        return WorkIdentifier(type=IdentifierType.DOI, value=doi, source=source)
    if pmcid := normalize_pmcid(value):
        return WorkIdentifier(type=IdentifierType.PMCID, value=pmcid, source=source)
    if pmid := normalize_pmid(value):
        return WorkIdentifier(type=IdentifierType.PMID, value=pmid, source=source)
    if arxiv := normalize_arxiv(value):
        return WorkIdentifier(type=IdentifierType.ARXIV, value=arxiv, source=source)
    if s2 := normalize_semantic_scholar(value):
        return WorkIdentifier(type=IdentifierType.SEMANTIC_SCHOLAR, value=s2, source=source)
    if oa := normalize_openalex(value):
        return WorkIdentifier(type=IdentifierType.OPENALEX, value=oa, source=source)

    return WorkIdentifier(type=IdentifierType.SOURCE_SPECIFIC, value=value, source=source)


def identifiers_from_dict(data: dict[str, Any]) -> dict[str, str]:
    """Extract normalized identifiers from a dictionary of source IDs."""
    ids: dict[str, str] = {}
    for key, val in data.items():
        if not val:
            continue
        key_norm = key.lower().strip()
        if key_norm in ("doi",) and (norm := normalize_doi(str(val))):
            ids["doi"] = norm
        elif key_norm in ("pmid", "pubmed") and (norm := normalize_pmid(str(val))):
            ids["pmid"] = norm
        elif key_norm in ("pmcid",) and (norm := normalize_pmcid(str(val))):
            ids["pmcid"] = norm
        elif key_norm in ("arxiv",) and (norm := normalize_arxiv(str(val))):
            ids["arxiv"] = norm
        elif key_norm in ("semantic_scholar", "s2", "paperid", "paper_id") and (
            norm := normalize_semantic_scholar(str(val))
        ):
            ids["semantic_scholar"] = norm
        elif key_norm in ("openalex", "openalex_id") and (norm := normalize_openalex(str(val))):
            ids["openalex"] = norm
        else:
            ids[key_norm] = str(val)
    return ids


def work_id_from_identifiers(identifiers: dict[str, str]) -> str:
    """Create a deterministic internal work ID from identifiers."""
    for key in ("doi", "pmid", "pmcid", "arxiv", "semantic_scholar", "openalex"):
        if key in identifiers:
            return f"work:{key}:{identifiers[key]}"
    return "work:unknown"


def normalize_title(title: str | None) -> str | None:
    """Normalize a title for comparison."""
    if not title:
        return None
    normalized = re.sub(r"[^\w\s]", "", title.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
