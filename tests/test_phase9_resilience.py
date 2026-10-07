import io
import json
import math
import struct
import wave
from unittest.mock import patch, MagicMock
import pytest
from starlette.testclient import TestClient

from verbatim.app import app
from verbatim.errors import CATALOGUE, PipelineError, make_app_error
from verbatim.export.exporter import verify_parity
from verbatim.jobs import jobs
from verbatim.pipeline import run_pipeline
from verbatim.schemas import MeetingRecord, MinutesTopic, Decision, ActionItem
from verbatim.store import (
    build_run_state,
    create_run,
    delete_run,
    events_since,
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


def _make_dummy_wav_bytes(duration_s: float = 3.0) -> bytes:
    num_samples = int(duration_s * 16000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        samples = [
            int(0.5 * 32767.0 * math.sin(2.0 * math.pi * 440.0 * i / 16000))
            for i in range(num_samples)
        ]
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def test_post_runs_submits_job_to_worker(client):
    """Verify that uploading audio via POST /api/runs enqueues the job to background worker."""
    wav_bytes = _make_dummy_wav_bytes(duration_s=3.0)
    with patch.object(jobs, "submit") as mock_submit:
        resp = client.post(
            "/api/runs",
            files={"file": ("meeting.wav", wav_bytes, "audio/wav")},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        mock_submit.assert_called_once_with(data["run_id"], from_stage="transcribe")


def test_queued_run_transitions_to_processing():
    """Verify that jobs.submit transitions a run from queued to running with appropriate events."""
    run_id = create_run(filename="queued_transition_test.wav")
    try:
        run_dir = get_run_dir(run_id)
        # Create audio.wav so transcribe can find it
        wav_bytes = _make_dummy_wav_bytes(duration_s=2.5)
        (run_dir / "audio.wav").write_bytes(wav_bytes)

        # Mock run_pipeline to verify it gets invoked by the worker
        with patch("verbatim.jobs.run_pipeline") as mock_pipeline:
            jobs.submit(run_id, from_stage="transcribe")

            # Wait briefly for thread execution
            import time
            for _ in range(20):
                if mock_pipeline.called:
                    break
                time.sleep(0.05)

            assert mock_pipeline.called
            mock_pipeline.assert_called_once_with(run_id=run_id, from_stage="transcribe")

        evs = events_since(run_id, 0)
        event_types = [e["type"] for e in evs]
        assert "run.queued" in event_types
    finally:
        delete_run(run_id)


def test_worker_exception_marks_run_failed():
    """Verify worker exceptions guarantee run status becomes failed and run.failed event is emitted."""
    run_id = create_run(filename="crash_test.wav")
    try:
        def crashing_pipeline(run_id, from_stage):
            raise RuntimeError("Unexpected pipeline crash")

        with patch("verbatim.jobs.run_pipeline", side_effect=crashing_pipeline):
            jobs.submit(run_id, from_stage="transcribe")

            import time
            for _ in range(20):
                meta = load_meta(run_id) or {}
                if meta.get("status") == "failed":
                    break
                time.sleep(0.05)

            meta = load_meta(run_id) or {}
            assert meta.get("status") == "failed"
            assert meta.get("error") is not None
            assert meta["error"]["code"] == "INTERNAL"

            evs = events_since(run_id, 0)
            assert any(e["type"] == "run.failed" for e in evs)
    finally:
        delete_run(run_id)


def test_rerun_endpoint_supports_transcribe_stage(client):
    """Verify POST /api/runs/{id}/rerun allows retrying from transcribe stage."""
    run_id = create_run(filename="rerun_transcribe_test.wav")
    try:
        with patch.object(jobs, "submit") as mock_submit:
            resp = client.post(f"/api/runs/{run_id}/rerun", json={"from_stage": "transcribe"})
            assert resp.status_code == 202
            mock_submit.assert_called_once_with(run_id, from_stage="transcribe")
    finally:
        delete_run(run_id)
