"""Conservative identifier resolution and duplicate merge for SearchPaper."""

from __future__ import annotations

import hashlib
from typing import Any

from searchpaper.identifiers import normalize_title, work_id_from_identifiers
from searchpaper.schemas import (
    Anchor,
    Author,
    FullTextAvailability,
    ProvenanceEntry,
    SourceConflict,
    SourceRecord,
    WorkRecord,
)


def _first_author_name(authors: list[Author]) -> str:
    if not authors:
        return ""
    return authors[0].name.lower().strip()


def _record_keys(record: SourceRecord) -> dict[str, str]:
    """Return merge keys for a source record."""
    ids = record.identifiers
    keys: dict[str, str] = {}
    if ids.get("doi"):
        keys["doi"] = ids["doi"].lower().strip()
    if ids.get("pmid"):
        keys["pmid"] = ids["pmid"]
    if ids.get("pmcid"):
        keys["pmcid"] = ids["pmcid"].upper()
    if ids.get("arxiv"):
        keys["arxiv"] = ids["arxiv"].lower()
    if ids.get("semantic_scholar"):
        keys["semantic_scholar"] = ids["semantic_scholar"].lower()
    if ids.get("openalex"):
        keys["openalex"] = ids["openalex"]
    return keys


def _make_group_id(keys: dict[str, str], title: str | None, year: int | None, first_author: str) -> str:
    if keys:
        return work_id_from_identifiers(keys)
    normalized = normalize_title(title) or ""
    return hashlib.sha256(f"{normalized}|{year}|{first_author}".encode()).hexdigest()[:16]


def _pick_best(field: str, candidates: list[Any]) -> Any:
    """Pick the most informative non-empty value for a field."""
    for c in candidates:
        if c is not None and c != "":
            if isinstance(c, list) and not c:
                continue
            return c
    return None


def _collect_values(field: str, records: list[SourceRecord]) -> list[Any]:
    values: list[Any] = []
    for rec in records:
        val = rec.normalized_fields.get(field)
        if val is not None and val != "" and val not in values:
            values.append(val)
    return values


def _merge_full_text_availability(records: list[SourceRecord]) -> FullTextAvailability | None:
    """Merge full-text availability reports from multiple source records."""
    reports: list[FullTextAvailability] = []
    for rec in records:
        raw = rec.normalized_fields.get("full_text_availability")
        if isinstance(raw, dict):
            reports.append(FullTextAvailability(**raw))
        elif isinstance(raw, FullTextAvailability):
            reports.append(raw)
    if not reports:
        return None

    sources: list[str] = []
    for r in reports:
        for s in r.sources:
            if s not in sources:
                sources.append(s)

    oa_url = _pick_best("oa_url", [r.oa_url for r in reports])
    oa_pdf_url = _pick_best("oa_pdf_url", [r.oa_pdf_url for r in reports])
    license = _pick_best("license", [r.license for r in reports])

    notes: list[str] = []
    for r in reports:
        for note in r.notes:
            if note not in notes:
                notes.append(note)

    return FullTextAvailability(
        has_full_text=any(r.has_full_text for r in reports),
        has_pdf=any(r.has_pdf for r in reports),
        sources=sources,
        oa_url=oa_url,
        oa_pdf_url=oa_pdf_url,
        license=license,
        notes=notes,
    )


def _build_urls(identifiers: dict[str, str], ft: FullTextAvailability | None) -> dict[str, str]:
    """Build canonical URLs from identifiers and full-text availability."""
    urls: dict[str, str] = {}
    if identifiers.get("doi"):
        urls["doi"] = f"https://doi.org/{identifiers['doi']}"
    if identifiers.get("pmid"):
        urls["pubmed"] = f"https://pubmed.ncbi.nlm.nih.gov/{identifiers['pmid']}/"
    if identifiers.get("pmcid"):
        urls["pmc"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{identifiers['pmcid']}/"
    if identifiers.get("arxiv"):
        urls["arxiv"] = f"https://arxiv.org/abs/{identifiers['arxiv']}"
    if ft:
        if ft.oa_url:
            urls["oa_url"] = ft.oa_url
        if ft.oa_pdf_url:
            urls["oa_pdf_url"] = ft.oa_pdf_url
    return urls


def _merge_anchors(records: list[SourceRecord]) -> list[Anchor]:
    """Deduplicate and order full-text anchors from source records."""
    anchors: list[Anchor] = []
    seen: set[str] = set()
    for rec in records:
        raw = rec.normalized_fields.get("full_text_anchors")
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, dict):
                anchor = Anchor(**item)
            elif isinstance(item, Anchor):
                anchor = item
            else:
                continue
            key = f"{anchor.anchor_type}:{anchor.section}:{anchor.anchor_text[:80]}"
            if key not in seen:
                seen.add(key)
                anchors.append(anchor)
    return anchors


