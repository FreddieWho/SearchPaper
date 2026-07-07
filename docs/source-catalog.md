# Source Catalog

SearchPaper keeps source coverage explicit. Implemented sources use the unified
adapter contract; unsupported or institution-gated sources are cataloged so
agents can report coverage gaps without pretending those sources were searched.

## Implemented Sources

| Source | Tier | Domain | Access |
|---|---|---|---|
| PubMed | T1 | Biomedical | Official NCBI E-utilities |
| Crossref | T1 | Cross-disciplinary | Official REST API |
| OpenAlex | T1 | Cross-disciplinary | Official REST API |
| Europe PMC | T1 | Biomedical | Official REST API |
| arXiv | T1 | Preprints | Official Atom API |
| bioRxiv | T2 | Preprints | Official bioRxiv API |
| medRxiv | T2 | Preprints | Official medRxiv API |
| Semantic Scholar | T2 | Citation graph | Official REST API |
| PubTator3 | Signal | Biomedical signals | Official NCBI API |

## Cataloged But Not Queried Automatically

| Source | Tier | Reason |
|---|---|---|
| Scopus | T3 | Institution/API entitlement and quota required |
| ScienceDirect | T3 | Elsevier entitlement required |
| Web of Science | T3 | Institution subscription required |
| Google Scholar | T3 | Scraping is unstable and may violate service limits |
| CNKI | Manual | No stable open programmatic access |
| 万方 | Manual | No stable open programmatic access |

This catalog is inspired by the source-tier routing in
`nature-academic-search`, but SearchPaper only implements sources that fit its
no-key or optional-key infrastructure model.
