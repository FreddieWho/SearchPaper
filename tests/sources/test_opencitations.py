"""Fixture-backed tests for the OpenCitations adapter."""

import respx
from httpx import Response

from searchpaper.schemas import SourceState, WorkIdentifier
from searchpaper.sources.opencitations import OpenCitationsAdapter


@respx.mock
async def test_opencitations_status_uses_canonical_endpoint():
    probe = respx.get(
        "https://api.opencitations.net/index/v1/citations/10.1038/nature12373"
    ).mock(return_value=Response(200, json=[]))
    adapter = OpenCitationsAdapter()
    try:
        status = await adapter.status()
    finally:
        await adapter.aclose()
    assert probe.called
    assert status.state == SourceState.AVAILABLE


@respx.mock
async def test_opencitations_get_citations():
    respx.get("https://api.opencitations.net/index/v1/citations/10.1000/test").mock(
        return_value=Response(
            200,
            json=[
                {"citing": "10.2000/a", "cited": "10.1000/test", "oci": "oci-1"},
                {"citing": "10.2000/b", "cited": "10.1000/test", "oci": "oci-2"},
            ],
        )
    )
    respx.get("https://api.opencitations.net/index/v1/references/10.1000/test").mock(
        return_value=Response(200, json=[])
    )

    adapter = OpenCitationsAdapter()
    record = await adapter.get(WorkIdentifier(type="doi", value="10.1000/test"))
    await adapter.aclose()
    assert record is not None
    assert record.normalized_fields["citation_count"] == 2
    assert record.normalized_fields["reference_count"] == 0


@respx.mock
async def test_opencitations_get_references():
    respx.get("https://api.opencitations.net/index/v1/citations/10.1000/test").mock(
        return_value=Response(200, json=[])
    )
    respx.get("https://api.opencitations.net/index/v1/references/10.1000/test").mock(
        return_value=Response(
            200,
            json=[
                {"citing": "10.1000/test", "cited": "10.2000/ref", "oci": "oci-3"},
            ],
        )
    )

    adapter = OpenCitationsAdapter()
    refs = await adapter.get_references("10.1000/test")
    await adapter.aclose()
    assert len(refs) == 1
    assert refs[0].normalized_fields["relation_type"] == "reference"
    assert refs[0].normalized_fields["object_doi"] == "10.2000/ref"
