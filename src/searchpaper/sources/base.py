"""Abstract source adapter contract for SearchPaper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

import httpx

from searchpaper.schemas import (
    FailureClass,
    SearchFilters,
    SourceError,
    SourceRecord,
    SourceState,
    SourceStatus,
    WorkIdentifier,
)


def classify_http_error(status: int, exc: Exception | None = None) -> FailureClass:
    """Classify an HTTP or transport failure."""
    if exc is not None and isinstance(exc, httpx.TimeoutException):
        return FailureClass.TIMEOUT
    if exc is not None and isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
        return FailureClass.NETWORK_ERROR
    if status == 429:
        return FailureClass.RATE_LIMITED
    if status == 401:
        return FailureClass.INVALID_API_KEY
    if status == 403:
        return FailureClass.AUTH_REQUIRED
    if status >= 500:
        return FailureClass.ENDPOINT_UNAVAILABLE
    if status >= 400:
        return FailureClass.UNSUPPORTED_QUERY
    return FailureClass.UNKNOWN_ERROR


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class SourceAdapter(ABC):
    """Common interface every literature source must implement."""

    name: str
    key_required: bool = False
    source_terms_url: str | None = None
    usage_note: str | None = None

    @abstractmethod
    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]: ...

    @abstractmethod
    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None: ...

    @abstractmethod
    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]: ...

    @abstractmethod
    async def status(self) -> SourceStatus: ...

    @abstractmethod
    async def aclose(self) -> None:
        """Adapters may override to close HTTP clients."""
        pass

    def _make_error(
        self,
        operation: str,
        failure_class: FailureClass,
        message: str,
        query_or_identifier: str | None = None,
        retry_count: int = 0,
    ) -> SourceError:
        return SourceError(
            source=self.name,
            operation=operation,
            failure_class=failure_class,
            message=message,
            timestamp=now_iso(),
            query_or_identifier=query_or_identifier,
            retry_count=retry_count,
        )

    def _make_status(
        self,
        state: SourceState,
        key_configured: bool = False,
        message: str = "",
        last_error_class: FailureClass | None = None,
    ) -> SourceStatus:
        return SourceStatus(
            source=self.name,
            state=state,
            key_configured=key_configured,
            key_required=self.key_required,
            last_checked_at=now_iso(),
            last_error_class=last_error_class,
            live_search_available=state in (SourceState.AVAILABLE, SourceState.AVAILABLE_WITH_KEY_OPTIONAL),
            fixture_tests_available=True,
            message=message,
            usage_note=self.usage_note,
            source_terms_url=self.source_terms_url,
        )
