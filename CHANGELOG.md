# Changelog

All notable changes to SearchPaper are tracked here.

## Unreleased

## 0.4.0 — Integration and Source Expansion

### Added

- **Unpaywall adapter** for open-access PDF resolution and OA status (requires `UNPAYWALL_EMAIL` or `CROSSREF_EMAIL` for polite pool).
- **OpenCitations adapter** for DOI-to-DOI citation links.
- **Remote/HTTP MCP server** via `searchpaper serve --mcp --transport http` using SSE.
- **Enhanced source health diagnostics**: `searchpaper sources explain <source>` and `searchpaper sources diagnose` with actionable recommendations.
- **Integration migration support**: `searchpaper integrate migrate` re-installs managed files and tracks `searchpaper_version` in integration state.
- **Project-level trace/export workflow**: `searchpaper init`, `searchpaper search ... --save`, `searchpaper project traces`, and `searchpaper project export <trace_id> --format ...`.
- **Zotero CSV** and **Obsidian YAML-frontmatter** export formats.
- Documentation for source-specific usage limitations in `docs/source-usage.md`.

### Changed

- Bumped version to `0.4.0`.
- Updated `searchpaper capabilities` to report new CLI commands and export formats.

## 0.3.0 — Biomedical Signal and Agent Hardening

### Fixed

- Fixed local test discovery by adding `src` to pytest's import path.
- Isolated test cache writes under the system temp directory so MCP imports do not depend on a writable user cache.
- Replaced working-directory-dependent agent skill fallback with a packaged shared literature-search instruction template.
- Brought OpenCode, Codex, and Claude integration instructions onto the same safety rules for provenance, degraded sources, and signal interpretation.

### Added

- Added writable repository skill templates for OpenCode and Claude alongside the generic `.agents` skill.
- Added integration tests covering shared agent instruction safety rules and Codex/Claude dry-run install targets.
- Added source catalog and search planner inspired by `nature-academic-search` source-tier workflows.
- Added arXiv, bioRxiv, and medRxiv source adapters using official public APIs.
- Added PubMed utility workflows for MeSH lookup, related articles, and DOI/PMID/PMCID conversion.
- Added source tier/preflight CLI commands and reference conversion for RIS/BibTeX/NBIB/ENW-style workflows.
- Added real `expand_from_work` support via Semantic Scholar citations, references, and recommendations.
- Added `searchpaper expand` CLI command.
- Added curated biomedical query set (`examples/biomedical_query_set.json`) and `scripts/smoke_benchmark.py`.
