import os
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from paper_search.cache import Cache
from paper_search.config import load_config
from paper_search.semantic_scholar import SemanticScholarClient
from paper_search.pubtator3 import PubTator3Client

mcp = FastMCP("paperSearch")

_config = load_config()

cache_path = os.getenv("PAPER_SEARCH_CACHE") or str(_config.get("cache_path", "/tmp/paper_search_cache.db"))
s2_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY") or _config.get("semantic_scholar_api_key")

cache = Cache(db_path=cache_path)
s2 = SemanticScholarClient(api_key=s2_api_key, cache=cache)
pubtator = PubTator3Client(cache=cache)


# --- Semantic Scholar Tools ---

@mcp.tool()
async def s2_search_papers(
    query: str,
    year: Optional[str] = None,
    venue: Optional[str] = None,
    fields_of_study: Optional[list[str]] = None,
    publication_types: Optional[list[str]] = None,
    min_citation_count: Optional[int] = None,
    open_access_pdf: Optional[bool] = None,
    limit: int = 20,
    include_abstract: bool = False,
    sort: Optional[str] = None,
    refresh: bool = False,
) -> dict[str, Any]:
    return await s2.search_papers(
        query=query,
        year=year,
        venue=venue,
        fields_of_study=fields_of_study,
        publication_types=publication_types,
        min_citation_count=min_citation_count,
        open_access_pdf=open_access_pdf,
        limit=limit,
        include_abstract=include_abstract,
        sort=sort,
        refresh=refresh,
    )


