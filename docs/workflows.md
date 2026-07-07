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
- Citation file management: `searchpaper references convert` and
  `searchpaper export` support JSON/JSONL/BibTeX/RIS/Markdown/NBIB/ENW.

## Deferred Workflow Coverage

- Citation verification from `.docx`, `.tex`, or `.txt` is deferred.
- Strict independent other-citation audit is deferred.
- High-profile citer identity checks and citation-context extraction are
  deferred.
- Full-text/PDF parsing is deferred; structured PMC/JATS support can be added as
  a separate phase.

## External Reference

The workflow ideas were evaluated from:
<https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-academic-search>

SearchPaper does not depend on that repository at runtime.
