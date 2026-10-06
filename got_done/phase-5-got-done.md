# Phase 5 — Pipeline Orchestration, Jobs, API & Exports

## Status

**Phase 5 is complete, verified, and accepted.**

- **Test Suite Status**: **50 passed, 0 failed, 0 skipped, 0 errors** across all test suites (Phases 1 through 5).
- **Ground Truth Evaluation**: `eval/check_sample.py` passes **100%** of requirements from Section 9 of `plan.md`.
- **Integrity**: **Zero pre-existing files were modified**. All functionality was implemented purely through modular additions.
- **Checkpoint Reached**: **The complete Machine Learning meeting assistant requirement set now works end-to-end through a unified API, background job queue, and automated file exporter.**

---

## 1. What Was Implemented in Phase 5

### A. Pipeline Orchestration Subsystem (`backend/verbatim/pipeline.py`)
Implemented `pipeline.run_pipeline(run_id, from_stage="ingest")`:
* **Linear Stage Flow**: `ingest` $\rightarrow$ `transcribe` $\rightarrow$ `refine` $\rightarrow$ `document` $\rightarrow$ `export`.
* **Resumable Execution**: Supports `from_stage` (`"ingest"`, `"transcribe"`, `"refine"`, `"document"`, `"export"`). When a user toggles a correction, the system can rerun starting strictly from `"document"` or `"refine"` without re-transcribing audio.
* **Live Event Broadcasting**: Emits `run.started`, `stage.started`, `stage.progress`, `audio.ready`, `transcript.segment`, `stage.done`, and terminal events (`run.done` or `run.failed`).
* **Error Resilience**: Catches `PipelineError` $\rightarrow$ emits structured `run.failed` event and marks run metadata as `"failed"`. Catches unexpected exceptions and converts them to actionable `INTERNAL` errors without crashing the server.

### B. Background Job Manager (`backend/verbatim/jobs.py`)
Implemented `JobManager` singleton with single-worker execution:
* **Hardware Protection**: Uses `ThreadPoolExecutor(max_workers=1)` to guarantee serial GPU access, preventing VRAM overflow.
* **Queue Management**: Tracks active and queued runs; emits `run.queued{position}` and assigns sequential positions.
* **Server Restart Recovery**: On startup, scans existing runs and marks any run left in `"running"` status as interrupted with a retryable `AppError("INTERNAL", "Interrupted by a server restart")`.

### C. Export Subsystem (`backend/verbatim/export/`)
Implemented full export generation under `backend/verbatim/export/`:
```text
backend/verbatim/export/
├── __init__.py
├── exporter.py
└── templates/
    └── meeting_record.md.j2
```
* **8 Export Deliverables Generated**:
  1. `raw_transcript.txt`: Formatted lines with `[MM:SS]` timestamps.
  2. `raw_transcript.srt`: Standard SRT subtitle track with sub-millisecond timestamps.
  3. `raw_transcript.json`: Full raw transcript schema with words and timestamps.
  4. `refined_transcript.txt`: Cleaned transcript with timestamps.
  5. `refined_transcript.json`: Refined transcript schema with diff spans and applied corrections.
  6. `corrections.csv`: Structured CSV table (`segment_id,time,original,corrected,reason,status`).
  7. `meeting_record.json`: Complete machine-readable record (decisions, unresolved, action items, minutes).
  8. `meeting_record.md`: Human-readable formatted report rendered via Jinja2 template.
  9. `bundle.zip`: Compressed archive packaging all 8 export files.
* **Parity Verification (`verify_parity`)**: Parses decision bullet points and task markdown table rows directly from the rendered markdown, asserting strict 1-to-1 parity in count, IDs, and text against `meeting_record.json`.

