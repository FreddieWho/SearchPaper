<p align="center">
  <img src="docs/assets/searchpaper-banner.png" alt="SearchPaper banner" width="100%">
</p>

# SearchPaper

[中文文档](README.zh.md)

**SearchPaper** is a literature-first infrastructure layer for agent-assisted
research. It searches open scholarly literature, normalizes identifiers, merges
duplicate records conservatively, preserves provenance, and exports traceable
results for downstream agents or human review.

SearchPaper is **not** a full research agent, systematic-review engine,
evidence evaluator, PDF parser, or Zotero replacement. It provides structured
literature records and provenance; interpretation stays with the user or a
downstream research workflow.

## 🔎 At a Glance

| Area | What SearchPaper provides |
|---|---|
| 📚 Sources | PubMed, Crossref, OpenAlex, Europe PMC, arXiv, bioRxiv, medRxiv, Semantic Scholar, Unpaywall, OpenCitations, PubTator3 |
| 🧬 Biomedical workflows | MeSH lookup, PubMed related articles, DOI/PMID/PMCID conversion, PubTator3 literature signals |
| 🔗 Identifiers | DOI, PMID, PMCID, arXiv, OpenAlex, Semantic Scholar IDs |
| 🧾 Provenance | Source records, merge reasons, conflicts, warnings, trace fields |
| 🧠 Agent access | CLI plus MCP tools for OpenCode, Codex, Claude, and other MCP clients |
| 📦 Exports | JSON, JSONL, BibTeX, RIS, NBIB, ENW, Markdown, Zotero CSV, Obsidian notes, APA, MLA |
| 🔓 API keys | Core workflows are no-key usable; optional keys improve rate limits and coverage |

## ✨ What It Does

- **Multi-source literature search** across open scholarly APIs.
- **Identifier resolution** for common scholarly IDs.
- **Conservative duplicate merge** with provenance and conflict preservation.
- **Local SQLite cache** for speed and reproducibility.
- **Full-text readiness** via OA links, Europe PMC XML anchors, and full-text availability fields.
- **Structured literature signals** from PubTator3 with explicit interpretation warnings.
- **CLI-first workflows** plus a small, stable MCP tool surface.
- **Agent integration helpers** for OpenCode, Codex, and Claude.

## ⚡ Quick Start

```bash
git clone <repo-url> ~/Publish/PaperSearch
cd ~/Publish/PaperSearch
uv sync --extra dev
uv run pytest -q
```

| Task | Command |
|---|---|
| Search literature | `uv run searchpaper search "HCC TACE PD-1" --json` |
| Resolve a DOI | `uv run searchpaper resolve --doi 10.1038/s41586-021-03819-2 --json` |
| Check source health | `uv run searchpaper sources status --json` |
| Run diagnostics | `uv run searchpaper doctor` |
| Start MCP server | `uv run searchpaper serve --mcp` |

For an editable local install:

```bash
uv pip install -e .
```

After installation, the package provides the `searchpaper` CLI.

## ⚙️ Configuration

SearchPaper reads `~/.config/searchpaper/config.json`. Environment variables
override file values.

```json
{
  "semantic_scholar_api_key": "YOUR_KEY",
  "crossref_email": "you@example.com",
  "openalex_email": "you@example.com",
  "ncbi_api_key": "YOUR_NCBI_KEY",
  "cache_path": "~/.cache/searchpaper/cache.db"
}
```

| Variable | Maps to | Description |
|---|---|---|
| `SEARCHPAPER_CACHE` | `cache_path` | SQLite cache file |
| `SEARCHPAPER_CONFIG` | `config_path` | Config file path |
| `SEMANTIC_SCHOLAR_API_KEY` | `semantic_scholar_api_key` | Optional Semantic Scholar key |
| `CROSSREF_EMAIL` | `crossref_email` | Crossref polite-pool email |
| `OPENALEX_EMAIL` | `openalex_email` | OpenAlex polite-pool email |
| `NCBI_API_KEY` | `ncbi_api_key` | Optional NCBI key |

## 🧭 Core CLI Workflows

