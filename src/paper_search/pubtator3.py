from typing import Any, Optional

import httpx

from paper_search.cache import Cache
from paper_search.normalize import normalize_entity, normalize_relation
from paper_search.rate_limit import fetch_with_retry

PUBTATOR_BASE = "https://www.ncbi.nlm.nih.gov"

TTL_ENTITY = 30 * 86400
TTL_RELATIONS = 14 * 86400
TTL_SEARCH = 7 * 86400

BLOCKED_ENTITY_NAMES = {
    "drug_related_side_effects_and_adverse_reactions",
    "pharmaceutical_preparations",
    "therapeutic_uses",
    "disease",
    "neoplasms",
    "chemicals_and_drugs",
    "genes",
    "cells",
}


def _is_blocked_entity(name: Optional[str]) -> bool:
    if not name:
        return False
    return name.lower().replace(" ", "_") in BLOCKED_ENTITY_NAMES


def _now() -> str:
    return __import__("datetime").datetime.utcnow().isoformat() + "Z"


class PubTator3Client:
    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache
        self.client = httpx.AsyncClient(timeout=30.0)

    def _cache_meta(self, endpoint: str, params: Any):
        if self.cache is None:
            return {"from_cache": False, "cache_key": None}
        _, meta = self.cache.get("pubtator3", endpoint, params, None)
        return meta

    def _error_result(self, resp: httpx.Response, query: Any, meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "pubtator3",
            "query": query,
            "retrieved_at": _now(),
            "cache_key": meta.get("cache_key"),
            "from_cache": False,
            "raw_ids": [],
            "items": [],
            "warnings": [f"PubTator3 HTTP {resp.status_code}: {resp.text[:200]}"],
        }

    async def find_entity(self, query: str, limit: int = 10, refresh: bool = False) -> dict[str, Any]:
        limit = min(max(limit, 1), 30)
        params = {"query": query, "limit": limit}
        meta = self._cache_meta("entity_autocomplete", params)

        if not refresh and self.cache:
            cached, _ = self.cache.get("pubtator3", "entity_autocomplete", params, None)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{PUBTATOR_BASE}/research/pubtator3-api/entity/autocomplete/"
        resp = await fetch_with_retry(self.client, "GET", url, params=params)
        if resp.status_code >= 400:
            return self._error_result(resp, query, meta)
        data = resp.json()
        raw_items = data if isinstance(data, list) else data.get("results", [])
        items = []
        for i in raw_items:
            if isinstance(i, dict) and not _is_blocked_entity(i.get("name")):
                items.append(normalize_entity(i))
        result = {
            "source": "pubtator3",
            "query": query,
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["entity_id"] for i in items if i.get("entity_id")],
            "items": items,
            "warnings": [],
        }
        if self.cache:
            self.cache.set("pubtator3", "entity_autocomplete", params, None, result, ttl_seconds=TTL_ENTITY)
        return result

    async def find_relations(
        self,
        e1: str,
        e2_type: str,
        relation_type: str,
        limit: int = 10,
        refresh: bool = False,
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), 50)
        params = {"e1": e1, "e2": e2_type, "type": relation_type, "limit": limit}
        meta = self._cache_meta("relations", params)

        if not refresh and self.cache:
            cached, _ = self.cache.get("pubtator3", "relations", params, None)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{PUBTATOR_BASE}/research/pubtator3-api/relations"
        resp = await fetch_with_retry(self.client, "GET", url, params=params)
        if resp.status_code >= 400:
            return self._error_result(resp, {"e1": e1, "e2_type": e2_type, "relation_type": relation_type}, meta)
        data = resp.json()
        raw_items = data if isinstance(data, list) else data.get("results", [])
        items = []
        for i in raw_items:
            if isinstance(i, dict):
                src = i.get("source")
                tgt = i.get("target")
                if src and tgt:
                    other = src if tgt == e1 else tgt
                elif src:
                    other = src
                else:
                    other = tgt
                rel = {
                    "entity1": {"_id": e1},
                    "entity2": i.get("entity2") or {"_id": other},
                    "relation_type": relation_type,
                    "pmids": [],
                    "evidence_count": i.get("publications"),
                }
                if not _is_blocked_entity(rel["entity2"].get("name") or rel["entity2"].get("_id")):
                    items.append(normalize_relation(rel))
        result = {
            "source": "pubtator3",
            "query": {"e1": e1, "e2_type": e2_type, "relation_type": relation_type},
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["entity2"]["entity_id"] for i in items if i.get("entity2")],
            "items": items,
            "warnings": [],
        }
        if self.cache:
            self.cache.set("pubtator3", "relations", params, None, result, ttl_seconds=TTL_RELATIONS)
        return result

    async def search(self, text: str, page: int = 1, refresh: bool = False) -> dict[str, Any]:
        params = {"text": text, "page": page}
        meta = self._cache_meta("search", params)

        if not refresh and self.cache:
            cached, _ = self.cache.get("pubtator3", "search", params, None)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{PUBTATOR_BASE}/research/pubtator3-api/search/"
        resp = await fetch_with_retry(self.client, "GET", url, params=params)
        if resp.status_code >= 400:
            return self._error_result(resp, text, meta)
        data = resp.json()
        raw_items = data if isinstance(data, list) else data.get("results", [])
        items = []
        for i in raw_items:
            if isinstance(i, dict):
                item = {
                    "pmid": i.get("pmid") or i.get("pmcid"),
                    "title": i.get("title"),
                    "source": "pubtator3",
                }
                pmid = item.get("pmid")
                if pmid:
                    item["pubmed_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    item["pubtator_url"] = f"https://www.ncbi.nlm.nih.gov/research/pubtator3/publication/{pmid}"
                items.append(item)
        result = {
            "source": "pubtator3",
            "query": text,
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["pmid"] for i in items if i.get("pmid")],
            "items": items,
            "warnings": [],
            "page": page,
        }
        if self.cache:
            self.cache.set("pubtator3", "search", params, None, result, ttl_seconds=TTL_SEARCH)
        return result
