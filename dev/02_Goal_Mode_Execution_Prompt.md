# SearchPaper `/goal` Execution Prompt

Use this prompt as the last document submitted to `/goal`, after the supporting documents listed below have already been provided.

## Authoritative Input Documents

The implementation must treat these documents as project context, in this priority order:

1. `01_SearchPaper_Roadmap.md` — primary product and engineering roadmap.
2. `03_Degradation_and_AntiLoop_Policy.md` — binding policy for unreliable public APIs, retry budgets, degraded adapters, partial success, and anti-loop behavior.
3. `04_Agent_Integration_and_Skill_Spec.md` — binding specification for OpenCode/Codex/Claude integration, CLI-first design, MCP surface, installer behavior, and skill content.
4. This prompt — execution plan and acceptance target for `/goal` mode.

If this prompt conflicts with the supporting documents, prefer the more conservative interpretation that preserves:

- stable CLI behavior;
- stable JSON schema;
- source provenance;
- degraded-source handling;
- testability without live APIs;
- future extensibility.

Do not treat this prompt as a replacement for the roadmap. It is an execution wrapper around the roadmap.

---

## Mission

You are implementing **SearchPaper** in `/goal` mode.

SearchPaper is a literature-first infrastructure layer for agent-assisted research. It is not a full research agent, not a scientific evidence-evaluation engine, not a Zotero replacement, and not a PDF parsing pipeline.

The goal is to turn the current repository into a solid, usable, extensible foundation for open/free multi-source literature search, identifier resolution, provenance tracking, CLI/MCP use, and agent integration.

Canonical naming:

- Display name: `SearchPaper`
- Python package: `searchpaper`
- CLI command: `searchpaper`
- MCP server name: `searchpaper`
- Repository name may remain `searchPaper`

---

## Execution Target

This `/goal` run should aim to complete:

1. **All v0.2 foundation requirements** from `01_SearchPaper_Roadmap.md`.
2. **The core v0.3 biomedical-signal and agent-hardening requirements** that are feasible without PDF/full-text parsing and without depending on unreliable live APIs.
3. **Minimal v0.4 extension hooks** only where they are low-risk and directly support future compatibility, such as stable `capabilities --json`, source adapter contracts, installer managed-state design, and export interfaces.

Do **not** stop at a “partial v0.3” unless blocked by a hard external constraint. If blocked, implement the adapter contract, fixture-backed tests, degraded status, and documented TODO instead of looping.

Do **not** attempt v0.5 full-text/PDF parsing in this run.

---

## Primary Deliverables

By the end of the run, SearchPaper should provide:

1. a stable Python core with source adapter contracts;
2. a stable CLI-first interface;
3. multi-source literature search across open/free sources where feasible;
4. conservative identifier resolution and duplicate merge;
5. local cache and query trace;
6. partial-success behavior when individual public APIs fail;
7. literature signals with explicit signal level and interpretation warnings;
8. a small MCP tool surface built on the same core logic as the CLI;
9. OpenCode integration first, with Codex and Claude support implemented or scaffolded at the same architectural level;
10. a cross-agent skill document;
11. tests that pass without live public APIs;
12. documentation explaining scope, no-key behavior, cache, degradation, non-goals, and usage.

---

## Hard Non-Goals

Do not implement:

- a research agent;
- scientific evidence grading or causal conclusion generation;
- PDF parsing;
- full-text indexing;
- a graphical UI;
- Zotero/Obsidian direct integration beyond export hooks;
- source-specific MCP tool explosion;
- LLM-based reranking as a default behavior;
- live API dependent CI;
- a large plugin ecosystem;
- a complex migration framework beyond minimal managed-state tracking and safe file modification.

---

## Priority 0 — Preserve Existing Working Behavior

Before major refactoring:

1. inspect the current repository structure;
2. run existing tests;
3. identify current MCP tools, source clients, cache code, config code, and tests;
4. preserve useful current functionality unless it conflicts with the roadmap;
5. prefer incremental refactor over destructive rewrite;
6. keep backward-compatible aliases where practical, especially for existing tool names.

If current package naming conflicts with canonical `searchpaper`, migrate carefully and keep import or command compatibility where reasonable.

---

## Priority 1 — Core Schema and Adapter Contracts

Implement or stabilize typed schemas, preferably with Pydantic v2, for:

- `WorkRecord`
- `SourceRecord`
- `WorkIdentifier`
- `SearchResult`
- `SearchTrace`
- `SourceStatus`
- `LiteratureSignal` / `RelationSignal`
- `SourceError`
- `MergeDecision` / merge reasons where useful

Every main machine output should include:

- `schema_version`
- `object_type`
- `data`
- `warnings`
- `trace`

Every source adapter should implement a common contract:

- `search(query, filters) -> list[SourceRecord]`
- `get(identifier) -> SourceRecord | None`
- `resolve(identifier) -> list[SourceRecord]`
- `status() -> SourceStatus`

