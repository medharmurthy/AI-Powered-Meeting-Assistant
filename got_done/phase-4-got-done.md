# Phase 4 — Documentation Stage & Task Extraction

## Status

**Phase 4 is complete, verified, and ready for Phase 5.**

- **Tests Passing**: **40 passed, 0 failed, 0 skipped, 0 errors** across all test suites (Phases 1–4).
- **Benchmark Evaluation**: `eval/check_sample.py` passes **100%** of ground-truth checks from Section 9 of `plan.md`.
- **Integrity**: **Zero existing files were modified**. All implementation was achieved by adding new modular files and prompt templates.

---

## 1. What Was Implemented in Phase 4

### A. Documentation Subsystem (`backend/verbatim/document/`)
Implemented the complete meeting secretary pipeline under `backend/verbatim/document/`:

```text
backend/verbatim/document/
├── __init__.py          # Exports document_meeting
├── schemas.py           # Structured output Pydantic schemas for LLM Calls 1–5
├── grounding.py         # Deterministic anti-hallucination filters & lexical support scoring
├── verify.py            # Call 5 LLM verification pass (agreed vs proposal, committed vs tentative)
├── stage.py             # 5-step orchestrated LLM calls + assembly into MeetingRecord
└── runner.py            # Standalone CLI runner (python -m verbatim.document.runner <run_id>)
```

### B. Prompt Templates (`prompts/`)
Added the 6 versioned Jinja2 prompt templates specified in Section 7 of `plan.md`:
* `prompts/doc_system.v1.md`: Shared secretary system prompt establishing rules (no background knowledge, cite `segment_ids`, preserve numbers/negations, concise sentences). Shared across calls for Ollama KV-caching.
* `prompts/doc_summary.v1.md`: Call 1 prompt extracting title (<= 10 words), summary (3–5 sentences), and attendee names.
* `prompts/doc_minutes.v1.md`: Call 2 prompt organizing discussion into 3–7 chronological topics with concise bullet points and cited segment IDs.
* `prompts/doc_decisions.v1.md`: Call 3 prompt separating agreed decisions from unresolved discussions (`proposal`, `question`, `deferred`).
* `prompts/doc_actions.v1.md`: Call 4 prompt extracting committed tasks (with verbatim owner and deadline) vs `possible_tasks`.
* `prompts/doc_verify.v1.md`: Call 5 self-check prompt verifying candidate items against cited lines $\pm 2$.

### C. Grounding & Anti-Hallucination Guardrails (`document/grounding.py`)
Deterministic checks applied before accepting items into the record:
1. **Segment ID Validation**: All cited IDs must exist in the transcript; items citing non-existent IDs are logged to `dropped` and filtered out.
2. **Lexical Support Scoring**:
   $$\text{tokens} = \text{lowercase content words} \ge 3 \text{ chars, stopwords stripped, crudely stemmed}$$
   $$\text{support} = \frac{|\text{tokens}(\text{item}) \cap \text{tokens}(\text{cited lines} \pm 1)|}{|\text{tokens}(\text{item})|}$$
   Items with $\text{support} < 0.4$ (`config.document.support_threshold`) are dropped with reason logged to `dropped`.
3. **Owner Validation & Pronoun Demotion**:
   * Generic pronouns and roles (`"we"`, `"us"`, `"team"`, `"someone"`, `"everybody"`, `"SPEAKER_nn"`) are stripped $\rightarrow$ owner set to `None` (`Unspecified`).
   * Owner must appear within $\pm 4$ lines (`owner_window`) of cited lines or in the explicit `participants` list. If not, owner is stripped $\rightarrow$ `None` and logged to `dropped`.
4. **Deadline Verbatim Preservation**:
   * Content tokens of the deadline must appear in cited lines $\pm 2$ (`deadline_window`). If absent, set to `None`.
   * Spoken deadlines (e.g. `"by Thursday"`, `"before the audit on the 15th"`) are kept verbatim. Calendar dates are never guessed or converted.
5. **Quote Verification**: `rapidfuzz.fuzz.partial_ratio(quote, cited_text) >= 85`, else quote is nullified without dropping the item.
6. **Deduplication**: Items with `token_set_ratio >= 88` are merged, retaining the item citing more `segment_ids`.
7. **Stable Sequential ID Assignment**: Generates canonical IDs `D1, D2...`, `T1, T2...`, `U1, U2...`.

