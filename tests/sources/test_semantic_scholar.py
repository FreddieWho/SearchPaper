"""Fixture-backed tests for the Semantic Scholar adapter."""

import respx
from httpx import Response

from searchpaper.schemas import SearchFilters, WorkIdentifier
from searchpaper.sources.semantic_scholar import SemanticScholarAdapter


@respx.mock
async def test_semantic_scholar_search():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=Response(
            200,
            json={
                "total": 1,
                "data": [
                    {
                        "paperId": "abc123",
                        "title": "S2 Test",
                        "year": 2023,
                        "authors": [{"authorId": "a1", "name": "A Smith"}],
                        "externalIds": {"DOI": "10.1000/test"},
                    }
                ],
            },
        )
    )
    adapter = SemanticScholarAdapter()
    records = await adapter.search("s2 test", SearchFilters(limit=5))
    await adapter.aclose()
    assert len(records) == 1
    assert records[0].source_record_id == "abc123"


@respx.mock
async def test_semantic_scholar_get_by_doi():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1000/test").mock(
        return_value=Response(
            200,
            json={
                "paperId": "abc123",
                "title": "S2 Test",
                "year": 2023,
                "externalIds": {"DOI": "10.1000/test"},
            },
        )
    )
    adapter = SemanticScholarAdapter()
    record = await adapter.get(WorkIdentifier(type="doi", value="10.1000/test"))
    await adapter.aclose()
    assert record is not None
    assert record.identifiers.get("doi") == "10.1000/test"


@respx.mock
async def test_semantic_scholar_get_citations():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1000/test").mock(
        return_value=Response(
            200,
            json={"paperId": "abc123", "title": "S2 Test", "externalIds": {"DOI": "10.1000/test"}},
        )
    )
    respx.get("https://api.semanticscholar.org/graph/v1/paper/abc123/citations").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {"citingPaper": {"paperId": "cit1", "title": "Citing One", "year": 2024}},
                    {"citingPaper": {"paperId": "cit2", "title": "Citing Two", "year": 2024}},
                ]
            },
        )
    )
    adapter = SemanticScholarAdapter()
    records = await adapter.get_citations(WorkIdentifier(type="doi", value="10.1000/test"), limit=5)
    await adapter.aclose()
    assert len(records) == 2
    assert records[0].source_record_id == "cit1"


@respx.mock
async def test_semantic_scholar_get_references():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1000/test").mock(
        return_value=Response(
            200,
            json={"paperId": "abc123", "title": "S2 Test", "externalIds": {"DOI": "10.1000/test"}},
        )
    )
    respx.get("https://api.semanticscholar.org/graph/v1/paper/abc123/references").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {"citedPaper": {"paperId": "ref1", "title": "Reference One", "year": 2020}},
                ]
            },
        )
    )
    adapter = SemanticScholarAdapter()
    records = await adapter.get_references(WorkIdentifier(type="doi", value="10.1000/test"), limit=5)
    await adapter.aclose()
    assert len(records) == 1
    assert records[0].source_record_id == "ref1"


@respx.mock
async def test_semantic_scholar_get_recommendations():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1000/test").mock(
        return_value=Response(
            200,
            json={"paperId": "abc123", "title": "S2 Test", "externalIds": {"DOI": "10.1000/test"}},
        )
    )
    respx.post("https://api.semanticscholar.org/graph/v1/paper/recommendations").mock(
        return_value=Response(
            200,
            json={"recommendedPapers": [{"paperId": "rec1", "title": "Recommended", "year": 2023}]},
        )
    )
    adapter = SemanticScholarAdapter()
    records = await adapter.get_recommendations(WorkIdentifier(type="doi", value="10.1000/test"), limit=5)
    await adapter.aclose()
    assert len(records) == 1
    assert records[0].source_record_id == "rec1"
