"""CLI surface for SearchPaper."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from searchpaper import __version__
from searchpaper.cache import Cache
from searchpaper.citation_parser import verify_document
from searchpaper.config import DEFAULT_CONFIG_DIR, DEFAULT_PROJECT_DIR, find_project_dir, get_cache_path, load_config
from searchpaper.engine import SearchEngine
from searchpaper.exceptions import SourceRequiredError
from searchpaper.fulltext import download_full_text
from searchpaper.identifiers import identify
from searchpaper.planner import plan_search
from searchpaper.project import save_search_trace
from searchpaper.schemas import SearchFilters, SourceMode
from searchpaper.source_catalog import list_source_descriptors
from searchpaper.sources import list_sources

app = typer.Typer(name="searchpaper", help="SearchPaper — literature search for agents and researchers")
console = Console(markup=False, highlight=False, soft_wrap=True)

DEFAULT_SEARCH_SOURCES = "pubmed,crossref,openalex"
DEFAULT_GET_SOURCES = "pubmed,crossref,openalex,semantic_scholar"


def _engine() -> SearchEngine:
    return SearchEngine()


def _print_json(data: Any) -> None:
    console.print(json.dumps(data, indent=2, ensure_ascii=False))


def _parse_source_modes(
    require: str | None = None,
    source_mode: str | None = None,
) -> dict[str, SourceMode]:
    """Build a source-name → SourceMode map from CLI options.

    ``--require pubmed,crossref`` is shorthand for ``--source-mode pubmed:required,crossref:required``.
    """
    modes: dict[str, SourceMode] = {}
    if require:
        for source in require.split(","):
            source = source.strip().lower()
            if source:
                modes[source] = SourceMode.REQUIRED
    if source_mode:
        for part in source_mode.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                continue
            source, mode_str = part.split(":", 1)
            source = source.strip().lower()
            mode_str = mode_str.strip().lower()
            if source:
                try:
                    modes[source] = SourceMode(mode_str)
                except ValueError:
                    pass
    return modes


def _parse_install_mode(mode: str | None) -> list[str] | None:
    """Convert CLI --mode value into a list of install modes."""
    if not mode:
        return None
    valid = {"mcp", "skill", "custom_tool"}
    chosen = [m.strip().lower() for m in mode.split(",") if m.strip()]
    if "both" in chosen:
        return ["mcp", "skill"]
    return [m for m in chosen if m in valid] or None


def _filters(
    year: str | None = None,
    venue: str | None = None,
    min_citation_count: int | None = None,
    open_access_only: bool = False,
    limit: int = 20,
    sort: str | None = None,
    source_modes: dict[str, SourceMode] | None = None,
) -> SearchFilters:
    return SearchFilters(
        year=year,
        venue=venue,
        min_citation_count=min_citation_count,
        open_access_only=open_access_only,
        limit=limit,
        sort=sort,
        source_modes=source_modes or {},
    )


@app.command("plan")
def plan(
    query: str = typer.Argument(..., help="Search query"),
    profile: str = typer.Option("default", "--profile", help="Search profile"),
    sort: str = typer.Option("relevance", "--sort", help="Ranking profile"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Plan source routing without running a live search."""
    result = plan_search(query, profile=profile, sort=sort)
    _print_json(result.model_dump(mode="json"))


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    sources: str = typer.Option(DEFAULT_SEARCH_SOURCES, "--sources", help="Comma-separated source names"),
    limit: int = typer.Option(20, "--limit", help="Maximum results"),
    year: str | None = typer.Option(None, "--year", help="Filter by year"),
    venue: str | None = typer.Option(None, "--venue", help="Filter by venue"),
    min_citation_count: int | None = typer.Option(None, "--min-citations", help="Minimum citation count"),
    open_access_only: bool = typer.Option(False, "--oa-only", help="Open access only"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache"),
    profile: str = typer.Option("default", "--profile", help="Search profile"),
    sort: str = typer.Option("relevance", "--sort", help="Ranking mode"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON envelope"),
    save: bool = typer.Option(False, "--save", help="Save trace and results when inside a project"),
    require: str | None = typer.Option(None, "--require", help="Comma-separated required sources"),
    source_mode: str | None = typer.Option(
        None,
        "--source-mode",
        help="Comma-separated source:mode pairs (optional/preferred/required)",
    ),
):
    """Search open scholarly literature."""
    if sources == DEFAULT_SEARCH_SOURCES and profile != "default":
        source_list = plan_search(query, profile=profile, sort=sort).selected_sources
    else:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
    modes = _parse_source_modes(require=require, source_mode=source_mode)
    filters = _filters(
        year=year,
        venue=venue,
        min_citation_count=min_citation_count,
        open_access_only=open_access_only,
        limit=limit,
        sort=sort,
        source_modes=modes,
    )
    try:
        result = asyncio.run(_engine().search(query, filters=filters, sources=source_list, no_cache=no_cache))
    except SourceRequiredError as exc:
        _print_json(exc.envelope.model_dump(mode="json"))
        raise typer.Exit(code=1) from exc
    envelope = result.model_dump(mode="json")
    if save:
        if find_project_dir() is None:
            console.print("[yellow]Warning:[/yellow] --save ignored; not inside a SearchPaper project.")
        else:
            try:
                saved = save_search_trace(query, envelope)
                console.print(f"Saved trace {saved['trace_id']} ({saved['work_count']} works)")
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Failed to save trace:[/red] {exc}")
    _print_json(envelope)


@app.command("get")
def get_work(
    pmid: str | None = typer.Option(None, "--pmid", help="PubMed ID"),
    doi: str | None = typer.Option(None, "--doi", help="DOI"),
    pmcid: str | None = typer.Option(None, "--pmcid", help="PubMed Central ID"),
    arxiv: str | None = typer.Option(None, "--arxiv", help="arXiv ID"),
    sources: str = typer.Option(DEFAULT_GET_SOURCES, "--sources", help="Comma-separated source names"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON envelope"),
    anchors: bool = typer.Option(False, "--anchors", help="Fetch full-text anchors when available"),
    download_pdf: Path | None = typer.Option(None, "--download-pdf", help="Download OA PDF to this path"),
    download_xml: Path | None = typer.Option(None, "--download-xml", help="Download Europe PMC XML to this path"),
    require: str | None = typer.Option(None, "--require", help="Comma-separated required sources"),
    source_mode: str | None = typer.Option(
        None,
        "--source-mode",
        help="Comma-separated source:mode pairs (optional/preferred/required)",
    ),
):
    """Get a work by identifier."""
    raw = pmid or doi or pmcid or arxiv
    if not raw:
        console.print("[red]Error:[/red] provide one of --pmid, --doi, --pmcid, --arxiv")
        raise typer.Exit(code=2)
    identifier = identify(raw)
    if not identifier:
        console.print(f"[red]Error:[/red] Could not identify: {raw}")
        raise typer.Exit(code=2)
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    modes = _parse_source_modes(require=require, source_mode=source_mode)
    try:
        result = asyncio.run(_engine().get(identifier, sources=source_list, anchors=anchors, source_modes=modes))
    except SourceRequiredError as exc:
        _print_json(exc.envelope.model_dump(mode="json"))
        raise typer.Exit(code=1) from exc

    output = result.model_dump(mode="json")
    works = output.get("data", {}).get("works", [])
    if (download_pdf or download_xml) and works:
        downloads = asyncio.run(download_full_text(works[0], pdf_path=download_pdf, xml_path=download_xml))
        output["downloads"] = downloads
    _print_json(output)


@app.command("resolve")
def resolve(
    doi: str | None = typer.Option(None, "--doi", help="DOI"),
    pmid: str | None = typer.Option(None, "--pmid", help="PMID"),
    sources: str = typer.Option(DEFAULT_GET_SOURCES, "--sources", help="Comma-separated source names"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON envelope"),
    anchors: bool = typer.Option(False, "--anchors", help="Fetch full-text anchors when available"),
    require: str | None = typer.Option(None, "--require", help="Comma-separated required sources"),
    source_mode: str | None = typer.Option(
        None,
        "--source-mode",
        help="Comma-separated source:mode pairs (optional/preferred/required)",
    ),
):
    """Resolve an identifier across sources."""
    raw = doi or pmid
    if not raw:
        console.print("[red]Error:[/red] provide --doi or --pmid")
        raise typer.Exit(code=2)
    identifier = identify(raw)
    if not identifier:
        console.print(f"[red]Error:[/red] Could not identify: {raw}")
        raise typer.Exit(code=2)
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    modes = _parse_source_modes(require=require, source_mode=source_mode)
    try:
        result = asyncio.run(_engine().resolve(identifier, sources=source_list, anchors=anchors, source_modes=modes))
    except SourceRequiredError as exc:
        _print_json(exc.envelope.model_dump(mode="json"))
        raise typer.Exit(code=1) from exc
    _print_json(result.model_dump(mode="json"))


@app.command("expand")
def expand(
    doi: str | None = typer.Option(None, "--doi", help="DOI"),
    pmid: str | None = typer.Option(None, "--pmid", help="PMID"),
    arxiv: str | None = typer.Option(None, "--arxiv", help="arXiv ID"),
    by: str = typer.Option("citations", "--by", help="Comma-separated: citations,references,similar"),
    limit: int = typer.Option(20, "--limit", help="Maximum results"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON envelope"),
    require: str | None = typer.Option(None, "--require", help="Comma-separated required sources"),
    source_mode: str | None = typer.Option(
        None,
        "--source-mode",
        help="Comma-separated source:mode pairs (optional/preferred/required)",
    ),
):
    """Expand from a known work by citations, references, or similar papers."""
    raw = doi or pmid or arxiv
    if not raw:
        console.print("[red]Error:[/red] provide --doi, --pmid, or --arxiv")
        raise typer.Exit(code=2)
    identifier = identify(raw)
    if not identifier:
        console.print(f"[red]Error:[/red] Could not identify: {raw}")
        raise typer.Exit(code=2)
    by_list = [s.strip() for s in by.split(",") if s.strip()]
    modes = _parse_source_modes(require=require, source_mode=source_mode)
    try:
        result = asyncio.run(_engine().expand(identifier, by=by_list, limit=limit, source_modes=modes))
    except SourceRequiredError as exc:
        _print_json(exc.envelope.model_dump(mode="json"))
        raise typer.Exit(code=1) from exc
    _print_json(result.model_dump(mode="json"))


@app.command("context")
def context(
    doi: str | None = typer.Option(None, "--doi", help="DOI"),
    pmid: str | None = typer.Option(None, "--pmid", help="PMID"),
    pmcid: str | None = typer.Option(None, "--pmcid", help="PMCID"),
    sources: str = typer.Option(DEFAULT_GET_SOURCES, "--sources", help="Comma-separated source names"),
    signals: bool = typer.Option(False, "--signals", help="Include PubTator3 biomedical signals"),
    expand: bool = typer.Option(False, "--expand", help="Include citation expansion"),
    expand_limit: int = typer.Option(5, "--expand-limit", help="Maximum expanded works"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON envelope"),
    require: str | None = typer.Option(None, "--require", help="Comma-separated required sources"),
    source_mode: str | None = typer.Option(
        None,
        "--source-mode",
        help="Comma-separated source:mode pairs (optional/preferred/required)",
    ),
):
    """Build a structured paper context pack for downstream agents."""
    raw = doi or pmid or pmcid
    if not raw:
        console.print("[red]Error:[/red] provide --doi, --pmid, or --pmcid")
        raise typer.Exit(code=2)
    identifier = identify(raw)
    if not identifier:
        console.print(f"[red]Error:[/red] Could not identify: {raw}")
        raise typer.Exit(code=2)
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    modes = _parse_source_modes(require=require, source_mode=source_mode)
    try:
        result = asyncio.run(
            _engine().context(
                identifier,
                sources=source_list,
                include_signals=signals,
                include_expand=expand,
                expand_limit=expand_limit,
                source_modes=modes,
            )
        )
    except SourceRequiredError as exc:
        _print_json(exc.envelope.model_dump(mode="json"))
        raise typer.Exit(code=1) from exc
    _print_json(result.model_dump(mode="json"))


@app.command("batch")
def batch(
    input_file: Path = typer.Argument(..., help="Input JSONL/text file (use - for stdin)"),
    format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json|jsonl|bibtex|ris|nbib|enw|markdown|zotero|obsidian",
    ),
    output: Path = typer.Option(Path("-"), "--output", help="Output file (default stdout)"),
    sources: str = typer.Option(DEFAULT_SEARCH_SOURCES, "--sources", help="Comma-separated source names"),
    limit: int = typer.Option(20, "--limit", help="Maximum results per search item"),
    year: str | None = typer.Option(None, "--year", help="Filter by year"),
    require: str | None = typer.Option(None, "--require", help="Comma-separated required sources"),
    source_mode: str | None = typer.Option(
        None,
        "--source-mode",
        help="Comma-separated source:mode pairs (optional/preferred/required)",
    ),
):
    """Process a batch of queries or identifiers."""
    from searchpaper.batch import process_batch

    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    modes = _parse_source_modes(require=require, source_mode=source_mode)
    filters = _filters(limit=limit, year=year, source_modes=modes)

    async def _run() -> str:
        engine = _engine()
        return await process_batch(
            input_file,
            engine,
            output_format=format,
            sources=source_list,
            filters=filters,
            source_modes=modes,
        )

    content = asyncio.run(_run())
    if str(output) == "-":
        console.print(content)
    else:
        output.write_text(content, encoding="utf-8")


sources_app = typer.Typer(help="Source diagnostics")
app.add_typer(sources_app, name="sources")


@sources_app.command("status")
def sources_status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show status of configured sources."""
    result = asyncio.run(_engine().source_statuses())
    _print_json(result.model_dump(mode="json"))


@sources_app.command("tiers")
def sources_tiers(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show source tier catalog."""
    _print_json([descriptor.model_dump(mode="json") for descriptor in list_source_descriptors()])


@sources_app.command("preflight")
def sources_preflight(
    sources: str = typer.Option(DEFAULT_SEARCH_SOURCES, "--sources", help="Comma-separated source names"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Run source status probes for selected sources."""
    from searchpaper.sources import get_adapter

    async def _run() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for source in [s.strip() for s in sources.split(",") if s.strip()]:
            try:
                adapter = get_adapter(source)
                try:
                    status = await adapter.status()
                    results.append(status.model_dump(mode="json"))
                finally:
                    await adapter.aclose()
            except Exception as exc:
                results.append({"source": source, "state": "offline", "message": str(exc)})
        return results

    _print_json(asyncio.run(_run()))


@sources_app.command("explain")
def sources_explain(
    source: str = typer.Argument(..., help="Source name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Explain a source: catalog metadata, current status, and recommendations."""
    from searchpaper.diagnostics import explain_source

    _print_json(asyncio.run(explain_source(source)))


@sources_app.command("diagnose")
def sources_diagnose(
    sources: str = typer.Option("", "--sources", help="Comma-separated source names (default: all implemented)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Run health diagnostics for selected sources and show recommendations."""
    from searchpaper.diagnostics import diagnose_sources

    source_list = [s.strip() for s in sources.split(",") if s.strip()] or None
    _print_json(asyncio.run(diagnose_sources(source_list)))


pubmed_app = typer.Typer(help="PubMed utilities")
app.add_typer(pubmed_app, name="pubmed")


@pubmed_app.command("mesh")
def pubmed_mesh(
    term: str = typer.Argument(..., help="MeSH lookup term"),
    limit: int = typer.Option(10, "--limit", help="Maximum descriptors"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Lookup MeSH descriptors."""
    from searchpaper.pubmed_utils import lookup_mesh

    _print_json(asyncio.run(lookup_mesh(term, limit=limit)))


@pubmed_app.command("related")
def pubmed_related(
    pmid: str = typer.Argument(..., help="PMID"),
    limit: int = typer.Option(20, "--limit", help="Maximum related PMIDs"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Find related PubMed articles."""
    from searchpaper.pubmed_utils import related_articles

    _print_json(asyncio.run(related_articles(pmid, limit=limit)))


@pubmed_app.command("convert-ids")
def pubmed_convert_ids(
    identifiers: list[str] = typer.Argument(..., help="DOI/PMID/PMCID identifiers"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Convert DOI/PMID/PMCID identifiers."""
    from searchpaper.pubmed_utils import convert_ids

    _print_json(asyncio.run(convert_ids(identifiers)))


references_app = typer.Typer(help="Reference file utilities")
app.add_typer(references_app, name="references")


@references_app.command("convert")
def references_convert(
    input_file: Path = typer.Argument(..., help="refs.txt input file"),
    format: str = typer.Option("ris", "--format", help="Output format"),
    output: Path = typer.Option(Path("-"), "--output", help="Output file"),
):
    """Convert refs.txt identifiers to citation formats."""
    from searchpaper.reference_convert import convert_refs_file

    content = convert_refs_file(input_file, format)
    if str(output) == "-":
        console.print(content)
    else:
        output.write_text(content, encoding="utf-8")


@references_app.command("verify")
def references_verify(
    input_file: Path = typer.Argument(..., help="Document with citations (.txt/.docx/.tex)"),
    format: str | None = typer.Option(None, "--format", help="Input format: txt/docx/tex"),
    output: Path = typer.Option(Path("-"), "--output", help="Output file"),
    output_format: str = typer.Option("json", "--output-format", help="json/jsonl/csv/markdown"),
):
    """Verify citations in a document against SearchPaper results."""
    content = verify_document(input_file, input_format=format, output_format=output_format)
    if str(output) == "-":
        console.print(content)
    else:
        output.write_text(content, encoding="utf-8")


cache_app = typer.Typer(help="Cache management")
app.add_typer(cache_app, name="cache")


@cache_app.command("stats")
def cache_stats():
    """Show cache statistics."""
    cache = Cache(get_cache_path(load_config()))
    _print_json(cache.stats())


@cache_app.command("clear")
def cache_clear(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
):
    """Clear the local cache."""
    if not yes:
        confirmed = typer.confirm("Clear SearchPaper cache?")
        if not confirmed:
            raise typer.Abort()
    cache = Cache(get_cache_path(load_config()))
    cache.clear()
    console.print("Cache cleared.")


@app.command("doctor")
def doctor():
    """Run diagnostics."""
    cfg = load_config()
    cache_path = get_cache_path(cfg)
    config_dir = DEFAULT_CONFIG_DIR
    rows = [
        ("Version", __version__),
        ("Config dir", str(config_dir)),
        ("Config exists", str(config_dir.exists())),
        ("Cache path", str(cache_path)),
        ("Cache exists", str(cache_path.exists())),
        ("Sources", ", ".join(list_sources())),
    ]
    table = Table(title="SearchPaper Doctor")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="magenta")
    for item, value in rows:
        table.add_row(item, value)
    console.print(table)


@app.command("capabilities")
def capabilities(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Report SearchPaper capabilities."""
    data = {
        "schema_version": "0.2",
        "cli_commands": [
            "search",
            "plan",
            "get",
            "resolve",
            "expand",
            "context",
            "batch",
            "sources status",
            "sources tiers",
            "sources preflight",
            "sources explain",
            "sources diagnose",
            "pubmed mesh",
            "pubmed related",
            "pubmed convert-ids",
            "cache stats",
            "cache clear",
            "doctor",
            "capabilities",
            "serve",
            "install",
            "integrate",
            "integrate migrate",
            "project traces",
            "project export",
            "export",
            "references convert",
            "references verify",
            "signals",
        ],
        "mcp_tools": [
            "search_literature",
            "plan_literature_search",
            "get_work",
            "resolve_identifiers",
            "get_source_status",
            "lookup_mesh",
            "find_related_articles",
            "convert_identifiers",
            "search_literature_signals",
            "expand_from_work",
            "export_records",
        ],
        "sources": list_sources(),
        "export_formats": [
            "json",
            "jsonl",
            "bibtex",
            "ris",
            "markdown",
            "nbib",
            "enw",
            "zotero",
            "obsidian",
            "apa",
            "mla",
        ],
        "agent_integrations": ["opencode", "codex", "claude"],
    }
    _print_json(data)


@app.command("serve")
def serve(
    mcp: bool = typer.Option(False, "--mcp", help="Start MCP server"),
    transport: str = typer.Option("stdio", "--transport", help="MCP transport: stdio or http"),
    host: str = typer.Option("127.0.0.1", "--host", help="HTTP server host"),
    port: int = typer.Option(8000, "--port", help="HTTP server port"),
    path: str = typer.Option("/mcp", "--path", help="HTTP MCP endpoint path"),
):
    """Serve SearchPaper over MCP (stdio or http)."""
    if not mcp:
        console.print("Use --mcp to start the MCP server.")
        raise typer.Exit(code=2)
    from searchpaper.mcp_server import main as mcp_main

    mcp_main(transport=transport, host=host, port=port, path=path)


@app.command("export")
def export_records(
    input_file: Path = typer.Argument(..., help="JSON result file"),
    format: str = typer.Option("bibtex", "--format", help="Output format"),
    output: Path = typer.Option(Path("-"), "--output", help="Output file (default stdout)"),
):
    """Export SearchPaper JSON results to BibTeX/RIS/Markdown/JSONL."""
    from searchpaper.export import export_file

    export_file(input_file, output, format)


@app.command("signals")
def signals(
    query: str | None = typer.Argument(None, help="Entity name or query"),
    entity1: str | None = typer.Option(None, "--entity1", help="First entity"),
    entity2: str | None = typer.Option(None, "--entity2", help="Second entity"),
    relation_type: str = typer.Option("interact", "--relation", help="Relation type"),
    entity2_type: str = typer.Option("chemical", "--entity2-type", help="Entity2 type filter"),
    limit: int = typer.Option(10, "--limit", help="Maximum relations"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON envelope"),
):
    """Search biomedical literature signals via PubTator3."""
    q = query or entity1
    if not q:
        console.print("[red]Error:[/red] provide a query or --entity1")
        raise typer.Exit(code=2)
    result = asyncio.run(
        _engine().signals(
            query=q,
            entity1=entity1,
            entity2=entity2,
            relation_type=relation_type,
            entity2_type=entity2_type,
            limit=limit,
        )
    )
    _print_json(result.model_dump(mode="json"))


@app.command("init")
def init(
    path: Path = typer.Option(Path("."), "--path", help="Project path"),
):
    """Initialize a SearchPaper project directory."""
    project_dir = path / DEFAULT_PROJECT_DIR
    (project_dir / "queries").mkdir(parents=True, exist_ok=True)
    (project_dir / "exports").mkdir(parents=True, exist_ok=True)
    (project_dir / "traces").mkdir(parents=True, exist_ok=True)
    config_path = project_dir / "config.toml"
    if not config_path.exists():
        config_path.write_text(
            "# SearchPaper project config\n"
            '# sources = ["pubmed", "crossref", "openalex"]\n'
            '# cache_path = ".searchpaper/cache.db"\n',
            encoding="utf-8",
        )
    console.print(f"Initialized SearchPaper project at {project_dir}")


project_app = typer.Typer(help="Project-level trace and export workflow")
app.add_typer(project_app, name="project")


@project_app.command("traces")
def project_traces(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """List saved search traces in the current project."""
    from searchpaper.project import list_traces

    if find_project_dir() is None:
        console.print("[red]Error:[/red] not inside a SearchPaper project.")
        raise typer.Exit(code=2)
    _print_json(list_traces())


@project_app.command("export")
def project_export(
    trace_id: str = typer.Argument(..., help="Trace ID or prefix"),
    format: str = typer.Option("jsonl", "--format", help="Export format"),
    output: Path = typer.Option(Path("-"), "--output", help="Output file (default stdout)"),
):
    """Export a saved project trace to a supported format."""
    from searchpaper.project import export_trace

    if find_project_dir() is None:
        console.print("[red]Error:[/red] not inside a SearchPaper project.")
        raise typer.Exit(code=2)
    try:
        result = export_trace(trace_id, fmt=format)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    content = result["content"]
    if str(output) == "-":
        console.print(content)
    else:
        output.write_text(content, encoding="utf-8")


integrate_app = typer.Typer(help="Agent integration management")
app.add_typer(integrate_app, name="integrate")


@app.command("install")
def install_top(
    target: str = typer.Option("all", "--target", help="Target agent: opencode, codex, claude, all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change"),
    mode: str | None = typer.Option(None, "--mode", help="Install mode: mcp, skill, custom_tool, both (OpenCode only)"),
):
    """Install SearchPaper integration for an agent."""
    install(target=target, dry_run=dry_run, mode=mode)


@integrate_app.command("install")
def install(
    target: str = typer.Option("all", "--target", help="Target agent: opencode, codex, claude, all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change"),
    mode: str | None = typer.Option(None, "--mode", help="Install mode: mcp, skill, custom_tool, both (OpenCode only)"),
):
    """Install SearchPaper integration for an agent."""
    from searchpaper.integrations.manager import IntegrationManager

    modes = _parse_install_mode(mode)
    mgr = IntegrationManager()
    result = asyncio.run(mgr.install(target, dry_run=dry_run, modes=modes))
    _print_json(result)


@integrate_app.command("status")
def integrate_status():
    """Show integration status."""
    from searchpaper.integrations.manager import IntegrationManager

    mgr = IntegrationManager()
    status = mgr.status()
    _print_json(status)


@integrate_app.command("dry-run")
def integrate_dry_run(
    target: str = typer.Option("opencode", "--target", help="Target agent"),
):
    """Preview integration changes."""
    install(target=target, dry_run=True)


@integrate_app.command("doctor")
def integrate_doctor():
    """Check integration health."""
    from searchpaper.integrations.manager import IntegrationManager

    mgr = IntegrationManager()
    report = mgr.doctor()
    _print_json(report)


@integrate_app.command("migrate")
def integrate_migrate(
    target: str = typer.Option("all", "--target", help="Target agent: opencode, codex, claude, all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change"),
    mode: str | None = typer.Option(None, "--mode", help="Install mode: mcp, skill, custom_tool, both (OpenCode only)"),
):
    """Re-install managed files to update integrations to the current SearchPaper version."""
    from searchpaper.integrations.manager import IntegrationManager

    modes = _parse_install_mode(mode)
    mgr = IntegrationManager()
    result = asyncio.run(mgr.migrate(target, dry_run=dry_run, modes=modes))
    _print_json(result)


@integrate_app.command("uninstall")
def integrate_uninstall(
    target: str = typer.Option("all", "--target", help="Target agent: opencode, codex, claude, all"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Uninstall mode: mcp, skill, custom_tool, both (OpenCode only)",
    ),
):
    """Uninstall SearchPaper integration for an agent."""
    if not yes:
        confirmed = typer.confirm(f"Uninstall SearchPaper integration for {target}?")
        if not confirmed:
            raise typer.Abort()
    from searchpaper.integrations.manager import IntegrationManager

    modes = _parse_install_mode(mode)
    mgr = IntegrationManager()
    result = asyncio.run(mgr.uninstall(target, modes=modes))
    _print_json(result)


def main() -> None:
    app()
