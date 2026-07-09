"""Tests for citation parsing and verification."""

import pytest

from searchpaper.citation_parser import (
    Citation,
    parse_document,
    parse_docx,
    parse_tex,
    parse_txt,
    verify_citation,
    verify_citations,
)


def test_parse_txt(tmp_path):
    path = tmp_path / "refs.txt"
    path.write_text("DOI:10.1000/test\n\nPMID:12345\n# comment\n")
    citations = parse_txt(path)
    assert len(citations) == 2
    assert citations[0].raw == "DOI:10.1000/test"


def test_parse_tex(tmp_path):
    path = tmp_path / "paper.tex"
    path.write_text(
        r"\cite{key1,key2}\n"
        r"\begin{thebibliography}{9}\n"
        r"\bibitem{key1} Smith, J. (2023). A paper. Journal of Tests.\n"
        r"\bibitem{key2} Doe, A. (2022). Another paper. Nature.\n"
        r"\end{thebibliography}\n"
    )
    citations = parse_tex(path)
    kinds = {c.kind for c in citations}
    assert "tex_cite" in kinds
    assert "tex_bibitem" in kinds
    assert any(c.key == "key1" for c in citations)


def test_parse_docx(tmp_path):
    try:
        import docx
    except ImportError:
        pytest.skip("python-docx not available")

    path = tmp_path / "refs.docx"
    document = docx.Document()
    document.add_paragraph("Smith J. A test paper. 2023.")
    document.add_paragraph("Doe A. Another paper. 2022.")
    document.save(str(path))

    citations = parse_docx(path)
    assert len(citations) == 2
    assert "A test paper" in citations[0].raw


def test_parse_document_dispatch(tmp_path):
    path = tmp_path / "refs.txt"
    path.write_text("Line one\n")
    citations = parse_document(path)
    assert citations[0].kind == "txt_line"


class _FakeResult:
    def __init__(self, works):
        self.data = {"works": works}


class _FakeEngine:
    def __init__(self, works):
        self._works = works

    async def resolve(self, identifier, sources=None):
        return _FakeResult(self._works)

    async def search(self, query, filters=None, sources=None):
        return _FakeResult(self._works)


async def test_verify_citation_verified_with_identifier():
    work = {
        "work_id": "w1",
        "title": "A Test Paper",
        "year": 2023,
        "venue": "Journal of Tests",
        "identifiers": {"doi": "10.1000/test"},
    }
    engine = _FakeEngine([work])
    citation = Citation(raw="Smith 2023 doi:10.1000/test", source="test", kind="txt_line")
    result = await verify_citation(citation, engine=engine)
    assert result["status"] == "verified"
    assert result["work"]["identifiers"]["doi"] == "10.1000/test"


async def test_verify_citation_manual_needed_for_short_text():
    engine = _FakeEngine([])
    citation = Citation(raw="Smith 2023", source="test", kind="txt_line")
    result = await verify_citation(citation, engine=engine)
    assert result["status"] == "not_found"


async def test_verify_citations_summary():
    work = {"work_id": "w1", "title": "A Test Paper", "year": 2023, "identifiers": {"doi": "10.1000/test"}}
    engine = _FakeEngine([work])
    citations = [
        Citation(raw="doi:10.1000/test", source="test", kind="txt_line"),
        Citation(raw="not found text", source="test", kind="txt_line"),
    ]
    report = await verify_citations(citations, engine=engine)
    assert report["total"] == 2
    assert "verified" in report["summary"]
    assert "manual_needed" in report["summary"]
