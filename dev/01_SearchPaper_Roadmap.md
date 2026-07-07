# SearchPaper Roadmap

Version: planning draft v0.1  
Target implementation style: `/goal` mode, single concentrated execution pass with strict anti-loop and degradation rules.

## 1. Project Definition

SearchPaper is a literature-first infrastructure layer for agent-assisted research. It is not intended to be a full research agent, systematic-review agent, evidence-evaluation engine, Zotero replacement, or PDF parsing pipeline.

The core product promise is:

> SearchPaper helps agents and researchers search open scholarly literature across multiple sources, normalize paper identifiers, merge duplicate records conservatively, preserve provenance, and export traceable results for downstream research workflows.

The project should remain useful even if only a small number of sources are available. Multi-source aggregation improves reliability and enrichment, but literature search remains the first-class foundation.

## 2. Scope and Positioning

### 2.1 Primary Scope

SearchPaper should provide:

1. Multi-source literature search across open/free APIs.
2. Conservative identifier resolution and duplicate merging.
3. Source provenance and query trace.
4. Local cache for speed and reproducibility.
5. CLI-first usage.
6. MCP server as a structured agent-tool adapter.
7. OpenCode-first agent integration, with Codex and Claude supported at the same architectural level.
8. Literature signals and reported relations for biomedical workflows, without scientific conclusion-making.
9. Export to JSON/JSONL first, plus BibTeX/RIS/Markdown.
10. Robust partial success when one or more public APIs fail.

### 2.2 Primary Users

The project should serve broad research users, but the first optimized domain is biomedical and life-science research. This means:

- examples may focus on biomedical queries;
- PubMed, Europe PMC, PubTator3, MeSH-like metadata, PMID/PMCID should be high priority;
- the data model must remain general enough for non-biomedical papers;
- biomedical signal extraction should be an enrichment module, not the whole product identity.

### 2.3 Non-Goals for v0.2

Do not implement these in v0.2:

1. Full research-agent reasoning.
2. Causal/evidence strength evaluation.
3. PDF downloading and PDF parsing.
4. Full-text indexing.
5. Zotero API integration.
6. Obsidian vault generation.
7. Graph database deployment.
8. LLM-based reranking as a default behavior.
9. Heavy plugin ecosystem.
10. Source-specific MCP tool explosion.

The architecture should leave extension points for several of these, but they must not block the v0.2 foundation.

## 3. Core Architecture

The target architecture should be layered:

```text
searchpaper core
  ├─ schemas
  ├─ source adapters
  ├─ identifier resolver
  ├─ merge and ranking
  ├─ cache and trace
  ├─ export
  └─ capabilities

searchpaper CLI
  ├─ search
  ├─ get
  ├─ resolve
  ├─ expand
  ├─ signals
  ├─ export
  ├─ sources status
  ├─ cache stats/clear
  ├─ doctor
  └─ serve --mcp

searchpaper MCP adapter
  └─ small stable MCP tool surface

searchpaper integrations
  ├─ opencode adapter
  ├─ codex adapter
  ├─ claude adapter
  └─ minimal managed-state installer

searchpaper skills
  ├─ .agents/skills/literature-search/SKILL.md
  └─ optional AGENTS.md marker block
```

The core library must not depend on any specific agent. MCP, OpenCode custom tool wrappers, Codex config, Claude config, and skills are adapters around the same stable CLI/core behavior.

## 4. Implementation Language and Stack

Recommended stack:

- Python >= 3.11
- `uv` for development and packaging
- `typer` or `click` for CLI
- `pydantic v2` for stable schemas
- `httpx.AsyncClient` for HTTP clients
- lightweight per-source rate limiter
- SQLite with WAL for cache and trace
- `aiosqlite` or carefully contained sync SQLite access
- `rich` for human-readable CLI output
- `pytest`, `respx`, fixtures, and schema snapshot tests
- `ruff` for linting
- optional `mypy` or `pyright` for type checks
- Python MCP SDK for the MCP server
- TypeScript only for very thin OpenCode custom tool/plugin wrappers when needed

Do not rewrite the core in Rust, Go, or TypeScript for v0.2. Public API latency, schema stability, and source behavior are more important than raw runtime performance.

## 5. Data Source Strategy

### 5.1 Source Priority

v0.2 should prioritize sources that are open/free and useful without mandatory paid credentials.

Recommended v0.2 source order:

1. PubMed / NCBI E-utilities
2. Europe PMC
3. Crossref
4. OpenAlex
5. Semantic Scholar
6. PubTator3

The system must be no-key usable by default. API keys may be supported as optional accelerators or enrichers. If a source benefits from a key, document it, but do not make core search depend on it.

### 5.2 Source Roles

