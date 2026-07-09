"""Tests for search planning and strategy templates."""

from searchpaper.planner import plan_search


def test_plan_search_includes_domain_templates():
    plan = plan_search("CRISPR knockout screening", profile="molecular")
    assert plan.profile == "molecular"
    assert "CRISPR knockout screening" in plan.query_variants
    assert any("gene expression" in variant for variant in plan.query_variants)


def test_plan_search_combined_sort_is_exposed():
    plan = plan_search("machine learning", profile="cross-disciplinary", sort="combined")
    assert plan.ranking_profile == "combined"


def test_plan_search_defaults_to_single_variant():
    plan = plan_search("deep learning", profile="preprint")
    assert plan.query_variants == ["deep learning"]
