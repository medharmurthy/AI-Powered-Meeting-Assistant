from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path
import re
import zipfile
import jinja2

from verbatim.config import find_repo_root
from verbatim.errors import PipelineError
from verbatim.store import get_run_dir, load_json, load_meta

logger = logging.getLogger("verbatim.export")

ALLOWED_EXPORTS = {
    "raw_transcript.txt",
    "raw_transcript.srt",
    "raw_transcript.json",
    "refined_transcript.txt",
    "refined_transcript.json",
    "corrections.csv",
    "meeting_record.json",
    "meeting_record.md",
    "bundle.zip",
}


def format_srt_time(seconds: float) -> str:
    """Format seconds into standard SRT timestamp HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    s = total_sec % 60
    total_min = total_sec // 60
    m = total_min % 60
    h = total_min // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_clock_time(seconds: float) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    if seconds < 0:
        seconds = 0.0
    total_sec = int(round(seconds))
    s = total_sec % 60
    total_min = total_sec // 60
    m = total_min % 60
    h = total_min // 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_duration_str(seconds: float | None) -> str:
    """Format total duration into human-readable minutes string (e.g. '04:52')."""
    if seconds is None or seconds <= 0:
        return "00:00"
    return format_clock_time(seconds)


def generate_raw_transcript_txt(segments: list[dict]) -> str:
    """Generate raw_transcript.txt with [MM:SS] text."""
    lines = []
    for s in segments:
        t = format_clock_time(s.get("start", 0.0))
        txt = s.get("text", "").strip()
        lines.append(f"[{t}] {txt}")
    return "\n".join(lines) + ("\n" if lines else "")


def generate_raw_transcript_srt(segments: list[dict]) -> str:
    """Generate raw_transcript.srt subtitle file."""
    blocks = []
    for i, s in enumerate(segments, start=1):
        start_srt = format_srt_time(s.get("start", 0.0))
        end_srt = format_srt_time(s.get("end", 0.0))
        txt = s.get("text", "").strip()
        blocks.append(f"{i}\n{start_srt} --> {end_srt}\n{txt}\n")
    return "\n".join(blocks)


def generate_refined_transcript_txt(segments: list[dict], raw_segments: list[dict] | None = None) -> str:
    """Generate refined_transcript.txt with [MM:SS] text."""
    time_map = {}
    if raw_segments:
        for s in raw_segments:
            time_map[s.get("id")] = s.get("start", 0.0)

    lines = []
    for s in segments:
        sid = s.get("id")
        start_time = s.get("start")
        if start_time is None:
            start_time = time_map.get(sid, 0.0)
        t = format_clock_time(start_time)
        txt = s.get("text", "").strip()
        lines.append(f"[{t}] {txt}")
    return "\n".join(lines) + ("\n" if lines else "")


def generate_corrections_csv(corrections: list[dict], segments: list[dict] | None = None) -> str:
    """Generate corrections.csv: segment_id,time,original,corrected,reason,status."""
    time_map = {}
    if segments:
        for s in segments:
            time_map[s.get("id")] = format_clock_time(s.get("start", 0.0))

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["segment_id", "time", "original", "corrected", "reason", "status"])

    for c in corrections:
        sid = c.get("segment_id", "")
        t_str = time_map.get(sid, "")
        writer.writerow([
            sid,
            t_str,
            c.get("original", ""),
            c.get("corrected", ""),
            c.get("reason", ""),
            c.get("status", "applied"),
        ])
    return output.getvalue()


def render_meeting_record_md(
    record: dict,
    meta: dict,
    segments: list[dict] | None = None,
) -> str:
    """Render meeting_record.md using the Jinja2 template."""
    template_path = Path(__file__).resolve().parent / "templates" / "meeting_record.md.j2"
    with open(template_path, "r", encoding="utf-8") as f:
        template = jinja2.Template(f.read())

    time_map = {}
    if segments:
        for s in segments:
            time_map[s.get("id")] = format_clock_time(s.get("start", 0.0))

    def get_time_for_sids(sids: list[int] | None) -> str:
        if not sids:
            return ""
        first_sid = sids[0]
        return time_map.get(first_sid, "")

    # Decorate minutes points with formatted time
    minutes_data = []
    for topic in record.get("minutes", []):
        pts = []
        for p in topic.get("points", []):
            pts.append({
                "text": p.get("text", ""),
                "time": get_time_for_sids(p.get("segment_ids")),
            })
        minutes_data.append({
            "title": topic.get("title", ""),
            "points": pts,
        })

    # Decorate decisions with formatted time
    decisions_data = []
    for d in record.get("decisions", []):
        decisions_data.append({
            "id": d.get("id", ""),
            "text": d.get("text", ""),
            "rationale": d.get("rationale"),
            "time": get_time_for_sids(d.get("segment_ids")),
        })

    # Decorate unresolved with formatted time
    unresolved_data = []
    for u in record.get("unresolved", []):
        unresolved_data.append({
            "id": u.get("id", ""),
            "kind": u.get("kind", ""),
            "text": u.get("text", ""),
            "time": get_time_for_sids(u.get("segment_ids")),
        })

    # Decorate action items with formatted time
    actions_data = []
    for a in record.get("action_items", []):
        actions_data.append({
            "id": a.get("id", ""),
            "task": a.get("task", ""),
            "owner": a.get("owner") or "Unspecified",
            "deadline": a.get("deadline") or "Unspecified",
            "time": get_time_for_sids(a.get("segment_ids")),
        })

    duration_val = meta.get("duration") or record.get("duration")
    duration_str = format_duration_str(duration_val)

    context = {
        "title": record.get("title", "Meeting Record"),
        "source_file": record.get("source_file") or meta.get("filename", "recording.wav"),
        "date": record.get("generated_at", "")[:10] if record.get("generated_at") else meta.get("created_at", "")[:10],
        "duration": duration_str,
        "summary": record.get("summary", ""),
        "attendees": record.get("attendees", []),
        "minutes": minutes_data,
        "decisions": decisions_data,
        "unresolved": unresolved_data,
        "action_items": actions_data,
        "models": record.get("models", {"stt": "whisper", "refiner": "qwen", "documenter": "gemma"}),
        "generated_at": record.get("generated_at", ""),
    }

    return template.render(**context)


def verify_parity(record: dict, md_text: str) -> dict:
    r"""
    Verify parity between JSON MeetingRecord and Markdown output:
    - parse ^- \*\*D(\d+)\.\*\* (.*?) \[(?:mm:ss)\] lines
    - parse ^\| T(\d+) \| (.*?) \| (.*?) \| (.*?) \| rows from the Action items table
    Assert same IDs and text.
    Returns: {"decisions": int, "tasks": int, "ok": bool}
    """
    json_decisions = {d["id"]: d["text"].strip() for d in record.get("decisions", [])}
    json_tasks = {a["id"]: a["task"].strip() for a in record.get("action_items", [])}

    # Extract decisions from Markdown
    # Matches: - **D1.** Some decision text [01:05] OR - **D1.** Some decision text
    md_decisions = {}
    for line in md_text.splitlines():
        m = re.match(r"^-\s+\*\*(D\d+)\.\*\*\s+(.*?)(?:\s+\[\d{2}:\d{2}\])?$", line.strip())
        if m:
            md_decisions[m.group(1)] = m.group(2).strip()

    # Extract tasks from Markdown table
    md_tasks = {}
    for line in md_text.splitlines():
        m = re.match(r"^\|\s+(T\d+)\s+\|\s+(.*?)\s+\|\s+(.*?)\s+\|\s+(.*?)\s+\|\s+\[.*?\]\s+\|$", line.strip())
        if m:
            # Unescape pipe character
            task_clean = m.group(2).replace(r"\|", "|").strip()
            md_tasks[m.group(1)] = task_clean

    decisions_ok = (len(json_decisions) == len(md_decisions)) and all(
        json_decisions.get(k) == v for k, v in md_decisions.items()
    )
    tasks_ok = (len(json_tasks) == len(md_tasks)) and all(
        json_tasks.get(k) == v for k, v in md_tasks.items()
    )

    all_ok = decisions_ok and tasks_ok
    return {
        "decisions": len(json_decisions),
        "tasks": len(json_tasks),
        "ok": all_ok,
    }


def export_all_run_files(run_id: str) -> dict[str, Path]:
    """
    Derive and write all 8 export files plus bundle.zip in the run directory.
    Returns mapping of filename -> absolute Path.
    """
    run_dir = get_run_dir(run_id, must_exist=True)
    meta = load_meta(run_id) or {}

    raw_data = load_json(run_id, "raw_transcript.json") or {"segments": []}
    refined_data = load_json(run_id, "refined_transcript.json") or {"segments": [], "corrections": []}
    record_data = load_json(run_id, "meeting_record.json") or {}

    raw_segments = raw_data.get("segments", [])
    refined_segments = refined_data.get("segments", [])
    corrections = refined_data.get("corrections", [])

    created_files: dict[str, Path] = {}

    # 1. raw_transcript.txt
    raw_txt = generate_raw_transcript_txt(raw_segments)
    p_raw_txt = run_dir / "raw_transcript.txt"
    p_raw_txt.write_text(raw_txt, encoding="utf-8")
    created_files["raw_transcript.txt"] = p_raw_txt

    # 2. raw_transcript.srt
    raw_srt = generate_raw_transcript_srt(raw_segments)
    p_raw_srt = run_dir / "raw_transcript.srt"
    p_raw_srt.write_text(raw_srt, encoding="utf-8")
    created_files["raw_transcript.srt"] = p_raw_srt

    # 3. raw_transcript.json
    p_raw_json = run_dir / "raw_transcript.json"
    if not p_raw_json.exists():
        p_raw_json.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
    created_files["raw_transcript.json"] = p_raw_json

    # 4. refined_transcript.txt
    ref_txt = generate_refined_transcript_txt(refined_segments, raw_segments)
    p_ref_txt = run_dir / "refined_transcript.txt"
    p_ref_txt.write_text(ref_txt, encoding="utf-8")
    created_files["refined_transcript.txt"] = p_ref_txt

    # 5. refined_transcript.json
    p_ref_json = run_dir / "refined_transcript.json"
    if not p_ref_json.exists():
        p_ref_json.write_text(json.dumps(refined_data, indent=2), encoding="utf-8")
    created_files["refined_transcript.json"] = p_ref_json

    # 6. corrections.csv
    corr_csv = generate_corrections_csv(corrections, raw_segments)
    p_corr_csv = run_dir / "corrections.csv"
    p_corr_csv.write_text(corr_csv, encoding="utf-8")
    created_files["corrections.csv"] = p_corr_csv

    # 7. meeting_record.json
    p_rec_json = run_dir / "meeting_record.json"
    if not p_rec_json.exists():
        p_rec_json.write_text(json.dumps(record_data, indent=2), encoding="utf-8")
    created_files["meeting_record.json"] = p_rec_json

    # 8. meeting_record.md
    rec_md = render_meeting_record_md(record_data, meta, raw_segments)
    p_rec_md = run_dir / "meeting_record.md"
    p_rec_md.write_text(rec_md, encoding="utf-8")
    created_files["meeting_record.md"] = p_rec_md

    # Parity check assertion
    parity_result = verify_parity(record_data, rec_md)
    meta["export_parity"] = parity_result
    from verbatim.store import save_meta
    save_meta(run_id, meta)

    # 9. bundle.zip
    p_zip = run_dir / "bundle.zip"
    with zipfile.ZipFile(p_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in created_files.items():
            if path.exists():
                zf.write(path, arcname=name)
    created_files["bundle.zip"] = p_zip

    logger.info("Export bundle generated for run %s: parity=%s", run_id, parity_result)
    return created_files
