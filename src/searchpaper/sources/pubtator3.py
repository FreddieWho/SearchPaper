"""PubTator3 adapter for SearchPaper.

PubTator3 is treated as a literature-signal source: it supplies biomedical
entity annotations and reported relations, not evaluated conclusions.
"""

from __future__ import annotations

from typing import Any

from searchpaper.http import HTTPClient
from searchpaper.identifiers import normalize_pmid
from searchpaper.schemas import (
    Anchor,
    LiteratureSignal,
    SearchFilters,
    SignalLevel,
    SignalType,
    SourceRecord,
    SourceState,
    SourceStatus,
    WorkIdentifier,
)
from searchpaper.sources.base import SourceAdapter, classify_http_error, now_iso
from searchpaper.sources.registry import register

PUBTATOR_BASE = "https://www.ncbi.nlm.nih.gov"
PUBTATOR_SOURCE = "pubtator3"
PUBTATOR_TERMS_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3/api.html"

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


def _is_blocked_entity(name: str | None) -> bool:
    if not name:
        return False
    return name.lower().replace(" ", "_") in BLOCKED_ENTITY_NAMES


def _normalize_entity(raw: dict[str, Any]) -> dict[str, Any]:
    entity_id = raw.get("_id") or raw.get("id", "")
    entity_type = raw.get("biotype") or raw.get("type")
    return {
        "entity_id": entity_id,
        "name": raw.get("name"),
        "type": entity_type,
    }


def _pmid_url(pmid: str) -> dict[str, str]:
    return {
        "pmid": pmid,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "pubtator_url": f"https://www.ncbi.nlm.nih.gov/research/pubtator3/publication/{pmid}",
    }


