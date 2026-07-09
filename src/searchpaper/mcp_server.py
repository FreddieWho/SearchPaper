"""MCP server for SearchPaper."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from searchpaper.config import load_config
from searchpaper.engine import SearchEngine
from searchpaper.exceptions import SourceRequiredError
from searchpaper.identifiers import identify
from searchpaper.planner import plan_search
from searchpaper.pubmed_utils import convert_ids as pubmed_convert_ids
from searchpaper.pubmed_utils import lookup_mesh as pubmed_lookup_mesh
from searchpaper.pubmed_utils import related_articles as pubmed_related_articles
from searchpaper.schemas import SearchFilters, SourceMode
from searchpaper.source_catalog import list_source_descriptors

_config = load_config()
_engine = SearchEngine()


def _parse_mcp_source_modes(source_modes: dict[str, str] | None) -> dict[str, SourceMode]:
    """Convert MCP string-valued source modes into typed SourceMode values."""
    if not source_modes:
        return {}
    result: dict[str, SourceMode] = {}
    for source, mode_str in source_modes.items():
        mode_str = str(mode_str).strip().lower()
        try:
            result[source.lower()] = SourceMode(mode_str)
        except ValueError:
            pass
    return result


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    yield


mcp = FastMCP("searchpaper", lifespan=_lifespan)


@mcp.tool()
async def search_literature(
    query: str,
    sources: list[str] | None = None,
    limit: int = 20,
    year: str | None = None,
    venue: str | None = None,
    min_citation_count: int | None = None,
    open_access_only: bool = False,
    no_cache: bool = False,
    profile: str = "default",
    sort: str = "relevance",
    source_modes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Search open scholarly literature across configured sources."""
    planned_sources = sources
    if planned_sources is None and profile != "default":
        planned_sources = plan_search(query, profile=profile, sort=sort).selected_sources
    modes = _parse_mcp_source_modes(source_modes)
    filters = SearchFilters(
        limit=limit,
        year=year,
        venue=venue,
        min_citation_count=min_citation_count,
        open_access_only=open_access_only,
        sort=sort,
        source_modes=modes,
    )
    try:
        result = await _engine.search(
            query=query,
            filters=filters,
            sources=planned_sources or ["pubmed", "crossref", "openalex"],
            no_cache=no_cache,
        )
    except SourceRequiredError as exc:
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": exc.envelope.data,
            "warnings": [*exc.envelope.warnings, str(exc)],
            "trace": exc.envelope.trace,
        }
    return result.model_dump(mode="json")


@mcp.tool()
async def plan_literature_search(query: str, profile: str = "default", sort: str = "relevance") -> dict[str, Any]:
    """Plan source routing and ranking without running a live search."""
    plan = plan_search(query, profile=profile, sort=sort)
    return {
        "schema_version": "0.2",
        "object_type": "search_plan",
        "data": plan.model_dump(mode="json"),
        "warnings": plan.warnings,
        "trace": {},
    }


@mcp.tool()
async def get_work(
    identifier: str,
    identifier_type: str | None = None,
    sources: list[str] | None = None,
    source_modes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Get a work by identifier (DOI, PMID, PMCID, arXiv, etc.)."""
    wid = identify(identifier)
    if not wid:
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": {"error": f"Could not identify: {identifier}"},
            "warnings": [],
            "trace": {},
        }
    modes = _parse_mcp_source_modes(source_modes)
    try:
        result = await _engine.get(wid, sources=sources, source_modes=modes)
    except SourceRequiredError as exc:
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": exc.envelope.data,
            "warnings": [*exc.envelope.warnings, str(exc)],
            "trace": exc.envelope.trace,
        }
    return result.model_dump(mode="json")


@mcp.tool()
async def resolve_identifiers(
    identifiers: list[str],
    sources: list[str] | None = None,
    source_modes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve a list of identifiers across sources and return merged records."""
    works = []
    trace_accumulated: dict[str, Any] = {}
    warnings: list[str] = []
    modes = _parse_mcp_source_modes(source_modes)
    required_failures: list[str] = []
    for raw in identifiers:
        wid = identify(raw)
        if not wid:
            warnings.append(f"Could not identify: {raw}")
            continue
        try:
            result = await _engine.resolve(wid, sources=sources, source_modes=modes)
        except SourceRequiredError as exc:
            required_failures.append(str(exc))
            data = exc.envelope.data if hasattr(exc.envelope, "data") else exc.envelope.get("data", {})
            trace = exc.envelope.trace if hasattr(exc.envelope, "trace") else exc.envelope.get("trace", {})
            works.extend(data.get("works", []))
            warnings.extend(
                exc.envelope.warnings if hasattr(exc.envelope, "warnings") else exc.envelope.get("warnings", [])
            )
            trace_accumulated = trace
            continue
        data = result.data if hasattr(result, "data") else result.get("data", {})
        trace = result.trace if hasattr(result, "trace") else result.get("trace", {})
        works.extend(data.get("works", []))
        warnings.extend(result.warnings if hasattr(result, "warnings") else result.get("warnings", []))
        trace_accumulated = trace

    if required_failures:
        warnings.extend(required_failures)
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": {"works": works, "count": len(works)},
            "warnings": warnings,
            "trace": trace_accumulated,
        }

    return {
        "schema_version": "0.2",
        "object_type": "resolve_result",
        "data": {"works": works, "count": len(works)},
        "warnings": warnings,
        "trace": trace_accumulated,
    }


