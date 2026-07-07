"""Export SearchPaper results to common formats."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_BIBTEX_KEY_RE = re.compile(r"[^a-zA-Z0-9_:-]")


def _bibtex_key(work: dict[str, Any]) -> str:
    authors = work.get("authors", [])
    first = "unknown"
    if authors:
        first = str(authors[0].get("last_name") or authors[0].get("name") or "unknown").lower()
    year = work.get("year") or "0000"
    title_words = re.findall(r"\w+", (work.get("title") or "untitled").lower())[:3]
    key = f"{first.split()[0] if first else 'unknown'}{year}{''.join(title_words)}"
    return _BIBTEX_KEY_RE.sub("", key)[:50] or "item"


def _escape_bibtex(value: str) -> str:
    return value.replace("{", "").replace("}", "").replace("\\", "")


def work_to_bibtex(work: dict[str, Any]) -> str:
    """Convert one work dict to a BibTeX entry."""
    entry_type = "article"
    if (work.get("publication_types") or [None])[0] in ("book", "Book"):
        entry_type = "book"
    key = _bibtex_key(work)
    lines = [f"@{entry_type}{{{key},"]
    if work.get("title"):
        lines.append(f"  title = {{{_escape_bibtex(work['title'])}}},")
    authors = work.get("authors", [])
    if authors:
        names = " and ".join(a.get("name") or "" for a in authors if a.get("name"))
        if names:
            lines.append(f"  author = {{{_escape_bibtex(names)}}},")
    if work.get("year"):
        lines.append(f"  year = {{{work['year']}}},")
    if work.get("venue"):
        lines.append(f"  journal = {{{_escape_bibtex(work['venue'])}}},")
    if work.get("identifiers", {}).get("doi"):
        lines.append(f"  doi = {{{work['identifiers']['doi']}}},")
    lines.append("}")
    return "\n".join(lines)


def work_to_ris(work: dict[str, Any]) -> str:
    """Convert one work dict to an RIS entry."""
    lines = ["TY  - JOUR"]
    if work.get("title"):
        lines.append(f"TI  - {work['title']}")
    for author in work.get("authors", []):
        if author.get("name"):
            lines.append(f"AU  - {author['name']}")
    if work.get("year"):
        lines.append(f"PY  - {work['year']}")
    if work.get("venue"):
        lines.append(f"JO  - {work['venue']}")
    if work.get("identifiers", {}).get("doi"):
        lines.append(f"DO  - {work['identifiers']['doi']}")
    if work.get("identifiers", {}).get("pmid"):
        lines.append(f"AN  - {work['identifiers']['pmid']}")
    lines.append("ER  - ")
    return "\n".join(lines)


def work_to_enw(work: dict[str, Any]) -> str:
    """Convert one work dict to EndNote tagged text."""
    lines = ["%0 Journal Article"]
    if work.get("title"):
        lines.append(f"%T {work['title']}")
    for author in work.get("authors", []):
        if author.get("name"):
            lines.append(f"%A {author['name']}")
    if work.get("year"):
        lines.append(f"%D {work['year']}")
    if work.get("venue"):
        lines.append(f"%J {work['venue']}")
    ids = work.get("identifiers", {})
    if ids.get("doi"):
        lines.append(f"%R {ids['doi']}")
    if ids.get("pmid"):
        lines.append(f"%M {ids['pmid']}")
    if work.get("abstract"):
        lines.append(f"%X {work['abstract']}")
    return "\n".join(lines)


def work_to_nbib(work: dict[str, Any]) -> str:
    """Convert one work dict to a minimal NBIB/MEDLINE-like record."""
    ids = work.get("identifiers", {})
    lines: list[str] = []
    if ids.get("pmid"):
        lines.append(f"PMID- {ids['pmid']}")
    if work.get("title"):
        lines.append(f"TI  - {work['title']}")
    for author in work.get("authors", []):
        if author.get("name"):
            lines.append(f"AU  - {author['name']}")
    if work.get("venue"):
        lines.append(f"JT  - {work['venue']}")
    if work.get("year"):
        lines.append(f"DP  - {work['year']}")
    if work.get("abstract"):
        lines.append(f"AB  - {work['abstract']}")
    if ids.get("doi"):
        lines.append(f"LID - {ids['doi']} [doi]")
    return "\n".join(lines)


def work_to_markdown(work: dict[str, Any]) -> str:
    """Convert one work dict to a Markdown citation."""
    parts: list[str] = []
    if work.get("title"):
        parts.append(f"### {work['title']}")
    authors = work.get("authors", [])
    if authors:
        parts.append(", ".join(a.get("name") or "" for a in authors if a.get("name")))
    meta = []
    if work.get("year"):
        meta.append(str(work["year"]))
    if work.get("venue"):
        meta.append(work["venue"])
    if meta:
        parts.append(". ".join(meta))
    ids = work.get("identifiers", {})
    if ids.get("doi"):
        parts.append(f"DOI: {ids['doi']}")
    if ids.get("pmid"):
        parts.append(f"PMID: {ids['pmid']}")
    if work.get("abstract"):
        parts.append(f"\n{work['abstract'][:500]}")
    return "\n\n".join(parts)


def works_to_format(works: list[dict[str, Any]], format: str) -> str:
    """Serialize a list of work dicts to the requested format."""
    fmt = format.lower().strip()
    if fmt == "json":
        return json.dumps(works, indent=2, ensure_ascii=False)
    if fmt == "jsonl":
        lines = [json.dumps(w, ensure_ascii=False) for w in works]
        return "\n".join(lines) + ("\n" if lines else "")
    if fmt == "bibtex":
        return "\n\n".join(work_to_bibtex(w) for w in works)
    if fmt == "ris":
        return "\n\n".join(work_to_ris(w) for w in works)
    if fmt == "enw":
        return "\n\n".join(work_to_enw(w) for w in works)
    if fmt == "nbib":
        return "\n\n".join(work_to_nbib(w) for w in works)
    if fmt == "markdown":
        return "\n\n---\n\n".join(work_to_markdown(w) for w in works)
    raise ValueError(f"Unsupported export format: {format}")


def export_file(input_file: Path, output: Path, format: str) -> None:
    """Read SearchPaper JSON result file and write exported content."""
    data = json.loads(input_file.read_text(encoding="utf-8"))
    works = data.get("data", {}).get("works", []) if isinstance(data.get("data"), dict) else data.get("works", [])
    content = works_to_format(works, format)
    if str(output) == "-":
        print(content)
    else:
        output.write_text(content, encoding="utf-8")
