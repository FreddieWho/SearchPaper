"""Tests for ranking profiles."""

from searchpaper.rank import rank_works
from searchpaper.schemas import WorkRecord


def _work(title: str, year: int, citations: int, abstract: str = "") -> WorkRecord:
    return WorkRecord(
        work_id=title,
        title=title,
        year=year,
        abstract=abstract or title,
        citation_count=citations,
        merged_from_sources=["test"],
    )


def test_rank_works_supports_date_sort():
    older = _work("Relevant older paper", 2010, 200)
    newer = _work("Relevant newer paper", 2024, 10)

    ranked = rank_works([older, newer], query="relevant paper", sort="date")

    assert ranked[0].work_id == "Relevant newer paper"


def test_rank_works_supports_citation_sort_with_relevance_floor():
    relevant = _work("Graph neural network potentials", 2021, 50)
    off_topic = _work("Cancer immunotherapy review", 2024, 5000)

    ranked = rank_works([off_topic, relevant], query="graph neural network potentials", sort="citations")

    assert ranked[0].work_id == "Graph neural network potentials"
