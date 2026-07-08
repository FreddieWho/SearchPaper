"""Fixture-backed tests for the Unpaywall adapter."""

import respx
from httpx import Response

from searchpaper.schemas import WorkIdentifier
from searchpaper.sources.unpaywall import UnpaywallAdapter


@respx.mock
async def test_unpaywall_get_by_doi():
    respx.get("https://api.unpaywall.org/v2/10.1000/test").mock(
        return_value=Response(
            200,
            json={
                "doi": "10.1000/test",
                "is_oa": True,
                "oa_status": "gold",
                "best_oa_location": {
                    "url": "https://example.com/paper",
                    "url_for_pdf": "https://example.com/paper.pdf",
                    "host_type": "publisher",
                    "license": "cc-by",
                },
            },
        )
    )
    adapter = UnpaywallAdapter(email="test@example.com")
    record = await adapter.get(WorkIdentifier(type="doi", value="10.1000/test"))
    await adapter.aclose()
    assert record is not None
    assert record.normalized_fields["is_oa"] is True
    assert record.normalized_fields["oa_status"] == "gold"
    assert record.normalized_fields["oa_url"] == "https://example.com/paper"


@respx.mock
async def test_unpaywall_get_not_oa():
    respx.get("https://api.unpaywall.org/v2/10.1000/closed").mock(
        return_value=Response(
            200,
            json={
                "doi": "10.1000/closed",
                "is_oa": False,
                "oa_status": "closed",
                "best_oa_location": None,
            },
        )
    )
    adapter = UnpaywallAdapter(email="test@example.com")
    record = await adapter.get(WorkIdentifier(type="doi", value="10.1000/closed"))
    await adapter.aclose()
    assert record is not None
    assert record.normalized_fields["is_oa"] is False


@respx.mock
async def test_unpaywall_get_404_returns_none():
    respx.get("https://api.unpaywall.org/v2/10.1000/missing").mock(return_value=Response(404))
    adapter = UnpaywallAdapter(email="test@example.com")
    record = await adapter.get(WorkIdentifier(type="doi", value="10.1000/missing"))
    await adapter.aclose()
    assert record is None
