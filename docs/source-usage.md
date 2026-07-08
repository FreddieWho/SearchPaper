# Source Usage and Limitations

SearchPaper aggregates open scholarly sources. Each source has its own access model, rate limits, and coverage quirks. This document is the canonical reference for source-specific behavior.

## Implemented Sources

### PubMed (NCBI E-utilities)

- **Access model**: Official API, no key required.
- **Recommended key**: `NCBI_API_KEY` increases rate limits from 3 to 10 requests/second.
- **Coverage**: Biomedical literature with PMID/PMCID, title, abstract, MeSH, publication metadata.
- **Limitations**:
  - Non-biomedical queries return few or no results.
  - Very broad queries may hit NCBI result limits.
- **Usage note**: Set `NCBI_API_KEY` for sustained use.

### Crossref

- **Access model**: Official REST API, no key required.
- **Recommended key**: `CROSSREF_EMAIL` puts requests in the "polite" pool.
- **Coverage**: Cross-disciplinary DOI metadata, publisher, journal, license.
- **Limitations**:
  - Rate limiting is stricter without an email.
  - Metadata quality varies by publisher.
- **Usage note**: Set `CROSSREF_EMAIL` to improve reliability.

### OpenAlex

- **Access model**: Official REST API, no key required.
- **Recommended key**: `OPENALEX_EMAIL` grants higher rate limits.
- **Coverage**: Broad scholarly graph: works, authors, institutions, concepts.
- **Limitations**:
  - Complex queries may require multiple paging requests.
  - Concept coverage is less granular than MeSH for biomedical topics.
- **Usage note**: Use for non-biomedical and cross-disciplinary queries.

### Europe PMC

- **Access model**: Official REST API, no key required.
- **Recommended key**: `EUROPEPMC_API_KEY` for higher quotas.
- **Coverage**: Biomedical and life-science abstracts, PMCID, OA links.
- **Limitations**:
  - Full-text availability links are metadata-only anchors; PDF parsing is not performed.
- **Usage note**: Good biomedical fallback or enrichment source.

### arXiv

- **Access model**: Official Atom API, no key required.
- **Coverage**: Physics, math, CS, and quantitative biology preprints.
- **Limitations**:
  - Limited to preprint content.
  - No citation counts from arXiv itself.
- **Usage note**: Use with preprint profiles.

### bioRxiv / medRxiv

- **Access model**: Official API, no key required.
- **Coverage**: Life-science and health-science preprints.
- **Limitations**:
  - Search is coarse; best used with specific DOIs or recent date ranges.
- **Usage note**: Enable in preprint-focused profiles.

### Semantic Scholar

- **Access model**: Official REST API, no key optional.
- **Recommended key**: `SEMANTIC_SCHOLAR_API_KEY` for higher rate limits.
- **Coverage**: Citation graph, references, recommendations, fields of study.
- **Limitations**:
  - Without a key, rate limits are low.
  - Citation counts may differ from publisher metrics.
- **Usage note**: Required for `expand --by citations/references/similar`.

### Unpaywall

- **Access model**: Official REST API, no key required.
- **Required configuration**: `UNPAYWALL_EMAIL` (falls back to `CROSSREF_EMAIL`).
- **Coverage**: Open-access PDF links and OA status.
- **Limitations**:
  - Only resolves by DOI.
  - Rate limits apply to the polite pool.
- **Usage note**: Configure an email to avoid being rate-limited.

### OpenCitations

- **Access model**: Official REST API, no key required.
- **Coverage**: DOI-to-DOI citation links.
- **Limitations**:
  - Rate limits are strict.
  - Primarily useful for citation linking, not full metadata.
- **Usage note**: Use as a citation-link enrichment source.

### PubTator3

- **Access model**: Official NCBI API, no key required.
- **Coverage**: Biomedical entity annotations and reported relations.
- **Limitations**:
  - Biomedical focus only.
  - Returned relations are literature-backed signals, not evaluated evidence.
- **Usage note**: Use via `signals` or `search_literature_signals` for entity/relation exploration.

## Cataloged but Not Implemented

These sources are listed in the catalog so SearchPaper can report coverage gaps without querying them.

| Source | Reason |
|---|---|
| Scopus | Institution/API entitlement required |
| ScienceDirect | Elsevier entitlement required |
| Web of Science | Institution subscription required |
| Google Scholar | Scraping is unstable and may violate service limits |
| CNKI | No stable open programmatic access |
| Wanfang | No stable open programmatic access |

## Environment Variables Summary

| Variable | Source | Required | Notes |
|---|---|---|---|
| `NCBI_API_KEY` | PubMed | Optional | Increases rate limit |
| `CROSSREF_EMAIL` | Crossref | Optional | Polite pool |
| `OPENALEX_EMAIL` | OpenAlex | Optional | Higher rate limits |
| `EUROPEPMC_API_KEY` | Europe PMC | Optional | Higher quotas |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | Optional | Higher rate limits |
| `UNPAYWALL_EMAIL` | Unpaywall | Recommended | Polite pool; falls back to `CROSSREF_EMAIL` |
| `SEARCHPAPER_CACHE` | Cache | Optional | Override default cache path |
| `SEARCHPAPER_CONFIG` | Config | Optional | Override default config path |

## Export Formats

SearchPaper supports the following export formats:

- `json`, `jsonl` — canonical machine-readable formats
- `bibtex`, `ris`, `nbib`, `enw` — citation/bibliography formats
- `markdown` — human-readable notes
- `zotero` — CSV table suitable for Zotero import helpers
- `obsidian` — Markdown notes with YAML frontmatter for Obsidian vaults

Zotero and Obsidian exports are extension points. For full Zotero API sync or Obsidian vault generation, see the v0.5 roadmap.
