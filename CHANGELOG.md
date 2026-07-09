# Changelog

All notable changes to SearchPaper are tracked here.

## Unreleased

## 0.5.0 — Full-Text-Ready Expansion

### Added

- **Full-text availability reporting**: `WorkRecord` now includes `full_text_availability` with `has_full_text`, `has_pdf`, `oa_url`, `oa_pdf_url`, and `license`.
- **Europe PMC full-text metadata**: Europe PMC adapter parses `fullTextUrlList`, `hasFullText`, and `isOpenAccess`.
- **Full-text anchors**: `Anchor` schema extended with `anchor_type`, `text_scope`, and `section`; Europe PMC adapter can extract section anchors from OA full-text XML.
- **Unpaywall automatic enrichment**: `get` and `resolve` now automatically enrich DOIs with Unpaywall OA metadata.
- **Paper context packs**: new `searchpaper context` CLI command builds a structured context pack for downstream agents.
- **Canonical URL generation**: merged works now expose DOI, PubMed, PMC, arXiv, and OA URLs.
- New CLI flags `--anchors` on `get` and `resolve` to fetch full-text anchors when available.
- **Source requirement modes**: `--require` and `--source-mode` let callers mark sources as `optional`, `preferred`, or `required`.
- **`searchpaper batch`**: process JSONL/text files of queries or identifiers and export to any supported format.
- **Citation verification**: `searchpaper references verify` parses `.txt`, `.docx`, and `.tex` documents and classifies each citation.
- **Full-text download**: `searchpaper get --download-pdf` and `--download-xml` save OA PDFs and Europe PMC XML without parsing.
- **APA/MLA export** formats and improved RIS/BibTeX field mapping.
- **Domain query templates** in `searchpaper plan` for medical, molecular, epidemiology, and methods queries.
- **`--sort combined`** ranking mode combining relevance, recency, and citations.
- Schema snapshot tests using `syrupy`.

### Changed

- Bumped version to `0.5.0`.
- Registered `unpaywall` and `opencitations` adapters in `searchpaper.sources` so they are discoverable by name.
- Updated `searchpaper capabilities` to report `expand`, `context`, `--anchors`, `batch`, `references verify`, and new export formats.
- Packaging metadata now uses the SPDX `license = "MIT"` form.

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
