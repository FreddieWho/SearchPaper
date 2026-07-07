"""Fixture-backed tests for arXiv adapter."""

import respx
from httpx import Response

from searchpaper.schemas import SearchFilters, WorkIdentifier
from searchpaper.sources.arxiv import ArxivAdapter

ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v2</id>
    <title>Graph Neural Network Potentials</title>
    <published>2024-01-01T00:00:00Z</published>
    <updated>2024-01-02T00:00:00Z</updated>
    <summary> A test abstract. </summary>
    <author><name>Alice Smith</name></author>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.48550/arXiv.2401.00001</arxiv:doi>
    <category term="cs.LG" />
  </entry>
</feed>
"""


@respx.mock
async def test_arxiv_search_parses_atom_feed():
    respx.get("https://export.arxiv.org/api/query").mock(return_value=Response(200, text=ARXIV_FEED))

    adapter = ArxivAdapter()
    records = await adapter.search("graph neural network", SearchFilters(limit=5))
    await adapter.aclose()

    assert len(records) == 1
    assert records[0].source == "arxiv"
    assert records[0].identifiers["arxiv"] == "2401.00001"
    assert records[0].normalized_fields["title"] == "Graph Neural Network Potentials"
    assert records[0].normalized_fields["year"] == 2024


@respx.mock
async def test_arxiv_get_by_identifier():
    respx.get("https://export.arxiv.org/api/query").mock(return_value=Response(200, text=ARXIV_FEED))

    adapter = ArxivAdapter()
    record = await adapter.get(WorkIdentifier(type="arxiv", value="2401.00001"))
    await adapter.aclose()

    assert record is not None
    assert record.identifiers["arxiv"] == "2401.00001"
