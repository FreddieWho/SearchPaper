"""CLI smoke tests for SearchPaper."""

import respx
from httpx import Response
from typer.testing import CliRunner

from searchpaper.cli import app

runner = CliRunner()


def test_cli_capabilities():
    result = runner.invoke(app, ["capabilities", "--json"])
    assert result.exit_code == 0
    assert "search_literature" in result.output
    assert "pubmed" in result.output
    assert "plan_literature_search" in result.output


def test_cli_plan():
    result = runner.invoke(app, ["plan", "hepatocellular carcinoma", "--profile", "auto", "--json"])
    assert result.exit_code == 0
    assert '"profile": "biomedical"' in result.output
    assert "pubmed" in result.output


def test_cli_sources_tiers():
    result = runner.invoke(app, ["sources", "tiers", "--json"])
    assert result.exit_code == 0
    assert "google_scholar" in result.output
    assert "implemented" in result.output


@respx.mock
def test_cli_references_convert(tmp_path):
    import os

    os.environ["SEARCHPAPER_CACHE"] = str(tmp_path / "cache.db")
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
    respx.get("https://api.crossref.org/works/10.1000/test").mock(
        return_value=Response(
            200,
            json={
                "message": {
                    "DOI": "10.1000/test",
                    "title": ["Test Paper"],
                    "published-print": {"date-parts": [[2023]]},
                    "type": "journal-article",
                }
            },
        )
    )

    refs = tmp_path / "refs.txt"
    refs.write_text("PMID:12345\nDOI:10.1000/test\n", encoding="utf-8")

    result = runner.invoke(app, ["references", "convert", str(refs), "--format", "ris"])

    assert result.exit_code == 0
    assert "AN  - PMID:12345" in result.output
    assert "DO  - 10.1000/test" in result.output


@respx.mock
def test_cli_references_convert_query_and_author_title(tmp_path):
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

    refs = tmp_path / "refs.txt"
    refs.write_text(
        "QUERY:HCC\nAUTHOR:Dheda TITLE:drug-resistant tuberculosis\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["references", "convert", str(refs), "--format", "ris"])

    assert result.exit_code == 0
    assert "HCC Paper" in result.output


@respx.mock
def test_cli_pubmed_mesh():
    respx.get("https://id.nlm.nih.gov/mesh/lookup/descriptor").mock(
        return_value=Response(200, json=[{"label": "Carcinoma, Hepatocellular"}])
    )

    result = runner.invoke(app, ["pubmed", "mesh", "hepatocellular carcinoma", "--json"])

    assert result.exit_code == 0
    assert "Carcinoma, Hepatocellular" in result.output


@respx.mock
def test_cli_pubmed_convert_ids():
    respx.get("https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/").mock(
        return_value=Response(200, json={"records": [{"doi": "10.1000/test", "pmid": "12345"}]})
    )

    result = runner.invoke(app, ["pubmed", "convert-ids", "10.1000/test", "--json"])

    assert result.exit_code == 0
    assert "12345" in result.output


def test_cli_doctor():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "SearchPaper Doctor" in result.output


def test_cli_cache_stats_and_clear(tmp_path):
    import os

    cache_db = tmp_path / "cache.db"
    os.environ["SEARCHPAPER_CACHE"] = str(cache_db)
    result = runner.invoke(app, ["cache", "stats"])
    assert result.exit_code == 0
    assert "total_entries" in result.output
    result = runner.invoke(app, ["cache", "clear", "--yes"])
    assert result.exit_code == 0
    assert "Cache cleared" in result.output


def test_cli_search(tmp_path):
    import os

    os.environ["SEARCHPAPER_CACHE"] = str(tmp_path / "cache.db")
    with respx.mock:
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
                            "title": "HCC TACE PD-1 Response",
                            "pubdate": "2023",
                            "articleids": [{"idtype": "pubmed", "value": "12345"}],
                        },
                    }
                },
            )
        )
        respx.get("https://api.crossref.org/works").mock(return_value=Response(500, text="error"))
        respx.get("https://api.openalex.org/works").mock(return_value=Response(500, text="error"))

        result = runner.invoke(app, ["search", "HCC TACE PD-1", "--sources", "pubmed", "--json"])
    assert result.exit_code == 0
    assert "HCC TACE PD-1 Response" in result.output
    assert "pubmed" in result.output


@respx.mock
def test_cli_expand():
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1000/test").mock(
        return_value=Response(
            200,
            json={"paperId": "s2id", "title": "S2 Test", "externalIds": {"DOI": "10.1000/test"}},
        )
    )
    respx.get("https://api.semanticscholar.org/graph/v1/paper/s2id/citations").mock(
        return_value=Response(
            200,
            json={"data": [{"citingPaper": {"paperId": "cit1", "title": "Citing", "year": 2024}}]},
        )
    )

    result = runner.invoke(app, ["expand", "--doi", "10.1000/test", "--by", "citations", "--limit", "5", "--json"])
    assert result.exit_code == 0
    assert "cit1" in result.output


@respx.mock
def test_cli_search_required_source_fails(tmp_path):
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

    result = runner.invoke(
        app,
        [
            "search",
            "HCC",
            "--sources",
            "pubmed,crossref",
            "--require",
            "crossref",
            "--json",
        ],
    )
    assert result.exit_code == 1
    assert "Required source(s) failed: crossref" in result.output
    assert "HCC Paper" in result.output


@respx.mock
def test_cli_search_source_mode_preferred(tmp_path):
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

    result = runner.invoke(
        app,
        [
            "search",
            "HCC",
            "--sources",
            "pubmed,crossref",
            "--source-mode",
            "crossref:preferred",
            "--json",
        ],
    )
    assert result.exit_code == 0
    assert "Preferred sources failed: crossref" in result.output