PubMed / NCBI:
- biomedical search backbone;
- PMID identity;
- title/abstract/MeSH/publication metadata where available.

Europe PMC:
- biomedical and life-science enrichment;
- abstract, PMCID, OA/full-text availability links;
- useful source for future full-text anchors.

Crossref:
- DOI and publication metadata;
- publisher, journal, date, license where available;
- DOI resolution and metadata correction.

OpenAlex:
- broad scholarly graph;
- works, authors, institutions, concepts/topics;
- useful for non-biomedical expansion and citation/context metadata.

Semantic Scholar:
- citation graph, references, recommendations, fields of study;
- useful enrichment source, but not required for no-key core usability.

PubTator3:
- biomedical entity annotations and reported relation signals;
- should be treated as a literature-signal adapter, not as a conclusion engine.

### 5.3 Later Sources

Defer to v0.4+ unless easy:

- Unpaywall
- OpenCitations
- arXiv
- bioRxiv / medRxiv
- DataCite
- DOAJ
- CORE
- Zotero API

## 6. Schema Design

All major returned objects should include:

```json
{
  "schema_version": "0.2",
  "object_type": "...",
  "data": {},
  "warnings": [],
  "trace": {}
}
```

### 6.1 WorkRecord

A normalized scholarly work.

Required conceptual fields:

- `work_id`: internal stable ID
- `title`
- `normalized_title`
- `year`
- `authors`
- `venue`
- `abstract`
- `identifiers`
- `source_records`
- `merged_from_sources`
- `provenance`
- `ranking_reasons`
- `warnings`

Identifiers should support:

- DOI
- PMID
- PMCID
- Semantic Scholar paperId
- OpenAlex ID
- Crossref DOI
- arXiv ID
- source-specific IDs

### 6.2 SourceRecord

A raw or near-raw source response mapped into a uniform envelope.

Required conceptual fields:

- `source`
- `source_record_id`
- `retrieved_at`
- `query_or_identifier`
- `raw_record`
- `normalized_fields`
- `usage_note`
- `source_terms_url`
- `warnings`
- `from_cache`

### 6.3 SearchTrace

Tracks reproducibility and source behavior.

Required conceptual fields:

- `query`
- `filters`
- `sources_requested`
- `sources_succeeded`
- `sources_degraded`
- `sources_failed`
- `retrieved_at`
- `cache_policy`
- `merge_strategy_version`
- `ranking_strategy_version`
- `source_errors`
- `result_count_by_source`

### 6.4 RelationSignal / LiteratureSignal

This object should describe literature-backed signals without making conclusions.

Recommended fields:

- `signal_id`
- `signal_type`: `bibliographic_match`, `co_mention`, `reported_relation`, `curated_relation`, `citation_link`, `semantic_similarity`, `entity_annotation`
- `signal_level`: `bibliographic`, `abstract`, `curated_or_extracted`, `full_text_anchor`, `evaluated_evidence`
- `entities`
- `relation_label`
- `supporting_work_ids`
- `source`
- `anchor`
- `confidence_or_score` if supplied by the source
- `interpretation_warning`
- `provenance`

v0.2 may implement only bibliographic, abstract, and curated/extracted signals. Full-text anchors and evaluated evidence are not v0.2 goals.

## 7. Signal Level Policy

This policy resolves the ambiguity between “evidence” and “signal”.

SearchPaper may return literature-backed signals, but it must not imply that the MCP itself has evaluated scientific truth.

Recommended levels:

```text
Level 0: bibliographic signal
Comes from title, venue, year, authors, citation neighborhood, source hit, or topic metadata.

Level 1: abstract signal
Comes from title, abstract, keywords, MeSH, OpenAlex concepts, or similar metadata-level text.

Level 2: curated or extracted relation signal
Comes from PubTator3, MeSH-like controlled vocabulary, source-provided entity annotations, or relation records.

Level 3: full-text anchored signal
Comes from OA/PMC full text sentence, section, table, or figure text. Reserved for future versions.

Level 4: evaluated evidence
Requires judgment about experimental support, direction, strength, species, model system, and applicability. Out of scope for this MCP foundation.
```

User-facing language can say “literature-backed records” or “evidence-linked literature records” if appropriate, but internal schema should use signal levels and interpretation warnings.

## 8. Source Adapter Contract

Each source adapter should implement a common interface:

```python
class SourceAdapter:
    name: str

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]: ...
    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None: ...
    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]: ...
    async def status(self) -> SourceStatus: ...
```

Adapters should not make global merge decisions. They should fetch, map fields, classify errors, and return source-level warnings.

All adapters must support mocked fixture tests. Live API tests must be optional and should not be required in CI.

## 9. Identifier Resolution and Merge Strategy

The identifier resolver is the most important reliability layer.

