from __future__ import annotations

import io
import math
import struct
import wave
import pytest
from starlette.testclient import TestClient

from verbatim.config import get_config
from verbatim.errors import PipelineError
from verbatim.ingest import (
    process_audio_file,
    save_stream_to_file,
    validate_file_extension,
)
from verbatim.main import app
from verbatim.store import (
    create_run,
    delete_run,
    get_run_dir,
    load_json,
)


def create_wave_bytes(duration_s: float, freq_hz: float = 440.0, amp: float = 0.5, rate: int = 16000) -> bytes:
    """Generate uncompressed WAV byte content."""
    num_samples = int(duration_s * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        if amp <= 0:
            samples = [0] * num_samples
        else:
            samples = [
                int(amp * 32767.0 * math.sin(2.0 * math.pi * freq_hz * i / rate))
                for i in range(num_samples)
            ]
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


@pytest.fixture
def client():
    return TestClient(app)


def test_unsupported_type(client):
    cfg = get_config()
    with pytest.raises(PipelineError) as exc_info:
        validate_file_extension("document.txt", cfg.limits.allowed_ext)
    assert exc_info.value.error.code == "UNSUPPORTED_TYPE"

    response = client.post(
        "/api/runs",
        files={"file": ("document.txt", b"plain text content", "text/plain")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNSUPPORTED_TYPE"
    assert "isn't supported" in data["error"]["title"].lower()


def test_empty_file(client, tmp_path):
    run_id = create_run("empty.wav")
    try:
        run_dir = get_run_dir(run_id)
        empty_path = run_dir / "original.wav"
        with pytest.raises(PipelineError) as exc_info:
            save_stream_to_file(io.BytesIO(b""), empty_path, max_bytes=1000)
        assert exc_info.value.error.code == "EMPTY_FILE"
    finally:
        delete_run(run_id)

    response = client.post(
        "/api/runs",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "EMPTY_FILE"
    assert "empty" in data["error"]["title"].lower()


def test_unreadable_file(client):
    run_id = create_run("fake.mp3")
    try:
        run_dir = get_run_dir(run_id)
        fake_path = run_dir / "original.mp3"
        fake_path.write_bytes(b"This is not a real audio file at all. Just random text.")

        with pytest.raises(PipelineError) as exc_info:
            process_audio_file(run_id, fake_path)
        assert exc_info.value.error.code == "UNREADABLE_FILE"
    finally:
        delete_run(run_id)

    response = client.post(
        "/api/runs",
        files={"file": ("fake.mp3", b"This is a text file renamed to mp3", "audio/mpeg")},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "UNREADABLE_FILE"


def test_silent_audio(client):
    silent_bytes = create_wave_bytes(duration_s=3.0, amp=0.0)
    run_id = create_run("silent.wav")
    try:
        run_dir = get_run_dir(run_id)
        silent_path = run_dir / "original.wav"
        silent_path.write_bytes(silent_bytes)

        with pytest.raises(PipelineError) as exc_info:
            process_audio_file(run_id, silent_path)
        assert exc_info.value.error.code == "SILENT_AUDIO"
    finally:
        delete_run(run_id)

    response = client.post(
        "/api/runs",
        files={"file": ("silent.wav", silent_bytes, "audio/wav")},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "SILENT_AUDIO"
    assert "silent" in data["error"]["title"].lower()


def test_valid_tone_audio(client):
    tone_bytes = create_wave_bytes(duration_s=3.0, freq_hz=440.0, amp=0.6)

    # 1. Direct unit test of process_audio_file
    run_id = create_run("tone.wav")
    try:
        run_dir = get_run_dir(run_id)
        original_path = run_dir / "original.wav"
        original_path.write_bytes(tone_bytes)

        result = process_audio_file(run_id, original_path)

        audio_wav = run_dir / "audio.wav"
        assert audio_wav.exists()
        assert audio_wav.stat().st_size > 0

        peaks_data = load_json(run_id, "peaks.json")
        assert peaks_data is not None
        assert "peaks" in peaks_data
        assert "duration" in peaks_data
        assert len(peaks_data["peaks"]) == 1600
        assert math.isclose(peaks_data["duration"], 3.0, abs_tol=0.1)
        assert all(0.0 <= p <= 1.0 for p in peaks_data["peaks"])
    finally:
        delete_run(run_id)

    # 2. HTTP POST /api/runs test
    response = client.post(
        "/api/runs",
        files={"file": ("tone.wav", tone_bytes, "audio/wav")},
        data={"glossary": '["Redis", "Kubernetes"]', "participants": '["Maya", "Dan"]'},
    )
    assert response.status_code == 202
    res_data = response.json()
    assert "run_id" in res_data
    created_id = res_data["run_id"]

    try:
        # Check GET /api/runs/{id}
        state_resp = client.get(f"/api/runs/{created_id}")
        assert state_resp.status_code == 200
        state = state_resp.json()
        assert state["id"] == created_id
        assert state["duration"] is not None
        assert math.isclose(state["duration"], 3.0, abs_tol=0.1)

        # Check GET /api/runs/{id}/peaks
        peaks_resp = client.get(f"/api/runs/{created_id}/peaks")
        assert peaks_resp.status_code == 200
        p_json = peaks_resp.json()
        assert len(p_json["peaks"]) == 1600

        # Check GET /api/runs/{id}/audio
        audio_resp = client.get(f"/api/runs/{created_id}/audio")
        assert audio_resp.status_code == 200
        assert audio_resp.headers["content-type"].startswith("audio/wav")
        assert len(audio_resp.content) > 0
    finally:
        delete_run(created_id)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert "profile" in data
    assert data["profile"] in ("lite", "standard", "quality", "auto")

    assert "gpu" in data
    assert "available" in data["gpu"]

    assert "stt" in data
    assert "model" in data["stt"]
    assert "device" in data["stt"]

    assert "llm" in data
    assert "reachable" in data["llm"]
    assert "refiner" in data["llm"]
    assert "documenter" in data["llm"]

    assert "issues" in data
    assert isinstance(data["issues"], list)