@mcp.tool()
async def s2_get_paper(
    paper_id: str,
    include_abstract: bool = True,
    include_tldr: bool = True,
    include_embedding: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    return await s2.get_paper(
        paper_id=paper_id,
        include_abstract=include_abstract,
        include_tldr=include_tldr,
        include_embedding=include_embedding,
        refresh=refresh,
    )


@mcp.tool()
async def s2_batch_get_papers(
    paper_ids: list[str],
    include_abstract: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    return await s2.batch_get_papers(
        paper_ids=paper_ids,
        include_abstract=include_abstract,
        refresh=refresh,
    )


@mcp.tool()
async def s2_get_citations(
    paper_id: str,
    limit: int = 50,
    offset_or_token: Optional[str] = None,
    include_abstract: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    return await s2.get_citations(
        paper_id=paper_id,
        limit=limit,
        offset_or_token=offset_or_token,
        include_abstract=include_abstract,
        refresh=refresh,
    )


@mcp.tool()
async def s2_get_references(
    paper_id: str,
    limit: int = 50,
    offset_or_token: Optional[str] = None,
    include_abstract: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    return await s2.get_references(
        paper_id=paper_id,
        limit=limit,
        offset_or_token=offset_or_token,
        include_abstract=include_abstract,
        refresh=refresh,
    )


@mcp.tool()
async def s2_recommend_papers(
    positive_paper_ids: list[str],
    negative_paper_ids: Optional[list[str]] = None,
    limit: int = 20,
    include_abstract: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    return await s2.recommend_papers(
        positive_paper_ids=positive_paper_ids,
        negative_paper_ids=negative_paper_ids or [],
        limit=limit,
        include_abstract=include_abstract,
        refresh=refresh,
    )


# --- PubTator3 Tools ---

@mcp.tool()
async def pubtator_find_entity(
    query: str,
    limit: int = 10,
    refresh: bool = False,
) -> dict[str, Any]:
    return await pubtator.find_entity(query=query, limit=limit, refresh=refresh)


@mcp.tool()
async def pubtator_find_relations(
    e1: str,
    e2_type: str,
    relation_type: str,
    limit: int = 10,
    refresh: bool = False,
) -> dict[str, Any]:
    return await pubtator.find_relations(
        e1=e1,
        e2_type=e2_type,
        relation_type=relation_type,
        limit=limit,
        refresh=refresh,
    )


@mcp.tool()
async def pubtator_search(
    text: str,
    page: int = 1,
    refresh: bool = False,
) -> dict[str, Any]:
    return await pubtator.search(text=text, page=page, refresh=refresh)


async def _fetch_relation_pmids(
    pubtator: PubTator3Client,
    e1: str,
    e2: str,
    relation_type: str,
    limit_pmids: int,
    refresh: bool,
) -> tuple[list[str], list[dict[str, str]]]:
    search_text = f"relations:{relation_type}|{e1}|{e2}"
    search_res = await pubtator.search(text=search_text, page=1, refresh=refresh)
    pmid_items = search_res.get("items", [])[:limit_pmids]
    pmids = [str(item["pmid"]) for item in pmid_items if item.get("pmid")]
    evidence_urls = [
        {
            "pmid": str(item["pmid"]),
            "pubmed_url": item["pubmed_url"],
            "pubtator_url": item["pubtator_url"],
        }
        for item in pmid_items
        if item.get("pmid")
    ]
    return pmids, evidence_urls


@mcp.tool()
async def biomed_relation_evidence(
    entity1_name: str,
    relation_type: str,
    entity2_name: Optional[str] = None,
    entity2_type: Optional[str] = None,
    limit_entities: int = 5,
    limit_pmids_per_pair: int = 5,
    refresh: bool = False,
) -> dict[str, Any]:
    warnings: list[str] = []
    intermediate: list[dict[str, Any]] = []

    e1 = entity1_name
    if not e1.startswith("@"):
        ent_res = await pubtator.find_entity(query=e1, limit=limit_entities, refresh=refresh)
        items = ent_res.get("items", [])
        if not items:
            return {
                "source": "composite",
                "query": {"entity1_name": entity1_name, "relation_type": relation_type, "entity2_name": entity2_name},
                "retrieved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "cache_key": None,
                "from_cache": False,
                "raw_ids": [],
                "items": [],
                "warnings": [f"No PubTator entity found for '{entity1_name}'"],
                "intermediate": [],
            }
        e1 = items[0]["entity_id"]
        intermediate.append({"step": "resolve_entity1", "input": entity1_name, "resolved_id": e1})

    e2 = entity2_name
    if e2 and not e2.startswith("@"):
        ent_res = await pubtator.find_entity(query=e2, limit=limit_entities, refresh=refresh)
        items = ent_res.get("items", [])
        if items:
            e2 = items[0]["entity_id"]
            intermediate.append({"step": "resolve_entity2", "input": entity2_name, "resolved_id": e2})
        else:
            warnings.append(f"No PubTator entity found for '{entity2_name}'")
            e2 = None

    if e2:
        entity2_type = entity2_type or "chemical"
        rel_res = await pubtator.find_relations(
            e1=e1, e2_type=entity2_type, relation_type=relation_type, limit=limit_entities, refresh=refresh
        )
        relations = rel_res.get("items", [])
        filtered = [r for r in relations if r["entity2"]["entity_id"] == e2 or r["entity2"]["name"] == entity2_name]
        if not filtered:
            filtered = relations
        results = []
        for r in filtered[:limit_entities]:
            e2_id = r["entity2"]["entity_id"] or e2
            pmids, evidence_urls = await _fetch_relation_pmids(
                pubtator, e1, e2_id, relation_type, limit_pmids_per_pair, refresh
            )
            r["pmids"] = pmids
            r["evidence_urls"] = evidence_urls
            r["evidence_count"] = r.get("evidence_count")
            results.append(r)
        return {
            "source": "composite",
            "query": {"entity1_name": entity1_name, "entity2_name": entity2_name, "relation_type": relation_type},
            "retrieved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "cache_key": None,
            "from_cache": False,
            "raw_ids": [r["entity2"]["entity_id"] for r in results],
            "items": results,
            "warnings": warnings,
            "intermediate": intermediate,
        }

    candidate_types = [entity2_type] if entity2_type else ["chemical", "disease", "gene"]
    all_results: list[dict[str, Any]] = []
    for ct in candidate_types:
        rel_res = await pubtator.find_relations(
            e1=e1, e2_type=ct, relation_type=relation_type, limit=limit_entities, refresh=refresh
        )
        for r in rel_res.get("items", []):
            e2_id = r["entity2"]["entity_id"]
            if not e2_id:
                continue
            pmids, evidence_urls = await _fetch_relation_pmids(
                pubtator, e1, e2_id, relation_type, limit_pmids_per_pair, refresh
            )
            r["pmids"] = pmids
            r["evidence_urls"] = evidence_urls
            r["evidence_count"] = r.get("evidence_count")
            all_results.append(r)

    return {
        "source": "composite",
        "query": {"entity1_name": entity1_name, "relation_type": relation_type, "entity2_name": entity2_name},
        "retrieved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "cache_key": None,
        "from_cache": False,
        "raw_ids": [r["entity2"]["entity_id"] for r in all_results],
        "items": all_results[:limit_entities],
        "warnings": warnings,
        "intermediate": intermediate,
    }


@mcp.tool()
async def paper_enrich_with_pubtator(
    paper_id_or_pmid: str,
    refresh: bool = False,
) -> dict[str, Any]:
    s2_res = await s2.get_paper(paper_id=paper_id_or_pmid, include_abstract=True, refresh=refresh)
    paper_items = s2_res.get("items", [])
    if not paper_items:
        return {
            "source": "composite",
            "query": {"paper_id_or_pmid": paper_id_or_pmid},
            "retrieved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "cache_key": None,
            "from_cache": False,
            "raw_ids": [],
            "items": [],
            "warnings": ["Paper not found in Semantic Scholar."],
        }
    paper = paper_items[0]
    pmid = paper.get("pmid")
    pubtator_annotations: dict[str, Any] = {"entities": [], "relations": [], "search_results": []}
    warnings: list[str] = []
    if pmid:
        search_res = await pubtator.search(text=pmid, page=1, refresh=refresh)
        pubtator_annotations["search_results"] = search_res.get("items", [])
        if not pubtator_annotations["search_results"]:
            warnings.append(f"PubTator search for PMID {pmid} returned no results.")
    else:
        warnings.append("No PMID available; PubTator enrichment skipped.")

    return {
        "source": "composite",
        "query": {"paper_id_or_pmid": paper_id_or_pmid},
        "retrieved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "cache_key": None,
        "from_cache": False,
        "raw_ids": [paper.get("paper_id")],
        "items": [{"paper": paper, "pubtator": pubtator_annotations}],
        "warnings": warnings,
    }


@mcp.tool()
async def research_query(
    query: str,
    domain: str = "general",
    year: Optional[str] = None,
    limit: int = 20,
    include_pubtator: bool = True,
    refresh: bool = False,
) -> dict[str, Any]:
    limit = min(max(limit, 1), 50)
    s2_res = await s2.search_papers(
        query=query, year=year, limit=limit, include_abstract=False, refresh=refresh
    )
    papers = s2_res.get("items", [])
    enriched = []
    warnings: list[str] = []
    pubtator_limit = 5
    if include_pubtator:
        count = 0
        for p in papers:
            pmid = p.get("pmid")
            if pmid and count < pubtator_limit:
                try:
                    pt_res = await pubtator.search(text=pmid, page=1, refresh=refresh)
                    p["pubtator_snippets"] = pt_res.get("items", [])
                    count += 1
                except Exception as e:
                    warnings.append(f"PubTator enrichment failed for PMID {pmid}: {e}")
            enriched.append(p)
    else:
        enriched = papers

    return {
        "source": "composite",
        "query": query,
        "retrieved_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "cache_key": s2_res.get("cache_key"),
        "from_cache": s2_res.get("from_cache", False),
        "raw_ids": s2_res.get("raw_ids", []),
        "items": enriched,
        "warnings": warnings + s2_res.get("warnings", []),
        "domain": domain,
        "total": s2_res.get("total"),
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
