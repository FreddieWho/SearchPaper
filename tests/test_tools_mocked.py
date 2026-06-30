import pytest
import respx
from httpx import Response

from paper_search.cache import Cache
from paper_search.pubtator3 import PubTator3Client
from paper_search.semantic_scholar import SemanticScholarClient


@pytest.fixture
def tmp_cache(tmp_path):
    return Cache(str(tmp_path / "cache.db"))


@respx.mock
async def test_s2_search_papers(tmp_cache):
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=Response(200, json={
            "total": 1,
            "data": [{
                "paperId": "p1",
                "title": "Cancer Immunotherapy",
                "year": 2023,
                "citationCount": 10,
                "authors": [],
                "externalIds": {},
            }]
        })
    )
    client = SemanticScholarClient(cache=tmp_cache)
    result = await client.search_papers("cancer immunotherapy", limit=5)
    assert len(result["items"]) == 1
    assert result["items"][0]["title"] == "Cancer Immunotherapy"
    assert result["from_cache"] is False

    # second call should hit cache
    result2 = await client.search_papers("cancer immunotherapy", limit=5)
    assert result2["from_cache"] is True


@respx.mock
async def test_s2_get_paper_404_returns_structured(tmp_cache):
    respx.get("https://api.semanticscholar.org/graph/v1/paper/doi:10.0000/nope").mock(
        return_value=Response(404, json={"error": "Not found"})
    )
    client = SemanticScholarClient(cache=tmp_cache)
    result = await client.get_paper("doi:10.0000/nope")
    assert result["items"] == []
    assert any("404" in w for w in result.get("warnings", []))


@respx.mock
async def test_pubtator_find_entity(tmp_cache):
    respx.get("https://www.ncbi.nlm.nih.gov/research/pubtator3-api/entity/autocomplete/").mock(
        return_value=Response(200, json=[
            {"id": "@GENE_JAK1", "name": "JAK1", "type": "gene"}
        ])
    )
    client = PubTator3Client(cache=tmp_cache)
    result = await client.find_entity("JAK1")
    assert len(result["items"]) == 1
    assert result["items"][0]["entity_id"] == "@GENE_JAK1"


@respx.mock
async def test_pubtator_find_relations(tmp_cache):
    respx.get("https://www.ncbi.nlm.nih.gov/research/pubtator3-api/relations").mock(
        return_value=Response(200, json=[
            {
                "entity1": {"id": "@GENE_JAK1"},
                "entity2": {"id": "@CHEMICAL_X", "name": "X", "type": "chemical"},
                "pmids": ["123"],
            }
        ])
    )
    client = PubTator3Client(cache=tmp_cache)
    result = await client.find_relations("@GENE_JAK1", "chemical", "inhibit")
    assert len(result["items"]) == 1
    assert result["items"][0]["relation_type"] == "inhibit"


@respx.mock
async def test_pubtator_search(tmp_cache):
    respx.get("https://www.ncbi.nlm.nih.gov/research/pubtator3-api/search/").mock(
        return_value=Response(200, json=[
            {"pmid": "123", "title": "Study"}
        ])
    )
    client = PubTator3Client(cache=tmp_cache)
    result = await client.search("JAK1")
    assert result["items"][0]["pmid"] == "123"
    assert "pubmed_url" in result["items"][0]