@register(PUBTATOR_SOURCE)
class PubTator3Adapter(SourceAdapter):
    """Search biomedical literature and retrieve entity/relation signals from PubTator3."""

    name = PUBTATOR_SOURCE
    source_terms_url = PUBTATOR_TERMS_URL
    usage_note = "PubTator3 provides biomedical entity annotations and reported relations; no API key required."

    def __init__(self) -> None:
        self.http = HTTPClient(timeout=30.0)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def search(self, query: str, filters: SearchFilters) -> list[SourceRecord]:
        """Search PubTator3 and return lightweight SourceRecords keyed by PMID."""
        limit = min(max(filters.limit, 1), 100)
        resp = await self.http.get(
            f"{PUBTATOR_BASE}/research/pubtator3-api/search/",
            params={"text": query, "page": 1},
        )
        if resp.status_code >= 400:
            return []
        data = resp.json()
        raw_items = data if isinstance(data, list) else data.get("results", [])
        records: list[SourceRecord] = []
        for i in raw_items[:limit]:
            if not isinstance(i, dict):
                continue
            pmid = i.get("pmid") or i.get("pmcid")
            ids: dict[str, str] = {}
            if pmid:
                ids["pmid"] = str(pmid)
            normalized = {
                "title": i.get("title"),
                "identifiers": ids,
            }
            records.append(
                SourceRecord(
                    source=PUBTATOR_SOURCE,
                    source_record_id=ids.get("pmid") or str(i.get("id", "")),
                    retrieved_at=now_iso(),
                    raw_record=i,
                    normalized_fields=normalized,
                    identifiers=ids,
                    source_terms_url=PUBTATOR_TERMS_URL,
                )
            )
        return records

    async def get(self, identifier: WorkIdentifier) -> SourceRecord | None:
        if identifier.type.value != "pmid":
            return None
        pmid = normalize_pmid(identifier.value)
        if not pmid:
            return None
        resp = await self.http.get(
            f"{PUBTATOR_BASE}/research/pubtator3-api/search/",
            params={"text": pmid, "page": 1},
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        raw_items = data if isinstance(data, list) else data.get("results", [])
        for i in raw_items:
            if str(i.get("pmid")) == pmid:
                rec = await self.search(pmid, SearchFilters(limit=1))
                return rec[0] if rec else None
        return None

    async def resolve(self, identifier: WorkIdentifier) -> list[SourceRecord]:
        rec = await self.get(identifier)
        return [rec] if rec else []

    async def status(self) -> SourceStatus:
        try:
            resp = await self.http.get(
                f"{PUBTATOR_BASE}/research/pubtator3-api/search/",
                params={"text": "test", "page": 1},
            )
            if resp.status_code == 200:
                return self._make_status(
                    SourceState.AVAILABLE,
                    message="PubTator3 API responded to a probe query.",
                )
            return self._make_status(
                SourceState.DEGRADED,
                message=f"PubTator3 probe returned HTTP {resp.status_code}.",
                last_error_class=classify_http_error(resp.status_code),
            )
        except Exception as exc:
            return self._make_status(
                SourceState.DEGRADED,
                message=f"PubTator3 probe failed: {exc}; fixture-backed signal adapter preserved.",
                last_error_class=classify_http_error(0, exc),
            )

    async def find_entity(self, query: str, limit: int = 10) -> dict[str, Any]:
        """PubTator3 entity autocomplete endpoint."""
        limit = min(max(limit, 1), 30)
        resp = await self.http.get(
            f"{PUBTATOR_BASE}/research/pubtator3-api/entity/autocomplete/",
            params={"query": query, "limit": limit},
        )
        if resp.status_code >= 400:
            return {
                "source": PUBTATOR_SOURCE,
                "query": query,
                "items": [],
                "warnings": [f"PubTator3 entity autocomplete HTTP {resp.status_code}: {resp.text[:200]}"],
            }
        data = resp.json()
        raw_items = data if isinstance(data, list) else data.get("results", [])
        items = []
        for i in raw_items:
            if isinstance(i, dict) and not _is_blocked_entity(i.get("name")):
                items.append(_normalize_entity(i))
        return {
            "source": PUBTATOR_SOURCE,
            "query": query,
            "items": items,
            "warnings": [],
        }

    async def find_relations(
        self, e1: str, e2_type: str, relation_type: str, limit: int = 10
    ) -> list[LiteratureSignal]:
        """Return literature signals for PubTator3 relations."""
        limit = min(max(limit, 1), 50)
        resp = await self.http.get(
            f"{PUBTATOR_BASE}/research/pubtator3-api/relations",
            params={"e1": e1, "e2": e2_type, "type": relation_type, "limit": limit},
        )
        if resp.status_code >= 400:
            return []
        data = resp.json()
        raw_items = data if isinstance(data, list) else data.get("results", [])
        signals: list[LiteratureSignal] = []
        for i in raw_items:
            if not isinstance(i, dict):
                continue
            src = i.get("source")
            tgt = i.get("target")
            if src and tgt:
                other = src if tgt == e1 else tgt
            elif src:
                other = src
            else:
                other = tgt
            entity2 = i.get("entity2") or {"_id": other}
            if _is_blocked_entity(entity2.get("name") or entity2.get("_id")):
                continue
            pmids = i.get("pmids") or []
            signals.append(
                LiteratureSignal(
                    signal_id=f"pubtator3:{e1}:{relation_type}:{other}",
                    signal_type=SignalType.CURATED_RELATION,
                    signal_level=SignalLevel.CURATED_OR_EXTRACTED,
                    entities=[
                        _normalize_entity({"_id": e1}),
                        _normalize_entity(entity2),
                    ],
                    relation_label=relation_type,
                    supporting_work_ids=[f"pmid:{p}" for p in pmids],
                    source=PUBTATOR_SOURCE,
                    anchor=Anchor(
                        anchor_type="pubtator3_relation",
                        url=f"https://www.ncbi.nlm.nih.gov/research/pubtator3/entity/{e1}",
                    ),
                    confidence_or_score=i.get("publications"),
                    interpretation_warning=(
                        "PubTator3 reports this relation from curated or extracted literature. "
                        "It is a literature signal, not evaluated scientific evidence."
                    ),
                )
            )
        return signals
