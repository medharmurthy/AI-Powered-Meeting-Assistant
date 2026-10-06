from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Literal
from fastapi import APIRouter, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from verbatim.config import find_repo_root, get_config
from verbatim.errors import make_app_error
from verbatim.export.exporter import ALLOWED_EXPORTS, export_all_run_files
from verbatim.jobs import jobs
from verbatim.refine.apply import apply
from verbatim.schemas import Correction, RefinedSegment, Span
from verbatim.store import (
    create_run,
    events_since,
    get_run_dir,
    load_json,
    load_meta,
    save_json,
    save_meta,
)

logger = logging.getLogger("verbatim.routes")

router = APIRouter(tags=["phase5"])


class PatchCorrectionRequest(BaseModel):
    applied: bool


class RerunRequest(BaseModel):
    from_stage: Literal["refine", "document"]


@router.get("/api/runs/{run_id}/events")
async def get_run_events(
    run_id: str,
    after: int = Query(0, ge=0),
    last_event_id: int | None = Header(None, alias="Last-Event-ID"),
):
    """
    Server-Sent Events (SSE) live event stream for run_id.
    Yields events since `after` (or Last-Event-ID). Closes on run.done or run.failed.
    """
    get_run_dir(run_id, must_exist=True)
    start_seq = last_event_id if last_event_id is not None else after

    async def event_generator():
        seq = start_seq
        idle_ticks = 0
        while True:
            evs = events_since(run_id, seq)
            for ev in evs:
                seq = ev["seq"]
                data_json = json.dumps(ev["data"])
                yield f"id: {seq}\nevent: {ev['type']}\ndata: {data_json}\n\n"
                if ev["type"] in ("run.done", "run.failed"):
                    return

            if not evs:
                idle_ticks += 1
                if idle_ticks % 60 == 0:  # ~15 seconds ping
                    yield ": ping\n\n"
            else:
                idle_ticks = 0

            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/runs/{run_id}/export/{name}")
async def download_export_file(run_id: str, name: str):
    """Download export files by name (from ALLOWED_EXPORTS whitelist)."""
    if name not in ALLOWED_EXPORTS:
        raise HTTPException(
            status_code=400,
            detail={"error": make_app_error("UNSUPPORTED_TYPE", detail=f"Export '{name}' is not in whitelist").model_dump()},
        )

    run_dir = get_run_dir(run_id, must_exist=True)
    target_path = run_dir / name

    # If file doesn't exist yet, trigger generation of export bundle
    if not target_path.exists():
        export_all_run_files(run_id)

    if not target_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": make_app_error("INTERNAL", detail=f"Export file '{name}' could not be generated").model_dump()},
        )

    # Determine media type
    if name.endswith(".zip"):
        media_type = "application/zip"
    elif name.endswith(".json"):
        media_type = "application/json"
    elif name.endswith(".csv"):
        media_type = "text/csv"
    elif name.endswith(".srt") or name.endswith(".txt"):
        media_type = "text/plain"
    elif name.endswith(".md"):
        media_type = "text/markdown"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        str(target_path),
        media_type=media_type,
        filename=name,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/api/runs/sample", status_code=status.HTTP_202_ACCEPTED)
async def create_sample_run():
    """Run real pipeline on samples/sample_meeting.mp3."""
    root = find_repo_root()
    sample_mp3 = root / "samples" / "sample_meeting.mp3"
    if not sample_mp3.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": make_app_error("INTERNAL", detail="Sample file sample_meeting.mp3 not found").model_dump()},
        )

    run_id = create_run(filename="sample_meeting.mp3")
    run_dir = get_run_dir(run_id)
    dest = run_dir / "original.mp3"
    shutil.copy2(sample_mp3, dest)

    save_meta(
        run_id,
        {
            "participants": ["Maya", "Priya", "Dan"],
            "glossary": [],
            "filename": "sample_meeting.mp3",
        },
    )

    # Submit job starting from ingest
    jobs.submit(run_id, from_stage="ingest")
    return {"run_id": run_id}