Adapters fetch and normalize source records. They must not make global merge decisions.

---

## Priority 2 — Source Adapters

Implement v0.2/v0.3 source adapters in this order:

1. PubMed / NCBI E-utilities
2. Crossref
3. OpenAlex
4. Europe PMC
5. Semantic Scholar, preserving existing support if present
6. PubTator3 as a biomedical literature-signal source, preserving existing support if present

Default behavior must be **no-key usable**. API keys may be optional accelerators or enrichers, not mandatory for the basic workflow.

For each source, implement:

- adapter contract;
- source status;
- rate-limit/error classification;
- fixture-backed tests;
- normalized output;
- usage note or source terms URL where feasible.

If a public API is unreliable, follow `03_Degradation_and_AntiLoop_Policy.md`: implement the adapter contract and mocked tests, mark live status degraded, return partial results, and continue.

A degraded adapter with a correct contract is acceptable. An endless live API debugging loop is not acceptable.

---

## Priority 3 — Identifier Resolution and Merge

Implement conservative identifier resolution and duplicate merge.

Merge priority:

1. DOI exact match;
2. PMID / PMCID exact match;
3. arXiv ID exact match;
4. known cross-linked source IDs;
5. normalized title + year + first author;
6. fuzzy title only with warnings and without destructive merge.

Every merged `WorkRecord` must preserve:

- source provenance;
- source-specific IDs;
- conflicts;
- merge reasons;
- warnings;
- original source records or links to cached raw records.

Never silently discard conflicting identifiers or metadata.

---

## Priority 4 — Literature Signal Model

Implement literature signals as structured, provenance-linked signals, not evaluated conclusions.

Use explicit signal levels:

- `bibliographic_signal`: title, venue, year, authors, citation, source hit, topic proximity;
- `abstract_signal`: title/abstract/keywords/MeSH/concepts;
- `curated_or_extracted_relation`: PubTator3, MeSH-like relation, source-provided structured entity relation;
- `full_text_anchor`: reserved for future PMC/OA full-text support; do not implement PDF/full-text parsing in this run;
- `evaluated_evidence`: out of scope for this MCP layer.

For every signal, include where possible:

- `signal_type`
- `signal_level`
- `supporting_work_ids`
- `source`
- `anchor_type`
- `anchor_text` or snippet when legally and technically available from metadata/abstract/curated source;
- `interpretation_warning`

Do not state that a signal proves a scientific conclusion.

---

## Priority 5 — Cache, Trace, and Storage

Use SQLite for local cache and trace unless the existing project already has a better equivalent.

Required behavior:

- default local cache enabled;
- `--no-cache` available for search;
- cache statistics;
- cache clear;
- query trace;
- partial-success trace;
- source error trace;
- degraded-source trace.

Required CLI commands:

- `searchpaper cache stats`
- `searchpaper cache clear`
- `searchpaper search ... --no-cache`

Search trace should include:

- query;
- filters;
- requested sources;
- succeeded sources;
- degraded sources;
- failed sources;
- source errors;
- cache policy;
- merge strategy version;
- ranking strategy version.

---

## Priority 6 — CLI Surface

The CLI is the stable user and agent contract. MCP must call the same core logic, not reimplement separate behavior.

Required commands:

- `searchpaper search "query" --json`
- `searchpaper get --pmid ID --json`
- `searchpaper get --doi DOI --json`
- `searchpaper resolve --doi DOI --json`
- `searchpaper sources status`
- `searchpaper cache stats`
- `searchpaper cache clear`
- `searchpaper doctor`
- `searchpaper capabilities --json`
- `searchpaper serve --mcp`

Strongly recommended if feasible in the same run:

- `searchpaper expand ... --json`
- `searchpaper signals ... --json`
- `searchpaper export ... --format jsonl|bibtex|ris|markdown`
- `searchpaper init`
- `searchpaper batch ... --jsonl`

JSON/JSONL output is the stable machine interface. Human-readable output may exist, but must not replace stable JSON.

---

## Priority 7 — MCP Surface

Expose a small stable MCP tool surface.

Required tools:

- `search_literature`
- `get_work`
- `resolve_identifiers`
- `get_source_status`

Strongly recommended if feasible:

- `expand_from_work`
- `search_literature_signals`
- `export_records`

Do not expose source-specific MCP tools by default. Source-specific debugging may exist in CLI advanced mode, not in the default MCP tool surface.

---

## Priority 8 — Agent Integration

Follow `04_Agent_Integration_and_Skill_Spec.md`.

OpenCode must be implemented first, but Codex and Claude must not be treated as afterthoughts. If full implementation for Codex/Claude is not feasible in this run, create clean adapter scaffolds, documented config templates, and tests for dry-run output.

Implement:

- `searchpaper install --target opencode`
- `searchpaper integrate status`
- `searchpaper integrate dry-run --target opencode`
- `searchpaper integrate doctor`
- `searchpaper integrate uninstall --target opencode`

