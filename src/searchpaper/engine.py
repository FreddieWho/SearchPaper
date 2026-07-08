"""Core search engine for SearchPaper."""

from __future__ import annotations

from typing import Any

from searchpaper.cache import Cache
from searchpaper.config import get_cache_path, load_config
from searchpaper.merge import merge_records
from searchpaper.rank import rank_works
from searchpaper.schemas import (
    FailureClass,
    ResponseEnvelope,
    SearchFilters,
    SearchResult,
    SourceError,
    SourceRecord,
    SourceResultCount,
    WorkIdentifier,
)
from searchpaper.sources import get_adapter
from searchpaper.sources.base import SourceAdapter
from searchpaper.sources.pubtator3 import PubTator3Adapter
from searchpaper.trace import TraceBuilder

DEFAULT_SOURCES = ["pubmed", "crossref", "openalex"]


def _source_kwargs(source: str) -> dict[str, Any]:
    return {}


class SearchEngine:
    """Orchestrates source adapters, merge, ranking, cache, and trace."""

    def __init__(self, cache: Cache | None = None, sources: list[str] | None = None):
        self.cache = cache or Cache(get_cache_path(load_config()))
        self.sources = sources or DEFAULT_SOURCES

    async def _call_adapter(
        self,
        adapter: SourceAdapter,
        operation: str,
        fn: Any,
        trace: TraceBuilder,
    ) -> Any:
        try:
            return await fn()
        except Exception as exc:
            error = SourceError(
                source=adapter.name,
                operation=operation,
                failure_class=FailureClass.UNKNOWN_ERROR,
                message=str(exc),
                timestamp=adapter._make_status.__self__ if hasattr(adapter, "_make_status") else "",
            )
            trace.add_error(error)
            trace.mark_failed(adapter.name)
            return None

    def _cache_params(self, query: str, filters: SearchFilters, source: str) -> dict[str, Any]:
        return {"query": query, "filters": filters.model_dump(mode="json"), "source": source}

    def _read_cached_records(
        self, query: str, filters: SearchFilters, source: str
    ) -> list[SourceRecord] | None:
        cached, _ = self.cache.get("engine", "search", self._cache_params(query, filters, source), None)
        if cached is None:
            return None
        try:
            return [SourceRecord(**rec) for rec in cached]
        except Exception:
            return None

    def _write_cached_records(
        self, query: str, filters: SearchFilters, source: str, records: list[SourceRecord]
    ) -> None:
        try:
            self.cache.set(
                "engine",
                "search",
                self._cache_params(query, filters, source),
                None,
                [rec.model_dump(mode="json") for rec in records],
            )
        except Exception:
            pass

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        sources: list[str] | None = None,
        no_cache: bool = False,
    ) -> ResponseEnvelope:
        filters = filters or SearchFilters()
        requested = sources or self.sources
        trace = TraceBuilder(
            query=query,
            filters=filters.model_dump(mode="json"),
            sources_requested=requested,
            cache_policy="no-cache" if no_cache else "default",
        )

        if not query or not query.strip():
            result = SearchResult(works=[], trace=trace.build())
            return ResponseEnvelope(
                data=result.model_dump(mode="json"),
                warnings=["Empty query; no sources queried."],
                trace=result.trace.model_dump(mode="json"),
            )

        all_records: list[SourceRecord] = []
        for source_name in requested:
            if source_name.lower() == "pubtator3":
                # PubTator3 is a signal adapter; skip in plain literature search unless explicitly requested.
                continue
            try:
                adapter = get_adapter(source_name)
            except KeyError:
                trace.add_error(
                    SourceError(
                        source=source_name,
                        operation="search",
                        failure_class=FailureClass.NOT_CONFIGURED,
                        message=f"Unknown source adapter: {source_name}",
                        timestamp=trace.trace.retrieved_at,
                    )
                )
                continue

            try:
                if not no_cache:
                    cached = self._read_cached_records(query, filters, adapter.name)
                    if cached is not None:
                        records = cached
                        trace.mark_succeeded(adapter.name)
                        all_records.extend(records)
                        trace.add_source_count(
                            SourceResultCount(
                                source=adapter.name,
                                requested=True,
                                succeeded=True,
                                returned_count=len(records),
                                from_cache=True,
                            )
                        )
                        continue

                records = await adapter.search(query, filters)
                if not no_cache:
                    self._write_cached_records(query, filters, adapter.name, records)
                trace.mark_succeeded(adapter.name)
                all_records.extend(records)
                trace.add_source_count(
                    SourceResultCount(
                        source=adapter.name,
                        requested=True,
                        succeeded=True,
                        returned_count=len(records),
                    )
                )
            except Exception as exc:
                trace.add_error(
                    SourceError(
                        source=adapter.name,
                        operation="search",
                        failure_class=FailureClass.UNKNOWN_ERROR,
                        message=str(exc),
                        timestamp=trace.trace.retrieved_at,
                    )
                )
                trace.mark_failed(adapter.name)
            finally:
                await adapter.aclose()

        works = merge_records(all_records)
        works = rank_works(works, query=query, sort=filters.sort)
        trace.set_result_counts(result_count=len(all_records), merged_count=len(works))

        result = SearchResult(works=works, trace=trace.build())
        warnings: list[str] = []
        if trace.trace.sources_failed:
            warnings.append(f"Some sources failed: {', '.join(trace.trace.sources_failed)}")
        if trace.trace.sources_degraded:
            warnings.append(f"Some sources are degraded: {', '.join(trace.trace.sources_degraded)}")
        return ResponseEnvelope(
            data=result.model_dump(mode="json"),
            warnings=warnings,
            trace=result.trace.model_dump(mode="json"),
        )

    async def get(self, identifier: WorkIdentifier, sources: list[str] | None = None) -> ResponseEnvelope:
        requested = sources or self.sources
        trace = TraceBuilder(sources_requested=requested, cache_policy="default")
        all_records: list[SourceRecord] = []
        for source_name in requested:
            try:
                adapter = get_adapter(source_name)
            except KeyError:
                continue
            try:
                record = await adapter.get(identifier)
                if record:
                    trace.mark_succeeded(adapter.name)
                    all_records.append(record)
                else:
                    trace.mark_failed(adapter.name)
            except Exception as exc:
                trace.add_error(
                    SourceError(
                        source=adapter.name,
                        operation="get",
                        failure_class=FailureClass.UNKNOWN_ERROR,
                        message=str(exc),
                        timestamp=trace.trace.retrieved_at,
                    )
                )
                trace.mark_failed(adapter.name)
            finally:
                await adapter.aclose()

        works = merge_records(all_records)
        works = rank_works(works)
        trace.set_result_counts(result_count=len(all_records), merged_count=len(works))
        result = SearchResult(works=works, trace=trace.build())
        return ResponseEnvelope(data=result.model_dump(mode="json"), trace=result.trace.model_dump(mode="json"))

    async def resolve(self, identifier: WorkIdentifier, sources: list[str] | None = None) -> ResponseEnvelope:
        requested = sources or self.sources
        trace = TraceBuilder(sources_requested=requested, cache_policy="default")
        all_records: list[SourceRecord] = []
        for source_name in requested:
            try:
                adapter = get_adapter(source_name)
            except KeyError:
                continue
            try:
                records = await adapter.resolve(identifier)
                if records:
                    trace.mark_succeeded(adapter.name)
                    all_records.extend(records)
                else:
                    trace.mark_failed(adapter.name)
            except Exception as exc:
                trace.add_error(
                    SourceError(
                        source=adapter.name,
                        operation="resolve",
                        failure_class=FailureClass.UNKNOWN_ERROR,
                        message=str(exc),
                        timestamp=trace.trace.retrieved_at,
                    )
                )
                trace.mark_failed(adapter.name)
            finally:
                await adapter.aclose()

        works = merge_records(all_records)
        works = rank_works(works)
        trace.set_result_counts(result_count=len(all_records), merged_count=len(works))
        result = SearchResult(works=works, trace=trace.build())
        return ResponseEnvelope(data=result.model_dump(mode="json"), trace=result.trace.model_dump(mode="json"))

    async def signals(
        self,
        query: str | None = None,
        entity1: str | None = None,
        entity2: str | None = None,
        relation_type: str = "interact",
        entity2_type: str = "chemical",
        limit: int = 10,
    ) -> ResponseEnvelope:
        trace = TraceBuilder(query=query, sources_requested=["pubtator3"], cache_policy="default")
        adapter = PubTator3Adapter()
        signals: list[dict[str, Any]] = []
        try:
            if entity1:
                resolved = entity1
                if not entity1.startswith("@"):
                    ent_res = await adapter.find_entity(entity1, limit=5)
                    items = ent_res.get("items", [])
                    if items:
                        resolved = items[0]["entity_id"]
                sigs = await adapter.find_relations(resolved, entity2_type, relation_type, limit=limit)
                signals = [s.model_dump(mode="json") for s in sigs]
                trace.mark_succeeded("pubtator3")
            elif query:
                # Treat query as entity lookup.
                ent_res = await adapter.find_entity(query, limit=1)
                items = ent_res.get("items", [])
                if items:
                    sigs = await adapter.find_relations(items[0]["entity_id"], entity2_type, relation_type, limit=limit)
                    signals = [s.model_dump(mode="json") for s in sigs]
                    trace.mark_succeeded("pubtator3")
                else:
                    trace.mark_failed("pubtator3")
            else:
                trace.mark_failed("pubtator3")
        except Exception as exc:
            trace.add_error(
                SourceError(
                    source="pubtator3",
                    operation="signals",
                    failure_class=FailureClass.UNKNOWN_ERROR,
                    message=str(exc),
                    timestamp=trace.trace.retrieved_at,
                )
            )
            trace.mark_failed("pubtator3")
        finally:
            await adapter.aclose()

        result = SearchResult(signals=signals, trace=trace.build())
        return ResponseEnvelope(data=result.model_dump(mode="json"), trace=result.trace.model_dump(mode="json"))

    async def source_statuses(self) -> ResponseEnvelope:
        from searchpaper.sources.registry import all_source_statuses

        statuses = await all_source_statuses()
        return ResponseEnvelope(
            data=[s.model_dump(mode="json") for s in statuses],
            object_type="source_statuses",
        )
