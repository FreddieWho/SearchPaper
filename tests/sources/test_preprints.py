"""Fixture-backed tests for bioRxiv and medRxiv adapters."""

import respx
from httpx import Response

from searchpaper.schemas import SearchFilters
from searchpaper.sources.biorxiv import BioRxivAdapter
from searchpaper.sources.medrxiv import MedRxivAdapter

PREPRINT_RESPONSE = {
    "messages": [{"status": "ok"}],
    "collection": [
        {
            "doi": "10.1101/2024.01.01.123456",
            "title": "A Preprint About Immunotherapy",
            "authors": "Alice Smith; Bob Jones",
            "date": "2024-01-01",
            "category": "cancer biology",
            "abstract": "A preprint abstract.",
            "server": "biorxiv",
        }
    ],
}


@respx.mock
async def test_biorxiv_search_parses_collection():
    respx.get("https://api.biorxiv.org/details/biorxiv/2020-01-01/3000-01-01").mock(
        return_value=Response(200, json=PREPRINT_RESPONSE)
    )

    adapter = BioRxivAdapter()
    records = await adapter.search("immunotherapy", SearchFilters(limit=10))
    await adapter.aclose()

    assert len(records) == 1
    assert records[0].source == "biorxiv"
    assert records[0].identifiers["doi"] == "10.1101/2024.01.01.123456"


@respx.mock
async def test_medrxiv_search_uses_medrxiv_endpoint():
    payload = {**PREPRINT_RESPONSE, "collection": [{**PREPRINT_RESPONSE["collection"][0], "server": "medrxiv"}]}
    respx.get("https://api.biorxiv.org/details/medrxiv/2020-01-01/3000-01-01").mock(
        return_value=Response(200, json=payload)
    )

    adapter = MedRxivAdapter()
    records = await adapter.search("immunotherapy", SearchFilters(limit=10))
    await adapter.aclose()

    assert len(records) == 1
    assert records[0].source == "medrxiv"
