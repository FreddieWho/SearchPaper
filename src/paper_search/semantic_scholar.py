import os
from typing import Any, Optional

import httpx

from paper_search.cache import Cache
from paper_search.normalize import normalize_paper
from paper_search.rate_limit import fetch_with_retry

S2_GRAPH_BASE = "https://api.semanticscholar.org/graph/v1"
S2_REC_BASE = "https://api.semanticscholar.org/recommendations/v1"

TTL_SEARCH = 7 * 86400
TTL_DETAILS = 30 * 86400
TTL_CITATIONS = 30 * 86400
TTL_RECOMMENDATIONS = 14 * 86400

DEFAULT_FIELDS = [
    "paperId",
    "title",
    "year",
    "publicationDate",
    "url",
    "venue",
    "citationCount",
    "influentialCitationCount",
    "authors",
    "externalIds",
    "openAccessPdf",
    "publicationTypes",
    "fieldsOfStudy",
]


def _now() -> str:
    return __import__("datetime").datetime.utcnow().isoformat() + "Z"


class SemanticScholarClient:
    def __init__(self, api_key: Optional[str] = None, cache: Optional[Cache] = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.cache = cache
        self.headers = {}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key
        self.client = httpx.AsyncClient(timeout=30.0, headers=self.headers)

    def _build_fields(self, include_abstract: bool, extra: Optional[list[str]] = None) -> str:
        fields = list(DEFAULT_FIELDS)
        if include_abstract:
            fields.append("abstract")
        if extra:
            for e in extra:
                if e not in fields:
                    fields.append(e)
        return ",".join(fields)

    def _cache_meta(self, source: str, endpoint: str, params: Any, fields: list[str]) -> dict[str, Any]:
        if self.cache is None:
            return {"from_cache": False, "cache_key": None}
        _, meta = self.cache.get(source, endpoint, params, fields)
        return meta

    def _error_result(self, resp: httpx.Response, query: Any, meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "semantic_scholar",
            "query": query,
            "retrieved_at": _now(),
            "cache_key": meta.get("cache_key"),
            "from_cache": False,
            "raw_ids": [],
            "items": [],
            "warnings": [f"Semantic Scholar HTTP {resp.status_code}: {resp.text[:200]}"],
        }

    async def search_papers(
        self,
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
        limit = min(max(limit, 1), 100)
        fields_str = self._build_fields(include_abstract)
        params: dict[str, Any] = {"query": query, "fields": fields_str, "limit": limit}
        if year:
            params["year"] = year
        if venue:
            params["venue"] = venue
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)
        if publication_types:
            params["publicationTypes"] = ",".join(publication_types)
        if min_citation_count is not None:
            params["minCitationCount"] = min_citation_count
        if open_access_pdf is not None:
            params["openAccessPdf"] = str(open_access_pdf)
        if sort:
            params["sort"] = sort

        cache_params = {k: v for k, v in params.items() if k != "fields"}
        cache_fields = fields_str.split(",")
        meta = self._cache_meta("s2", "search", cache_params, cache_fields)

        if not refresh and self.cache:
            cached, _ = self.cache.get("s2", "search", cache_params, cache_fields)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{S2_GRAPH_BASE}/paper/search"
        resp = await fetch_with_retry(self.client, "GET", url, params=params)
        if resp.status_code >= 400:
            return self._error_result(resp, query, meta)
        data = resp.json()
        raw_items = data.get("data", [])
        items = [normalize_paper(i) for i in raw_items]
        result = {
            "source": "semantic_scholar",
            "query": query,
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["paperId"] for i in raw_items if i.get("paperId")],
            "items": items,
            "warnings": [],
            "total": data.get("total"),
            "next": data.get("next"),
        }
        if not self.api_key:
            result["warnings"].append("No SEMANTIC_SCHOLAR_API_KEY set; anonymous rate limits apply.")
        if self.cache:
            self.cache.set("s2", "search", cache_params, cache_fields, result, ttl_seconds=TTL_SEARCH)
        return result

    async def get_paper(
        self,
        paper_id: str,
        include_abstract: bool = True,
        include_tldr: bool = True,
        include_embedding: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        extra = []
        if include_tldr:
            extra.append("tldr")
        if include_embedding:
            extra.append("embedding")
        fields_str = self._build_fields(include_abstract, extra=extra)
        params = {"fields": fields_str}
        cache_fields = fields_str.split(",")
        meta = self._cache_meta("s2", "paper_details", {"paper_id": paper_id}, cache_fields)

        if not refresh and self.cache:
            cached, _ = self.cache.get("s2", "paper_details", {"paper_id": paper_id}, cache_fields)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{S2_GRAPH_BASE}/paper/{paper_id}"
        resp = await fetch_with_retry(self.client, "GET", url, params=params)
        if resp.status_code >= 400:
            return self._error_result(resp, {"paper_id": paper_id}, meta)
        data = resp.json()
        item = normalize_paper(data)
        result = {
            "source": "semantic_scholar",
            "query": {"paper_id": paper_id},
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [item["paper_id"]] if item["paper_id"] else [],
            "items": [item],
            "warnings": [],
        }
        if not self.api_key:
            result["warnings"].append("No SEMANTIC_SCHOLAR_API_KEY set; anonymous rate limits apply.")
        if self.cache:
            self.cache.set("s2", "paper_details", {"paper_id": paper_id}, cache_fields, result, ttl_seconds=TTL_DETAILS)
        return result

    async def batch_get_papers(
        self,
        paper_ids: list[str],
        include_abstract: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        paper_ids = paper_ids[:100]
        fields_str = self._build_fields(include_abstract)
        payload = {"ids": paper_ids, "fields": fields_str}
        cache_fields = fields_str.split(",")
        meta = self._cache_meta("s2", "paper_batch", {"ids": paper_ids}, cache_fields)

        if not refresh and self.cache:
            cached, _ = self.cache.get("s2", "paper_batch", {"ids": paper_ids}, cache_fields)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{S2_GRAPH_BASE}/paper/batch"
        resp = await fetch_with_retry(self.client, "POST", url, json=payload)
        if resp.status_code >= 400:
            return self._error_result(resp, {"paper_ids": paper_ids}, meta)
        data = resp.json()
        raw_items = data if isinstance(data, list) else []
        items = [normalize_paper(i) for i in raw_items]
        result = {
            "source": "semantic_scholar",
            "query": {"paper_ids": paper_ids},
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["paperId"] for i in raw_items if i.get("paperId")],
            "items": items,
            "warnings": [],
        }
        if not self.api_key:
            result["warnings"].append("No SEMANTIC_SCHOLAR_API_KEY set; anonymous rate limits apply.")
        if self.cache:
            self.cache.set("s2", "paper_batch", {"ids": paper_ids}, cache_fields, result, ttl_seconds=TTL_DETAILS)
        return result

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 50,
        offset_or_token: Optional[str] = None,
        include_abstract: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), 200)
        fields_str = self._build_fields(include_abstract)
        params: dict[str, Any] = {"fields": fields_str, "limit": limit}
        if offset_or_token:
            params["offset"] = offset_or_token
        cache_fields = fields_str.split(",")
        cache_params = {"paper_id": paper_id, "limit": limit, "offset": offset_or_token}
        meta = self._cache_meta("s2", "citations", cache_params, cache_fields)

        if not refresh and self.cache:
            cached, _ = self.cache.get("s2", "citations", cache_params, cache_fields)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{S2_GRAPH_BASE}/paper/{paper_id}/citations"
        resp = await fetch_with_retry(self.client, "GET", url, params=params)
        if resp.status_code >= 400:
            return self._error_result(resp, {"paper_id": paper_id, "type": "citations"}, meta)
        data = resp.json()
        raw_items = [c.get("citingPaper", {}) for c in data.get("data", [])]
        items = [normalize_paper(i) for i in raw_items]
        result = {
            "source": "semantic_scholar",
            "query": {"paper_id": paper_id, "type": "citations"},
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["paperId"] for i in raw_items if i.get("paperId")],
            "items": items,
            "warnings": [],
            "next": data.get("next"),
            "offset": data.get("offset"),
        }
        if not self.api_key:
            result["warnings"].append("No SEMANTIC_SCHOLAR_API_KEY set; anonymous rate limits apply.")
        if self.cache:
            self.cache.set("s2", "citations", cache_params, cache_fields, result, ttl_seconds=TTL_CITATIONS)
        return result

    async def get_references(
        self,
        paper_id: str,
        limit: int = 50,
        offset_or_token: Optional[str] = None,
        include_abstract: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), 200)
        fields_str = self._build_fields(include_abstract)
        params: dict[str, Any] = {"fields": fields_str, "limit": limit}
        if offset_or_token:
            params["offset"] = offset_or_token
        cache_fields = fields_str.split(",")
        cache_params = {"paper_id": paper_id, "limit": limit, "offset": offset_or_token}
        meta = self._cache_meta("s2", "references", cache_params, cache_fields)

        if not refresh and self.cache:
            cached, _ = self.cache.get("s2", "references", cache_params, cache_fields)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{S2_GRAPH_BASE}/paper/{paper_id}/references"
        resp = await fetch_with_retry(self.client, "GET", url, params=params)
        if resp.status_code >= 400:
            return self._error_result(resp, {"paper_id": paper_id, "type": "references"}, meta)
        data = resp.json()
        raw_items = [c.get("citedPaper", {}) for c in data.get("data", [])]
        items = [normalize_paper(i) for i in raw_items]
        result = {
            "source": "semantic_scholar",
            "query": {"paper_id": paper_id, "type": "references"},
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["paperId"] for i in raw_items if i.get("paperId")],
            "items": items,
            "warnings": [],
            "next": data.get("next"),
            "offset": data.get("offset"),
        }
        if not self.api_key:
            result["warnings"].append("No SEMANTIC_SCHOLAR_API_KEY set; anonymous rate limits apply.")
        if self.cache:
            self.cache.set("s2", "references", cache_params, cache_fields, result, ttl_seconds=TTL_CITATIONS)
        return result

    async def recommend_papers(
        self,
        positive_paper_ids: list[str],
        negative_paper_ids: Optional[list[str]] = None,
        limit: int = 20,
        include_abstract: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), 100)
        fields_str = self._build_fields(include_abstract)
        payload = {
            "positivePaperIds": positive_paper_ids,
            "negativePaperIds": negative_paper_ids or [],
            "fields": fields_str,
            "limit": limit,
        }
        cache_fields = fields_str.split(",")
        cache_params = {"positive": positive_paper_ids, "negative": negative_paper_ids or [], "limit": limit}
        meta = self._cache_meta("s2", "recommendations", cache_params, cache_fields)

        if not refresh and self.cache:
            cached, _ = self.cache.get("s2", "recommendations", cache_params, cache_fields)
            if cached is not None:
                cached["from_cache"] = True
                cached["cache_key"] = meta["cache_key"]
                return cached

        url = f"{S2_REC_BASE}/papers"
        resp = await fetch_with_retry(self.client, "POST", url, json=payload)
        if resp.status_code >= 400:
            return self._error_result(resp, {"positive_paper_ids": positive_paper_ids, "negative_paper_ids": negative_paper_ids or []}, meta)
        data = resp.json()
        raw_items = data.get("recommendedPapers", [])
        items = [normalize_paper(i) for i in raw_items]
        result = {
            "source": "semantic_scholar",
            "query": {"positive_paper_ids": positive_paper_ids, "negative_paper_ids": negative_paper_ids or []},
            "retrieved_at": _now(),
            "cache_key": meta["cache_key"],
            "from_cache": False,
            "raw_ids": [i["paperId"] for i in raw_items if i.get("paperId")],
            "items": items,
            "warnings": [],
        }
        if not self.api_key:
            result["warnings"].append("No SEMANTIC_SCHOLAR_API_KEY set; anonymous rate limits apply.")
        if self.cache:
            self.cache.set("s2", "recommendations", cache_params, cache_fields, result, ttl_seconds=TTL_RECOMMENDATIONS)
        return result
