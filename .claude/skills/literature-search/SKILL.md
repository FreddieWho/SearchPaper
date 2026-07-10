---
name: literature-search
description: Use when a task requires scholarly literature search, paper metadata, DOI/PMID/PMCID resolution, citation/context expansion, biomedical literature signals, or exportable literature records with SearchPaper.
---

# Literature Search with SearchPaper

Use SearchPaper when a task requires scholarly literature search, paper metadata,
DOI/PMID/PMCID resolution, citation/context expansion, biomedical literature
signals, or exportable literature records.

SearchPaper is not a research agent and does not evaluate scientific truth. It
returns literature records, provenance, identifiers, and signals that must be
interpreted by the user or a downstream research workflow.

## Preferred Workflow

1. Start with `searchpaper search "<query>" --json` or MCP `search_literature`.
   Use `searchpaper plan "<query>" --profile auto --json` or MCP
   `plan_literature_search` first when source coverage matters.
2. Preserve DOI, PMID, PMCID, source, and trace fields.
3. Use `resolve_identifiers` or `searchpaper resolve` when merging or checking a
   known paper.
4. Use `expand_from_work` only after identifying a reliable seed paper.
5. Use `search_literature_signals` for biomedical entity/relation signals, but
   do not call those signals proof.
6. If results are sparse or suspicious, call `get_source_status` or
   `searchpaper sources status`. Use `searchpaper sources tiers` to report
   sources that are cataloged but not queried automatically.
7. Use PubMed utilities (`searchpaper pubmed mesh`, `pubmed related`,
   `pubmed convert-ids`) for MeSH strategy, related articles, and DOI/PMID/PMCID
   conversion.
8. Export machine-readable results with JSONL when passing results to downstream
   agents.

## Interpretation Rules

- A literature signal is not an evaluated conclusion.
- A PubTator or abstract co-mention signal does not prove causality.
- A single relevant paper is still a useful literature-backed record, but the
  agent must report its source and limitations.
- Do not hide degraded or failed sources.
- Do not retry a broken public API repeatedly.
- Do not imply Scopus, Web of Science, Google Scholar, CNKI, or 万方 were
  searched unless an external/manual workflow actually checked them.

## Output Rules

When summarizing SearchPaper results, include:

- title;
- year;
- DOI/PMID/PMCID when available;
- source provenance;
- signal level if using signals;
- warnings or degraded-source notes.
