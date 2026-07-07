"""Tests for export formats."""

from searchpaper.export import work_to_bibtex, work_to_markdown, work_to_ris, works_to_format


def sample_work():
    return {
        "title": "A Test Paper",
        "year": 2023,
        "venue": "Journal of Tests",
        "authors": [{"name": "Alice Smith", "last_name": "Smith"}],
        "identifiers": {"doi": "10.1000/test", "pmid": "12345"},
        "abstract": "This is a test abstract.",
        "publication_types": ["journal-article"],
    }


def test_work_to_bibtex():
    bib = work_to_bibtex(sample_work())
    assert "@article{" in bib
    assert "10.1000/test" in bib


def test_work_to_ris():
    ris = work_to_ris(sample_work())
    assert "TY  - JOUR" in ris
    assert "DO  - 10.1000/test" in ris


def test_work_to_markdown():
    md = work_to_markdown(sample_work())
    assert "A Test Paper" in md
    assert "10.1000/test" in md


def test_works_to_jsonl():
    out = works_to_format([sample_work()], "jsonl")
    assert "A Test Paper" in out
    assert "\n" in out


def test_works_to_enw():
    out = works_to_format([sample_work()], "enw")
    assert "%0 Journal Article" in out
    assert "%D 2023" in out
    assert "%R 10.1000/test" in out


def test_works_to_nbib():
    out = works_to_format([sample_work()], "nbib")
    assert "PMID- 12345" in out
    assert "TI  - A Test Paper" in out
    assert "LID - 10.1000/test [doi]" in out
