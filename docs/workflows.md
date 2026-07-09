# Literature Workflows

SearchPaper borrows the workflow shape from `nature-academic-search` while
keeping implementation inside its own schemas, source adapters, CLI, and MCP
tools.

## Implemented Workflow Coverage

- Multi-source search: `searchpaper search`, `searchpaper plan`, and MCP
  `search_literature` / `plan_literature_search`.
- Source routing and preflight: `searchpaper sources tiers` and
  `searchpaper sources preflight`.
- PubMed utilities: `searchpaper pubmed mesh`, `searchpaper pubmed related`,
  and `searchpaper pubmed convert-ids`.
- Citation file management: `searchpaper references convert` supports
  `DOI:` / `PMID:` / `ARXIV:` / `QUERY:` / `AUTHOR:` / `TITLE:` lines and
  exports to JSON/JSONL/BibTeX/RIS/Markdown/NBIB/ENW/APA/MLA.
- Citation verification: `searchpaper references verify` parses `.txt`, `.docx`,
  and `.tex` documents and classifies each citation as `verified`, `mismatch`,
  `not_found`, `suspicious`, or `manual_needed`.
- Batch processing: `searchpaper batch` runs many queries or identifiers and
  outputs JSON/JSONL or any supported citation format.
- Full-text readiness: `searchpaper get --download-pdf` / `--download-xml`
  downloads OA PDFs and Europe PMC XML without parsing.

## Deferred Workflow Coverage

- Strict independent other-citation audit is deferred.
- High-profile citer identity checks and citation-context extraction are deferred.
- Full-text/PDF parsing is deferred; structured PMC/JATS support can be added as
  a separate phase.

## External Reference

The workflow ideas were evaluated from:
<https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-academic-search>

SearchPaper does not depend on that repository at runtime.
