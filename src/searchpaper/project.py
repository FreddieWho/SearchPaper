"""Project-level trace and export workflow for SearchPaper."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from searchpaper.config import find_project_dir


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _slug(text: str) -> str:
    """Create a filesystem-safe slug from arbitrary text."""
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "query"


def _trace_id(query: str, timestamp: str) -> str:
    return f"{_slug(query)}-{timestamp.replace(':', '').replace('-', '').replace('.', '')}"


def project_dir() -> Path | None:
    """Return the current SearchPaper project directory, if any."""
    return find_project_dir()


def traces_dir(project: Path | None = None) -> Path | None:
    proj = project or project_dir()
    return proj / "traces" if proj else None


def exports_dir(project: Path | None = None) -> Path | None:
    proj = project or project_dir()
    return proj / "exports" if proj else None


def queries_dir(project: Path | None = None) -> Path | None:
    proj = project or project_dir()
    return proj / "queries" if proj else None


def save_search_trace(
    query: str,
    envelope: dict[str, Any],
    project: Path | None = None,
) -> dict[str, Any]:
    """Save a search result envelope and its trace into the current project."""
    proj = project or project_dir()
    if proj is None:
        raise RuntimeError("Not inside a SearchPaper project. Run `searchpaper init` first.")

    tdir = traces_dir(proj)
    edir = exports_dir(proj)
    qdir = queries_dir(proj)
    if tdir is None or edir is None or qdir is None:
        raise RuntimeError("Project directories are missing.")

    tdir.mkdir(parents=True, exist_ok=True)
    edir.mkdir(parents=True, exist_ok=True)
    qdir.mkdir(parents=True, exist_ok=True)

    timestamp = _now()
    trace_id = _trace_id(query, timestamp)

    trace_entry = {
        "schema_version": envelope.get("schema_version", "0.2"),
        "object_type": "project_trace",
        "trace_id": trace_id,
        "query": query,
        "created_at": timestamp,
        "envelope": envelope,
    }
    trace_path = tdir / f"{trace_id}.json"
    trace_path.write_text(json.dumps(trace_entry, indent=2, ensure_ascii=False), encoding="utf-8")

    result_path = edir / f"{trace_id}.jsonl"
    works = envelope.get("data", {}).get("works", [])
    result_path.write_text(
        "".join(json.dumps(work, ensure_ascii=False) + "\n" for work in works),
        encoding="utf-8",
    )

    query_path = qdir / f"{trace_id}.txt"
    query_path.write_text(query, encoding="utf-8")

    return {
        "trace_id": trace_id,
        "trace_path": str(trace_path),
        "result_path": str(result_path),
        "query_path": str(query_path),
        "work_count": len(works),
    }


def list_traces(project: Path | None = None) -> list[dict[str, Any]]:
    """List saved traces in the current project."""
    tdir = traces_dir(project)
    if tdir is None or not tdir.exists():
        return []

    traces = []
    for path in sorted(tdir.glob("*.json"), reverse=True):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            traces.append(
                {
                    "trace_id": entry.get("trace_id", path.stem),
                    "query": entry.get("query"),
                    "created_at": entry.get("created_at"),
                    "work_count": len(entry.get("envelope", {}).get("data", {}).get("works", [])),
                    "path": str(path),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return traces


def load_trace(trace_id: str, project: Path | None = None) -> dict[str, Any]:
    """Load a saved trace by ID."""
    tdir = traces_dir(project)
    if tdir is None:
        raise RuntimeError("Not inside a SearchPaper project.")

    path = tdir / f"{trace_id}.json"
    if not path.exists():
        # Fall back to prefix search.
        matches = [p for p in tdir.glob("*.json") if p.stem.startswith(trace_id)]
        if not matches:
            raise FileNotFoundError(f"Trace not found: {trace_id}")
        path = sorted(matches, reverse=True)[0]

    return json.loads(path.read_text(encoding="utf-8"))


def export_trace(trace_id: str, fmt: str = "jsonl", project: Path | None = None) -> dict[str, Any]:
    """Export a saved trace to a supported format and return the output content."""
    from searchpaper.export import works_to_format

    trace = load_trace(trace_id, project=project)
    works = trace.get("envelope", {}).get("data", {}).get("works", [])
    content = works_to_format(works, fmt)
    return {
        "trace_id": trace.get("trace_id"),
        "format": fmt,
        "work_count": len(works),
        "content": content,
    }
