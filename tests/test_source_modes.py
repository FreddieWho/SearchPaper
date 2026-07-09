"""Tests for source requirement modes (optional/preferred/required)."""

from __future__ import annotations

import respx
from httpx import Response

from searchpaper.engine import SearchEngine
from searchpaper.exceptions import SourceRequiredError
from searchpaper.schemas import SearchFilters, SourceMode


@respx.mock
async def test_required_source_failure_raises(tmp_cache):
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

    engine = SearchEngine(cache=tmp_cache, sources=["pubmed", "crossref"])
    try:
        await engine.search(
            "HCC",
            filters=SearchFilters(limit=5),
            source_modes={"crossref": SourceMode.REQUIRED},
        )
    except SourceRequiredError as exc:
        data = exc.envelope.data
        trace = data["trace"]
        assert "crossref" in trace["sources_failed"]
        assert "pubmed" in trace["sources_succeeded"]
        assert len(data["works"]) >= 1
    else:
        raise AssertionError("Expected SourceRequiredError")


@respx.mock
async def test_preferred_source_failure_adds_loud_warning(tmp_cache):
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

    engine = SearchEngine(cache=tmp_cache, sources=["pubmed", "crossref"])
    result = await engine.search(
        "HCC",
        filters=SearchFilters(limit=5),
        source_modes={"crossref": SourceMode.PREFERRED},
    )
    assert any("Preferred sources failed: crossref" in w for w in result.warnings)


@respx.mock
async def test_optional_source_failure_does_not_raise(tmp_cache):
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

    engine = SearchEngine(cache=tmp_cache, sources=["pubmed", "crossref"])
    result = await engine.search("HCC", filters=SearchFilters(limit=5))
    assert len(result.data["works"]) >= 1


@respx.mock
async def test_required_source_failure_in_get(tmp_cache):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(500, text="Internal Server Error")
    )

    from searchpaper.identifiers import identify

    engine = SearchEngine(cache=tmp_cache, sources=["pubmed"])
    try:
        await engine.get(
            identify("12345"),
            source_modes={"pubmed": SourceMode.REQUIRED},
        )
    except SourceRequiredError:
        pass
    else:
        raise AssertionError("Expected SourceRequiredError for failed required source in get")


@respx.mock
async def test_required_source_failure_in_resolve(tmp_cache):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(500, text="Internal Server Error")
    )

    from searchpaper.identifiers import identify

    engine = SearchEngine(cache=tmp_cache, sources=["pubmed"])
    try:
        await engine.resolve(
            identify("12345"),
            source_modes={"pubmed": SourceMode.REQUIRED},
        )
    except SourceRequiredError:
        pass
    else:
        raise AssertionError("Expected SourceRequiredError for failed required source in resolve")


def test_search_filters_source_modes_roundtrip():
    filters = SearchFilters(source_modes={"pubmed": SourceMode.REQUIRED, "crossref": SourceMode.PREFERRED})
    data = filters.model_dump(mode="json")
    restored = SearchFilters(**data)
    assert restored.source_modes["pubmed"] == SourceMode.REQUIRED
    assert restored.source_modes["crossref"] == SourceMode.PREFERRED
