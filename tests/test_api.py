from __future__ import annotations

import io
import json
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from verbatim.app import app
from verbatim.export.exporter import export_all_run_files
from verbatim.store import append_event, create_run, get_run_dir, save_json, save_meta


@pytest.fixture
def client():
    return TestClient(app)


def test_upload_invalid_files_returns_app_error(client):
    # 1. Unsupported extension
    resp = client.post(
        "/api/runs",
        files={"file": ("bad_file.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNSUPPORTED_TYPE"

    # 2. Empty file
    resp2 = client.post(
        "/api/runs",
        files={"file": ("empty.mp3", b"", "audio/mpeg")},
    )
    assert resp2.status_code == 400
    data2 = resp2.json()
    assert data2["error"]["code"] == "EMPTY_FILE"


def test_sample_endpoint_returns_202(client):
    with patch("verbatim.routes.jobs.submit") as mock_submit:
        resp = client.post("/api/runs/sample")
        assert resp.status_code == 202
        data = resp.json()
        assert "run_id" in data
        assert len(data["run_id"]) > 5
        mock_submit.assert_called_once()


def test_export_endpoints(client):
    run_id = create_run(filename="export_api_test.wav")
    save_json(run_id, "raw_transcript.json", {"segments": []})
    save_json(run_id, "refined_transcript.json", {"segments": [], "corrections": []})
    save_json(run_id, "meeting_record.json", {
        "title": "API Test",
        "summary": "Summary",
        "attendees": [],
        "minutes": [],
        "decisions": [],
        "unresolved": [],
        "action_items": [],
        "models": {"stt": "whisper", "refiner": "qwen", "documenter": "gemma"},
    })
    save_meta(run_id, {"filename": "export_api_test.wav", "duration": 5.0})

    export_all_run_files(run_id)

    # 1. Valid export download
    res_md = client.get(f"/api/runs/{run_id}/export/meeting_record.md")
    assert res_md.status_code == 200
    assert "Meeting Record" in res_md.text or "API Test" in res_md.text

    # 2. Bundle zip download
    res_zip = client.get(f"/api/runs/{run_id}/export/bundle.zip")
    assert res_zip.status_code == 200
    assert res_zip.headers["content-type"] == "application/zip"

    # 3. Invalid export name rejected
    res_bad = client.get(f"/api/runs/{run_id}/export/secret_passwords.txt")
    assert res_bad.status_code == 400


def test_sse_events_replay_after_param(client):
    run_id = create_run(filename="events_test.wav")
    append_event(run_id, "stage.started", {"stage": "ingest"})
    append_event(run_id, "stage.done", {"stage": "ingest", "seconds": 0.5})
    append_event(run_id, "run.done", {})

    # Replay events starting after seq 1
    resp = client.get(f"/api/runs/{run_id}/events?after=1")
    assert resp.status_code == 200
    content = resp.text

    # Should contain event 2 and 3, but not event 1
    assert "id: 2" in content
    assert "event: stage.done" in content
    assert "id: 3" in content
    assert "event: run.done" in content
    assert "id: 1" not in content


def test_patch_correction_and_rerun(client):
    run_id = create_run(filename="patch_test.wav")
    raw_data = {"segments": [{"id": 1, "start": 0.0, "end": 2.0, "text": "Testing Memcatch database"}]}
    refined_data = {
        "segments": [{"id": 1, "start": 0.0, "end": 2.0, "text": "Testing Memcached database", "spans": []}],
        "corrections": [
            {
                "id": "c1",
                "segment_id": 1,
                "original": "Memcatch",
                "corrected": "Memcached",
                "reason": "Fix typo",
                "status": "applied",
            }
        ],
    }
    save_json(run_id, "raw_transcript.json", raw_data)
    save_json(run_id, "refined_transcript.json", refined_data)
    save_meta(run_id, {"filename": "patch_test.wav"})

    # Toggle correction off (revert)
    patch_res = client.patch(
        f"/api/runs/{run_id}/corrections/c1",
        json={"applied": False},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["record_stale"] is True

    # Check that text was reverted to raw
    updated = client.get(f"/api/runs/{run_id}").json()
    assert updated["recordStale"] is True
    assert updated["refined"][0]["text"] == "Testing Memcatch database"

    # Test rerun trigger
    with patch("verbatim.routes.jobs.submit") as mock_rerun:
        rerun_res = client.post(
            f"/api/runs/{run_id}/rerun",
            json={"from_stage": "document"},
        )
        assert rerun_res.status_code == 202
        mock_rerun.assert_called_once_with(run_id, from_stage="document")
