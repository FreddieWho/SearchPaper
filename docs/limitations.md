# Known Limitations

This document lists deliberate scope boundaries and known gaps in SearchPaper.

## Sources

- **T3 sources** such as Scopus, Web of Science, Google Scholar, CNKI, and Wanfang
  are cataloged for reference but are not automatically queried. They require
  API access, institutional subscriptions, or legal/integration work outside the
  current scope.
- Chinese-language academic databases are not implemented.

## Citation and Reference Formats

- APA 7 and MLA 9 formatters cover common journal-article cases. Edge cases such
  as edited volumes, dissertations, legal citations, and non-Latin scripts are
  not exhaustively handled.
- Citation verification relies on open-access identifiers and search matching;
  it can miss paywalled or unindexed references.

## Full Text

- SearchPaper reports full-text availability and can download OA PDFs and
  Europe PMC XML, but it does **not** parse PDF content.
- Structured full-text anchor extraction is currently limited to Europe PMC OA
  XML.

## Agent Integrations

- Codex and Claude integrations generate scaffold files and safe config snippets.
  They do not overwrite user config files by default; manual merge may be required.

## Evaluation

- SearchPaper returns literature-backed signals, not evaluated scientific
  evidence. Do not treat co-mentions or relations as proof of causality.
