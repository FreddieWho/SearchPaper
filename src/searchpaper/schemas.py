"""Stable Pydantic v2 schemas for SearchPaper.

Every major machine output should include ``schema_version``, ``object_type``,
``data``, ``warnings``, and ``trace``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "0.2"
MERGE_STRATEGY_VERSION = "0.2.0"
RANKING_STRATEGY_VERSION = "0.2.0"


class SignalLevel(StrEnum):
    """Explicit signal level per the SearchPaper signal-level policy."""

    BIBLIOGRAPHIC = "bibliographic"
    ABSTRACT = "abstract"
    CURATED_OR_EXTRACTED = "curated_or_extracted"
    FULL_TEXT_ANCHOR = "full_text_anchor"
    EVALUATED_EVIDENCE = "evaluated_evidence"


class SignalType(StrEnum):
    """Types of literature-backed signals."""

    BIBLIOGRAPHIC_MATCH = "bibliographic_match"
    CO_MENTION = "co_mention"
    REPORTED_RELATION = "reported_relation"
    CURATED_RELATION = "curated_relation"
    CITATION_LINK = "citation_link"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    ENTITY_ANNOTATION = "entity_annotation"


class FailureClass(StrEnum):
    """Classification for source failures."""

    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    AUTH_REQUIRED = "auth_required"
    INVALID_API_KEY = "invalid_api_key"
    ENDPOINT_UNAVAILABLE = "endpoint_unavailable"
    SCHEMA_CHANGED = "schema_changed"
    EMPTY_RESULT = "empty_result"
    UNSUPPORTED_QUERY = "unsupported_query"
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN_ERROR = "unknown_error"


class SourceState(StrEnum):
    """Health state reported by a source adapter."""

    AVAILABLE = "available"
    AVAILABLE_WITH_KEY_OPTIONAL = "available_with_key_optional"
    AVAILABLE_WITH_KEY_REQUIRED = "available_with_key_required"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    OFFLINE = "offline"
    NOT_CONFIGURED = "not_configured"
    NOT_IMPLEMENTED = "not_implemented"


class IdentifierType(StrEnum):
    """Supported identifier kinds."""

    DOI = "doi"
    PMID = "pmid"
    PMCID = "pmcid"
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    CROSSREF = "crossref"
    EUROPEPMC = "europepmc"
    PUBTATOR3 = "pubtator3"
    SOURCE_SPECIFIC = "source_specific"


class WorkIdentifier(BaseModel):
    """A typed scholarly identifier."""

    model_config = ConfigDict(extra="forbid")

    type: IdentifierType
    value: str = Field(..., min_length=1)
    normalized: str | None = None
    source: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.normalized is None:
            self.normalized = self.value.lower().strip()


class Author(BaseModel):
    """Normalized author representation."""

    model_config = ConfigDict(extra="allow")

    name: str
    first_name: str | None = None
    last_name: str | None = None
    orcid: str | None = None
    affiliations: list[str] = Field(default_factory=list)
    source_ids: dict[str, str] = Field(default_factory=dict)


class SourceRecord(BaseModel):
    """A raw or near-raw source response mapped into a uniform envelope."""

    model_config = ConfigDict(extra="allow")

    source: str
    source_record_id: str
    retrieved_at: str
    query_or_identifier: str | None = None
    raw_record: dict[str, Any] = Field(default_factory=dict)
    normalized_fields: dict[str, Any] = Field(default_factory=dict)
    identifiers: dict[str, str] = Field(default_factory=dict)
    usage_note: str | None = None
    source_terms_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    from_cache: bool = False


class ProvenanceEntry(BaseModel):
    """One provenance entry describing where a field value came from."""

    source: str
    source_record_id: str
    field: str
    value: Any
    retrieved_at: str


class SourceConflict(BaseModel):
    """A conflict between sources for a given field."""

    field: str
    values: list[Any]
    sources: list[str]
    resolution: str = "preserved"


class Anchor(BaseModel):
    """Anchor pointing to a specific location in a source document."""

    model_config = ConfigDict(extra="allow")

    anchor_type: str = Field(default="metadata")
    text_scope: str | None = None
    section: str | None = None
    anchor_text: str | None = None
    url: str | None = None


class FullTextAvailability(BaseModel):
    """Report whether and where full text is available without downloading it."""

    has_full_text: bool = False
    has_pdf: bool = False
    sources: list[str] = Field(default_factory=list)
    oa_url: str | None = None
    oa_pdf_url: str | None = None
    license: str | None = None
    notes: list[str] = Field(default_factory=list)


class WorkRecord(BaseModel):
    """A normalized, merged scholarly work."""

    model_config = ConfigDict(extra="allow")

    work_id: str
    title: str | None = None
    normalized_title: str | None = None
    year: int | None = None
    publication_date: str | None = None
    venue: str | None = None
    authors: list[Author] = Field(default_factory=list)
    abstract: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    source_records: list[SourceRecord] = Field(default_factory=list)
    merged_from_sources: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    conflicts: list[SourceConflict] = Field(default_factory=list)
    merge_reasons: list[str] = Field(default_factory=list)
    ranking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    urls: dict[str, str] = Field(default_factory=dict)
    open_access_pdf: dict[str, Any] | None = None
    full_text_availability: FullTextAvailability | None = None
    full_text_anchors: list[Anchor] = Field(default_factory=list)
    citation_count: int | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)


class MergeDecision(BaseModel):
    """Record of why two works were merged or kept separate."""

    work_ids: list[str]
    merged: bool
    reason: str
    confidence: str = "low"
    shared_identifiers: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SourceError(BaseModel):
    """Structured error from a single source."""

    source: str
    operation: str
    failure_class: FailureClass
    message: str
    timestamp: str
    retry_count: int = 0
    fallback_used: bool = False
    query_or_identifier: str | None = None


class SourceStatus(BaseModel):
    """Status reported by a source adapter."""

    source: str
    state: SourceState
    key_configured: bool = False
    key_required: bool = False
    last_checked_at: str | None = None
    last_error_class: FailureClass | None = None
    live_search_available: bool = True
    fixture_tests_available: bool = True
    message: str = ""
    usage_note: str | None = None
    source_terms_url: str | None = None


class SearchFilters(BaseModel):
    """Filters that may be applied to a search."""

    model_config = ConfigDict(extra="allow")

    year: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    venue: str | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    min_citation_count: int | None = None
    open_access_only: bool = False
    limit: int = Field(default=20, ge=1, le=200)
    sort: str | None = None


class SourceResultCount(BaseModel):
    """Result counts per source."""

    source: str
    requested: bool
    succeeded: bool
    degraded: bool = False
    failed: bool = False
    from_cache: bool = False
    returned_count: int = 0
    merged_count: int = 0


class SearchTrace(BaseModel):
    """Reproducibility and source-behavior trace for a search."""

    query: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    sources_requested: list[str] = Field(default_factory=list)
    sources_succeeded: list[str] = Field(default_factory=list)
    sources_degraded: list[str] = Field(default_factory=list)
    sources_failed: list[str] = Field(default_factory=list)
    source_errors: list[SourceError] = Field(default_factory=list)
    source_result_counts: list[SourceResultCount] = Field(default_factory=list)
    retrieved_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"))
    cache_policy: str = "default"
    merge_strategy_version: str = MERGE_STRATEGY_VERSION
    ranking_strategy_version: str = RANKING_STRATEGY_VERSION
    result_count: int = 0
    merged_count: int = 0


class LiteratureSignal(BaseModel):
    """A structured, provenance-linked literature signal, not an evaluated conclusion."""

    model_config = ConfigDict(extra="allow")

    signal_id: str
    signal_type: SignalType
    signal_level: SignalLevel
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relation_label: str | None = None
    supporting_work_ids: list[str] = Field(default_factory=list)
    source: str
    anchor: Anchor = Field(default_factory=Anchor)
    confidence_or_score: float | None = None
    interpretation_warning: str = "This is a literature-backed signal, not evaluated scientific evidence."
    provenance: list[ProvenanceEntry] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Top-level search result."""

    works: list[WorkRecord] = Field(default_factory=list)
    signals: list[LiteratureSignal] = Field(default_factory=list)
    trace: SearchTrace = Field(default_factory=SearchTrace)
    warnings: list[str] = Field(default_factory=list)
    total: int | None = None
    next_offset: str | None = None


