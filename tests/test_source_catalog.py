"""Tests for source catalog and search planning."""

from searchpaper.planner import plan_search
from searchpaper.source_catalog import get_source_descriptor, list_source_descriptors


def test_source_catalog_includes_implemented_and_manual_sources():
    names = {descriptor.name for descriptor in list_source_descriptors()}

    assert {"pubmed", "crossref", "openalex", "arxiv", "biorxiv", "medrxiv"}.issubset(names)
    assert {"scopus", "webofscience", "google_scholar", "cnki", "wanfang"}.issubset(names)
    assert get_source_descriptor("google_scholar").implemented is False
    assert get_source_descriptor("google_scholar").tier == "T3"


def test_plan_search_routes_profiles_and_warns_about_manual_sources():
    plan = plan_search("graph neural network potentials", profile="preprint", sort="date")

    assert plan.profile == "preprint"
    assert "arxiv" in plan.selected_sources
    assert "google_scholar" not in plan.selected_sources
    assert plan.ranking_profile == "date"
    assert any("manual" in warning.lower() or "unsupported" in warning.lower() for warning in plan.warnings)


def test_plan_search_auto_detects_biomedical_queries():
    plan = plan_search("hepatocellular carcinoma immunotherapy", profile="auto")

    assert plan.profile == "biomedical"
    assert "pubmed" in plan.selected_sources
    assert "biorxiv" in plan.fallback_sources or "medrxiv" in plan.fallback_sources