| Workflow | Command |
|---|---|
| Plan source routing | `searchpaper plan "query" --profile auto --json` |
| Search literature | `searchpaper search "query" --json` |
| Get work by PMID | `searchpaper get --pmid 12345 --json` |
| Resolve identifier | `searchpaper resolve --doi 10.xxx --json` |
| Expand from a seed work | `searchpaper expand --doi 10.xxx --by citations,references --json` |
| Build context pack | `searchpaper context --doi 10.xxx --json` |
| Fetch full-text anchors | `searchpaper get --pmcid PMC8371605 --sources europepmc --anchors --json` |
| Probe sources | `searchpaper sources preflight --sources pubmed,arxiv --json` |
| Explain source behavior | `searchpaper sources explain pubmed` |
| Diagnose source health | `searchpaper sources diagnose --json` |
| Save project trace | `searchpaper search "query" --json --save` |
| Export saved trace | `searchpaper project export <trace_id> --format bibtex` |
| Lookup MeSH | `searchpaper pubmed mesh "term" --json` |
| Find related PubMed articles | `searchpaper pubmed related 12345 --json` |
| Convert PubMed IDs | `searchpaper pubmed convert-ids 10.xxx --json` |
| Batch process inputs | `searchpaper batch queries.jsonl --format jsonl --output results.jsonl` |
| Verify references | `searchpaper references verify refs.txt --output-format markdown` |
| Export results | `searchpaper export results.json --format bibtex` |
| Inspect capabilities | `searchpaper capabilities --json` |

## 🧩 MCP and Agent Integration

Start the default stdio MCP server:

```bash
searchpaper serve --mcp
```

Start a remote HTTP/SSE MCP server with `searchpaper[remote]` installed:

```bash
searchpaper serve --mcp --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

| Tool | Purpose |
|---|---|
| `search_literature` | Multi-source literature search |
| `plan_literature_search` | Source-routing plan without a live search |
| `get_work` | Fetch one work by identifier |
| `resolve_identifiers` | Resolve and merge multiple identifiers |
| `get_source_status` | Source health and optional catalog |
| `lookup_mesh` | PubMed MeSH descriptor lookup |
| `find_related_articles` | PubMed related article IDs |
| `convert_identifiers` | DOI/PMID/PMCID conversion |
| `search_literature_signals` | Biomedical entity/relation signals |
| `expand_from_work` | Citations, references, and related papers |
| `export_records` | Export structured records |

| Agent | Install command | Output |
|---|---|---|
| OpenCode | `searchpaper install --target opencode` | MCP config plus `literature-search` skill |
| Codex | `searchpaper install --target codex` | MCP snippet plus SearchPaper instructions |
| Claude | `searchpaper install --target claude` | MCP snippet plus SearchPaper instructions |
| All | `searchpaper install --target all` | Scaffolds all supported integrations |

Review generated files and enable the `searchpaper` MCP server in your agent
settings.

## 📖 Full-Text Readiness

SearchPaper reports full-text availability without requiring PDF parsing.
Records may include `full_text_availability`, `open_access_pdf`, and canonical
URLs such as `doi`, `pubmed`, `pmc`, `oa_url`, and `oa_pdf_url`.

```bash
searchpaper resolve --doi 10.1038/s41586-021-03819-2 --json
searchpaper get --pmcid PMC8371605 --sources europepmc --anchors --json
searchpaper context --doi 10.1038/s41586-021-03819-2 --json
searchpaper get --doi 10.1038/s41586-021-03819-2 --download-pdf paper.pdf --json
searchpaper get --pmcid PMC8371605 --download-xml paper.xml --json
```

PDF parsing remains optional and out of scope.

## 🛡️ Failure Modes and Signal Rules

| Topic | Behavior |
|---|---|
| Source degradation | Public APIs can fail; optional sources warn and continue |
| Required sources | `--require pubmed` or `--source-mode pubmed:required` returns exit code 1 on failure |
| Preferred sources | `source:preferred` emits louder warnings but does not fail the full search |
| Biomedical signals | PubTator3/co-mention signals are not proof of causality |
| Evidence evaluation | Out of scope; SearchPaper returns records, provenance, and signals |

## 🗂️ Cache, Privacy, and Project Mode

- Default cache: `~/.cache/searchpaper/cache.db`
- Bypass cache: `searchpaper search "query" --no-cache --json`
- Project mode:

```bash
searchpaper init
searchpaper search "HCC TACE PD-1" --json --save
searchpaper project traces
searchpaper project export <trace_id> --format bibtex
```

The cache may contain raw API responses and query identifiers. Store it
accordingly.

## 🧪 Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check .
uv run ruff format .
```

CI should rely on fixture-backed tests. Live public APIs are useful for manual
checks but should not be required for routine validation.

## 📜 License

MIT
