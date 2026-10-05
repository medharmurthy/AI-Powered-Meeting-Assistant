from __future__ import annotations

import io
import math
import struct
import wave
import pytest

from verbatim.errors import PipelineError
from verbatim.schemas import RawTranscript, Segment
from verbatim.stt import (
    build_prompt,
    collapse_repeated_runs,
    format_time,
    transcribe_audio,
)
from verbatim.store import create_run, delete_run, get_run_dir, load_json


def test_build_prompt():
    assert build_prompt([], []) is None
    assert build_prompt(None, None) is None

    p1 = build_prompt(["Redis", "Kubernetes"], [])
    assert p1 == "Meeting transcript. Terms: Redis, Kubernetes."

    p2 = build_prompt([], ["Maya", "Dan"])
    assert p2 == "Meeting transcript. Participants: Maya, Dan."

    p3 = build_prompt(["Redis"], ["Maya"])
    assert p3 == "Meeting transcript. Participants: Maya. Terms: Redis."


def test_format_time():
    assert format_time(0) == "00:00"
    assert format_time(59) == "00:59"
    assert format_time(60) == "01:00"
    assert format_time(75.4) == "01:15"
    assert format_time(3600) == "01:00:00"
    assert format_time(3665) == "01:01:05"


def test_collapse_repeated_runs():
    class DummySeg:
        def __init__(self, idx, text):
            self.id = idx
            self.text = text

    # Case 1: no run >= 3
    items = [(DummySeg(1, "A"), "A"), (DummySeg(2, "A"), "A"), (DummySeg(3, "B"), "B")]
    out = list(collapse_repeated_runs(iter(items)))
    assert len(out) == 3

    # Case 2: run of 4 identical -> collapsed to 1
    items2 = [
        (DummySeg(1, "A"), "A"),
        (DummySeg(2, "A"), "A"),
        (DummySeg(3, "A"), "A"),
        (DummySeg(4, "A"), "A"),
        (DummySeg(5, "B"), "B"),
    ]
    out2 = list(collapse_repeated_runs(iter(items2)))
    assert len(out2) == 2
    assert out2[0][1] == "A"
    assert out2[1][1] == "B"

    # Case 3: run of 3 at the very end -> collapsed to 1
    items3 = [
        (DummySeg(1, "A"), "A"),
        (DummySeg(2, "B"), "B"),
        (DummySeg(3, "B"), "B"),
        (DummySeg(4, "B"), "B"),
    ]
    out3 = list(collapse_repeated_runs(iter(items3)))
    assert len(out3) == 2
    assert out3[0][1] == "A"
    assert out3[1][1] == "B"


def test_no_speech_detection():
    # If audio is silent/blank and VAD detects no speech, transcribe_audio raises NO_SPEECH
    run_id = create_run("silent.wav")
    try:
        run_dir = get_run_dir(run_id)
        audio_wav = run_dir / "audio.wav"
        # 3 seconds of zeros
        with wave.open(str(audio_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 48000)

        with pytest.raises(PipelineError) as exc_info:
            transcribe_audio(run_id, model_override="tiny")
        assert exc_info.value.error.code == "NO_SPEECH"
    finally:
        delete_run(run_id)
