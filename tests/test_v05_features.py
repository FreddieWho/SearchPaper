"""Tests for v0.5 full-text-ready features."""

from searchpaper.engine import SearchEngine
from searchpaper.merge import merge_records
from searchpaper.schemas import Anchor, FullTextAvailability, SourceRecord, WorkIdentifier
from searchpaper.sources.europepmc import _extract_anchors_from_xml, _parse_full_text_urls


def test_parse_full_text_urls_with_open_access():
    item = {
        "doi": "10.1000/test",
        "pmid": "12345",
        "pmcid": "PMC12345",
        "hasFullText": "Y",
        "isOpenAccess": "Y",
        "fullTextUrlList": {
            "fullTextUrl": [
                {"documentStyle": "html", "availabilityCode": "OA", "url": "https://example.com/html"},
                {"documentStyle": "pdf", "availabilityCode": "OA", "url": "https://example.com/pdf.pdf"},
            ]
        },
    }
    ft = _parse_full_text_urls(item)
    assert ft.has_full_text is True
    assert ft.has_pdf is True
    assert ft.oa_url == "https://example.com/html"
    assert ft.oa_pdf_url == "https://example.com/pdf.pdf"
    assert "europepmc:html" in ft.sources
    assert "europepmc:pdf" in ft.sources


def test_parse_full_text_urls_without_urls():
    ft = _parse_full_text_urls({"pmid": "12345"})
    assert ft.has_full_text is False
    assert ft.oa_url is None


def test_extract_anchors_from_xml():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <article>
      <front>
        <article-meta>
          <abstract><p>Test abstract content.</p></abstract>
        </article-meta>
      </front>
      <body>
        <sec><title>Introduction</title><p>First sentence.</p></sec>
        <sec><title>Methods</title><p>Another sentence.</p></sec>
      </body>
    </article>
    """
    anchors = _extract_anchors_from_xml(xml)
    sections = {a.section for a in anchors}
    assert "Abstract" in sections
    assert "Introduction" in sections
    assert "Methods" in sections
    assert all(a.anchor_type in ("abstract", "full_text_section") for a in anchors)


def test_extract_anchors_from_invalid_xml():
    assert _extract_anchors_from_xml("not xml") == []


def test_merge_full_text_availability_and_anchors():
    rec1 = SourceRecord(
        source="europepmc",
        source_record_id="PMC12345",
        retrieved_at="2024-01-01T00:00:00Z",
        identifiers={"pmcid": "PMC12345"},
        normalized_fields={
            "title": "Test",
            "full_text_availability": FullTextAvailability(
                has_full_text=True,
                has_pdf=True,
                oa_url="https://example.com/html",
                sources=["europepmc:html"],
            ).model_dump(mode="json"),
            "full_text_anchors": [
                Anchor(anchor_type="abstract", section="Abstract", anchor_text="Abstract text").model_dump(mode="json")
            ],
        },
    )
    rec2 = SourceRecord(
        source="unpaywall",
        source_record_id="10.1000/test",
        retrieved_at="2024-01-01T00:00:00Z",
        identifiers={"pmcid": "PMC12345"},
        normalized_fields={
            "full_text_availability": FullTextAvailability(
                has_full_text=True,
                oa_pdf_url="https://example.com/pdf.pdf",
                sources=["unpaywall:pdf"],
            ).model_dump(mode="json"),
        },
    )
    works = merge_records([rec1, rec2])
    assert len(works) == 1
    work = works[0]
    assert work.full_text_availability is not None
    assert work.full_text_availability.has_full_text is True
    assert work.full_text_availability.has_pdf is True
    assert work.full_text_availability.oa_url == "https://example.com/html"
    assert work.full_text_availability.oa_pdf_url == "https://example.com/pdf.pdf"
    assert "europepmc:html" in work.full_text_availability.sources
    assert "unpaywall:pdf" in work.full_text_availability.sources
    assert len(work.full_text_anchors) == 1
    assert work.full_text_anchors[0].section == "Abstract"


async def test_engine_context_command():
    engine = SearchEngine(sources=[])
    wid = WorkIdentifier(type="doi", value="10.1000/test")
    result = await engine.context(wid)
    assert result.data["object_type"] == "paper_context_pack"
    assert result.data["work"] is None


def test_work_record_has_full_text_fields():
    from searchpaper.schemas import WorkRecord

    work = WorkRecord(
        work_id="w1",
        full_text_availability=FullTextAvailability(has_full_text=True),
        full_text_anchors=[Anchor(anchor_type="abstract", section="Abstract")],
    )
    data = work.model_dump(mode="json")
    assert data["full_text_availability"]["has_full_text"] is True
    assert data["full_text_anchors"][0]["section"] == "Abstract"