@router.patch("/api/runs/{run_id}/corrections/{cid}")
async def patch_correction(run_id: str, cid: str, body: PatchCorrectionRequest):
    """Toggle a correction applied/reverted and re-apply spans on refined text."""
    get_run_dir(run_id, must_exist=True)
    refined_data = load_json(run_id, "refined_transcript.json")
    if not refined_data:
        raise HTTPException(status_code=404, detail="Refined transcript not found")

    corrections_raw = refined_data.get("corrections", [])
    target_corr = None
    for c in corrections_raw:
        if c.get("id") == cid:
            target_corr = c
            break

    if not target_corr:
        raise HTTPException(status_code=404, detail=f"Correction '{cid}' not found")

    new_status = "applied" if body.applied else "reverted"
    target_corr["status"] = new_status

    # Re-apply corrections to segments
    raw_data = load_json(run_id, "raw_transcript.json") or {}
    raw_by_id = {s["id"]: s["text"] for s in raw_data.get("segments", [])}

    parsed_corrections = [Correction(**c) for c in corrections_raw]
    corrs_by_seg: dict[int, list[Correction]] = {}
    for c in parsed_corrections:
        corrs_by_seg.setdefault(c.segment_id, []).append(c)

    new_refined_segments = []
    for s_dict in refined_data.get("segments", []):
        sid = s_dict["id"]
        raw_text = raw_by_id.get(sid, s_dict.get("text", ""))
        seg_corrs = corrs_by_seg.get(sid, [])
        applied_corrs = [c for c in seg_corrs if c.status == "applied"]
        refined_text, spans = apply(raw_text, applied_corrs)
        new_refined_segments.append({
            "id": sid,
            "start": s_dict.get("start", 0.0),
            "end": s_dict.get("end", 0.0),
            "text": refined_text,
            "spans": [sp.model_dump() for sp in spans],
        })

    refined_data["segments"] = new_refined_segments
    refined_data["corrections"] = corrections_raw
    save_json(run_id, "refined_transcript.json", refined_data)

    # Set record_stale = True in metadata
    meta = load_meta(run_id) or {}
    meta["record_stale"] = True
    save_meta(run_id, meta)

    return {"status": "ok", "record_stale": True}


@router.post("/api/runs/{run_id}/rerun", status_code=status.HTTP_202_ACCEPTED)
async def rerun_stage(run_id: str, body: RerunRequest):
    """Rerun pipeline starting from refine or document stage."""
    get_run_dir(run_id, must_exist=True)
    meta = load_meta(run_id) or {}
    meta["record_stale"] = False
    save_meta(run_id, meta)

    jobs.submit(run_id, from_stage=body.from_stage)
    return {"run_id": run_id}


def attach_phase5_routes(app: FastAPI) -> None:
    """Attach Phase 5 routes to an existing FastAPI app instance and auto-enqueue POST /api/runs."""
    # Check if already attached
    for route in app.routes:
        if getattr(route, "path", None) == "/api/runs/sample":
            return

    # In Starlette, routes are evaluated in registration order.
    # Move the catch-all SPA fallback route to the very end so /api/... routes match first.
    spa_route = None
    for i, r in enumerate(app.routes):
        if getattr(r, "path", None) == "/{full_path:path}":
            spa_route = app.routes.pop(i)
            break

    app.include_router(router)

    if spa_route is not None:
        app.routes.append(spa_route)

    # Wrap POST /api/runs route to submit job to worker after ingestion
    for route in app.routes:
        if getattr(route, "path", None) == "/api/runs" and "POST" in getattr(route, "methods", set()):
            original_endpoint = route.endpoint

            async def wrapped_post_runs(*args, **kwargs):
                res = await original_endpoint(*args, **kwargs)
                if isinstance(res, dict) and "run_id" in res:
                    jobs.submit(res["run_id"], from_stage="transcribe")
                return res

            route.endpoint = wrapped_post_runs
            break

    logger.info("Phase 5 API routes and background worker auto-trigger attached successfully.")
