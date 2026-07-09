"""Parse citations from documents and verify them against SearchPaper results."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from searchpaper.engine import SearchEngine
from searchpaper.identifiers import identify, normalize_doi


class Citation:
    """One extracted citation candidate."""

    def __init__(
        self,
        raw: str,
        source: str,
        kind: str = "unknown",
        key: str | None = None,
    ):
        self.raw = raw
        self.source = source
        self.kind = kind
        self.key = key

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "source": self.source,
            "kind": self.kind,
            "key": self.key,
        }


_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s]+")
_PMID_RE = re.compile(r"\bPMID:\s*(\d+)\b", re.IGNORECASE)
_PMID_BARE_RE = re.compile(r"\b(\d{7,})\b")
_ARXIV_RE = re.compile(r"\barXiv:\s*(\d{4}\.\d{4,5})\b", re.IGNORECASE)


def _extract_identifier(raw: str) -> tuple[str, str] | None:
    """Return (kind, value) if an identifier can be extracted, else None."""
    m = _DOI_RE.search(raw)
    if m:
        doi = normalize_doi(m.group(0))
        if doi:
            return ("doi", doi)
    m = _PMID_RE.search(raw)
    if m:
        return ("pmid", m.group(1))
    m = _ARXIV_RE.search(raw)
    if m:
        return ("arxiv", m.group(1))
    # Bare 7+ digit as a last-resort PMID candidate.
    m = _PMID_BARE_RE.search(raw)
    if m:
        return ("pmid", m.group(1))
    return None


def _clean_query(raw: str) -> str:
    """Strip obvious identifiers to leave a searchable free-text query."""
    q = raw
    q = _DOI_RE.sub("", q)
    q = _PMID_RE.sub("", q)
    q = _ARXIV_RE.sub("", q)
    q = re.sub(r"\[\d+\]", "", q)
    return re.sub(r"\s+", " ", q).strip() or raw


def parse_txt(path: Path) -> list[Citation]:
    """Parse a plain-text reference list, one citation per non-empty line."""
    citations: list[Citation] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        citations.append(Citation(raw=raw, source=str(path), kind="txt_line"))
    return citations


def parse_docx(path: Path) -> list[Citation]:
    """Parse a Word document's paragraphs into citation strings."""
    try:
        import docx  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("python-docx is required to parse .docx files") from exc

    doc = docx.Document(str(path))
    citations: list[Citation] = []
    for para in doc.paragraphs:
        raw = para.text.strip()
        if raw:
            citations.append(Citation(raw=raw, source=str(path), kind="docx_paragraph"))
    return citations


