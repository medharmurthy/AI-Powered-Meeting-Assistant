from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import threading
from typing import Any

from verbatim.errors import make_app_error
from verbatim.pipeline import run_pipeline
from verbatim.store import (
    append_event,
    get_run_dir,
    list_runs,
    load_meta,
    save_meta,
)

logger = logging.getLogger("verbatim.jobs")


class JobManager:
    """Single-worker background job executor for serial GPU execution."""

    def __init__(self, max_workers: int = 1):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="verbatim-worker")
        self._lock = threading.Lock()
        self._active_run_id: str | None = None
        self._queued_run_ids: list[str] = []
        self._interrupted_cleaned = False

    def check_and_recover_interrupted_runs(self) -> None:
        """Scan existing runs on startup; mark any run left 'running' as interrupted."""
        with self._lock:
            if self._interrupted_cleaned:
                return
            self._interrupted_cleaned = True

        for summary in list_runs():
            meta = load_meta(summary.id)
            if meta and meta.get("status") == "running":
                logger.warning("Run %s was left in 'running' state; marking as interrupted", summary.id)
                app_err = make_app_error(
                    code="INTERNAL",
                    title="Processing interrupted",
                    detail="Interrupted by a server restart",
                    stage=meta.get("stage"),
                    retryable=True,
                )
                meta["status"] = "failed"
                meta["error"] = app_err.model_dump()
                save_meta(summary.id, meta)
                append_event(summary.id, "run.failed", app_err.model_dump())

    def get_queue_position(self, run_id: str) -> int | None:
        """Return position in queue (1-indexed), or None if not queued."""
        with self._lock:
            if run_id in self._queued_run_ids:
                return self._queued_run_ids.index(run_id) + 1
            return None

    def submit(self, run_id: str, from_stage: str = "ingest") -> None:
        """Enqueue run execution into the background single worker."""
        self.check_and_recover_interrupted_runs()

        with self._lock:
            self._queued_run_ids.append(run_id)
            pos = len(self._queued_run_ids)

        meta = load_meta(run_id) or {}
        meta["status"] = "queued"
        meta["queue_position"] = pos
        meta["stage"] = from_stage
        save_meta(run_id, meta)

        append_event(run_id, "run.queued", {"position": pos})
        logger.info("Enqueued run %s at position %d", run_id, pos)

        self._executor.submit(self._worker_entry, run_id, from_stage)

    def _worker_entry(self, run_id: str, from_stage: str) -> None:
        with self._lock:
            if run_id in self._queued_run_ids:
                self._queued_run_ids.remove(run_id)
            self._active_run_id = run_id

        logger.info("Starting processing for run %s from stage '%s'", run_id, from_stage)
        try:
            run_pipeline(run_id=run_id, from_stage=from_stage)
        except Exception as e:
            logger.error("Job execution failed for run %s: %s", run_id, e)
        finally:
            with self._lock:
                if self._active_run_id == run_id:
                    self._active_run_id = None


# Global job manager singleton
jobs = JobManager(max_workers=1)
