"""Schema validation and snapshot-style tests for SearchPaper."""

import json

from searchpaper.schemas import (
    Author,
    Envelope,
    LiteratureSignal,
    SearchFilters,
    SearchResult,
    SearchTrace,
    SignalLevel,
    SignalType,
    SourceState,
    SourceStatus,
    WorkRecord,
)


def test_work_record_schema():
    work = WorkRecord(
        work_id="work:doi:10.1000/test",
        title="A Test Paper",
        identifiers={"doi": "10.1000/test"},
    )
    data = work.model_dump(mode="json")
    assert data["work_id"] == "work:doi:10.1000/test"
    assert data["title"] == "A Test Paper"


def test_search_result_envelope():
    result = SearchResult(
        works=[WorkRecord(work_id="w1", title="Test")],
        trace=SearchTrace(query="test query"),
    )
    envelope = Envelope(data=result.model_dump(mode="json"), object_type="search_result")
    data = envelope.model_dump(mode="json")
    assert data["schema_version"] == "0.2"
    assert data["object_type"] == "search_result"
    assert data["data"]["works"][0]["work_id"] == "w1"


def test_signal_levels_serialization():
    signal = LiteratureSignal(
        signal_id="s1",
        signal_type=SignalType.CURATED_RELATION,
        signal_level=SignalLevel.CURATED_OR_EXTRACTED,
        source="pubtator3",
    )
    data = signal.model_dump(mode="json")
    assert data["signal_level"] == "curated_or_extracted"
    assert "interpretation_warning" in data


def test_source_status_serialization():
    status = SourceStatus(
        source="pubmed",
        state=SourceState.AVAILABLE,
        message="ok",
    )
    data = status.model_dump(mode="json")
    assert data["state"] == "available"


def test_search_filters_roundtrip():
    filters = SearchFilters(year="2023", limit=10, open_access_only=True)
    data = filters.model_dump(mode="json")
    restored = SearchFilters(**data)
    assert restored.year == "2023"
    assert restored.limit == 10


def test_json_output_is_valid():
    work = WorkRecord(work_id="w1", title="Test", authors=[Author(name="A Smith")])
    result = SearchResult(works=[work])
    envelope = Envelope(data=result.model_dump(mode="json"), object_type="search_result")
    text = json.dumps(envelope.model_dump(mode="json"))
    parsed = json.loads(text)
    assert parsed["data"]["works"][0]["authors"][0]["name"] == "A Smith"


def test_work_record_snapshot(snapshot):
    work = WorkRecord(
        work_id="work:doi:10.1000/test",
        title="A Test Paper",
        year=2023,
        venue="Journal of Tests",
        authors=[Author(name="Alice Smith", last_name="Smith")],
        identifiers={"doi": "10.1000/test", "pmid": "12345"},
    )
    assert work.model_dump(mode="json") == snapshot


def test_literature_signal_snapshot(snapshot):
    signal = LiteratureSignal(
        signal_id="s1",
        signal_type=SignalType.CURATED_RELATION,
        signal_level=SignalLevel.CURATED_OR_EXTRACTED,
        source="pubtator3",
        relation_label="interacts",
    )
    assert signal.model_dump(mode="json") == snapshot


def test_source_status_snapshot(snapshot):
    status = SourceStatus(
        source="pubmed",
        state=SourceState.AVAILABLE,
        key_configured=False,
        message="ok",
    )
    assert status.model_dump(mode="json") == snapshot


def test_search_result_envelope_snapshot(snapshot):
    work = WorkRecord(work_id="w1", title="Test")
    result = SearchResult(
        works=[work],
        trace=SearchTrace(
            query="test query",
            sources_requested=["pubmed"],
            retrieved_at="2026-01-01T00:00:00Z",
        ),
    )
    envelope = Envelope(data=result.model_dump(mode="json"), object_type="search_result")
    assert envelope.model_dump(mode="json") == snapshot