### D. Phase 5 REST API & SSE Streaming (`backend/verbatim/routes.py` & `app.py`)
* `GET /api/runs/{id}/events`: Server-Sent Events (SSE) live stream with `?after=N` and `Last-Event-ID` support. Emits `: ping` keep-alive every ~15s; cleanly terminates on `run.done` or `run.failed`.
* `GET /api/runs/{id}/export/{name}`: Whitelisted secure download endpoint for all export files and `bundle.zip`.
* `POST /api/runs/sample`: Triggers full end-to-end execution on `samples/sample_meeting.mp3` and returns `202 {"run_id": ...}`.
* `PATCH /api/runs/{id}/corrections/{cid}`: Toggles correction status between `applied` and `reverted`, re-applies non-overlapping spans, and flags `record_stale: true`.
* `POST /api/runs/{id}/rerun`: Submits rerun job starting from `"refine"` or `"document"` with `202 Accepted`.
* `app.py`: Clean application entrypoint registering Phase 5 endpoints dynamically before SPA catch-all routing without touching `main.py`.

---

## 2. Test Suite & Verification Results

### A. Combined Test Execution (50 tests)
Command: `pytest tests/ -v`
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\AIMLProjects\bootcamp\AI-Powered-Meeting-Assistant-main
configfile: pyproject.toml
plugins: anyio-4.15.1
collected 50 items

tests/test_api.py::test_upload_invalid_files_returns_app_error PASSED    [  2%]
tests/test_api.py::test_sample_endpoint_returns_202 PASSED               [  4%]
tests/test_api.py::test_export_endpoints PASSED                          [  6%]
tests/test_api.py::test_sse_events_replay_after_param PASSED             [  8%]
tests/test_api.py::test_patch_correction_and_rerun PASSED                [ 10%]
tests/test_apply.py::test_apply_zero_corrections PASSED                  [ 12%]
tests/test_apply.py::test_apply_one_correction PASSED                    [ 14%]
tests/test_apply.py::test_apply_two_non_overlapping_corrections PASSED   [ 16%]
tests/test_apply.py::test_apply_overlapping_corrections PASSED           [ 18%]
tests/test_apply.py::test_apply_case_insensitive_fallback PASSED         [ 20%]
tests/test_apply.py::test_propagation_across_segments PASSED             [ 22%]
tests/test_apply.py::test_refine_transcript_stage_end_to_end PASSED      [ 24%]
tests/test_document.py::test_document_meeting_pipeline_flow PASSED       [ 26%]
tests/test_exporter.py::test_srt_and_txt_generation PASSED               [ 28%]
tests/test_exporter.py::test_corrections_csv_generation PASSED           [ 30%]
tests/test_exporter.py::test_render_meeting_record_and_parity PASSED     [ 32%]
tests/test_exporter.py::test_empty_record_renders_empty_sentences PASSED [ 34%]
tests/test_exporter.py::test_export_all_run_files_bundle PASSED          [ 36%]
tests/test_grounding.py::test_crude_stem_and_tokens PASSED               [ 38%]
tests/test_grounding.py::test_generic_owner_demoted PASSED               [ 40%]
tests/test_grounding.py::test_hallucinated_owner_demoted PASSED          [ 42%]
tests/test_grounding.py::test_valid_owner_accepted PASSED                [ 44%]
tests/test_grounding.py::test_hallucinated_deadline_demoted PASSED       [ 46%]
tests/test_grounding.py::test_valid_deadline_preserved_verbatim PASSED   [ 48%]
tests/test_grounding.py::test_support_threshold_filter PASSED            [ 50%]
tests/test_grounding.py::test_deduplicate_items PASSED                   [ 52%]
tests/test_grounding.py::test_validate_quote PASSED                      [ 54%]
tests/test_guardrails.py::test_rule_1_segment_existence_and_editable_window PASSED [ 56%]
tests/test_guardrails.py::test_rule_2_original_verbatim_presence PASSED  [ 58%]
tests/test_guardrails.py::test_rule_3_edit_size_and_identity PASSED      [ 60%]
tests/test_guardrails.py::test_rule_4_number_invariance PASSED           [ 62%]
tests/test_guardrails.py::test_rule_5_negation_invariance PASSED         [ 64%]
tests/test_guardrails.py::test_rule_6_commitment_words_invariance PASSED [ 66%]
tests/test_guardrails.py::test_rule_7_participant_names_preservation PASSED [ 68%]
tests/test_guardrails.py::test_valid_technical_proposals_pass PASSED     [ 70%]
tests/test_hints.py::test_hints_post_gress_ql_to_postgresql PASSED       [ 72%]
tests/test_hints.py::test_hints_cooper_netties_to_kubernetes PASSED      [ 74%]
tests/test_hints.py::test_hints_memcatch_to_memcached PASSED             [ 76%]
tests/test_hints.py::test_hints_excludes_exact_matches PASSED            [ 78%]
tests/test_hints.py::test_hint_object_properties_and_access PASSED       [ 80%]
tests/test_ingest.py::test_unsupported_type PASSED                       [ 82%]
tests/test_ingest.py::test_empty_file PASSED                             [ 84%]
tests/test_ingest.py::test_unreadable_file PASSED                        [ 86%]
tests/test_ingest.py::test_silent_audio PASSED                           [ 88%]
tests/test_ingest.py::test_valid_tone_audio PASSED                       [ 90%]
tests/test_ingest.py::test_health_endpoint PASSED                        [ 92%]
tests/test_stt.py::test_build_prompt PASSED                              [ 94%]
tests/test_stt.py::test_format_time PASSED                               [ 96%]
tests/test_stt.py::test_collapse_repeated_runs PASSED                    [ 98%]
tests/test_stt.py::test_no_speech_detection PASSED                       [100%]

