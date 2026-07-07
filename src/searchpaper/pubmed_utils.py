"""PubMed utility workflows outside the generic literature adapter."""

from __future__ import annotations

from typing import Any

from searchpaper.config import load_config
from searchpaper.http import HTTPClient

NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_IDCONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
MESH_LOOKUP = "https://id.nlm.nih.gov/mesh/lookup/descriptor"


def _ncbi_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config()
    params: dict[str, Any] = {"retmode": "json"}
    if cfg.get("ncbi_api_key"):
        params["api_key"] = cfg["ncbi_api_key"]
    if extra:
        params.update(extra)
    return params


async def lookup_mesh(term: str, limit: int = 10) -> list[dict[str, Any]]:
    http = HTTPClient(timeout=30.0)
    try:
        resp = await http.get(MESH_LOOKUP, params={"label": term, "match": "contains", "limit": limit})
        return resp.json()
    finally:
        await http.aclose()


async def related_articles(pmid: str, limit: int = 20) -> list[str]:
    http = HTTPClient(timeout=30.0)
    try:
        resp = await http.get(
            f"{NCBI_EUTILS}/elink.fcgi",
            params=_ncbi_params({"dbfrom": "pubmed", "db": "pubmed", "id": pmid, "cmd": "neighbor"}),
        )
        data = resp.json()
    finally:
        await http.aclose()
    links: list[str] = []
    for linkset in data.get("linksets", []):
        for linksetdb in linkset.get("linksetdbs", []):
            links.extend(str(link) for link in linksetdb.get("links", []))
    return links[:limit]


async def convert_ids(identifiers: list[str]) -> list[dict[str, Any]]:
    http = HTTPClient(timeout=30.0)
    try:
        resp = await http.get(NCBI_IDCONV, params={"ids": ",".join(identifiers), "format": "json"})
        return resp.json().get("records", [])
    finally:
        await http.aclose()
