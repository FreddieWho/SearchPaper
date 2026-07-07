# Changelog

All notable changes to SearchPaper are tracked here.

## Unreleased

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

### Next README / Release What's New

- SearchPaper now installs consistent agent guidance for OpenCode, Codex, and Claude through a package-backed instruction template.
- Test runs are more reproducible in sandboxed or CI environments because source imports and cache paths are configured explicitly.
- SearchPaper now covers official preprint sources and PubMed utility workflows while cataloging Scopus, Web of Science, Google Scholar, CNKI, and 万方 as external/manual sources.
