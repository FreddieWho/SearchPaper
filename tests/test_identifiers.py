"""Tests for identifier normalization."""

from searchpaper.identifiers import (
    identify,
    normalize_arxiv,
    normalize_doi,
    normalize_pmcid,
    normalize_pmid,
    work_id_from_identifiers,
)
from searchpaper.schemas import IdentifierType


def test_normalize_doi():
    assert normalize_doi("  10.1000/test  ") == "10.1000/test"
    assert normalize_doi("doi: 10.1000/test") == "10.1000/test"
    assert normalize_doi("not a doi") is None


def test_normalize_pmid():
    assert normalize_pmid("12345678") == "12345678"
    assert normalize_pmid("pmid:12345678") == "12345678"
    assert normalize_pmid("abc") is None


def test_normalize_pmcid():
    assert normalize_pmcid("PMC12345") == "PMC12345"
    assert normalize_pmcid("pmcid:12345") == "PMC12345"
    assert normalize_pmcid("12345") is None


def test_normalize_arxiv():
    assert normalize_arxiv("2401.00001") == "2401.00001"
    assert normalize_arxiv("arxiv:2401.00001") == "2401.00001"
    assert normalize_arxiv("notarxiv") is None


def test_identify():
    assert identify("10.1000/test").type == IdentifierType.DOI
    assert identify("12345678").type == IdentifierType.PMID
    assert identify("PMC12345").type == IdentifierType.PMCID
    assert identify("2401.00001").type == IdentifierType.ARXIV


def test_work_id_from_identifiers():
    assert work_id_from_identifiers({"doi": "10.1000/test"}) == "work:doi:10.1000/test"
    assert work_id_from_identifiers({"pmid": "12345"}) == "work:pmid:12345"
