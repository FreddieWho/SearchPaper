"""Tests for PubMed utility workflows."""

import respx
from httpx import Response

from searchpaper.pubmed_utils import convert_ids, lookup_mesh, related_articles


@respx.mock
async def test_lookup_mesh_returns_terms():
    respx.get("https://id.nlm.nih.gov/mesh/lookup/descriptor").mock(
        return_value=Response(200, json=[{"label": "Carcinoma, Hepatocellular", "resource": "D006528"}])
    )

    result = await lookup_mesh("hepatocellular carcinoma")

    assert result[0]["label"] == "Carcinoma, Hepatocellular"


@respx.mock
async def test_related_articles_returns_pmids():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi").mock(
        return_value=Response(
            200,
            json={
                "linksets": [
                    {
                        "linksetdbs": [
                            {"dbto": "pubmed", "linkname": "pubmed_pubmed", "links": ["111", "222"]}
                        ]
                    }
                ]
            },
        )
    )

    result = await related_articles("12345")

    assert result == ["111", "222"]


@respx.mock
async def test_convert_ids_returns_id_map():
    respx.get("https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/").mock(
        return_value=Response(
            200,
            json={
                "records": [
                    {"doi": "10.1000/test", "pmid": "12345", "pmcid": "PMC123456"},
                ]
            },
        )
    )

    result = await convert_ids(["10.1000/test"])

    assert result["records"][0]["doi"] == "10.1000/test"
    assert result["records"][0]["pmid"] == "12345"


@respx.mock
async def test_convert_ids_handles_non_json_response():
    respx.get("https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/").mock(
        return_value=Response(200, text="not json")
    )

    result = await convert_ids(["10.1000/test"])

    assert result["records"] == []
    assert any("non-JSON" in w for w in result["warnings"])


@respx.mock
async def test_convert_ids_handles_http_error():
    respx.get("https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/").mock(
        return_value=Response(500, text="Internal Server Error")
    )

    result = await convert_ids(["10.1000/test"])

    assert result["records"] == []
    assert any("500" in w for w in result["warnings"])
