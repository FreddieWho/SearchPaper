# SearchPaper

[中文文档](README.zh.md)

**SearchPaper** is a literature-first infrastructure layer for agent-assisted
research. It searches open scholarly literature across multiple sources,
normalizes identifiers, merges duplicate records conservatively, preserves
provenance, and exports traceable results.

It is **not** a full research agent, systematic-review agent, evidence-evaluation
engine, PDF parser, or Zotero replacement.

Supported sources: PubMed, Crossref, OpenAlex, Europe PMC, arXiv, bioRxiv,
medRxiv, Semantic Scholar, Unpaywall, OpenCitations, and PubTator3 (biomedical
signals). All core workflows are **no-key usable** by default; API keys are
optional accelerators.

---

## What it does

- **Multi-source literature search** across PubMed, Crossref, OpenAlex, Europe
  PMC, and Semantic Scholar.
- **Identifier resolution** for DOI, PMID, PMCID, arXiv, OpenAlex, and Semantic
  Scholar IDs.
- **Conservative duplicate merge** preserving source provenance, conflicts, and
  merge reasons.
- **Local SQLite cache** with query/source-error trace for speed and
  reproducibility.
- **Literature signals** from PubTator3 with explicit signal levels and
  interpretation warnings.
- **CLI-first interface** and a small, stable MCP tool surface.
- **Agent integration** helpers for OpenCode, Codex, and Claude.

---

## Quick start

```bash
git clone <repo-url> ~/Publish/paperSearch
cd ~/Publish/paperSearch
uv sync --extra dev
uv run pytest -q
```

Search:

```bash
searchpaper search "HCC TACE PD-1" --json
```

Resolve a DOI:

```bash
searchpaper resolve --doi 10.1038/s41586-021-03819-2 --json
```

Check source health:

```bash
searchpaper sources status --json
searchpaper doctor
```

---

## Installation

The package is named `searchpaper` and provides the `searchpaper` CLI.

```bash
uv pip install -e .
```

---

## Configuration

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
| `SEMANTIC_SCHOLAR_API_KEY` | `semantic_scholar_api_key` | Optional S2 key |
| `CROSSREF_EMAIL` | `crossref_email` | Polite pool email |
| `OPENALEX_EMAIL` | `openalex_email` | Polite pool email |
| `NCBI_API_KEY` | `ncbi_api_key` | Optional NCBI key |

---

## CLI commands

| Command | Description |
|---|---|
| `searchpaper search "query" --json` | Search literature |
| `searchpaper plan "query" --profile auto --json` | Plan source routing |
| `searchpaper get --pmid 12345 --json` | Get work by identifier |
| `searchpaper resolve --doi 10.xxx --json` | Resolve identifier across sources |
| `searchpaper expand --doi 10.xxx --by citations,references --json` | Expand from a work |
| `searchpaper sources status --json` | Source health status |
| `searchpaper sources tiers --json` | Source tier catalog |
| `searchpaper sources preflight --sources pubmed,arxiv --json` | Probe selected sources |
| `searchpaper sources explain pubmed` | Source metadata and recommendations |
| `searchpaper sources diagnose --json` | Aggregate source health diagnosis |
| `searchpaper project traces` | List saved project traces |
| `searchpaper project export <trace_id> --format bibtex` | Export a saved trace |
| `searchpaper pubmed mesh "term" --json` | MeSH descriptor lookup |
| `searchpaper pubmed related 12345 --json` | PubMed related articles |
| `searchpaper pubmed convert-ids 10.xxx --json` | DOI/PMID/PMCID conversion |
| `searchpaper cache stats` | Cache statistics |
| `searchpaper cache clear` | Clear cache |
| `searchpaper doctor` | Diagnostics |
| `searchpaper capabilities --json` | Report capabilities |
| `searchpaper serve --mcp` | Start MCP server (stdio) |
| `searchpaper signals "PDCD1" --entity2-type chemical --json` | Biomedical signals |
| `searchpaper export results.json --format bibtex` | Export results |
| `searchpaper references convert refs.txt --format ris` | Convert reference IDs |
| `searchpaper install --target opencode` | Install agent integration |
| `searchpaper integrate dry-run --target opencode` | Preview integration changes |
| `searchpaper integrate migrate --target all` | Update managed integrations |
| `searchpaper integrate uninstall --target opencode` | Remove integration |

Supported export formats: `json`, `jsonl`, `bibtex`, `ris`, `nbib`, `enw`,
`markdown`, `zotero` (CSV), and `obsidian` (YAML-frontmatter notes).

---

## Project mode

Initialize a project directory to save traces and exports locally:

```bash
searchpaper init
searchpaper search "HCC TACE PD-1" --json --save
searchpaper project traces
searchpaper project export <trace_id> --format bibtex
```

---

## MCP server

Start the default stdio MCP server:

```bash
searchpaper serve --mcp
```

Start a remote HTTP/SSE MCP server (requires `searchpaper[remote]`):

```bash
searchpaper serve --mcp --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

The HTTP endpoint exposes `/mcp/sse` and `/mcp/messages/` for MCP clients that
support SSE transport.

---

## MCP tools

The MCP server exposes a small stable surface:

- `search_literature`
- `get_work`
- `resolve_identifiers`
- `get_source_status`
- `search_literature_signals`
- `expand_from_work`
- `export_records`

No source-specific tools are exposed by default.

---

## Agent integration

### OpenCode

```bash
searchpaper install --target opencode
```

This writes an MCP server entry and installs the cross-agent skill.

### Codex and Claude

Scaffolds are generated with MCP config snippets and instruction files:

```bash
searchpaper install --target codex
searchpaper install --target claude
searchpaper install --target all
```

Review the generated files and enable the `searchpaper` MCP server in your
agent's settings.

---

## Signal levels

SearchPaper returns literature signals with explicit levels:

1. **Bibliographic** — title, venue, year, authors, citation, source hit.
2. **Abstract** — title/abstract/keywords/MeSH/concepts.
3. **Curated or extracted** — PubTator3, MeSH-like relations, source-provided
   entity relations.
4. **Full-text anchor** — reserved for future OA/PMC support.
5. **Evaluated evidence** — out of scope for SearchPaper.

A signal is not an evaluated conclusion. Do not report PubTator co-mentions or
relations as proof of causality.

---

## Source degradation

Public APIs can be unreliable. If a source fails, SearchPaper returns partial
results with clear warnings and trace entries. A degraded source does not fail
the whole search. Use `searchpaper sources status` to see current source health.

---

## Cache and privacy

- Cache is stored in `~/.cache/searchpaper/cache.db` by default.
- Use `--no-cache` on `search` to bypass it.
- The cache contains raw API responses and query identifiers; keep the file in a
  secure location.

---

## Testing without live APIs

CI runs fixture-backed tests only. Live API tests are optional and skipped by
default:

```bash
uv run pytest -q
```

---

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format .
uv run pytest -q
```

---

## License

MIT
