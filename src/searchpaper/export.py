"""Export SearchPaper results to common formats."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_BIBTEX_KEY_RE = re.compile(r"[^a-zA-Z0-9_:-]")


def _strip_html(value: str) -> str:
    """Remove simple HTML tags from a string."""
    return _HTML_TAG_RE.sub("", value)


def _bibtex_key(work: dict[str, Any]) -> str:
    """Build a stable BibTeX citation key.

    Prefer ``pmid<pmid>`` when a PMID is present, otherwise use
    ``firstauthorYEAR``.
    """
    ids = work.get("identifiers", {})
    if ids.get("pmid"):
        return _BIBTEX_KEY_RE.sub("", f"pmid{ids['pmid']}")[:50] or "item"

    authors = work.get("authors", [])
    first = "unknown"
    if authors:
        first = str(authors[0].get("last_name") or authors[0].get("name") or "unknown").lower()
    year = work.get("year") or "0000"
    key = f"{first.split()[0] if first else 'unknown'}{year}"
    return _BIBTEX_KEY_RE.sub("", key)[:50] or "item"


def _escape_bibtex(value: str) -> str:
    """Escape characters that are special inside BibTeX brace-delimited values."""
    value = _strip_html(value)
    # Escape backslash first, then braces.
    value = value.replace("\\", "\\\\")
    value = value.replace("{", "\\{")
    value = value.replace("}", "\\}")
    return value


def _escape_ris(value: str) -> str:
    """Clean a value for RIS output (no newlines, no HTML)."""
    value = _strip_html(value)
    return value.replace("\n", " ").replace("\r", "")


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
    pages = work.get("pages")
    if pages and isinstance(pages, str) and "-" in pages:
        start, _, end = pages.partition("-")
        if start and end:
            lines.append(f"  pages = {{{start}--{end}}},")
    lines.append("}")
    return "\n".join(lines)


def work_to_ris(work: dict[str, Any]) -> str:
    """Convert one work dict to an RIS entry."""
    lines = ["TY  - JOUR"]
    if work.get("title"):
        lines.append(f"TI  - {_escape_ris(work['title'])}")
    for author in work.get("authors", []):
        if author.get("name"):
            lines.append(f"AU  - {_escape_ris(author['name'])}")
    if work.get("year"):
        lines.append(f"PY  - {work['year']}")
    if work.get("venue"):
        lines.append(f"JO  - {_escape_ris(work['venue'])}")
    pages = work.get("pages")
    if pages and isinstance(pages, str) and "-" in pages:
        start, _, end = pages.partition("-")
        if start:
            lines.append(f"SP  - {start}")
        if end:
            lines.append(f"EP  - {end}")
    if work.get("identifiers", {}).get("doi"):
        lines.append(f"DO  - {work['identifiers']['doi']}")
    if work.get("identifiers", {}).get("pmid"):
        lines.append(f"AN  - PMID:{work['identifiers']['pmid']}")
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


def work_to_zotero_csv_row(work: dict[str, Any]) -> dict[str, str]:
    """Map a work dict to a flat row suitable for Zotero import helpers."""
    ids = work.get("identifiers", {})
    authors = work.get("authors", [])
    return {
        "title": work.get("title") or "",
        "authors": "; ".join(a.get("name") or "" for a in authors if a.get("name")),
        "year": str(work.get("year") or ""),
        "venue": work.get("venue") or "",
        "doi": ids.get("doi") or "",
        "pmid": ids.get("pmid") or "",
        "abstract": (work.get("abstract") or "")[:2000],
    }


def works_to_zotero(works: list[dict[str, Any]]) -> str:
    """Export works to a CSV table that can be imported into Zotero via plugins or scripts."""
    if not works:
        return ""
    fieldnames = ["title", "authors", "year", "venue", "doi", "pmid", "abstract"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for work in works:
        writer.writerow(work_to_zotero_csv_row(work))
    return buffer.getvalue()


def work_to_obsidian(work: dict[str, Any]) -> str:
    """Convert one work dict to an Obsidian literature note with YAML frontmatter."""
    ids = work.get("identifiers", {})
    authors = work.get("authors", [])
    frontmatter = {
        "title": work.get("title") or "",
        "authors": [a.get("name") or "" for a in authors if a.get("name")],
        "year": work.get("year"),
        "venue": work.get("venue") or "",
        "doi": ids.get("doi") or "",
        "pmid": ids.get("pmid") or "",
        "source": ",".join(work.get("merged_from_sources", [])),
    }
    yaml = json.dumps(frontmatter, indent=2, ensure_ascii=False)
    body = f"# {work.get('title') or 'Untitled'}\n\n"
    if work.get("abstract"):
        body += f"## Abstract\n\n{work.get('abstract')}\n\n"
    body += "## Links\n\n"
    if ids.get("doi"):
        body += f"- DOI: https://doi.org/{ids['doi']}\n"
    if ids.get("pmid"):
        body += f"- PubMed: https://pubmed.ncbi.nlm.nih.gov/{ids['pmid']}/\n"
    return f"---\n{yaml}\n---\n\n{body}"


def _format_author_list_apa(authors: list[dict[str, Any]]) -> str:
    if not authors:
        return ""
    names = [a.get("name") or "" for a in authors if a.get("name")]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return ", ".join(names[:-1]) + f", & {names[-1]}"


def _format_author_list_mla(authors: list[dict[str, Any]]) -> str:
    if not authors:
        return ""
    names = [a.get("name") or "" for a in authors if a.get("name")]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, and {names[1]}"
    return ", ".join(names[:-1]) + ", et al."


def work_to_apa(work: dict[str, Any]) -> str:
    """Convert one work dict to an APA 7 style citation."""
    authors = work.get("authors", [])
    author_str = _format_author_list_apa(authors)
    year = work.get("year") or "n.d."
    title = work.get("title") or "Untitled"
    venue = work.get("venue") or ""
    ids = work.get("identifiers", {})
    doi = ids.get("doi")

    parts: list[str] = []
    if author_str:
        parts.append(f"{author_str} ({year}). {title}.")
    else:
        parts.append(f"({year}). {title}.")
    if venue:
        parts.append(venue)
    if doi:
        parts.append(f"https://doi.org/{doi}")
    return " ".join(parts)


def work_to_mla(work: dict[str, Any]) -> str:
    """Convert one work dict to an MLA 9 style citation."""
    authors = work.get("authors", [])
    author_str = _format_author_list_mla(authors)
    year = work.get("year") or "n.d."
    title = work.get("title") or "Untitled"
    venue = work.get("venue") or ""

    citation = f'"{title}."'
    if author_str:
        citation = f"{author_str}. {citation}"
    if venue:
        citation += f" {venue},"
    citation += f" {year}."
    return citation


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
    if fmt == "zotero":
        return works_to_zotero(works)
    if fmt == "obsidian":
        return "\n\n---\n\n".join(work_to_obsidian(w) for w in works)
    if fmt == "apa":
        return "\n\n".join(work_to_apa(w) for w in works)
    if fmt == "mla":
        return "\n\n".join(work_to_mla(w) for w in works)
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
