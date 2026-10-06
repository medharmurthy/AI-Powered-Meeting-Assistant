# Phase 7 — Home and Live Workspace

## Status

**Phase 7 is complete, verified, and accepted.**

- **Backend Test Suite Status**: **52 passed, 0 failed, 0 skipped** across all backend test suites (`tests/`).
- **Frontend Test Suite Status**: **16 passed, 0 failed** in Vitest covering home components, preflight validation, record sections, unspecified pills, and evidence linking.
- **Production Build Status**: `npm run build` succeeds cleanly in ~300ms, outputting assets to `backend/verbatim/static/`.
- **E2E Integration Verification**: Full pipeline streaming, SSE reconnection, and SPA serving verified end-to-end with `VERBATIM_FAKE=1` (`tests/test_phase7_e2e.py`).

---

## 1. What Was Implemented in Phase 7

### A. Home Screen Components (`frontend/src/components/home/` & `pages/Home.tsx`)
* **`DropStage`**:
  * Drop target supporting `dragenter`, `dragover`, `dragleave`, `drop`, and keyboard triggers.
  * Flat tape of waveform bars that dynamically rise with staggered CSS `scaleY` transitions upon drag-over.
  * Preflight client-side validation that immediately blocks invalid files without network calls:
    * `UNSUPPORTED_TYPE`: Checks extension allow-list (`wav`, `mp3`, `m4a`, `aac`, `flac`, `ogg`, `opus`, `webm`, `mp4`, `mov`, `mkv`).
    * `EMPTY_FILE`: Blocks 0-byte files with catalogue fix "Choose a different file".
    * `TOO_LARGE`: Blocks files $> 500\text{ MB}$ with catalogue fix "Trim or compress the recording".
  * Selected file metadata display: filename, human-readable file size, audio duration (read via browser `<audio>` element metadata), and removal button.
* **`ChipInput`**:
  * Input for "Terms to listen for (optional)" and "Who's in the meeting (optional)".
  * Handles comma, Enter, Backspace deletion, and multi-token paste parsing with a 40-chip cap.
* **`HealthList`**:
  * Actionable warnings from `GET /api/health` displaying missing models or GPU fallback with a one-click copy button for commands (e.g. `ollama pull gemma3:12b`).
* **`RecentRuns`**:
  * Ruled list of recent recordings from `/api/runs` showing title, formatted duration (`MM:SS`), status, and date.
* **Action Buttons**:
  * **Process recording**: Disabled until a valid file is chosen; initiates `createRun` and routes directly to `/r/:id`.
  * **Try the sample recording**: Triggers `createSampleRun` (`/api/runs/sample`) and navigates immediately to `/r/:id`.

### B. Record Pane (`frontend/src/components/record/`)
* **`Unspecified`**:
  * Pill with dashed border and literal text **Unspecified** for missing owner or deadline fields.
* **`EvidenceChip`**:
  * Pill indicating citation time (e.g. `▶ 01:05` or `▶ 01:05 +1`).
  * Hover/focus soft highlights cited segments in the transcript pane via `focusStore`.
  * Clicking toggles pinned highlight and smoothly scrolls the transcript to the cited segment.
* **`SummarySection`**:
  * Renders meeting title, attendee pills, and summary in Literata serif (`font-doc`).
  * Displays quiet "Writing summary…" during processing.
* **`MinutesSection`**:
  * Chronological topic hierarchy with points and inline `EvidenceChip` citations.
* **`DecisionsSection`**:
  * Numbered decisions (D1, D2) with rationale in `--ink-soft` and quote excerpts.
  * Exact microcopy empty state: *"No decisions were agreed in this recording."*
* **`UnresolvedSection`**:
  * Items discussed but not settled with kind pills (`Proposal`, `Open question`, `Deferred`, `Possible task`).
* **`TasksSection`**:
  * Semantic `<table>` with columns: Task, Owner, Deadline, Source.
  * Strictly renders `<Unspecified />` for missing values, never empty cells.
  * Exact microcopy empty state: *"No tasks were assigned in this recording."*
* **`RecordNav`**:
  * Sticky section navigation bar with IntersectionObserver tracking the active section.
* **`RecordPane`**:
  * Complete sheet with header, source metadata, and dropped items popover for safety check removals.

### C. Transcript Pane (`frontend/src/components/transcript/`)
* **`SegmentRow`**:
  * 60px tabular time gutter, speaker tag (if present), and segment text in Literata font.
  * Shows subtle streaming caret on the newest line during transcription (without jarring fade-up animations).
  * Evidence highlight states: soft highlighter wash on hover, solid marker on pin.
* **`TranscriptPane`**:
  * Tab navigation for **Raw** (streaming lines), **Refined**, and **Compare**.
  * Search bar with `/` keyboard focus shortcut and `Esc` reset.
  * Auto-scrolls to newest segment as lines stream in during live processing.

### D. Reconnection & Mid-Run State Reconstruction
* `runStore.ts`:
  * Mid-run page refresh queries `/api/runs/{id}`. If the run is `queued` or `running`, it subscribes to `/api/runs/{id}/events?after=0` and sequentially reconstructs state using the pure `applyEvent` reducer.
  * Final authoritative `fetchRun` is executed upon terminal events (`run.done` or `run.failed`).
  * Reconnection automatically resumes from `after=N` via browser `Last-Event-ID`.

---

## 2. Test Verification

### A. Frontend Vitest Tests (`npm test`)
```text
 ✓ src/state/__tests__/runStore.test.ts (2 tests)
 ✓ src/components/__tests__/record.test.tsx (8 tests)
 ✓ src/components/__tests__/home.test.tsx (6 tests)

 Test Files  3 passed (3)
      Tests  16 passed (16)
```

### B. Frontend Production Build (`npm run build`)
```text
> frontend@0.0.0 build
> tsc -b && vite build

✓ 1942 modules transformed.
../backend/verbatim/static/index.html                     0.57 kB
../backend/verbatim/static/assets/index-FMJpY9HS.css     13.69 kB
../backend/verbatim/static/assets/index-DOfNSEbP.js     282.49 kB
✓ built in 310ms
```

### C. Backend Full Test Suite (`pytest tests/ -v`)
```text
tests/test_api.py (5 passed)
tests/test_apply.py (7 passed)
tests/test_document.py (1 passed)
tests/test_exporter.py (5 passed)
tests/test_grounding.py (9 passed)
tests/test_guardrails.py (8 passed)
tests/test_hints.py (5 passed)
tests/test_ingest.py (6 passed)
tests/test_phase7_e2e.py (2 passed)
tests/test_stt.py (4 passed)

============================= 52 passed in 13.71s ==============================
```

---

## 3. Git Commits
- Changes staged, committed, and ready for Phase 8 (Player and evidence linking).
