"""SearchPaper — literature-first infrastructure for agent-assisted research."""

__version__ = "0.5.1"

from searchpaper.schemas import (
    Envelope,
    LiteratureSignal,
    MergeDecision,
    ResponseEnvelope,
    SearchFilters,
    SearchResult,
    SearchTrace,
    SourceError,
    SourceRecord,
    SourceStatus,
    WorkIdentifier,
    WorkRecord,
)

__all__ = [
    "__version__",
    "Envelope",
    "LiteratureSignal",
    "MergeDecision",
    "ResponseEnvelope",
    "SearchFilters",
    "SearchResult",
    "SearchTrace",
    "SourceError",
    "SourceRecord",
    "SourceStatus",
    "WorkIdentifier",
    "WorkRecord",
]
