"""Tests for source health diagnostics."""

import respx
from httpx import Response

from searchpaper.diagnostics import diagnose_configuration, diagnose_sources, explain_source


@respx.mock
async def test_explain_source_returns_descriptor_and_status():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["1"]}})
    )

    result = await explain_source("pubmed")

    assert result["object_type"] == "source_explanation"
    assert result["source"] == "pubmed"
    assert result["descriptor"]["name"] == "pubmed"
    assert result["status"]["source"] == "pubmed"
    assert any("healthy" in r.lower() for r in result["recommendations"])


@respx.mock
async def test_diagnose_sources_returns_aggregate_summary():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["1"]}})
    )
    respx.get("https://api.crossref.org/works").mock(return_value=Response(500, text="error"))
    respx.get("https://api.openalex.org/works").mock(return_value=Response(500, text="error"))

    result = await diagnose_sources(["pubmed", "crossref", "openalex"])

    assert result["object_type"] == "source_diagnosis"
    assert result["summary"]["total"] == 3
    assert result["summary"]["healthy"] >= 1
    assert any(entry["source"] == "pubmed" for entry in result["sources"])


def test_diagnose_configuration_reports_known_keys():
    result = diagnose_configuration()
    assert result["object_type"] == "configuration_diagnosis"
    assert "cache_path" in result
    assert isinstance(result["configured_keys"], list)
    assert isinstance(result["issues"], list)