def merge_records(records: list[SourceRecord]) -> list[WorkRecord]:
    """Merge source records into WorkRecords conservatively."""
    groups: dict[str, dict[str, Any]] = {}

    for record in records:
        keys = _record_keys(record)
        title = record.normalized_fields.get("title")
        year = record.normalized_fields.get("year")
        authors = record.normalized_fields.get("authors", [])
        first_author = ""
        if authors and isinstance(authors, list) and authors[0]:
            first_author = str(authors[0].get("name", "")).lower().strip()

        group_id = _make_group_id(keys, title, year, first_author)

        # Try to merge with an existing group on any shared identifier key.
        merged_into: str | None = None
        if keys:
            for gid, gdata in groups.items():
                existing_keys = gdata["keys"]
                shared = {k for k in keys if k in existing_keys and keys[k] == existing_keys[k]}
                if shared:
                    merged_into = gid
                    break
        if merged_into:
            groups[merged_into]["records"].append(record)
            groups[merged_into]["keys"].update(keys)
        else:
            groups[group_id] = {
                "keys": keys,
                "records": [record],
                "title": title,
                "year": year,
                "first_author": first_author,
            }

    works: list[WorkRecord] = []
    for gid, gdata in groups.items():
        recs = gdata["records"]
        keys = gdata["keys"]
        identifiers: dict[str, str] = {}
        for rec in recs:
            identifiers.update(rec.identifiers)

        # Build provenance.
        provenance: list[ProvenanceEntry] = []
        for rec in recs:
            for field, value in rec.normalized_fields.items():
                if value is None or value == "":
                    continue
                provenance.append(
                    ProvenanceEntry(
                        source=rec.source,
                        source_record_id=rec.source_record_id,
                        field=field,
                        value=value,
                        retrieved_at=rec.retrieved_at,
                    )
                )

        # Detect conflicts for fields present in multiple sources with different values.
        conflicts: list[SourceConflict] = []
        conflict_fields = ["title", "year", "publication_date", "venue", "abstract"]
        for field in conflict_fields:
            values = _collect_values(field, recs)
            if len(values) > 1:
                conflicts.append(
                    SourceConflict(
                        field=field,
                        values=values,
                        sources=[rec.source for rec in recs if rec.normalized_fields.get(field) in values],
                    )
                )

        # Build merged WorkRecord.
        title = _pick_best("title", [rec.normalized_fields.get("title") for rec in recs])
        year_val = _pick_best("year", [rec.normalized_fields.get("year") for rec in recs])
        year: int | None = None
        if isinstance(year_val, int):
            year = year_val
        elif isinstance(year_val, str) and year_val.isdigit():
            year = int(year_val)

        authors_raw = _pick_best("authors", [rec.normalized_fields.get("authors") for rec in recs])
        authors: list[Author] = []
        if isinstance(authors_raw, list):
            for a in authors_raw:
                if isinstance(a, Author):
                    authors.append(a)
                elif isinstance(a, dict):
                    authors.append(Author(**a))

        abstract = _pick_best("abstract", [rec.normalized_fields.get("abstract") for rec in recs])
        venue = _pick_best("venue", [rec.normalized_fields.get("venue") for rec in recs])
        citation_count = _pick_best("citation_count", [rec.normalized_fields.get("citation_count") for rec in recs])
        open_access_pdf = _pick_best("open_access_pdf", [rec.normalized_fields.get("open_access_pdf") for rec in recs])
        full_text_availability = _merge_full_text_availability(recs)
        full_text_anchors = _merge_anchors(recs)

        merge_reasons = [f"merged from {len(recs)} source(s): {', '.join(sorted({rec.source for rec in recs}))}"]
        if conflicts:
            merge_reasons.append(f"preserved {len(conflicts)} source conflict(s)")

        warnings: list[str] = []
        for rec in recs:
            warnings.extend(rec.warnings)
        if conflicts:
            warnings.append("Sources disagree on one or more fields; conflicts are preserved.")

        publication_date = _pick_best(
            "publication_date", [rec.normalized_fields.get("publication_date") for rec in recs]
        )
        fields_of_study = (
            _pick_best("fields_of_study", [rec.normalized_fields.get("fields_of_study") for rec in recs]) or []
        )
        publication_types = (
            _pick_best("publication_types", [rec.normalized_fields.get("publication_types") for rec in recs]) or []
        )
        keywords = _pick_best("keywords", [rec.normalized_fields.get("keywords") for rec in recs]) or []
        mesh_terms = _pick_best("mesh_terms", [rec.normalized_fields.get("mesh_terms") for rec in recs]) or []
        concepts = _pick_best("concepts", [rec.normalized_fields.get("concepts") for rec in recs]) or []

        works.append(
            WorkRecord(
                work_id=work_id_from_identifiers(identifiers) or gid,
                title=title,
                normalized_title=normalize_title(title),
                year=year,
                publication_date=publication_date,
                venue=venue,
                authors=authors,
                abstract=abstract,
                identifiers=identifiers,
                source_records=recs,
                merged_from_sources=sorted({rec.source for rec in recs}),
                provenance=provenance,
                conflicts=conflicts,
                merge_reasons=merge_reasons,
                citation_count=citation_count if isinstance(citation_count, int) else None,
                open_access_pdf=open_access_pdf if isinstance(open_access_pdf, dict) else None,
                full_text_availability=full_text_availability,
                full_text_anchors=full_text_anchors,
                urls=_build_urls(identifiers, full_text_availability),
                fields_of_study=fields_of_study,
                publication_types=publication_types,
                keywords=keywords,
                mesh_terms=mesh_terms,
                concepts=concepts,
                warnings=warnings,
            )
        )

    return works