### D. Verification Pass (`document/verify.py`)
If `cfg.document.verify_pass` is enabled:
* Runs LLM Call 5 over all candidates.
* Demotes `proposal_only` decisions to `unresolved` (`kind="proposal"`).
* Demotes `tentative` actions to `unresolved` (`kind="possible_task"`).
* Drops `unsupported` items and clears unconfirmed owners/deadlines.

### E. Test Suite & Evaluation Tools
* `tests/test_grounding.py`: 9 unit tests for stemming, owner filters, deadline extraction, support threshold, deduplication, and quotes.
* `tests/test_document.py`: End-to-end integration test with `MockDocumenterLLM` validating event emission, schema assembly, disk persistence, and model unload.
* `samples/expected.json`: Canonical test matrix based on Section 9 of `plan.md`.
* `eval/check_sample.py`: CLI evaluation script testing meeting records against ground truth.

---

## 2. Verification Evidence

### A. Full Test Suite Execution
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\AIMLProjects\bootcamp\AI-Powered-Meeting-Assistant-main
configfile: pyproject.toml
plugins: anyio-4.15.1
collected 40 items

tests\test_apply.py .......                                              [ 17%]
tests\test_document.py .                                                 [ 20%]
tests\test_grounding.py .........                                        [ 42%]
tests\test_guardrails.py ........                                        [ 62%]
tests\test_hints.py .....                                                [ 75%]
tests\test_ingest.py ......                                              [ 90%]
tests\test_stt.py ....                                                   [100%]

======================== 40 passed, 1 warning in 6.96s ========================
```
**Result: 40 passed, 0 failed, 0 skipped, 0 errors.**

### B. Ground Truth Benchmark Results (`eval/check_sample.py`)
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

## 3. Important Notes for the Phase 5 Agent / Teammate

Phase 4 is complete, fully tested, and cleanly integrated.

### Phase 5 Scope: Pipeline Orchestrator, Jobs, API & Exports
The next agent (Person 3) should implement **Phase 5**:

1. **`backend/verbatim/pipeline.py`**:
   * Implement `pipeline.run(run_id, from_stage="ingest")`:
     `ingest` $\rightarrow$ `transcribe` $\rightarrow$ `refine` $\rightarrow$ `document` $\rightarrow$ `export`.
   * Emit `stage.started{stage, model}` and `stage.done{stage, seconds}` for each stage.
   * Catch `PipelineError` $\rightarrow$ emit `run.failed{error}` and update meta status.
   * Hook `document_meeting(run_id)` directly into the `document` stage of the pipeline.

2. **`backend/verbatim/jobs.py`**:
   * Single-worker queue (`ThreadPoolExecutor(max_workers=1)`).
   * Manage run states (`queued` with position $\rightarrow$ `running` $\rightarrow$ `done` / `failed`).
   * Maintain `events.jsonl` per run with monotonic sequence numbers (`seq`).

3. **Export Subsystem (`backend/verbatim/export/`)**:
   * `exporter.py`: Derive all export formats from `MeetingRecord` and `RefinedTranscript`:
     * `raw_transcript.txt` and `raw_transcript.srt`
     * `refined_transcript.txt` and `refined_transcript.json`
     * `corrections.csv`
     * `meeting_record.json`
     * `meeting_record.md` (rendered via Jinja2 template `templates/meeting_record.md.j2`)
     * `bundle.zip`
   * Implement `verify_parity(record, md_text)` to assert exact parity of decisions and tasks between Markdown and JSON.

4. **FastAPI Endpoints in `backend/verbatim/main.py`**:
   * `POST /api/runs`: File upload + validation $\rightarrow$ launch background job.
   * `POST /api/runs/sample`: Run real pipeline on `samples/sample_meeting.mp3`.
   * `GET /api/runs/{id}`: Returns `RunState`.
   * `GET /api/runs/{id}/events`: SSE stream for live updates.
   * `GET /api/runs/{id}/export/{name}`: Download export files.
   * `POST /api/runs/{id}/rerun`: Rerun from `"refine"` or `"document"`.

5. **Tests to add in Phase 5**:
   * `tests/test_exporter.py`: Verify export files and Markdown-JSON parity.
   * `tests/test_api.py`: Verify REST endpoints and SSE reconnection.

---

## 4. How to Run Phase 4 Standalone

To run Phase 4 on any existing run:
```bash
python -m verbatim.document.runner <run_id>
```

To evaluate the result:
```bash
python eval/check_sample.py runs/<run_id>
```
