"""Tests for full-text download helpers."""

import asyncio

from searchpaper.fulltext import download_full_text


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content


def _run(coro):
    return asyncio.run(coro)


def test_download_reports_unavailable_pdf(monkeypatch, tmp_path):
    work = {"full_text_availability": {}, "identifiers": {}}
    result = _run(download_full_text(work, pdf_path=tmp_path / "paper.pdf"))
    assert result["pdf"]["ok"] is False
    assert result["pdf"]["available"] is False


def test_download_pdf_writes_file(monkeypatch, tmp_path):
    work = {
        "full_text_availability": {"oa_pdf_url": "https://example.com/paper.pdf"},
        "identifiers": {},
    }

    async def fake_get(self, url, **kwargs):
        return _FakeResponse(200, b"pdf content")

    monkeypatch.setattr("searchpaper.fulltext.HTTPClient.get", fake_get)

    out = tmp_path / "paper.pdf"
    result = _run(download_full_text(work, pdf_path=out))
    assert result["pdf"]["ok"] is True
    assert result["pdf"]["bytes"] == 11
    assert out.read_bytes() == b"pdf content"


def test_download_xml_requires_pmcid(monkeypatch, tmp_path):
    work = {"full_text_availability": {}, "identifiers": {}}
    result = _run(download_full_text(work, xml_path=tmp_path / "paper.xml"))
    assert result["xml"]["ok"] is False
    assert result["xml"]["available"] is False


def test_download_xml_writes_file(monkeypatch, tmp_path):
    work = {
        "full_text_availability": {},
        "identifiers": {"pmcid": "PMC12345"},
    }

    async def fake_get(self, url, **kwargs):
        return _FakeResponse(200, b"<article/>")

    monkeypatch.setattr("searchpaper.fulltext.HTTPClient.get", fake_get)

    out = tmp_path / "paper.xml"
    result = _run(download_full_text(work, xml_path=out))
    assert result["xml"]["ok"] is True
    assert out.read_bytes() == b"<article/>"