class Envelope(BaseModel):
    """Generic envelope for any machine output."""

    schema_version: str = SCHEMA_VERSION
    object_type: str
    data: Any
    warnings: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)


class ResponseEnvelope(Envelope):
    """Convenience envelope for typed responses."""

    object_type: str = "response"


def make_envelope(
    data: Any,
    object_type: str = "response",
    warnings: list[str] | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a plain-dict envelope."""
    return {
        "schema_version": SCHEMA_VERSION,
        "object_type": object_type,
        "data": data,
        "warnings": warnings or [],
        "trace": trace or {},
    }


# Backward-compatibility aliases for legacy package users.


class UnifiedPaper(BaseModel):
    paper_id: str
    title: str
    year: int | None = None
    publication_date: str | None = None
    venue: str | None = None
    url: str | None = None
    doi: str | None = None
    pmid: str | None = None
    arxiv: str | None = None
    citation_count: int | None = None
    influential_citation_count: int | None = None
    authors: list[dict[str, Any]] = Field(default_factory=list)
    open_access_pdf: dict[str, Any] | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    abstract: str | None = None
    tldr: str | None = None
    source: str = "semantic_scholar"


class UnifiedEntity(BaseModel):
    entity_id: str
    name: str | None = None
    type: str | None = None
    source: str = "pubtator3"


class EvidenceUrl(BaseModel):
    pmid: str
    pubmed_url: str
    pubtator_url: str


class UnifiedRelation(BaseModel):
    entity1: UnifiedEntity
    entity2: UnifiedEntity
    relation_type: str
    pmids: list[str] = Field(default_factory=list)
    evidence_urls: list[EvidenceUrl] = Field(default_factory=list)
    source: str = "pubtator3"


def make_search_envelope(result: SearchResult, warnings: list[str] | None = None) -> dict[str, Any]:
    return make_envelope(
        data=result.model_dump(mode="json"),
        object_type="search_result",
        warnings=warnings or result.warnings,
        trace=result.trace.model_dump(mode="json"),
    )
