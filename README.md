# paperSearch

[中文文档](README.zh.md)

A local stdio MCP server for academic literature search. It wraps **Semantic Scholar** (general paper search, citations, references, recommendations) and **PubTator3** (biomedical entity normalization, entity relations, PMID evidence) into a single, cached, reproducible toolset for AI agents.

Built for bioinformatics, immuno-oncology, single-cell, and immunotherapy workflows.

---

## Features

- **Semantic Scholar tools**
  - `s2_search_papers` – general paper search with year, venue, citation count, and sorting filters
  - `s2_get_paper` – single paper metadata (supports S2 paperId, DOI, PMID, arXiv)
  - `s2_batch_get_papers` – batch metadata lookup (max 100)
  - `s2_get_citations` / `s2_get_references` – citation graph traversal
  - `s2_recommend_papers` – recommendation from positive/negative examples
- **PubTator3 tools**
  - `pubtator_find_entity` – normalize biomedical entities (`@GENE_JAK1`, `@CHEMICAL_Pembrolizumab`, …)
  - `pubtator_find_relations` – entity–entity relations with PMID evidence
  - `pubtator_search` – free-text or relation-query search
- **Composite helpers**
  - `biomed_relation_evidence` – one-shot resolver from plain names to entity IDs, relations, and PMIDs
  - `paper_enrich_with_pubtator` – enrich a Semantic Scholar paper with PubTator annotations
  - `research_query` – unified literature search with optional PubTator enrichment

---

## Quick Start

```bash
git clone <repo-url> ~/Publish/paperSearch
cd ~/Publish/paperSearch
uv sync --extra dev
```

Create your local config file:

```bash
mkdir -p ~/.config/paperSearch
cp config.example.json ~/.config/paperSearch/config.json
# edit ~/.config/paperSearch/config.json and add your Semantic Scholar API key
```

Run the smoke test:

```bash
uv run python scripts/smoke_test.py
```

---

## Configuration

paperSearch reads a user-level JSON config file, then lets environment variables override it.

### Config file (recommended)

Path: `~/.config/paperSearch/config.json`

```json
{
  "semantic_scholar_api_key": "YOUR_SEMANTIC_SCHOLAR_API_KEY",
  "cache_path": "/tmp/paper_search_cache.db"
}
```

| Key | Required | Default | Description |
|---|---|---|---|
| `semantic_scholar_api_key` | recommended | — | See [API tokens](#api-tokens) below |
| `cache_path` | no | `/tmp/paper_search_cache.db` | Local SQLite cache file |

### Environment variables

These override the config file if set:

| Variable | Description |
|---|---|
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key |
| `PAPER_SEARCH_CACHE` | SQLite cache file path |

An `.env.example` template is included for users who prefer dotenv-style setup. **Do not commit `.env` or `config.json`.** Both are already ignored in `.gitignore`.

---

## API Tokens

### Semantic Scholar API Key

- **Purpose:** Authenticates requests to the Semantic Scholar Academic Graph API. Using a key raises rate limits compared to anonymous access.
- **Source:** https://www.semanticscholar.org/product/api
- **Required?** No. The server works without a key, but you will hit stricter anonymous rate limits.
- **How to provide:** Write it in `~/.config/paperSearch/config.json` under `semantic_scholar_api_key`, or export `SEMANTIC_SCHOLAR_API_KEY`.

### PubTator3

- **Purpose:** NCBI PubTator3 provides biomedical entity normalization, relation mining, and article search.
- **Source:** https://www.ncbi.nlm.nih.gov/research/pubtator3/
- **Required?** No token is required; PubTator3 is a public NCBI service. Respect NCBI rate-limit guidelines.

---

## Agent Setup

### Claude Code

Edit `~/.claude/settings.json` (global) or `~/.claude.json` (project-level) and add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "paperSearch": {
      "command": "uv",
      "args": [
        "--project",
        "/home/huyudi/Publish/paperSearch",
        "run",
        "python",
        "-m",
        "paper_search.server"
      ],
      "env": {}
    }
  }
}
```

The API key is read from `~/.config/paperSearch/config.json`, so you do not need to put it in the Claude config.

### Codex

Edit `~/.codex/.mcp.json`:

```json
{
  "mcpServers": {
    "paperSearch": {
      "command": "uv",
      "args": [
        "--project",
        "/home/huyudi/Publish/paperSearch",
        "run",
        "python",
        "-m",
        "paper_search.server"
      ],
      "env": {}
    }
  }
}
```

Or, if you use `~/.codex/config.toml`:

```toml
[mcp_servers.paperSearch]
type = "stdio"
command = "uv"
args = ["--project", "/home/huyudi/Publish/paperSearch", "run", "python", "-m", "paper_search.server"]

[mcp_servers.paperSearch.env]
```

### OpenCode

Edit `~/.config/opencode/opencode.json` (global) or create `opencode.json` in your project root:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "paperSearch": {
      "type": "local",
      "command": [
        "uv",
        "--project",
        "/home/huyudi/Publish/paperSearch",
        "run",
        "python",
        "-m",
        "paper_search.server"
      ],
      "environment": {},
      "enabled": true
    }
  }
}
```

---

## Tool Reference

All tools return a normalized envelope:

```json
{
  "source": "semantic_scholar|pubtator3|composite",
  "query": ...,
  "retrieved_at": "2026-06-30T12:00:00Z",
  "cache_key": "sha256...",
  "from_cache": false,
  "raw_ids": [...],
  "items": [...],
  "warnings": []
}
```

### Semantic Scholar

| Tool | Description |
|---|---|
| `s2_search_papers` | General paper search |
| `s2_get_paper` | Single paper details |
| `s2_batch_get_papers` | Batch metadata lookup (max 100) |
| `s2_get_citations` | Papers citing a given paper |
| `s2_get_references` | Papers referenced by a given paper |
| `s2_recommend_papers` | Recommendations from example papers |

### PubTator3

| Tool | Description |
|---|---|
| `pubtator_find_entity` | Entity autocomplete/normalization |
| `pubtator_find_relations` | Biomedical relations between entities |
| `pubtator_search` | Article/PMID search |

### Composite

| Tool | Description |
|---|---|
| `biomed_relation_evidence` | Resolve names → entity IDs → relations → PMIDs |
| `paper_enrich_with_pubtator` | Enrich a paper with PubTator annotations |
| `research_query` | Unified search with optional PubTator enrichment |

---

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run python scripts/smoke_test.py
```

---

## License

MIT
