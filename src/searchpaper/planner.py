"""Search planning and source routing."""

from __future__ import annotations

from pydantic import BaseModel, Field

from searchpaper.source_catalog import list_source_descriptors


class SearchPlan(BaseModel):
    query: str
    profile: str
    selected_sources: list[str] = Field(default_factory=list)
    fallback_sources: list[str] = Field(default_factory=list)
    ranking_profile: str = "relevance"
    query_variants: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


PROFILE_SOURCES: dict[str, list[str]] = {
    "default": ["pubmed", "crossref", "openalex"],
    "biomedical": ["pubmed", "europepmc", "openalex", "crossref"],
    "cross-disciplinary": ["openalex", "crossref", "semantic_scholar"],
    "preprint": ["arxiv", "biorxiv", "medrxiv", "openalex", "semantic_scholar"],
    "citation": ["semantic_scholar", "openalex", "crossref"],
    "exhaustive": ["pubmed", "europepmc", "crossref", "openalex", "arxiv", "biorxiv", "medrxiv", "semantic_scholar"],
}

BIOMEDICAL_TERMS = {
    "cancer",
    "carcinoma",
    "clinical",
    "disease",
    "drug",
    "gene",
    "hepatocellular",
    "immunotherapy",
    "medicine",
    "patient",
    "protein",
    "therapy",
    "tumor",
}

PREPRINT_TERMS = {"arxiv", "physics", "mathematics", "computer", "algorithm", "graph neural", "preprint"}


def detect_profile(query: str) -> str:
    q = query.lower()
    if any(term in q for term in BIOMEDICAL_TERMS):
        return "biomedical"
    if any(term in q for term in PREPRINT_TERMS):
        return "preprint"
    return "cross-disciplinary"


def plan_search(query: str, profile: str = "default", sort: str | None = None) -> SearchPlan:
    resolved_profile = detect_profile(query) if profile == "auto" else profile
    selected = PROFILE_SOURCES.get(resolved_profile, PROFILE_SOURCES["default"])
    descriptors = {descriptor.name: descriptor for descriptor in list_source_descriptors()}
    implemented = [source for source in selected if descriptors.get(source) and descriptors[source].implemented]
    fallback = [
        descriptor.name
        for descriptor in descriptors.values()
        if descriptor.implemented and descriptor.name not in implemented and descriptor.tier in {"T1", "T2"}
    ]
    manual = [descriptor.name for descriptor in descriptors.values() if not descriptor.implemented]
    warnings = [
        "Manual or unsupported sources are cataloged but not queried automatically: " + ", ".join(manual),
    ]
    return SearchPlan(
        query=query,
        profile=resolved_profile,
        selected_sources=implemented,
        fallback_sources=fallback,
        ranking_profile=sort or "relevance",
        query_variants=[query],
        warnings=warnings,
    )
