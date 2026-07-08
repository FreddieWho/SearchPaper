"""Tests for project-level trace/export workflow."""

from searchpaper.project import export_trace, list_traces, load_trace, save_search_trace


def test_save_and_list_traces(tmp_path):
    project = tmp_path / ".searchpaper"
    (project / "traces").mkdir(parents=True)
    (project / "exports").mkdir(parents=True)
    (project / "queries").mkdir(parents=True)

    envelope = {
        "schema_version": "0.2",
        "object_type": "search_result",
        "data": {
            "works": [
                {"work_id": "w1", "title": "Test Paper"},
            ],
        },
        "warnings": [],
        "trace": {},
    }

    saved = save_search_trace("test query", envelope, project=project)
    assert saved["work_count"] == 1
    assert "trace_id" in saved

    traces = list_traces(project=project)
    assert len(traces) == 1
    assert traces[0]["query"] == "test query"


def test_load_and_export_trace(tmp_path):
    project = tmp_path / ".searchpaper"
    (project / "traces").mkdir(parents=True)
    (project / "exports").mkdir(parents=True)
    (project / "queries").mkdir(parents=True)

    envelope = {
        "schema_version": "0.2",
        "object_type": "search_result",
        "data": {
            "works": [
                {"work_id": "w1", "title": "Test Paper"},
            ],
        },
        "warnings": [],
        "trace": {},
    }

    saved = save_search_trace("test query", envelope, project=project)
    trace_id = saved["trace_id"]

    loaded = load_trace(trace_id, project=project)
    assert loaded["trace_id"] == trace_id

    exported = export_trace(trace_id, fmt="json", project=project)
    assert exported["work_count"] == 1
    assert "Test Paper" in exported["content"]
