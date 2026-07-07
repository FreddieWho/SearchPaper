"""Fixture-backed tests for the PubMed adapter."""

import respx
from httpx import Response

from searchpaper.schemas import SearchFilters, WorkIdentifier
from searchpaper.sources.pubmed import PubMedAdapter


@respx.mock
async def test_pubmed_search(tmp_cache):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(
            200,
            json={
                "esearchresult": {
                    "idlist": ["12345"],
                }
            },
        )
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "Hepatocellular Carcinoma and Immunotherapy",
                        "pubdate": "2023 Jan 1",
                        "fulljournalname": "Journal of Oncology",
                        "authors": [{"Name": "Smith J"}],
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )
    adapter = PubMedAdapter()
    records = await adapter.search("HCC immunotherapy", SearchFilters(limit=10))
    await adapter.aclose()
    assert len(records) == 1
    assert records[0].source == "pubmed"
    assert records[0].identifiers.get("pmid") == "12345"


@respx.mock
async def test_pubmed_get_by_pmid(tmp_cache):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "Test Paper",
                        "pubdate": "2024",
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )
    adapter = PubMedAdapter()
    record = await adapter.get(WorkIdentifier(type="pmid", value="12345"))
    await adapter.aclose()
    assert record is not None
    assert record.identifiers["pmid"] == "12345"