Also implement or scaffold:

- `searchpaper install --target codex`
- `searchpaper install --target claude`
- `searchpaper install --target all`

The installer must:

- avoid destructive overwrites;
- record managed files;
- support dry-run;
- support uninstall;
- create backups before modifying user config;
- use marker-delimited managed sections when modifying text files;
- store minimal integration state, for example under `~/.config/searchpaper/integrations.json` or an equivalent platform-appropriate path.

---

## Priority 9 — Cross-Agent Skill

Add a skill document at:

```text
.agents/skills/literature-search/SKILL.md
```

The skill must teach agents:

- when to use SearchPaper;
- how to prefer CLI or MCP tools;
- how to preserve DOI/PMID/source provenance;
- how to treat literature signals as signals, not evaluated conclusions;
- how to handle degraded sources;
- how to export results for downstream research agents;
- how to avoid repeated live API retry loops.

If existing agent-specific instruction files exist, update them with marker-delimited SearchPaper sections rather than overwriting user content.

---

## Priority 10 — Documentation

Update README or docs to explain:

- project scope and non-goals;
- no-key usable default behavior;
- optional API keys;
- source degradation behavior;
- cache path and privacy notes;
- CLI quickstart;
- OpenCode quickstart;
- MCP configuration;
- Codex and Claude support status;
- JSON/JSONL output stability;
- signal levels and interpretation limits;
- testing without live public APIs.

Do not over-document speculative future features. Document implemented behavior and clearly marked extension points.

---

## Testing Requirements

CI must pass without live public APIs.

Required tests:

1. schema validation tests;
2. schema snapshot tests;
3. source adapter fixture tests;
4. merge regression tests;
5. cache tests;
6. CLI smoke tests;
7. MCP mocked tool tests;
8. degraded-source partial success tests;
9. installer dry-run tests;
10. signal-level serialization tests;
11. capabilities output tests.

Live API tests may be optional and must not gate CI.

---

## Degradation Rules

Public APIs are allowed to be unreliable. The correct behavior is controlled degradation, not endless retries or deleting the source from the design.

For each source:

- make at most 2 live debugging attempts before marking degraded;
- spend no more than 15 minutes of focused debugging on a single external API endpoint in `/goal` mode;
- after degradation, preserve adapter contract and mocked tests;
- add source status and warnings;
- continue implementing the rest of the system.

Do not remove a planned source entirely unless it is clearly out of scope or impossible to model. Prefer a degraded adapter with clear status over blocking implementation.

---

## Anti-Loop Rules

Do not loop on:

- project naming;
- exact wording of evidence vs signal;
- perfect source ranking;
- perfect API coverage;
- PDF parsing;
- UI;
- source-specific MCP tool proliferation;
- plugin packaging;
- full migration framework;
- Zotero/Obsidian integration;
- graph database selection;
- live API CI instability.

When uncertain, choose the simpler option that preserves schema, provenance, partial success, tests, and future extension points.

---

## Acceptance Criteria

The `/goal` run is successful if all of the following are true:

1. `searchpaper search "HCC TACE PD-1" --json` returns normalized records with provenance, warnings, and trace.
2. At least three source adapters are implemented with fixture-backed tests, and at least two can work in normal live usage where possible.
3. PubMed or Europe PMC is included unless a clear external blocker is documented.
4. A failed or degraded source does not fail the whole search.
5. Identifier resolution and merge preserve DOI/PMID/PMCID where available.
6. Results include source provenance, merge reasons, trace, and warnings.
7. Literature signals include explicit signal level and interpretation warning.
8. Cache stats, cache clear, and no-cache search behavior work.
9. `searchpaper capabilities --json` reports available CLI commands, MCP tools, sources, export formats, and integration targets.
10. MCP server starts and exposes the required core tools.
11. OpenCode install or dry-run works and does not destructively overwrite user files.
12. Codex and Claude support is implemented or scaffolded with config templates/dry-run behavior.
13. Cross-agent skill exists at `.agents/skills/literature-search/SKILL.md`.
14. CI passes without live API dependency.
15. README or docs explain no-key usage, cache, degradation, signal limits, and non-goals.

Stretch success, if feasible without destabilizing the foundation:

- `searchpaper export` supports JSONL and at least one citation format such as BibTeX or RIS;
- `searchpaper signals` exposes PubTator3 or metadata/abstract-level signals;
- `searchpaper init` creates optional project-level `.searchpaper/` trace/export state;
- `searchpaper batch` handles simple JSONL or text input.

---

## Final Instruction

Optimize for a solid, extensible foundation rather than broad but fragile feature coverage.

Do not skip planned public sources just because a live endpoint is temporarily unreliable. Implement the adapter boundary, fixture tests, degraded status, and documentation, then continue.

A partially degraded but well-structured SearchPaper is acceptable. A broad but fragile tool, or an agent trapped in live API debugging loops, is not acceptable.
