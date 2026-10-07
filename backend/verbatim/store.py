from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import string
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verbatim.config import find_repo_root
from verbatim.errors import PipelineError
from verbatim.schemas import (
    AppError,
    Correction,
    DomainProfile,
    RefinedSegment,
    RunState,
    RunSummary,
    Segment,
)

RUN_ID_REGEX = re.compile(r"^[0-9A-Za-z-]+$")


def get_runs_dir() -> Path:
    runs_dir = find_repo_root() / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


def generate_run_id() -> str:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(4))
    return f"{timestamp}-{suffix}"


def validate_run_id(run_id: str) -> str:
    if not run_id or not RUN_ID_REGEX.match(run_id):
        raise PipelineError(code="INTERNAL", detail=f"Invalid run ID: {run_id}")
    return run_id


def get_run_dir(run_id: str, must_exist: bool = False) -> Path:
    validate_run_id(run_id)
    path = get_runs_dir() / run_id
    if must_exist and not path.exists():
        raise PipelineError(code="INTERNAL", detail=f"Run directory not found: {run_id}")
    return path


def create_run(filename: str, fake: bool | None = None) -> str:
    run_id = generate_run_id()
    run_dir = get_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    if fake is None:
        fake = os.environ.get("VERBATIM_FAKE") == "1"

    meta = {
        "id": run_id,
        "filename": filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
        "stage": None,
        "duration": None,
        "title": None,
        "fake": bool(fake),
    }
    save_meta(run_id, meta)

    events_file = run_dir / "events.jsonl"
    events_file.touch(exist_ok=True)

    return run_id


def save_meta(run_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    run_dir = get_run_dir(run_id, must_exist=True)
    meta_path = run_dir / "meta.json"
    data: dict[str, Any] = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data.update(updates)
    temp_path = run_dir / "meta.json.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp_path.replace(meta_path)
    return data


def load_meta(run_id: str) -> dict[str, Any]:
    run_dir = get_run_dir(run_id, must_exist=True)
    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        return {}
    for attempt in range(5):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (PermissionError, json.JSONDecodeError):
            if attempt == 4:
                raise
            time.sleep(0.02 * (attempt + 1))
    return {}


def save_json(run_id: str, filename: str, data: Any) -> Path:
    run_dir = get_run_dir(run_id, must_exist=True)
    target = run_dir / filename
    temp = run_dir / f"{filename}.tmp"
    with open(temp, "w", encoding="utf-8") as f:
        if hasattr(data, "model_dump_json"):
            f.write(data.model_dump_json(indent=2))
        else:
            json.dump(data, f, indent=2)
    temp.replace(target)
    return target


def load_json(run_id: str, filename: str) -> Any | None:
    run_dir = get_run_dir(run_id, must_exist=True)
    target = run_dir / filename
    if not target.exists():
        return None
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def append_event(run_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    run_dir = get_run_dir(run_id, must_exist=True)
    events_path = run_dir / "events.jsonl"

    last_seq = 0
    if events_path.exists():
        try:
            with open(events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        ev = json.loads(line)
                        last_seq = max(last_seq, ev.get("seq", 0))
        except Exception:
            pass

    next_seq = last_seq + 1
    event_entry = {
        "seq": next_seq,
        "type": event_type,
        "data": data,
        "t": round(time.time(), 3),
    }

    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event_entry) + "\n")

    return event_entry


def events_since(run_id: str, after: int = 0) -> list[dict[str, Any]]:
    run_dir = get_run_dir(run_id, must_exist=True)
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return []

    results = []
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("seq", 0) > after:
                results.append(ev)
    return results


def list_runs() -> list[RunSummary]:
    runs_dir = get_runs_dir()
    summaries: list[RunSummary] = []
    if not runs_dir.exists():
        return summaries

    for child in runs_dir.iterdir():
        if child.is_dir() and RUN_ID_REGEX.match(child.name):
            meta_path = child / "meta.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        summaries.append(
                            RunSummary(
                                id=meta.get("id", child.name),
                                filename=meta.get("filename", "unknown"),
                                created_at=meta.get("created_at", ""),
                                duration=meta.get("duration"),
                                status=meta.get("status", "unknown"),
                                title=meta.get("title"),
                            )
                        )
                except Exception:
                    pass

    summaries.sort(key=lambda s: s.created_at or s.id, reverse=True)
    return summaries


def delete_run(run_id: str) -> None:
    run_dir = get_run_dir(run_id, must_exist=True)
    shutil.rmtree(run_dir, ignore_errors=True)


def build_run_state(run_id: str) -> RunState:
    meta = load_meta(run_id)
    run_dir = get_run_dir(run_id, must_exist=True)

    peaks_data = load_json(run_id, "peaks.json")
    peaks = peaks_data.get("peaks") if peaks_data else None
    duration = meta.get("duration") or (peaks_data.get("duration") if peaks_data else None)

    raw_data = load_json(run_id, "raw_transcript.json")
    raw_segments: list[Segment] = []
    if raw_data and "segments" in raw_data:
        raw_segments = [Segment(**s) for s in raw_data["segments"]]

    refined_data = load_json(run_id, "refined_transcript.json")
    refined_segments: list[RefinedSegment] | None = None
    corrections: list[Correction] = []
    profile: DomainProfile | None = None

    if refined_data:
        if "segments" in refined_data:
            refined_segments = [RefinedSegment(**s) for s in refined_data["segments"]]
        if "corrections" in refined_data:
            corrections = [Correction(**c) for c in refined_data["corrections"]]
        if "profile" in refined_data:
            profile = DomainProfile(**refined_data["profile"])

    record = load_json(run_id, "meeting_record.json") or {}

    audio_path = run_dir / "audio.wav"
    audio_url = f"/api/runs/{run_id}/audio" if audio_path.exists() else None

    error = None
    if meta.get("error"):
        error = AppError(**meta["error"])

    warnings = [AppError(**w) for w in meta.get("warnings", [])]

    return RunState(
        id=run_id,
        filename=meta.get("filename", "unknown"),
        fake=meta.get("fake", False),
        status=meta.get("status", "queued"),
        stage=meta.get("stage"),
        queuePosition=meta.get("queue_position"),
        duration=duration,
        audioUrl=audio_url,
        peaks=peaks,
        models=meta.get("models", {}),
        timings=meta.get("timings", {}),
        progress=meta.get("progress", {}),
        raw=raw_segments,
        refined=refined_segments,
        corrections=corrections,
        profile=profile,
        record=record,
        recordStale=meta.get("record_stale", False),
        warnings=warnings,
        error=error,
        exportParity=meta.get("export_parity"),
    )