Recommended merge priority:

1. DOI exact match
2. PMID / PMCID exact match
3. arXiv ID exact match
4. Semantic Scholar / OpenAlex cross-linked IDs when available
5. normalized title + year + first author
6. fuzzy title only with strict warning and no destructive merge

Every merge must preserve provenance. Do not overwrite source-specific metadata without recording source origin.

Merged records should expose:

- `canonical_work_id`
- `identifiers`
- `merged_from_sources`
- `source_conflicts`
- `merge_confidence`
- `merge_reasons`
- `warnings`

Never hide conflicts. If PubMed and Crossref disagree on title/year/venue, preserve both and mark the conflict.

## 10. Ranking Policy

v0.2 should not implement LLM-based reranking by default.

Default ranking should be transparent and rule-based. Recommended factors:

- source original rank;
- number of sources that found the work;
- presence of DOI/PMID/PMCID;
- title/abstract keyword match;
- publication year preference if user specified recency;
- availability of abstract;
- availability of OA/full-text link;
- citation count if supplied;
- biomedical match boost only in biomedical profile.

Every ranked result should include `ranking_reasons`.

## 11. Cache, Trace, and Storage

Use SQLite for v0.2.

Recommended tables:

- `cache_entries`
- `source_records`
- `works`
- `work_identifiers`
- `work_sources`
- `queries`
- `query_results`
- `relation_signals`
- `integration_state` or external JSON state file

Cache should be on by default but user-controllable:

```bash
searchpaper cache stats
searchpaper cache clear
searchpaper search "..." --no-cache
```

Default cache location should be documented. Project mode may use `.searchpaper/` after `searchpaper init`; otherwise use global cache.

## 12. CLI Surface

The CLI is a first-class product surface. MCP should call the same core logic as CLI.

Recommended commands:

```bash
searchpaper search "HCC TACE PD-1 response" --sources pubmed,europepmc,openalex,crossref --limit 30 --json
searchpaper get --pmid 12345678 --json
searchpaper get --doi 10.xxxx --json
searchpaper resolve --doi 10.xxxx --json
searchpaper expand --pmid 12345678 --by citations,references,similar --json
searchpaper signals --entity "PDCD1" --entity "HCC" --json
searchpaper export results.jsonl --format bibtex
searchpaper sources status
searchpaper capabilities --json
searchpaper cache stats
searchpaper cache clear
searchpaper doctor
searchpaper serve --mcp
searchpaper init
```

Advanced/debug source-specific commands may exist under:

```bash
searchpaper source pubmed search "..."
searchpaper source openalex get "..."
```

Do not expose these as default MCP tools.

## 13. MCP Tool Surface

Keep MCP tool surface small and stable.

Recommended v0.2 MCP tools:

1. `search_literature`
2. `get_work`
3. `resolve_identifiers`
4. `expand_from_work`
5. `search_literature_signals`
6. `export_records`
7. `get_source_status`

Avoid source-specific MCP tools such as `search_pubmed`, `search_crossref`, or `search_openalex` unless in an explicit advanced/debug mode. Too many tools increase token load and degrade agent behavior.

## 14. Agent Integration Strategy

OpenCode must be implemented first, but Codex and Claude must be architecturally co-equal.

v0.2 should implement:

```bash
searchpaper install --target opencode
searchpaper install --target codex
searchpaper install --target claude
searchpaper install --target all
searchpaper integrate status
searchpaper integrate doctor
searchpaper integrate dry-run --target opencode
searchpaper integrate uninstall --target opencode
```

Minimum integration manager capabilities:

- detect target availability;
- install MCP config and skill files;
- support dry-run;
- record managed files;
- support uninstall;
- run doctor checks;
- avoid destructive overwrite of user config.

Full migration/update logic may be v0.3, but v0.2 must not force users to delete and reinstall for normal changes.

## 15. Project Mode

Default behavior:

- no project init required;
- use global cache and config.

Optional behavior:

```bash
searchpaper init
```

Creates:

```text
.searchpaper/
  config.toml
  queries/
  exports/
  traces/
```

Project mode is useful for reproducible research workflows but should not be mandatory.

## 16. Export Strategy

JSON and JSONL are first-class formats.

Required v0.2 formats:

- JSON
- JSONL
- BibTeX
- RIS
- Markdown

Zotero and Obsidian integrations should be left as extension points for later versions.

## 17. Testing Strategy

CI should not depend on live public APIs.

Required tests:

1. Source adapter fixture tests.
2. Schema validation tests.
3. Schema snapshot tests.
4. Identifier normalization tests.
5. Merge regression tests.
6. Cache behavior tests.
7. CLI smoke tests.
8. MCP mocked tool tests.
9. Installer dry-run tests.
10. Degraded-source partial success tests.

