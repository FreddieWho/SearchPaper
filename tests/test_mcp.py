"""Mocked MCP tool tests for SearchPaper."""

import respx
from httpx import Response

from searchpaper.mcp_server import (
    convert_identifiers,
    get_source_status,
    lookup_mesh,
    plan_literature_search,
    search_literature,
)


@respx.mock
async def test_mcp_search_literature():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["12345"]}})
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "HCC Paper",
                        "pubdate": "2023",
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )
    respx.get("https://api.crossref.org/works").mock(return_value=Response(500, text="error"))
    respx.get("https://api.openalex.org/works").mock(return_value=Response(500, text="error"))

    result = await search_literature("HCC", sources=["pubmed"], limit=5)
    data = result["data"]
    assert len(data["works"]) == 1
    assert data["works"][0]["identifiers"]["pmid"] == "12345"


@respx.mock
async def test_mcp_get_source_status():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["1"]}})
    )
    respx.get("https://api.crossref.org/works").mock(return_value=Response(500, text="error"))
    respx.get("https://api.openalex.org/works").mock(return_value=Response(500, text="error"))

    result = await get_source_status()
    sources = {s["source"]: s for s in result["data"]}
    assert "pubmed" in sources
    assert sources["pubmed"]["state"] == "available"


async def test_mcp_plan_literature_search():
    result = await plan_literature_search("hepatocellular carcinoma", profile="auto", sort="combined")
    assert result["data"]["profile"] == "biomedical"
    assert "pubmed" in result["data"]["selected_sources"]


@respx.mock
async def test_mcp_lookup_mesh():
    respx.get("https://id.nlm.nih.gov/mesh/lookup/descriptor").mock(
        return_value=Response(200, json=[{"label": "Carcinoma, Hepatocellular"}])
    )
    result = await lookup_mesh("hepatocellular carcinoma")
    assert result["data"][0]["label"] == "Carcinoma, Hepatocellular"


@respx.mock
async def test_mcp_convert_identifiers():
    respx.get("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/").mock(
        return_value=Response(200, json={"records": [{"pmid": "12345", "doi": "10.1000/test"}]})
    )
    result = await convert_identifiers(["10.1000/test"])
    assert result["data"][0]["pmid"] == "12345"
