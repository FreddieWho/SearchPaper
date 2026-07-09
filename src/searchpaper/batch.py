"""Batch processing for SearchPaper CLI and library callers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from searchpaper.engine import SearchEngine
from searchpaper.exceptions import SourceRequiredError
from searchpaper.export import works_to_format
from searchpaper.identifiers import identify
from searchpaper.schemas import SearchFilters, SourceMode


@dataclass
class BatchItemResult:
    """Result for one batch input item."""

    input: dict[str, Any]
    status: str  # "ok" or "failed"
    envelope: dict[str, Any]
    error: str | None = None


@dataclass
class BatchResult:
    """Aggregated result for a batch run."""

    schema_version: str = "0.2"
    object_type: str = "batch_result"
    items: list[BatchItemResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "data": {
                "items": [
                    {
                        "input": item.input,
                        "status": item.status,
                        "envelope": item.envelope,
                        "error": item.error,
                    }
                    for item in self.items
                ],
                "summary": self.summary,
            },
            "warnings": self.warnings,
            "trace": self.trace,
        }


def _parse_input_line(line: str) -> dict[str, Any]:
    """Parse one input line into a request dict."""
    line = line.strip()
    if not line:
        return {}
    if line.startswith("{"):
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    # Treat plain text as a query.
    return {"query": line}


def _is_identifier_only(item: dict[str, Any]) -> bool:
    """Return True if the item contains an identifier but no query."""
    return "query" not in item and any(k in item for k in ("doi", "pmid", "pmcid", "arxiv"))


def _extract_identifier(item: dict[str, Any]) -> Any:
    """Build a WorkIdentifier from an item dict, or None."""
    for key in ("doi", "pmid", "pmcid", "arxiv"):
        value = item.get(key)
        if value:
            return identify(str(value))
    return None


def _read_input_lines(input_file: Path) -> list[str]:
    """Read lines from a file or stdin."""
    if str(input_file) == "-":
        import sys

        return sys.stdin.read().splitlines()
    return input_file.read_text(encoding="utf-8").splitlines()


async def process_batch(
    input_file: Path,
    engine: SearchEngine,
    output_format: str = "json",
    sources: list[str] | None = None,
    filters: SearchFilters | None = None,
    source_modes: dict[str, SourceMode] | None = None,
) -> str:
    """Process a batch input file and return the serialized output."""
    filters = filters or SearchFilters()
    lines = _read_input_lines(input_file)
    items: list[BatchItemResult] = []
    all_works: list[dict[str, Any]] = []
    aggregated_warnings: list[str] = []
    aggregated_trace: dict[str, Any] = {
        "inputs_processed": 0,
        "sources_requested": sources or engine.sources,
        "source_modes": {k: v.value for k, v in (source_modes or {}).items()},
        "item_traces": [],
    }

    for line in lines:
        item_input = _parse_input_line(line)
        if not item_input:
            continue

        aggregated_trace["inputs_processed"] += 1
        status = "ok"
        error: str | None = None
        envelope: dict[str, Any]

        try:
            if "query" in item_input:
                result = await engine.search(
                    item_input["query"],
                    filters=filters,
                    sources=sources,
                    source_modes=source_modes,
                )
                envelope = result.model_dump(mode="json")
            elif _is_identifier_only(item_input):
                wid = _extract_identifier(item_input)
                if not wid:
                    status = "failed"
                    error = "Could not identify item"
                    envelope = {
                        "schema_version": "0.2",
                        "object_type": "error",
                        "data": {},
                        "warnings": [error],
                        "trace": {},
                    }
                else:
                    result = await engine.resolve(
                        wid,
                        sources=sources,
                        source_modes=source_modes,
                    )
                    envelope = result.model_dump(mode="json")
            else:
                status = "failed"
                error = "Batch item must contain 'query' or an identifier (doi/pmid/pmcid/arxiv)"
                envelope = {
                    "schema_version": "0.2",
                    "object_type": "error",
                    "data": {},
                    "warnings": [error],
                    "trace": {},
                }
        except SourceRequiredError as exc:
            status = "failed"
            error = str(exc)
            envelope = exc.envelope.model_dump(mode="json")
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
            envelope = {
                "schema_version": "0.2",
                "object_type": "error",
                "data": {},
                "warnings": [error],
                "trace": {},
            }

        items.append(BatchItemResult(input=item_input, status=status, envelope=envelope, error=error))
        aggregated_trace["item_traces"].append(envelope.get("trace", {}))
        if envelope.get("warnings"):
            aggregated_warnings.extend(envelope["warnings"])
        if status == "ok" and isinstance(envelope.get("data"), dict):
            all_works.extend(envelope["data"].get("works", []))

    summary = {
        "total": len(items),
        "succeeded": sum(1 for item in items if item.status == "ok"),
        "failed": sum(1 for item in items if item.status == "failed"),
        "works": len(all_works),
    }

    fmt = output_format.lower().strip()
    if fmt == "jsonl":
        return "\n".join(json.dumps(item.envelope, ensure_ascii=False) for item in items) + ("\n" if items else "")
    if fmt in ("bibtex", "ris", "nbib", "enw", "markdown", "zotero", "obsidian"):
        return works_to_format(all_works, fmt)

    # Default JSON envelope.
    result = BatchResult(
        items=items,
        warnings=aggregated_warnings,
        trace=aggregated_trace,
        summary=summary,
    )
    return json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False)