Optional tests:

- live API integration tests, manually triggered or nightly;
- benchmark query set.

## 18. Phased Roadmap

### v0.2: Foundation Release

Goal: establish a usable, stable, no-key core that can search literature, normalize/merge records, preserve provenance, expose CLI/MCP, and install into OpenCode first.

Deliverables:

1. Canonical project naming: `SearchPaper`, package/CLI `searchpaper`.
2. Pydantic schema definitions.
3. Source adapter contract.
4. PubMed adapter.
5. Crossref adapter.
6. OpenAlex adapter.
7. Europe PMC adapter if feasible; otherwise fixture-backed degraded adapter with clear status.
8. Conservative identifier resolver.
9. Merge and provenance layer.
10. Rule-based ranking with ranking reasons.
11. SQLite cache and query trace.
12. CLI commands: `search`, `get`, `resolve`, `sources status`, `cache stats`, `doctor`, `serve --mcp`.
13. MCP tools: `search_literature`, `get_work`, `resolve_identifiers`, `get_source_status`.
14. OpenCode installer first; Codex/Claude minimal installer support if time allows.
15. `.agents/skills/literature-search/SKILL.md` draft.
16. Mocked tests and schema snapshot tests.

Acceptance criteria:

- A user can install and run `searchpaper search "HCC TACE PD-1" --json`.
- Search returns normalized records with source provenance.
- At least two sources can succeed in a normal environment.
- If one source fails, the command returns partial results with clear warnings.
- No-key usage works.
- MCP server starts and exposes the core tools.
- OpenCode can be configured through installer or generated config.
- CI passes without live API dependency.

### v0.3: Biomedical Signal and Agent Hardening

Goal: enrich biomedical workflows and make agent use smoother without turning SearchPaper into a research agent.

Deliverables:

1. PubTator3 adapter as `literature_signals` provider.
2. Semantic Scholar adapter for citation/recommendation enrichment.
3. `signals` CLI and `search_literature_signals` MCP tool.
4. Signal level policy implemented in schema.
5. `expand_from_work` CLI/MCP support.
6. JSONL/BibTeX/RIS/Markdown export.
7. `capabilities --json`.
8. Optional `searchpaper init` project mode.
9. Basic `integrate status`, `dry-run`, `uninstall`, and managed state file.
10. OpenCode custom tool thin wrapper if useful.
11. Codex/Claude integration parity for MCP config and skill installation.
12. Small curated biomedical query set for smoke evaluation.

Acceptance criteria:

- PubTator failure does not block literature search.
- Signal results are clearly marked as bibliographic/abstract/curated/extracted.
- Agent skill warns against treating signals as evaluated conclusions.
- Export works for a multi-source query result.
- Installer can uninstall managed files without touching user-owned config.

### v0.4: Integration and Source Expansion

Goal: improve source coverage and long-term maintainability.

Deliverables:

1. Unpaywall adapter.
2. OpenCitations adapter.
3. arXiv adapter.
4. bioRxiv/medRxiv adapter.
5. Update/migration support for integrations.
6. More robust project-level trace/export workflow.
7. Optional remote/HTTP MCP mode.
8. Better source health diagnostics.
9. Documentation for source-specific usage limitations.
10. Extension points for Zotero/Obsidian.

Acceptance criteria:

- New sources can be added without changing core schema.
- Old configs can be migrated or repaired by `doctor`.
- Degraded sources are visible but do not derail core workflows.

### v0.5: Full-Text-Ready Expansion

Goal: prepare for full-text anchors without falling into PDF parsing too early.

Deliverables:

1. Europe PMC / PMC full-text availability support.
2. OA link resolution through Unpaywall.
3. Optional full-text metadata anchors where source APIs provide structured text.
4. `anchor_type` and `text_scope` support for full-text future expansion.
5. Improved paper context packs for downstream research agents.
6. Zotero/Obsidian interface hooks if still relevant.

Acceptance criteria:

- Full-text availability can be reported.
- Full-text anchors can be stored if available from structured open sources.
- PDF parsing remains optional and not required for core stability.

## 19. /goal Execution Rule

The implementation agent should pursue the v0.2 foundation first. If time remains, it may implement selected v0.3 items, but it must not sacrifice v0.2 stability for source expansion or feature breadth.

Primary success is not “every API adapter perfect”. Primary success is a stable, traceable, partially-degraded-tolerant SearchPaper foundation that works through CLI and MCP.

## 20. Final Product Principle

SearchPaper should be boring in the right places.

- boring schema;
- boring provenance;
- boring cache;
- boring CLI;
- boring installer safety;
- interesting only where literature search becomes more reliable and agent-usable.

A reliable literature MCP beats a fragile mini research agent.
