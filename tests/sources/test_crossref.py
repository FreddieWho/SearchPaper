"""Fixture-backed tests for the Crossref adapter."""

import respx
from httpx import Response

from searchpaper.schemas import SearchFilters, WorkIdentifier
from searchpaper.sources.crossref import CrossrefAdapter


@respx.mock
async def test_crossref_search():
    respx.get("https://api.crossref.org/works").mock(
        return_value=Response(
            200,
            json={
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/test",
                            "title": ["A Test Paper"],
                            "published-print": {"date-parts": [[2023, 1, 1]]},
                            "container-title": ["Journal"],
                            "author": [{"given": "A", "family": "Smith"}],
                            "type": "journal-article",
                        }
                    ]
                }
            },
        )
    )
    adapter = CrossrefAdapter()
    records = await adapter.search("test paper", SearchFilters(limit=5))
    await adapter.aclose()
    assert len(records) == 1
    assert records[0].identifiers.get("doi") == "10.1000/test"


@respx.mock
async def test_crossref_get_by_doi():
    respx.get("https://api.crossref.org/works/10.1000/test").mock(
        return_value=Response(
            200,
            json={
                "message": {
                    "DOI": "10.1000/test",
                    "title": ["A Test Paper"],
                    "published-print": {"date-parts": [[2023]]},
                    "type": "journal-article",
                }
            },
        )
    )
    adapter = CrossrefAdapter()
    record = await adapter.get(WorkIdentifier(type="doi", value="10.1000/test"))
    await adapter.aclose()
    assert record is not None
    assert record.identifiers.get("doi") == "10.1000/test"
