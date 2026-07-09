"""Custom exceptions for SearchPaper."""

from __future__ import annotations

from searchpaper.schemas import ResponseEnvelope


class SourceRequiredError(Exception):
    """Raised when a source marked as required fails or returns no usable data.

    Carries the partial ResponseEnvelope so callers can still report results,
    provenance, and trace before exiting with a non-zero status.
    """

    def __init__(self, message: str, envelope: ResponseEnvelope) -> None:
        super().__init__(message)
        self.envelope = envelope
