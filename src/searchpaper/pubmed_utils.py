"""PubMed utility workflows outside the generic literature adapter."""

from __future__ import annotations

from typing import Any

from searchpaper.config import load_config
from searchpaper.http import HTTPClient

NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_IDCONV = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
MESH_LOOKUP = "https://id.nlm.nih.gov/mesh/lookup/descriptor"


def _ncbi_params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config()
    params: dict[str, Any] = {"retmode": "json"}
    if cfg.get("ncbi_api_key"):
        params["api_key"] = cfg["ncbi_api_key"]
    if extra:
        params.update(extra)
    return params


def _safe_json(resp: Any) -> dict[str, Any] | None:
    try:
        return resp.json()
    except Exception:
        return None


async def lookup_mesh(term: str, limit: int = 10) -> list[dict[str, Any]]:
    http = HTTPClient(timeout=30.0)
    try:
        resp = await http.get(MESH_LOOKUP, params={"label": term, "match": "contains", "limit": limit})
        if resp.status_code >= 400:
            return []
        data = _safe_json(resp)
        return data if isinstance(data, list) else []
    finally:
        await http.aclose()


async def related_articles(pmid: str, limit: int = 20) -> list[str]:
    http = HTTPClient(timeout=30.0)
    try:
        resp = await http.get(
            f"{NCBI_EUTILS}/elink.fcgi",
            params=_ncbi_params({"dbfrom": "pubmed", "db": "pubmed", "id": pmid, "cmd": "neighbor"}),
        )
        if resp.status_code >= 400:
            return []
        data = _safe_json(resp) or {}
    finally:
        await http.aclose()
    links: list[str] = []
    for linkset in data.get("linksets", []):
        for linksetdb in linkset.get("linksetdbs", []):
            links.extend(str(link) for link in linksetdb.get("links", []))
    return links[:limit]


async def convert_ids(identifiers: list[str]) -> dict[str, Any]:
    """Convert DOI/PMID/PMCID identifiers through the NCBI ID converter.

    Returns a structured envelope so callers can distinguish records from errors.
    """
    if not identifiers:
        return {"records": [], "warnings": ["No identifiers provided"]}

    http = HTTPClient(timeout=30.0)
    try:
        resp = await http.get(NCBI_IDCONV, params={"ids": ",".join(identifiers), "format": "json"})
        if resp.status_code >= 400:
            return {
                "records": [],
                "warnings": [f"NCBI ID converter returned HTTP {resp.status_code}: {resp.text[:200]}"],
            }
        data = _safe_json(resp)
        if data is None:
            return {
                "records": [],
                "warnings": ["NCBI ID converter returned non-JSON response"],
            }
        return {
            "records": data.get("records", []),
            "warnings": [],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "records": [],
            "warnings": [f"NCBI ID converter request failed: {type(exc).__name__}: {exc}"],
        }
    finally:
        await http.aclose()