def parse_tex(path: Path) -> list[Citation]:
    r"""Parse LaTeX citation keys and bibliography items.

    Returns ``\cite`` keys as ``tex_cite`` items and ``\bibitem`` bodies as
    ``tex_bibitem`` items. If both are present the caller can choose to verify
    the richer bibliography entries instead of the raw keys.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    citations: list[Citation] = []

    # \cite{key1,key2}
    for match in re.finditer(r"\\cite\{([^}]+)\}", text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key:
                citations.append(Citation(raw=key, source=str(path), kind="tex_cite", key=key))

    # \bibitem{key} ... (until next bibitem or end of environment)
    bib_pattern = re.compile(
        r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\}|$)",
        re.DOTALL,
    )
    for match in bib_pattern.finditer(text):
        key = match.group(1).strip()
        body = re.sub(r"\s+", " ", match.group(2)).strip()
        if body:
            citations.append(Citation(raw=body, source=str(path), kind="tex_bibitem", key=key or None))

    return citations


def parse_document(path: Path, format: str | None = None) -> list[Citation]:
    """Dispatch to the correct parser based on format or file extension."""
    fmt = (format or path.suffix.lower().lstrip(".")).lower()
    if fmt == "txt":
        return parse_txt(path)
    if fmt == "docx":
        return parse_docx(path)
    if fmt == "tex":
        return parse_tex(path)
    raise ValueError(f"Unsupported citation document format: {fmt}")


async def verify_citation(
    citation: Citation,
    engine: SearchEngine | None = None,
) -> dict[str, Any]:
    """Verify a single citation and return a structured result.

    Status values:
      - verified: a work was found and appears to match.
      - mismatch: a work was found but metadata differs.
      - not_found: no matching work could be located.
      - suspicious: ambiguous or very low-confidence match.
      - manual_needed: no identifier and free-text search was inconclusive.
    """
    engine = engine or SearchEngine()
    raw = citation.raw
    identifier = _extract_identifier(raw)

    work: dict[str, Any] | None = None
    source = "unknown"

    if identifier:
        kind, value = identifier
        wid = identify(value)
        if wid:
            try:
                result = await engine.resolve(wid, sources=["pubmed", "crossref", "openalex"])
                data = result.data if hasattr(result, "data") else result.get("data", {})
                works = data.get("works", []) if isinstance(data, dict) else []
                if works:
                    work = works[0] if isinstance(works[0], dict) else works[0].model_dump(mode="json")
                    source = f"{kind}_resolve"
            except Exception:
                pass

    if not work:
        query = _clean_query(raw)
        if len(query) >= 8:
            try:
                from searchpaper.schemas import SearchFilters

                result = await engine.search(
                    query, filters=SearchFilters(limit=3), sources=["pubmed", "crossref", "openalex"]
                )
                data = result.data if hasattr(result, "data") else result.get("data", {})
                works = data.get("works", []) if isinstance(data, dict) else []
                if works:
                    work = works[0] if isinstance(works[0], dict) else works[0].model_dump(mode="json")
                    source = "search"
            except Exception:
                pass

    if not work:
        return {
            **citation.to_dict(),
            "status": "not_found",
            "source": source,
            "work": None,
            "checks": {"identifier": bool(identifier)},
        }

    title = (work.get("title") or "").lower()
    raw_lower = raw.lower()
    title_match = title and (title in raw_lower or any(word in raw_lower for word in title.split() if len(word) > 4))

    if identifier or title_match:
        status = "verified"
    elif len(_clean_query(raw)) >= 20:
        status = "mismatch"
    else:
        status = "manual_needed"

    return {
        **citation.to_dict(),
        "status": status,
        "source": source,
        "work": {
            "work_id": work.get("work_id"),
            "title": work.get("title"),
            "year": work.get("year"),
            "venue": work.get("venue"),
            "identifiers": work.get("identifiers", {}),
        },
        "checks": {
            "identifier": bool(identifier),
            "title_match": title_match,
        },
    }


async def verify_citations(
    citations: list[Citation],
    engine: SearchEngine | None = None,
) -> dict[str, Any]:
    """Verify a list of citations and return a summary + detail list."""
    engine = engine or SearchEngine()
    results = [await verify_citation(c, engine=engine) for c in citations]
    summary: dict[str, int] = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {
        "schema_version": "0.2",
        "object_type": "citation_verification",
        "total": len(results),
        "summary": summary,
        "results": results,
    }


def _format_verification_markdown(report: dict[str, Any]) -> str:
    lines = ["# Citation Verification Report", ""]
    lines.append(f"Total citations: {report['total']}")
    for status, count in report["summary"].items():
        lines.append(f"- {status}: {count}")
    lines.append("")
    for r in report["results"]:
        lines.append(f"## {r['status'].upper()}")
        lines.append(f"- Raw: {r['raw']}")
        if r.get("work"):
            work = r["work"]
            lines.append(f"- Matched: {work.get('title')} ({work.get('year')})")
            ids = work.get("identifiers", {})
            if ids:
                lines.append(f"- IDs: {ids}")
        lines.append("")
    return "\n".join(lines)


def _format_verification_csv(report: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["status", "raw", "kind", "matched_title", "matched_year", "matched_doi", "matched_pmid"],
    )
    writer.writeheader()
    for r in report["results"]:
        work = r.get("work") or {}
        ids = work.get("identifiers", {})
        writer.writerow(
            {
                "status": r["status"],
                "raw": r["raw"],
                "kind": r["kind"],
                "matched_title": work.get("title", ""),
                "matched_year": work.get("year", ""),
                "matched_doi": ids.get("doi", ""),
                "matched_pmid": ids.get("pmid", ""),
            }
        )
    return buffer.getvalue()


def format_verification_report(report: dict[str, Any], output_format: str) -> str:
    """Serialize a verification report to JSON, JSONL, CSV, or Markdown."""
    fmt = output_format.lower().strip()
    if fmt == "json":
        return json.dumps(report, indent=2, ensure_ascii=False)
    if fmt == "jsonl":
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in report["results"])
    if fmt == "csv":
        return _format_verification_csv(report)
    if fmt == "markdown":
        return _format_verification_markdown(report)
    raise ValueError(f"Unsupported verification output format: {output_format}")


def verify_document(
    path: Path,
    input_format: str | None = None,
    output_format: str = "json",
    engine: SearchEngine | None = None,
) -> str:
    """High-level entry point: parse a document and verify its citations."""
    citations = parse_document(path, format=input_format)
    report = asyncio.run(verify_citations(citations, engine=engine))
    return format_verification_report(report, output_format)
