"""Trace builder for SearchPaper searches."""

from __future__ import annotations

from typing import Any

from searchpaper.schemas import SearchTrace, SourceError, SourceResultCount


class TraceBuilder:
    """Build a SearchTrace incrementally."""

    def __init__(
        self,
        query: str | None = None,
        filters: dict[str, Any] | None = None,
        sources_requested: list[str] | None = None,
        cache_policy: str = "default",
    ):
        self.trace = SearchTrace(
            query=query,
            filters=filters or {},
            sources_requested=sources_requested or [],
            cache_policy=cache_policy,
        )

    def mark_succeeded(self, source: str) -> None:
        if source not in self.trace.sources_succeeded:
            self.trace.sources_succeeded.append(source)

    def mark_degraded(self, source: str) -> None:
        if source not in self.trace.sources_degraded:
            self.trace.sources_degraded.append(source)

    def mark_failed(self, source: str) -> None:
        if source not in self.trace.sources_failed:
            self.trace.sources_failed.append(source)

    def add_error(self, error: SourceError) -> None:
        self.trace.source_errors.append(error)
        self.mark_failed(error.source)

    def add_source_count(self, count: SourceResultCount) -> None:
        self.trace.source_result_counts.append(count)

    def set_result_counts(self, result_count: int, merged_count: int) -> None:
        self.trace.result_count = result_count
        self.trace.merged_count = merged_count

    def build(self) -> SearchTrace:
        return self.trace
