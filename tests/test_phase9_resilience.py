from __future__ import annotations

import json
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from verbatim.app import app
from verbatim.errors import CATALOGUE, PipelineError, make_app_error
from verbatim.export.exporter import verify_parity
from verbatim.pipeline import run_pipeline
from verbatim.schemas import MeetingRecord, MinutesTopic, Decision, ActionItem
from verbatim.store import (
    build_run_state,
    create_run,
    get_run_dir,
    load_meta,
    save_json,
    save_meta,
)


@pytest.fixture
def client():
    return TestClient(app)


import asyncio
from verbatim.main import pipeline_error_handler


def test_all_16_catalogue_error_codes():
    """Verify all 16 error codes in CATALOGUE produce valid AppErrors and map to correct HTTP status codes."""
    assert len(CATALOGUE) == 16, f"Expected 16 error codes in CATALOGUE, got {len(CATALOGUE)}"

    expected_status = {
        "UNSUPPORTED_TYPE": 400,
        "EMPTY_FILE": 400,
        "TOO_LARGE": 413,
        "UNREADABLE_FILE": 400,
        "NO_AUDIO_STREAM": 400,
        "TOO_SHORT": 400,
        "TOO_LONG": 400,
        "SILENT_AUDIO": 400,
        "NO_SPEECH": 400,
        "NOT_ENGLISH": 500,
        "GPU_FALLBACK": 500,
        "OLLAMA_UNREACHABLE": 503,
        "MODEL_MISSING": 503,
        "LLM_BAD_OUTPUT": 500,
        "LLM_TIMEOUT": 504,
        "INTERNAL": 500,
    }

    for code, expected_code in expected_status.items():
        err = make_app_error(code)
        assert err.code == code
        assert len(err.title) > 0
        assert len(err.detail) > 0

        # Verify FastAPI exception handler maps this code to the right HTTP status
        resp = asyncio.run(pipeline_error_handler(None, PipelineError(code=code)))
        assert resp.status_code == expected_code, (
            f"Code {code} expected status {expected_code}, got {resp.status_code}"
        )
        data = json.loads(resp.body.decode("utf-8"))
        assert "error" in data
        assert data["error"]["code"] == code


def test_delete_run_endpoint_removes_dir_and_meta(client):
    """Test DELETE /api/runs/{id} removes run directory from disk and excludes it from list."""
    run_id = create_run(filename="to_delete.wav")
    run_dir = get_run_dir(run_id)
    test_file = run_dir / "sample_artifact.txt"
    test_file.write_text("temporary artifact", encoding="utf-8")

    assert run_dir.exists()
    assert test_file.exists()

    # Verify present in list
    runs_before = client.get("/api/runs").json()
    assert any(r["id"] == run_id for r in runs_before)

    # Perform deletion
    del_resp = client.delete(f"/api/runs/{run_id}")
    assert del_resp.status_code == 204

    # Verify removed from disk
    assert not run_dir.exists()

    # Verify excluded from runs list
    runs_after = client.get("/api/runs").json()
    assert not any(r["id"] == run_id for r in runs_after)


def test_mid_run_failure_preserves_earlier_stage_artifacts():
    """Verify mid-run failure preserves prior stage outputs and allows resumption from failed stage."""
    run_id = create_run(filename="mid_run_test.wav")
    run_dir = get_run_dir(run_id)

    raw_data = {
        "segments": [{"id": 0, "start": 0.0, "end": 2.0, "text": "Raw transcribed text."}],
        "duration": 2.0,
        "language": "en",
        "model": "distil-large-v3",
        "device": "cpu",
    }
    refined_data = {
        "segments": [{"id": 0, "start": 0.0, "end": 2.0, "text": "Refined text.", "spans": []}],
        "corrections": [],
        "profile": {"topic": "T", "domain": "D", "likely_terms": [], "names": []},
        "model": "qwen3:4b",
    }
    save_json(run_id, "raw_transcript.json", raw_data)
    save_json(run_id, "refined_transcript.json", refined_data)
    save_meta(run_id, {"filename": "mid_run_test.wav", "duration": 2.0})

    # Simulate Ollama crash during document stage
    with patch("verbatim.pipeline.document_meeting") as mock_doc:
        mock_doc.side_effect = PipelineError(
            code="OLLAMA_UNREACHABLE",
            detail="Could not connect to Ollama at http://127.0.0.1:11434",
            fix="Start Ollama (`ollama serve`)",
            stage="document",
        )

        with pytest.raises(PipelineError) as exc_info:
            run_pipeline(run_id, from_stage="document")

        assert exc_info.value.error.code == "OLLAMA_UNREACHABLE"

    # Assert earlier artifacts remain completely intact
    meta_after_fail = load_meta(run_id)
    assert meta_after_fail["status"] == "failed"
    assert meta_after_fail["error"]["code"] == "OLLAMA_UNREACHABLE"
    assert (run_dir / "raw_transcript.json").exists()
    assert (run_dir / "refined_transcript.json").exists()

    # Now simulate Ollama returning and user clicking "Retry from this step"
    dummy_record = MeetingRecord(
        title="Recovered Meeting",
        summary="Summary of meeting.",
        attendees=["Maya"],
        minutes=[MinutesTopic(title="Topic 1", points=[])],
        decisions=[Decision(id="D1", text="Decision 1", segment_ids=[0])],
        unresolved=[],
        action_items=[ActionItem(id="T1", task="Task 1", segment_ids=[0])],
        models={"stt": "distil-large-v3", "refiner": "qwen3:4b", "documenter": "gemma3:4b"},
        source_file="mid_run_test.wav",
        generated_at="2026-10-07T10:00:00Z",
    )

    with patch("verbatim.pipeline.document_meeting", return_value=dummy_record):
        run_pipeline(run_id, from_stage="document")

    meta_after_retry = load_meta(run_id)
    assert meta_after_retry["status"] == "done"
    assert (run_dir / "meeting_record.json").exists()
    assert (run_dir / "bundle.zip").exists()


def test_export_parity_failure_state():
    """Verify verify_parity accurately detects discrepancy when Markdown and JSON disagree."""
    record = {
        "decisions": [
            {"id": "D1", "text": "Migrate to Redis"},
            {"id": "D2", "text": "Do not upgrade PostgreSQL"},
        ],
        "action_items": [
            {"id": "T1", "task": "Write Terraform module"},
        ],
    }

    # Markdown missing D2
    mismatched_md = """
# Test
## Decisions
- **D1.** Migrate to Redis [01:05]
## Action items
| # | Task | Owner | Deadline | Source |
|---|------|-------|----------|--------|
| T1 | Write Terraform module | Dan | by Thursday | [01:05] |
"""
    result = verify_parity(record, mismatched_md)
    assert result["ok"] is False
    assert result["decisions"] == 2
    assert result["tasks"] == 1


def test_run_state_includes_export_parity(client):
    """Verify GET /api/runs/{id} returns exportParity in RunState."""
    run_id = create_run(filename="parity_api_test.wav")
    save_meta(
        run_id,
        {
            "filename": "parity_api_test.wav",
            "export_parity": {"decisions": 2, "tasks": 3, "ok": True},
        },
    )

    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "exportParity" in data
    assert data["exportParity"] == {"decisions": 2, "tasks": 3, "ok": True}
