"""Transparent rule-based ranking for SearchPaper results."""

from __future__ import annotations

from searchpaper.schemas import WorkRecord


def _keyword_score(record: WorkRecord, query: str) -> float:
    if not query:
        return 0.0
    terms = [t.lower() for t in query.split() if len(t) > 2]
    if not terms:
        return 0.0
    text = " ".join(
        filter(
            None,
            [
                (record.title or "").lower(),
                (record.abstract or "").lower(),
                " ".join(record.keywords).lower(),
                " ".join(record.mesh_terms).lower(),
            ],
        )
    )
    matches = sum(1 for t in terms if t in text)
    return matches / len(terms)


def _recency_score(record: WorkRecord) -> float:
    if not record.year:
        return 0.0
    return max(min((record.year - 2000) / 30.0, 1.0), 0.0)


def rank_works(works: list[WorkRecord], query: str = "", sort: str | None = None) -> list[WorkRecord]:
    """Rank merged works using transparent rule-based scoring."""
    mode = (sort or "relevance").lower()
    scored: list[tuple[WorkRecord, float]] = []
    relevance_scores = {work.work_id: _keyword_score(work, query) for work in works}
    max_relevance = max(relevance_scores.values(), default=0.0)
    for work in works:
        score = 0.0
        reasons: list[str] = []

        source_count = len(work.merged_from_sources)
        score += source_count * 2.0
        if source_count > 1:
            reasons.append(f"found by {source_count} sources")

        if work.identifiers.get("doi"):
            score += 1.5
            reasons.append("has DOI")
        if work.identifiers.get("pmid"):
            score += 1.5
            reasons.append("has PMID")
        if work.identifiers.get("pmcid"):
            score += 1.0
            reasons.append("has PMCID")

        if work.abstract:
            score += 0.5
            reasons.append("has abstract")
        if work.open_access_pdf:
            score += 0.5
            reasons.append("has open access PDF link")

        if work.citation_count:
            score += min(work.citation_count / 100.0, 3.0)
            reasons.append(f"citation count {work.citation_count}")

        kw_score = relevance_scores[work.work_id]
        if kw_score:
            score += kw_score * 2.0
            reasons.append(f"keyword match {kw_score:.2f}")

        if work.year:
            score += _recency_score(work)

        if mode == "date":
            score = float(work.year or 0) + kw_score
            reasons.append("date sort")
        elif mode == "citations":
            if max_relevance and kw_score < max_relevance * 0.3:
                score = -1.0
                reasons.append("below relevance floor for citation sort")
            else:
                score = float(work.citation_count or 0) + kw_score
                reasons.append("citation sort")
        elif mode == "combined":
            citation_component = min((work.citation_count or 0) / 100.0, 1.0) * 0.2
            score = (kw_score * 0.5) + (_recency_score(work) * 0.3) + citation_component
            reasons.append("combined relevance/recency/citation sort")

        work.ranking_reasons = reasons
        scored.append((work, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [w for w, _ in scored]
