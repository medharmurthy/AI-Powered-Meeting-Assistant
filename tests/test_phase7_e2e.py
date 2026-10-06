import os
import pytest
from starlette.testclient import TestClient
from verbatim.main import app

@pytest.fixture(autouse=True)
def enable_fake_env(monkeypatch):
    monkeypatch.setenv("VERBATIM_FAKE", "1")

def test_phase7_fake_pipeline_streaming_and_reconnection():
    client = TestClient(app)

    # 1. Trigger sample run
    resp = client.post("/api/runs/sample")
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]
    assert run_id

    # 2. Check initial run state
    state_resp = client.get(f"/api/runs/{run_id}")
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["id"] == run_id
    assert state["fake"] is True

    # 3. Stream SSE events
    with client.stream("GET", f"/api/runs/{run_id}/events?after=0") as stream:
        event_lines = []
        for line in stream.iter_lines():
            if line:
                event_lines.append(line)
            if "event: run.done" in line:
                break

    assert any("event: transcript.segment" in line for line in event_lines)
    assert any("event: record.section" in line for line in event_lines)
    assert any("event: run.done" in line for line in event_lines)

    # 4. Check post-run state (authoritative GET)
    done_resp = client.get(f"/api/runs/{run_id}")
    assert done_resp.status_code == 200
    done_state = done_resp.json()
    assert done_state["status"] == "done"
    assert len(done_state["raw"]) > 0
    assert done_state["record"]["summary"] is not None
    assert len(done_state["record"]["decisions"]) > 0
    assert len(done_state["record"]["action_items"]) > 0

    # 5. Mid-run event replay test: reconnect with after=5
    with client.stream("GET", f"/api/runs/{run_id}/events?after=5") as replay_stream:
        replayed = []
        for line in replay_stream.iter_lines():
            if line:
                replayed.append(line)
            if "event: run.done" in line:
                break
    assert any("event: run.done" in line for line in replayed)

def test_static_spa_serving():
    client = TestClient(app)
    # Check root index.html serves SPA
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<div id=\"root\">" in resp.text
