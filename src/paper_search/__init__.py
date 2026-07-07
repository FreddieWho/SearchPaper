"""Compatibility shim for the legacy ``paper_search`` package.

New code should import from ``searchpaper`` directly. This module re-exports the
canonical API and CLI so existing ``paper-search`` entry points continue to work.
"""

import warnings

from searchpaper import (
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
    __version__,
)
from searchpaper.cache import Cache
from searchpaper.config import ensure_config_dir, load_config
from searchpaper.http import HTTPClient
from searchpaper.normalize import normalize_entity, normalize_paper, normalize_relation
from searchpaper.schemas import UnifiedEntity, UnifiedPaper, UnifiedRelation

warnings.warn(
    "paper_search is deprecated; use searchpaper instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "__version__",
    "Cache",
    "ensure_config_dir",
    "Envelope",
    "HTTPClient",
    "load_config",
    "LiteratureSignal",
    "MergeDecision",
    "normalize_entity",
    "normalize_paper",
    "normalize_relation",
    "ResponseEnvelope",
    "SearchFilters",
    "SearchResult",
    "SearchTrace",
    "SourceError",
    "SourceRecord",
    "SourceStatus",
    "UnifiedEntity",
    "UnifiedPaper",
    "UnifiedRelation",
    "WorkIdentifier",
    "WorkRecord",
]
