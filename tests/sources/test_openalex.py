"""Fixture-backed tests for the OpenAlex adapter."""

import respx
from httpx import Response

from searchpaper.schemas import SearchFilters, WorkIdentifier
from searchpaper.sources.openalex import OpenAlexAdapter


@respx.mock
async def test_openalex_search():
    respx.get("https://api.openalex.org/works").mock(
        return_value=Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W123456789",
                        "title": "OpenAlex Test Paper",
                        "publication_year": 2023,
                        "doi": "https://doi.org/10.1000/test",
                        "authorships": [
                            {
                                "author": {"display_name": "A Smith"},
                                "institutions": [{"display_name": "Institute"}],
                            }
                        ],
                        "cited_by_count": 42,
                    }
                ]
            },
        )
    )
    adapter = OpenAlexAdapter()
    records = await adapter.search("openalex test", SearchFilters(limit=5))
    await adapter.aclose()
    assert len(records) == 1
    assert records[0].identifiers.get("openalex") == "W123456789"


@respx.mock
async def test_openalex_get_by_doi():
    respx.get("https://api.openalex.org/works/doi:10.1000/test").mock(
        return_value=Response(
            200,
            json={
                "id": "https://openalex.org/W123456789",
                "title": "OpenAlex Test Paper",
                "publication_year": 2023,
                "doi": "https://doi.org/10.1000/test",
            },
        )
    )
    adapter = OpenAlexAdapter()
    record = await adapter.get(WorkIdentifier(type="doi", value="10.1000/test"))
    await adapter.aclose()
    assert record is not None
    assert record.identifiers.get("doi") == "10.1000/test"
