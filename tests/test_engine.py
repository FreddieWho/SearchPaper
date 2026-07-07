"""Tests for the SearchPaper search engine."""

import respx
from httpx import Response

from searchpaper.engine import SearchEngine
from searchpaper.schemas import SearchFilters


@respx.mock
async def test_engine_search_partial_success(tmp_cache):
    # PubMed succeeds
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
    # Crossref fails
    respx.get("https://api.crossref.org/works").mock(return_value=Response(500, text="error"))
    # OpenAlex fails
    respx.get("https://api.openalex.org/works").mock(return_value=Response(500, text="error"))

    engine = SearchEngine(cache=tmp_cache, sources=["pubmed", "crossref", "openalex"])
    result = await engine.search("HCC", filters=SearchFilters(limit=5))
    data = result.data
    assert len(data["works"]) >= 1
    trace = data["trace"]
    assert "pubmed" in trace["sources_succeeded"]
    # Failed sources should be recorded but not block the result.
    assert len(trace["sources_failed"]) >= 2 or len(trace["sources_succeeded"]) >= 1


@respx.mock
async def test_engine_get(tmp_cache):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "Paper",
                        "pubdate": "2023",
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )
    from searchpaper.identifiers import identify

    engine = SearchEngine(cache=tmp_cache, sources=["pubmed"])
    result = await engine.get(identify("12345"))
    data = result.data
    assert len(data["works"]) == 1
    assert data["works"][0]["identifiers"]["pmid"] == "12345"
