"""Source adapters for SearchPaper."""

# Import adapters to trigger registration.
from searchpaper.sources import (
    arxiv,
    biorxiv,
    crossref,
    europepmc,
    medrxiv,
    openalex,
    pubmed,
    pubtator3,
    semantic_scholar,
)
from searchpaper.sources.base import SourceAdapter
from searchpaper.sources.registry import get_adapter, list_sources, source_status

__all__ = [
    "SourceAdapter",
    "arxiv",
    "biorxiv",
    "crossref",
    "europepmc",
    "get_adapter",
    "list_sources",
    "medrxiv",
    "openalex",
    "pubmed",
    "pubtator3",
    "semantic_scholar",
    "source_status",
]
