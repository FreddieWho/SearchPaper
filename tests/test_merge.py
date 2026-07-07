"""Tests for identifier resolution and merge."""

from searchpaper.merge import merge_records
from searchpaper.schemas import SourceRecord


def _srecord(source: str, sid: str, ids: dict, **fields) -> SourceRecord:
    return SourceRecord(
        source=source,
        source_record_id=sid,
        retrieved_at="2024-01-01T00:00:00Z",
        identifiers=ids,
        normalized_fields={"identifiers": ids, **fields},
    )


def test_merge_by_doi():
    r1 = _srecord("pubmed", "p1", {"doi": "10.1000/test", "pmid": "12345"}, title="Paper", year=2023)
    r2 = _srecord("crossref", "c1", {"doi": "10.1000/test"}, title="Paper", year=2023)
    works = merge_records([r1, r2])
    assert len(works) == 1
    work = works[0]
    assert work.identifiers["doi"] == "10.1000/test"
    assert work.identifiers["pmid"] == "12345"
    assert set(work.merged_from_sources) == {"pubmed", "crossref"}
    assert len(work.source_records) == 2


def test_merge_preserves_conflicts():
    r1 = _srecord("pubmed", "p1", {"doi": "10.1000/test"}, title="Title A", year=2023)
    r2 = _srecord("crossref", "c1", {"doi": "10.1000/test"}, title="Title B", year=2023)
    works = merge_records([r1, r2])
    assert len(works) == 1
    assert len(works[0].conflicts) >= 1
    assert any(c.field == "title" for c in works[0].conflicts)


def test_merge_by_title_year_first_author():
    r1 = _srecord("openalex", "o1", {}, title="Unique Title", year=2022, authors=[{"name": "Smith"}])
    r2 = _srecord("pubmed", "p2", {}, title="Unique Title", year=2022, authors=[{"name": "Smith"}])
    works = merge_records([r1, r2])
    assert len(works) == 1


def test_no_merge_different_titles():
    r1 = _srecord("pubmed", "p1", {}, title="Alpha", year=2022)
    r2 = _srecord("pubmed", "p2", {}, title="Beta", year=2022)
    works = merge_records([r1, r2])
    assert len(works) == 2
