from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Header,
    Request,
    Response,
    UploadFile,
    status,
)
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from verbatim.config import get_config
from verbatim.errors import PipelineError, make_app_error
from verbatim.health import check_health
from verbatim.ingest import (
    process_audio_file,
    save_stream_to_file,
    validate_file_extension,
)
from verbatim.jobs import jobs
from verbatim.schemas import (
    AppError,
    HealthResponse,
    RunState,
    RunSummary,
)
from verbatim.store import (
    build_run_state,
    create_run,
    delete_run,
    get_run_dir,
    list_runs,
    load_json,
    save_meta,
)

logger = logging.getLogger("verbatim")


@asynccontextmanager
async def lifespan(app: FastAPI):
    jobs.check_and_recover_interrupted_runs()
    yield


app = FastAPI(
    title="Verbatim API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PipelineError)
async def pipeline_error_handler(request: Request, exc: PipelineError):
    code = exc.error.code
    if code in (
        "UNSUPPORTED_TYPE",
        "EMPTY_FILE",
        "UNREADABLE_FILE",
        "NO_AUDIO_STREAM",
        "TOO_SHORT",
        "TOO_LONG",
        "SILENT_AUDIO",
        "NO_SPEECH",
    ):
        status_code = status.HTTP_400_BAD_REQUEST
    elif code == "TOO_LARGE":
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif code in ("OLLAMA_UNREACHABLE", "MODEL_MISSING"):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif code == "LLM_TIMEOUT":
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content={"error": exc.error.model_dump()},
    )


@app.get("/api/health", response_model=HealthResponse)
async def get_health():
    return check_health()


@app.get("/api/runs", response_model=list[RunSummary])
async def get_runs():
    return list_runs()


@app.post("/api/runs", status_code=status.HTTP_202_ACCEPTED)
async def post_runs(
    file: UploadFile = File(...),
    glossary: str | None = Form(None),
    participants: str | None = Form(None),
):
    cfg = get_config()
    filename = file.filename or "recording.wav"

    # 1. Extension check
    ext = validate_file_extension(filename, cfg.limits.allowed_ext)

    # 2. Parse glossary & participants
    glossary_list: list[str] = []
    if glossary:
        try:
            parsed = json.loads(glossary)
            if isinstance(parsed, list):
                glossary_list = [str(x) for x in parsed]
        except Exception:
            glossary_list = [x.strip() for x in glossary.split(",") if x.strip()]

    participants_list: list[str] = []
    if participants:
        try:
            parsed = json.loads(participants)
            if isinstance(parsed, list):
                participants_list = [str(x) for x in parsed]
        except Exception:
            participants_list = [x.strip() for x in participants.split(",") if x.strip()]

    # 3. Create run directory
    run_id = create_run(filename=filename)
    run_dir = get_run_dir(run_id)
    save_meta(
        run_id,
        {
            "glossary": glossary_list,
            "participants": participants_list,
        },
    )

    # 4. Save upload stream to original.<ext>
    original_path = run_dir / f"original.{ext}"
    max_bytes = cfg.limits.max_upload_mb * 1024 * 1024
    save_stream_to_file(file.file, original_path, max_bytes=max_bytes)

    # 5. Process audio (decoding, duration, silence, peaks, audio.wav)
    process_audio_file(run_id, original_path)

    # 6. Submit job to background worker starting from transcribe stage
    jobs.submit(run_id, from_stage="transcribe")

    return {"run_id": run_id}


@app.get("/api/runs/{run_id}", response_model=RunState)
async def get_run_state_by_id(run_id: str):
    try:
        return build_run_state(run_id)
    except PipelineError as exc:
        raise HTTPException(status_code=404, detail=exc.error.model_dump())


@app.get("/api/runs/{run_id}/peaks")
async def get_run_peaks(run_id: str):
    data = load_json(run_id, "peaks.json")
    if not data:
        raise HTTPException(
            status_code=404,
            detail={"error": make_app_error("INTERNAL", detail="Peaks not found").model_dump()},
        )
    return data


@app.get("/api/runs/{run_id}/audio")
async def get_run_audio(run_id: str, range: str | None = Header(None)):
    run_dir = get_run_dir(run_id, must_exist=True)
    audio_path = run_dir / "audio.wav"
    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": make_app_error("INTERNAL", detail="Audio file not found").model_dump()},
        )

    file_size = audio_path.stat().st_size
    if not range:
        return FileResponse(
            str(audio_path),
            media_type="audio/wav",
            headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
        )

    match = re.match(r"bytes=(\d+)-(\d*)", range)
    if not match:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    start = int(match.group(1))
    end_str = match.group(2)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    chunk_size = end - start + 1
    with open(audio_path, "rb") as f:
        f.seek(start)
        data = f.read(chunk_size)

    return Response(
        content=data,
        status_code=206,
        media_type="audio/wav",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        },
    )


@app.delete("/api/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run_by_id(run_id: str):
    delete_run(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Static assets and SPA fallback
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists() and (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    # Placeholder while frontend is being built
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html>
<head><title>Verbatim</title></head>
<body style="font-family: sans-serif; padding: 2rem; background: #F3F5F7; color: #16222B;">
  <h1>Verbatim Backend API</h1>
  <p>The Verbatim backend is up and running.</p>
  <p>Interactive API documentation is available at <a href="/api/docs">/api/docs</a>.</p>
</body>
</html>"""
    )


# Attach Phase 5 routes (SSE, exports, samples, reruns, background workers)
from verbatim.routes import attach_phase5_routes
attach_phase5_routes(app)
