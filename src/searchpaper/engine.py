"""Core search engine for SearchPaper."""

from __future__ import annotations

from typing import Any

from searchpaper.cache import Cache
from searchpaper.config import get_cache_path, load_config
from searchpaper.exceptions import SourceRequiredError
from searchpaper.merge import merge_records
from searchpaper.rank import rank_works
from searchpaper.schemas import (
    FailureClass,
    IdentifierType,
    ResponseEnvelope,
    SearchFilters,
    SearchResult,
    SourceError,
    SourceMode,
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


def _resolve_source_modes(
    requested: list[str],
    modes: dict[str, SourceMode] | None = None,
) -> dict[str, SourceMode]:
    """Return a mode for every requested source, defaulting to OPTIONAL."""
    resolved: dict[str, SourceMode] = {source.lower(): SourceMode.OPTIONAL for source in requested}
    if modes:
        for source, mode in modes.items():
            resolved[source.lower()] = mode
    return resolved


def _format_source_modes(modes: dict[str, SourceMode]) -> dict[str, str]:
    """Serialize source modes for trace output."""
    return {source: mode.value for source, mode in modes.items()}


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

    def _read_cached_records(self, query: str, filters: SearchFilters, source: str) -> list[SourceRecord] | None:
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
        source_modes: dict[str, SourceMode] | None = None,
    ) -> ResponseEnvelope:
        filters = filters or SearchFilters()
        requested = sources or self.sources
        modes = source_modes if source_modes is not None else filters.source_modes
        source_mode_map = _resolve_source_modes(requested, modes)
        trace_filters = filters.model_dump(mode="json")
        trace_filters["source_modes"] = _format_source_modes(source_mode_map)
        trace = TraceBuilder(
            query=query,
            filters=trace_filters,
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

        failed_required = [
            source
            for source in trace.trace.sources_failed
            if source_mode_map.get(source.lower()) == SourceMode.REQUIRED
        ]
        failed_preferred = [
            source
            for source in trace.trace.sources_failed
            if source_mode_map.get(source.lower()) == SourceMode.PREFERRED
        ]
        if failed_preferred:
            warnings.insert(
                0,
                f"Preferred sources failed: {', '.join(failed_preferred)}",
            )

        envelope = ResponseEnvelope(
            data=result.model_dump(mode="json"),
            warnings=warnings,
            trace=result.trace.model_dump(mode="json"),
        )
        if failed_required:
            required_msg = f"Required source(s) failed: {', '.join(failed_required)}"
            envelope.warnings.insert(0, required_msg)
            raise SourceRequiredError(required_msg, envelope)
        return envelope

    async def _maybe_enrich(
        self,
        identifier: WorkIdentifier,
        records: list[SourceRecord],
        trace: TraceBuilder,
        enrich: bool,
        anchors: bool,
    ) -> list[SourceRecord]:
        """Optionally enrich records with Unpaywall OA metadata and full-text anchors."""
        if not enrich:
            return records

        source_names = {rec.source for rec in records}
        doi = identifier.normalized if identifier.type.value == "doi" else None
        if not doi:
            for rec in records:
                doi = rec.identifiers.get("doi")
                if doi:
                    break
        if not doi:
            return records

        # Unpaywall enrichment.
        if "unpaywall" not in source_names:
            try:
                adapter = get_adapter("unpaywall")
                try:
                    wid = WorkIdentifier(type=IdentifierType.DOI, value=doi)
                    rec = await adapter.get(wid)
                    if rec:
                        trace.mark_succeeded(adapter.name)
                        records.append(rec)
                except Exception as exc:
                    trace.add_error(
                        SourceError(
                            source=adapter.name,
                            operation="enrich",
                            failure_class=FailureClass.UNKNOWN_ERROR,
                            message=str(exc),
                            timestamp=trace.trace.retrieved_at,
                        )
                    )
                    trace.mark_failed(adapter.name)
                finally:
                    await adapter.aclose()
            except KeyError:
                pass

        # Europe PMC full-text anchors.
        if anchors:
            try:
                adapter = get_adapter("europepmc")
                try:
                    pmcid = None
                    for rec in records:
                        pmcid = rec.identifiers.get("pmcid")
                        if pmcid:
                            break
                    if pmcid:
                        wid = WorkIdentifier(type=IdentifierType.PMCID, value=pmcid)
                        anchors_list = await adapter.fetch_anchors(wid)
                        if anchors_list:
                            for rec in records:
                                if rec.source == "europepmc":
                                    rec.normalized_fields["full_text_anchors"] = [
                                        a.model_dump(mode="json") for a in anchors_list
                                    ]
                                    break
                            else:
                                # No Europe PMC record yet; create a lightweight enrichment record.
                                records.append(
                                    SourceRecord(
                                        source="europepmc",
                                        source_record_id=pmcid,
                                        retrieved_at=trace.trace.retrieved_at,
                                        query_or_identifier=pmcid,
                                        identifiers={"pmcid": pmcid},
                                        normalized_fields={
                                            "full_text_anchors": [a.model_dump(mode="json") for a in anchors_list]
                                        },
                                    )
                                )
                except Exception as exc:
                    trace.add_error(
                        SourceError(
                            source=adapter.name,
                            operation="anchors",
                            failure_class=FailureClass.UNKNOWN_ERROR,
                            message=str(exc),
                            timestamp=trace.trace.retrieved_at,
                        )
                    )
                finally:
                    await adapter.aclose()
            except KeyError:
                pass

        return records

    async def get(
        self,
        identifier: WorkIdentifier,
        sources: list[str] | None = None,
        enrich: bool = True,
        anchors: bool = False,
        source_modes: dict[str, SourceMode] | None = None,
    ) -> ResponseEnvelope:
        requested = sources or self.sources
        source_mode_map = _resolve_source_modes(requested, source_modes)
        trace = TraceBuilder(
            sources_requested=requested,
            cache_policy="default",
            filters={"source_modes": _format_source_modes(source_mode_map)},
        )
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

        all_records = await self._maybe_enrich(identifier, all_records, trace, enrich=enrich, anchors=anchors)

        works = merge_records(all_records)
        works = rank_works(works)
        trace.set_result_counts(result_count=len(all_records), merged_count=len(works))
        result = SearchResult(works=works, trace=trace.build())
        warnings: list[str] = []
        failed_required = [
            source
            for source in trace.trace.sources_failed
            if source_mode_map.get(source.lower()) == SourceMode.REQUIRED
        ]
        failed_preferred = [
            source
            for source in trace.trace.sources_failed
            if source_mode_map.get(source.lower()) == SourceMode.PREFERRED
        ]
        if failed_preferred:
            warnings.insert(0, f"Preferred sources failed: {', '.join(failed_preferred)}")
        envelope = ResponseEnvelope(
            data=result.model_dump(mode="json"),
            warnings=warnings,
            trace=result.trace.model_dump(mode="json"),
        )
        if failed_required:
            required_msg = f"Required source(s) failed: {', '.join(failed_required)}"
            envelope.warnings.insert(0, required_msg)
            raise SourceRequiredError(required_msg, envelope)
        return envelope

    async def resolve(
        self,
        identifier: WorkIdentifier,
        sources: list[str] | None = None,
        enrich: bool = True,
        anchors: bool = False,
        source_modes: dict[str, SourceMode] | None = None,
    ) -> ResponseEnvelope:
        requested = sources or self.sources
        source_mode_map = _resolve_source_modes(requested, source_modes)
        trace = TraceBuilder(
            sources_requested=requested,
            cache_policy="default",
            filters={"source_modes": _format_source_modes(source_mode_map)},
        )
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

        all_records = await self._maybe_enrich(identifier, all_records, trace, enrich=enrich, anchors=anchors)

        works = merge_records(all_records)
        works = rank_works(works)
        trace.set_result_counts(result_count=len(all_records), merged_count=len(works))
        result = SearchResult(works=works, trace=trace.build())
        warnings: list[str] = []
        failed_required = [
            source
            for source in trace.trace.sources_failed
            if source_mode_map.get(source.lower()) == SourceMode.REQUIRED
        ]
        failed_preferred = [
            source
            for source in trace.trace.sources_failed
            if source_mode_map.get(source.lower()) == SourceMode.PREFERRED
        ]
        if failed_preferred:
            warnings.insert(0, f"Preferred sources failed: {', '.join(failed_preferred)}")
        envelope = ResponseEnvelope(
            data=result.model_dump(mode="json"),
            warnings=warnings,
            trace=result.trace.model_dump(mode="json"),
        )
        if failed_required:
            required_msg = f"Required source(s) failed: {', '.join(failed_required)}"
            envelope.warnings.insert(0, required_msg)
            raise SourceRequiredError(required_msg, envelope)
        return envelope

    async def context(
        self,
        identifier: WorkIdentifier,
        sources: list[str] | None = None,
        include_signals: bool = False,
        include_expand: bool = False,
        expand_limit: int = 5,
        source_modes: dict[str, SourceMode] | None = None,
    ) -> ResponseEnvelope:
        """Build a structured paper context pack for downstream agents."""
        resolve_result = await self.resolve(
            identifier, sources=sources, enrich=True, anchors=True, source_modes=source_modes
        )
        data = resolve_result.data if hasattr(resolve_result, "data") else resolve_result.get("data", {})
        works = data.get("works", [])
        if not works:
            return ResponseEnvelope(
                data={"schema_version": "0.2", "object_type": "paper_context_pack", "work": None, "context": {}},
                warnings=["Could not resolve identifier to a work."],
                trace=data.get("trace", {}),
            )
        work = works[0]
        work_data = work if isinstance(work, dict) else work.model_dump(mode="json")

        signals: list[dict[str, Any]] = []
        if include_signals:
            sig_result = await self.signals(query=work_data.get("title"), limit=10)
            sig_data = sig_result.data if hasattr(sig_result, "data") else sig_result.get("data", {})
            signals = sig_data.get("signals", [])

        expand_result: dict[str, Any] | None = None
        if include_expand:
            exp_result = await self.expand(identifier, by=["citations"], limit=expand_limit)
            exp_data = exp_result.data if hasattr(exp_result, "data") else exp_result.get("data", {})
            expand_result = {
                "by": ["citations"],
                "works": exp_data.get("works", []),
                "count": len(exp_data.get("works", [])),
            }

        context_pack = {
            "schema_version": "0.2",
            "object_type": "paper_context_pack",
            "work": work_data,
            "abstract": work_data.get("abstract"),
            "full_text_availability": work_data.get("full_text_availability"),
            "full_text_anchors": work_data.get("full_text_anchors", []),
            "signals": signals,
            "expand": expand_result,
            "urls": self._build_urls(work_data),
        }
        if hasattr(resolve_result, "warnings"):
            warnings = resolve_result.warnings
        else:
            warnings = resolve_result.get("warnings", [])
        return ResponseEnvelope(
            data=context_pack,
            warnings=warnings,
            trace=work_data.get("trace", {}),
        )

    def _build_urls(self, work_data: dict[str, Any]) -> dict[str, str]:
        urls: dict[str, str] = {}
        ids = work_data.get("identifiers", {})
        if ids.get("doi"):
            urls["doi"] = f"https://doi.org/{ids['doi']}"
        if ids.get("pmid"):
            urls["pubmed"] = f"https://pubmed.ncbi.nlm.nih.gov/{ids['pmid']}/"
        if ids.get("pmcid"):
            urls["pmc"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{ids['pmcid']}/"
        if ids.get("arxiv"):
            urls["arxiv"] = f"https://arxiv.org/abs/{ids['arxiv']}"
        ft = work_data.get("full_text_availability") or {}
        if ft.get("oa_url"):
            urls["oa_url"] = ft["oa_url"]
        if ft.get("oa_pdf_url"):
            urls["oa_pdf_url"] = ft["oa_pdf_url"]
        return urls

    async def expand(
        self,
        identifier: WorkIdentifier,
        by: list[str] | None = None,
        limit: int = 20,
        source_modes: dict[str, SourceMode] | None = None,
    ) -> ResponseEnvelope:
        """Expand from a known work by citations, references, or similar papers.

        Currently uses Semantic Scholar as the primary enrichment source. If S2
        fails or is unavailable, falls back to a basic resolve.
        """
        by = by or ["citations"]
        valid_modes = {"citations", "references", "similar"}
        modes = [m for m in by if m in valid_modes]
        if not modes:
            modes = ["citations"]

        source_mode_map = _resolve_source_modes(["semantic_scholar"], source_modes)
        trace = TraceBuilder(
            sources_requested=["semantic_scholar"],
            cache_policy="default",
            filters={"source_modes": _format_source_modes(source_mode_map)},
        )
        all_records: list[SourceRecord] = []
        warnings: list[str] = []
        s2_failed = False

        try:
            adapter = get_adapter("semantic_scholar")
        except KeyError:
            warnings.append("Semantic Scholar adapter not available; falling back to resolve.")
            return await self.resolve(identifier, source_modes=source_modes)

        try:
            for mode in modes:
                if mode == "citations":
                    records = await adapter.get_citations(identifier, limit=limit)
                elif mode == "references":
                    records = await adapter.get_references(identifier, limit=limit)
                else:  # similar
                    records = await adapter.get_recommendations(identifier, limit=limit)

                if records:
                    trace.mark_succeeded(adapter.name)
                    all_records.extend(records)
                else:
                    trace.mark_failed(adapter.name)
                    s2_failed = True
        except Exception as exc:
            trace.add_error(
                SourceError(
                    source=adapter.name,
                    operation="expand",
                    failure_class=FailureClass.UNKNOWN_ERROR,
                    message=str(exc),
                    timestamp=trace.trace.retrieved_at,
                )
            )
            trace.mark_failed(adapter.name)
            s2_failed = True
            warnings.append(f"Semantic Scholar expansion failed: {exc}; falling back to resolve.")
        finally:
            await adapter.aclose()

        if not all_records and warnings:
            if source_mode_map.get("semantic_scholar") == SourceMode.REQUIRED and s2_failed:
                raise SourceRequiredError(
                    "Required source semantic_scholar failed during expansion.",
                    ResponseEnvelope(
                        data=SearchResult(works=[], trace=trace.build()).model_dump(mode="json"),
                        warnings=warnings,
                        trace=trace.trace.model_dump(mode="json"),
                    ),
                )
            return await self.resolve(identifier, source_modes=source_modes)

        works = merge_records(all_records)
        works = rank_works(works)
        trace.set_result_counts(result_count=len(all_records), merged_count=len(works))
        result = SearchResult(works=works, trace=trace.build())
        return ResponseEnvelope(
            data=result.model_dump(mode="json"),
            warnings=warnings,
            trace=result.trace.model_dump(mode="json"),
        )

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
