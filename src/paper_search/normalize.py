from typing import Any


def _val(d: dict, key: str, default=None):
    return d.get(key, default) if d else default


def normalize_paper(raw: dict[str, Any]) -> dict[str, Any]:
    ext = _val(raw, "externalIds") or {}
    authors = []
    for a in _val(raw, "authors") or []:
        if isinstance(a, dict):
            authors.append({"author_id": a.get("authorId"), "name": a.get("name", "")})
    oa = _val(raw, "openAccessPdf")
    if isinstance(oa, dict):
        open_access_pdf = {"url": oa.get("url"), "status": oa.get("status")}
    else:
        open_access_pdf = {"url": None, "status": None}
    tldr = raw.get("tldr")
    tldr_text = tldr.get("text") if isinstance(tldr, dict) else None

    return {
        "paper_id": raw.get("paperId", ""),
        "title": raw.get("title", ""),
        "year": raw.get("year"),
        "publication_date": raw.get("publicationDate"),
        "venue": raw.get("venue"),
        "url": raw.get("url"),
        "doi": ext.get("DOI"),
        "pmid": ext.get("PubMed"),
        "arxiv": ext.get("ArXiv"),
        "citation_count": raw.get("citationCount"),
        "influential_citation_count": raw.get("influentialCitationCount"),
        "authors": authors,
        "open_access_pdf": open_access_pdf,
        "fields_of_study": raw.get("fieldsOfStudy") or [],
        "publication_types": raw.get("publicationTypes") or [],
        "abstract": raw.get("abstract"),
        "tldr": tldr_text,
        "source": "semantic_scholar",
    }


def normalize_entity(raw: dict[str, Any]) -> dict[str, Any]:
    entity_id = raw.get("_id") or raw.get("id", "")
    entity_type = raw.get("biotype") or raw.get("type")
    return {
        "entity_id": entity_id,
        "name": raw.get("name"),
        "type": entity_type,
        "source": "pubtator3",
    }


def _pmid_url(pmid: str) -> dict[str, str]:
    return {
        "pmid": pmid,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "pubtator_url": f"https://www.ncbi.nlm.nih.gov/research/pubtator3/publication/{pmid}",
    }


def normalize_relation(raw: dict[str, Any]) -> dict[str, Any]:
    e1 = normalize_entity(raw.get("entity1") or {})
    e2 = normalize_entity(raw.get("entity2") or {})
    pmids = raw.get("pmids") or []
    evidence_count = raw.get("evidence_count")
    return {
        "entity1": e1,
        "entity2": e2,
        "relation_type": raw.get("relation_type", ""),
        "pmids": pmids,
        "evidence_count": evidence_count,
        "evidence_urls": [_pmid_url(str(p)) for p in pmids],
        "source": "pubtator3",
    }