======================= 50 passed, 1 warning in 17.77s ========================
```
**Result: 50 passed, 0 failed, 0 skipped, 0 errors.**

### B. Ground-Truth Evaluation (`eval/check_sample.py`)
```text
=======================================================
Verifying Run: 20261006-091847-txoz
=======================================================

--- Decisions Check ---
  [PASS] Decision present: 'Migrate the session cache from Memcached to Redis'
  [PASS] Decision present: 'Do not upgrade PostgreSQL to version 16 this quarter'
  [PASS] Forbidden decision omitted from decisions: 'gRPC'
  [PASS] Forbidden decision omitted from decisions: 'Kafka'
  [PASS] Forbidden decision omitted from decisions: 'Grafana'

--- Unresolved / Discussed Not Settled Check ---
  [PASS] Item present in unresolved: 'grpc'
  [PASS] Item present in unresolved: 'grafana'

--- Action Items Check ---
  [PASS] Task 'terraform': Owner correctly assigned as 'Dan'
  [PASS] Task 'terraform': Deadline verbatim as 'by Thursday'
  [PASS] Task 'oauth': Owner correctly assigned as 'Priya'
  [PASS] Task 'oauth': Deadline correctly Unspecified (null)
  [PASS] Task 'credentials': Owner correctly Unspecified (null)
  [PASS] Task 'credentials': Deadline verbatim as 'before the audit on the 15th'
  [PASS] Non-task 'Grafana' correctly excluded from action items

-------------------------------------------------------
RESULT: ALL GROUND TRUTH CHECKS PASSED!
-------------------------------------------------------
```

---

## 3. Handoff for Phase 6 (Frontend Foundation)

With Phase 5 complete, **the entire backend and ML pipeline is finished, tested, and callable via REST and SSE**.

The next team member can now begin **Phase 6: Frontend Foundation**:
* **Scaffolding**: Vite + React 18 + TypeScript in `frontend/`.
* **Design Tokens & System**: Implement proofreading aesthetic (`tokens.css` with blue pencil `#2A44D4`, marker highlight `#FFD84A`, Literata serif for documents, Hanken Grotesk for interface).
* **API Client & SSE Listener**: Connect to `GET /api/runs/{id}/events` to receive real-time stage updates.
* **State Management**: `zustand` store (`runStore`) reducing events sequentially into live state.
