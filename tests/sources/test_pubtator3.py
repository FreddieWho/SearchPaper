"""Fixture-backed tests for the PubTator3 adapter."""

import respx
from httpx import Response

from searchpaper.schemas import SearchFilters
from searchpaper.sources.pubtator3 import PubTator3Adapter


@respx.mock
async def test_pubtator3_search():
    respx.get("https://www.ncbi.nlm.nih.gov/research/pubtator3-api/search/").mock(
        return_value=Response(200, json=[{"pmid": "12345", "title": "Test"}])
    )
    adapter = PubTator3Adapter()
    records = await adapter.search("JAK1", SearchFilters(limit=5))
    await adapter.aclose()
    assert len(records) == 1
    assert records[0].identifiers.get("pmid") == "12345"


@respx.mock
async def test_pubtator3_find_entity():
    respx.get("https://www.ncbi.nlm.nih.gov/research/pubtator3-api/entity/autocomplete/").mock(
        return_value=Response(200, json=[{"id": "@GENE_JAK1", "name": "JAK1", "type": "gene"}])
    )
    adapter = PubTator3Adapter()
    result = await adapter.find_entity("JAK1")
    await adapter.aclose()
    assert len(result["items"]) == 1
    assert result["items"][0]["entity_id"] == "@GENE_JAK1"


@respx.mock
async def test_pubtator3_find_relations():
    respx.get("https://www.ncbi.nlm.nih.gov/research/pubtator3-api/relations").mock(
        return_value=Response(
            200,
            json=[
                {
                    "source": "@GENE_JAK1",
                    "target": "@CHEMICAL_X",
                    "publications": 5,
                }
            ],
        )
    )
    adapter = PubTator3Adapter()
    signals = await adapter.find_relations("@GENE_JAK1", "chemical", "interact", limit=5)
    await adapter.aclose()
    assert len(signals) == 1
    assert signals[0].signal_level.value == "curated_or_extracted"
