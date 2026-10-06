from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import zipfile
import pytest

from verbatim.export.exporter import (
    export_all_run_files,
    generate_corrections_csv,
    generate_raw_transcript_srt,
    generate_raw_transcript_txt,
    generate_refined_transcript_txt,
    render_meeting_record_md,
    verify_parity,
)
from verbatim.store import create_run, get_run_dir, save_json, save_meta


def test_srt_and_txt_generation():
    segments = [
        {"id": 1, "start": 0.0, "end": 2.5, "text": "Hello world."},
        {"id": 2, "start": 3.0, "end": 5.25, "text": "Testing subtitles."},
    ]
    txt = generate_raw_transcript_txt(segments)
    assert "[00:00] Hello world." in txt
    assert "[00:03] Testing subtitles." in txt

    srt = generate_raw_transcript_srt(segments)
    assert "00:00:00,000 --> 00:00:02,500" in srt
    assert "00:00:03,000 --> 00:00:05,250" in srt
    assert "Hello world." in srt


def test_corrections_csv_generation():
    corrections = [
        {
            "segment_id": 1,
            "original": "Memcatch",
            "corrected": "Memcached",
            "reason": "Technical term",
            "status": "applied",
        }
    ]
    segments = [{"id": 1, "start": 12.0, "text": "Memcatch is used."}]
    csv_str = generate_corrections_csv(corrections, segments)
    reader = list(csv.reader(io.StringIO(csv_str)))
    assert reader[0] == ["segment_id", "time", "original", "corrected", "reason", "status"]
    assert reader[1] == ["1", "00:12", "Memcatch", "Memcached", "Technical term", "applied"]


def test_render_meeting_record_and_parity():
    record = {
        "title": "Cache Architecture",
        "source_file": "meeting.mp3",
        "generated_at": "2026-10-06T12:00:00Z",
        "summary": "Team agreed to migrate cache to Redis.",
        "attendees": ["Maya", "Dan"],
        "minutes": [
            {
                "title": "Caching",
                "points": [{"text": "Discussed Memcached latency.", "segment_ids": [1]}],
            }
        ],
        "decisions": [
            {
                "id": "D1",
                "text": "Migrate session cache from Memcached to Redis",
                "rationale": "Better latency",
                "segment_ids": [1],
            },
            {
                "id": "D2",
                "text": "Do not upgrade PostgreSQL to version 16 this quarter",
                "rationale": None,
                "segment_ids": [2],
            },
        ],
        "unresolved": [
            {
                "id": "U1",
                "kind": "deferred",
                "text": "Move services to gRPC",
                "segment_ids": [3],
            }
        ],
        "action_items": [
            {
                "id": "T1",
                "task": "Write Terraform module for Redis",
                "owner": "Dan",
                "deadline": "by Thursday",
                "segment_ids": [4],
            },
            {
                "id": "T2",
                "task": "Update documentation",
                "owner": None,  # Must render as Unspecified
                "deadline": None,  # Must render as Unspecified
                "segment_ids": [5],
            },
        ],
        "models": {"stt": "whisper", "refiner": "qwen", "documenter": "gemma"},
    }
    meta = {"filename": "meeting.mp3", "duration": 115.5}
    segments = [
        {"id": 1, "start": 10.0, "text": "..."},
        {"id": 2, "start": 20.0, "text": "..."},
        {"id": 3, "start": 30.0, "text": "..."},
        {"id": 4, "start": 40.0, "text": "..."},
        {"id": 5, "start": 50.0, "text": "..."},
    ]

    md_text = render_meeting_record_md(record, meta, segments)

    # Check unassigned / unspecified rendering
    assert "Unspecified" in md_text
    assert "Dan" in md_text
    assert "by Thursday" in md_text

    # Verify parity
    parity = verify_parity(record, md_text)
    assert parity["ok"] is True
    assert parity["decisions"] == 2
    assert parity["tasks"] == 2


def test_empty_record_renders_empty_sentences():
    record = {
        "title": "Empty Meeting",
        "source_file": "empty.mp3",
        "generated_at": "2026-10-06T12:00:00Z",
        "summary": "Quick sync with no decisions.",
        "attendees": [],
        "minutes": [],
        "decisions": [],
        "unresolved": [],
        "action_items": [],
        "models": {"stt": "whisper", "refiner": "qwen", "documenter": "gemma"},
    }
    md = render_meeting_record_md(record, {})
    assert "None were agreed in this recording." in md
    assert "None were assigned in this recording." in md
    assert "None recorded." in md
    assert "None specified." in md


def test_export_all_run_files_bundle():
    run_id = create_run(filename="test_bundle.wav")
    run_dir = get_run_dir(run_id)

    raw_data = {
        "segments": [{"id": 1, "start": 0.0, "end": 2.0, "text": "Sample audio"}],
    }
    refined_data = {
        "segments": [{"id": 1, "start": 0.0, "end": 2.0, "text": "Sample audio"}],
        "corrections": [],
    }
    record_data = {
        "title": "Test Title",
        "summary": "Test Summary",
        "attendees": [],
        "minutes": [],
        "decisions": [{"id": "D1", "text": "Test Decision", "segment_ids": [1]}],
        "unresolved": [],
        "action_items": [{"id": "T1", "task": "Test Task", "owner": None, "deadline": None, "segment_ids": [1]}],
        "models": {"stt": "whisper", "refiner": "qwen", "documenter": "gemma"},
    }

    save_json(run_id, "raw_transcript.json", raw_data)
    save_json(run_id, "refined_transcript.json", refined_data)
    save_json(run_id, "meeting_record.json", record_data)
    save_meta(run_id, {"filename": "test_bundle.wav", "duration": 2.0})

    files = export_all_run_files(run_id)

    assert "raw_transcript.txt" in files
    assert "raw_transcript.srt" in files
    assert "refined_transcript.txt" in files
    assert "corrections.csv" in files
    assert "meeting_record.json" in files
    assert "meeting_record.md" in files
    assert "bundle.zip" in files

    # Verify bundle.zip is valid and contains all files
    p_zip = files["bundle.zip"]
    with zipfile.ZipFile(p_zip, "r") as zf:
        names = zf.namelist()
        assert "meeting_record.md" in names
        assert "meeting_record.json" in names
        assert "raw_transcript.srt" in names
