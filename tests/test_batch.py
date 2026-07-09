"""Tests for SearchPaper batch processing."""

from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from searchpaper.batch import process_batch
from searchpaper.cache import Cache
from searchpaper.cli import app
from searchpaper.engine import SearchEngine
from searchpaper.schemas import SearchFilters


@respx.mock
async def test_batch_json_output(tmp_path):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["12345"]}})
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "HCC Paper",
                        "pubdate": "2023",
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )
    respx.get("https://api.crossref.org/works").mock(return_value=Response(500, text="error"))
    respx.get("https://api.openalex.org/works").mock(return_value=Response(500, text="error"))

    input_file = tmp_path / "input.jsonl"
    input_file.write_text('{"query": "HCC"}\n{"pmid": "12345"}\n', encoding="utf-8")

    cache = Cache(str(tmp_path / "cache.db"))
    engine = SearchEngine(cache=cache, sources=["pubmed"])

    output = await process_batch(
        input_file,
        engine,
        output_format="json",
        sources=["pubmed"],
        filters=SearchFilters(limit=5),
    )
    data = json.loads(output)
    assert data["object_type"] == "batch_result"
    assert data["data"]["summary"]["total"] == 2
    assert data["data"]["summary"]["succeeded"] == 2
    assert len(data["data"]["items"]) == 2
    assert data["data"]["items"][0]["envelope"]["data"]["works"][0]["identifiers"]["pmid"] == "12345"


@respx.mock
async def test_batch_jsonl_output(tmp_path):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["12345"]}})
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "HCC Paper",
                        "pubdate": "2023",
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )

    input_file = tmp_path / "input.txt"
    input_file.write_text("HCC\n", encoding="utf-8")

    cache = Cache(str(tmp_path / "cache.db"))
    engine = SearchEngine(cache=cache, sources=["pubmed"])

    output = await process_batch(
        input_file,
        engine,
        output_format="jsonl",
        sources=["pubmed"],
        filters=SearchFilters(limit=5),
    )
    lines = [line for line in output.splitlines() if line.strip()]
    assert len(lines) == 1
    envelope = json.loads(lines[0])
    assert envelope["data"]["works"][0]["identifiers"]["pmid"] == "12345"


@respx.mock
async def test_batch_bibtex_output(tmp_path):
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["12345"]}})
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "HCC Paper",
                        "pubdate": "2023",
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )

    input_file = tmp_path / "input.jsonl"
    input_file.write_text('{"query": "HCC"}\n', encoding="utf-8")

    cache = Cache(str(tmp_path / "cache.db"))
    engine = SearchEngine(cache=cache, sources=["pubmed"])

    output = await process_batch(
        input_file,
        engine,
        output_format="bibtex",
        sources=["pubmed"],
        filters=SearchFilters(limit=5),
    )
    assert "@article{" in output
    assert "HCC Paper" in output


@respx.mock
def test_cli_batch(tmp_path):
    import os

    os.environ["SEARCHPAPER_CACHE"] = str(tmp_path / "cache.db")
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": ["12345"]}})
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "HCC Paper",
                        "pubdate": "2023",
                        "articleids": [{"idtype": "pubmed", "value": "12345"}],
                    },
                }
            },
        )
    )
    respx.get("https://api.crossref.org/works").mock(return_value=Response(500, text="error"))
    respx.get("https://api.openalex.org/works").mock(return_value=Response(500, text="error"))

    input_file = tmp_path / "input.jsonl"
    input_file.write_text('{"query": "HCC"}\n', encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["batch", str(input_file), "--sources", "pubmed", "--format", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["object_type"] == "batch_result"
    assert data["data"]["summary"]["succeeded"] == 1