@mcp.tool()
async def get_source_status(include_catalog: bool = False) -> dict[str, Any]:
    """Return the health status of all configured sources."""
    result = await _engine.source_statuses()
    data = result.model_dump(mode="json")
    if include_catalog:
        data["source_catalog"] = [descriptor.model_dump(mode="json") for descriptor in list_source_descriptors()]
    return data


@mcp.tool()
async def lookup_mesh(term: str, limit: int = 10) -> dict[str, Any]:
    """Lookup MeSH descriptors for a biomedical term."""
    data = await pubmed_lookup_mesh(term, limit=limit)
    return {
        "schema_version": "0.2",
        "object_type": "mesh_lookup",
        "data": data,
        "warnings": [],
        "trace": {},
    }


@mcp.tool()
async def find_related_articles(pmid: str, limit: int = 20) -> dict[str, Any]:
    """Find PubMed related article PMIDs."""
    data = await pubmed_related_articles(pmid, limit=limit)
    return {
        "schema_version": "0.2",
        "object_type": "related_articles",
        "data": data,
        "warnings": [],
        "trace": {},
    }


@mcp.tool()
async def convert_identifiers(identifiers: list[str]) -> dict[str, Any]:
    """Convert DOI/PMID/PMCID identifiers through the NCBI ID converter."""
    result = await pubmed_convert_ids(identifiers)
    return {
        "schema_version": "0.2",
        "object_type": "identifier_conversion",
        "data": result.get("records", []),
        "warnings": result.get("warnings", []),
        "trace": {},
    }


@mcp.tool()
async def search_literature_signals(
    query: str | None = None,
    entity1: str | None = None,
    entity2: str | None = None,
    relation_type: str = "interact",
    entity2_type: str = "chemical",
    limit: int = 10,
) -> dict[str, Any]:
    """Search biomedical literature signals via PubTator3."""
    q = query or entity1
    if not q:
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": {"error": "Provide query or entity1"},
            "warnings": ["No query or entity1 provided"],
            "trace": {},
        }
    result = await _engine.signals(
        query=q,
        entity1=entity1,
        entity2=entity2,
        relation_type=relation_type,
        entity2_type=entity2_type,
        limit=limit,
    )
    return result.model_dump(mode="json")


@mcp.tool()
async def expand_from_work(
    identifier: str,
    by: list[str] | None = None,
    sources: list[str] | None = None,
    limit: int = 20,
    source_modes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Expand from a known work by citations, references, or similar papers."""
    wid = identify(identifier)
    if not wid:
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": {"error": f"Could not identify: {identifier}"},
            "warnings": [],
            "trace": {},
        }
    modes = _parse_mcp_source_modes(source_modes)
    try:
        result = await _engine.expand(wid, by=by, limit=limit, source_modes=modes)
    except SourceRequiredError as exc:
        return {
            "schema_version": "0.2",
            "object_type": "error",
            "data": exc.envelope.data,
            "warnings": [*exc.envelope.warnings, str(exc)],
            "trace": exc.envelope.trace,
        }
    data = result.data if hasattr(result, "data") else result.get("data", {})
    works = data.get("works", [])
    return {
        "schema_version": "0.2",
        "object_type": "expand_result",
        "data": {"works": works, "by": by or [], "count": len(works)},
        "warnings": result.warnings if hasattr(result, "warnings") else result.get("warnings", []),
        "trace": result.trace if hasattr(result, "trace") else result.get("trace", {}),
    }


@mcp.tool()
async def export_records(
    works: list[dict[str, Any]],
    format: str = "jsonl",
) -> dict[str, Any]:
    """Export a list of works to a supported format."""
    from searchpaper.export import works_to_format

    output = works_to_format(works, format)
    return {
        "schema_version": "0.2",
        "object_type": "export_result",
        "data": {"format": format, "content": output},
        "warnings": [],
        "trace": {},
    }


def main(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000, path: str = "/mcp") -> None:
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "http":
        _run_http_server(host=host, port=port, path=path)
    else:
        raise ValueError(f"Unsupported MCP transport: {transport}")


def create_http_app(path: str = "/mcp") -> Any:
    """Create a Starlette application exposing the MCP server over SSE."""
    try:
        from starlette.applications import Starlette
        from starlette.routing import Route
    except ImportError as exc:
        raise ImportError(
            "Remote MCP server requires 'starlette' and 'uvicorn'. Install with: uv pip install 'searchpaper[remote]'"
        ) from exc

    from mcp.server.sse import SseServerTransport

    sse = SseServerTransport(f"{path}/messages/")

    class _SseHandler:
        async def __call__(self, scope, receive, send):
            async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await mcp._mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp._mcp_server.create_initialization_options(),
                )

    class _MessagesHandler:
        async def __call__(self, scope, receive, send):
            await sse.handle_post_message(scope, receive, send)

    return Starlette(
        debug=False,
        routes=[
            Route(f"{path}/sse", endpoint=_SseHandler()),
            Route(f"{path}/messages/", endpoint=_MessagesHandler(), methods=["POST"]),
        ],
    )


def _run_http_server(host: str, port: int, path: str) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(
            "Remote MCP server requires 'starlette' and 'uvicorn'. Install with: uv pip install 'searchpaper[remote]'"
        ) from exc

    app = create_http_app(path=path)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
