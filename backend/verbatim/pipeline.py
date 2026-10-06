from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any, Callable

from verbatim.config import get_config
from verbatim.document.stage import document_meeting
from verbatim.errors import PipelineError, make_app_error
from verbatim.export.exporter import export_all_run_files
from verbatim.ingest import process_audio_file
from verbatim.refine.stage import refine_transcript
from verbatim.store import (
    append_event,
    get_run_dir,
    load_meta,
    save_meta,
)
from verbatim.stt import transcribe_audio

logger = logging.getLogger("verbatim.pipeline")

STAGES = ["ingest", "transcribe", "refine", "document", "export"]


def run_pipeline(
    run_id: str,
    from_stage: str = "ingest",
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """
    Execute full Verbatim ML pipeline from `from_stage` through export:
    ingest -> transcribe -> refine -> document -> export.
    Emits stage.started, stage.done, progress, and terminal events (run.done / run.failed).
    """
    cfg = get_config()
    run_dir = get_run_dir(run_id, must_exist=True)
    meta = load_meta(run_id) or {}

    if from_stage not in STAGES:
        raise PipelineError(
            code="INTERNAL",
            detail=f"Invalid from_stage '{from_stage}'. Allowed: {STAGES}",
        )

    start_idx = STAGES.index(from_stage)
    stages_to_run = STAGES[start_idx:]

    models_info = {
        "stt": cfg.active_profile_config.stt.model,
        "refiner": cfg.active_profile_config.refiner.model,
        "documenter": cfg.active_profile_config.documenter.model,
    }

    meta["status"] = "running"
    meta["stage"] = from_stage
    meta["models"] = models_info
    save_meta(run_id, meta)

    append_event(
        run_id,
        "run.started",
        {
            "from_stage": from_stage,
            "models": models_info,
            "profile": cfg.active_profile,
        },
    )

    try:
        # 1. Stage: INGEST
        if "ingest" in stages_to_run:
            t0 = time.time()
            append_event(run_id, "stage.started", {"stage": "ingest"})
            meta["stage"] = "ingest"
            save_meta(run_id, meta)

            # Find original file
            original_files = list(run_dir.glob("original.*"))
            if not original_files:
                # If audio.wav already exists, reuse it
                if not (run_dir / "audio.wav").exists():
                    raise PipelineError(
                        code="UNREADABLE_FILE",
                        detail=f"No audio file found in run directory {run_id}",
                    )
            else:
                ingest_res = process_audio_file(run_id, original_files[0])
                append_event(
                    run_id,
                    "audio.ready",
                    {
                        "duration": ingest_res["duration"],
                        "audio_url": f"/api/runs/{run_id}/audio",
                        "peaks_url": f"/api/runs/{run_id}/peaks",
                    },
                )

            elapsed = time.time() - t0
            append_event(run_id, "stage.done", {"stage": "ingest", "seconds": round(elapsed, 2)})

        # 2. Stage: TRANSCRIBE
        if "transcribe" in stages_to_run:
            t0 = time.time()
            stt_model = cfg.active_profile_config.stt.model
            append_event(run_id, "stage.started", {"stage": "transcribe", "model": stt_model})
            meta["stage"] = "transcribe"
            save_meta(run_id, meta)

            def on_stt_progress(done_s: float, total_s: float, label: str):
                append_event(
                    run_id,
                    "stage.progress",
                    {"stage": "transcribe", "done": done_s, "total": total_s, "label": label},
                )

            raw_transcript = transcribe_audio(
                run_id=run_id,
                progress_callback=on_stt_progress,
            )

            # Broadcast transcribed segments for live UI streaming
            for seg in raw_transcript.segments:
                append_event(run_id, "transcript.segment", seg.model_dump())

            elapsed = time.time() - t0
            append_event(run_id, "stage.done", {"stage": "transcribe", "seconds": round(elapsed, 2)})

        # 3. Stage: REFINE
        if "refine" in stages_to_run:
            t0 = time.time()
            refiner_model = cfg.active_profile_config.refiner.model
            append_event(run_id, "stage.started", {"stage": "refine", "model": refiner_model})
            meta["stage"] = "refine"
            save_meta(run_id, meta)

            refined_transcript = refine_transcript(run_id=run_id)

            elapsed = time.time() - t0
            append_event(run_id, "stage.done", {"stage": "refine", "seconds": round(elapsed, 2)})

        # 4. Stage: DOCUMENT
        if "document" in stages_to_run:
            meta["stage"] = "document"
            save_meta(run_id, meta)

            # document_meeting emits stage.started and stage.done internally
            meeting_record = document_meeting(run_id=run_id)

        # 5. Stage: EXPORT
        if "export" in stages_to_run:
            t0 = time.time()
            append_event(run_id, "stage.started", {"stage": "export"})
            meta["stage"] = "export"
            save_meta(run_id, meta)

            export_all_run_files(run_id=run_id)

            elapsed = time.time() - t0
            append_event(run_id, "stage.done", {"stage": "export", "seconds": round(elapsed, 2)})

        # Terminal Success
        meta = load_meta(run_id) or {}
        meta["status"] = "done"
        meta["stage"] = None
        save_meta(run_id, meta)
        append_event(run_id, "run.done", {})
        logger.info("Pipeline completed successfully for run %s", run_id)

    except PipelineError as e:
        logger.error("Pipeline failed for run %s with PipelineError: %s", run_id, e)
        meta = load_meta(run_id) or {}
        meta["status"] = "failed"
        meta["error"] = e.error.model_dump()
        save_meta(run_id, meta)
        append_event(run_id, "run.failed", e.error.model_dump())
        raise

    except Exception as e:
        logger.exception("Unexpected exception in pipeline for run %s: %s", run_id, e)
        app_err = make_app_error("INTERNAL", detail=str(e), stage=meta.get("stage"))
        meta = load_meta(run_id) or {}
        meta["status"] = "failed"
        meta["error"] = app_err.model_dump()
        save_meta(run_id, meta)
        append_event(run_id, "run.failed", app_err.model_dump())
        raise PipelineError(code="INTERNAL", detail=str(e)) from e
