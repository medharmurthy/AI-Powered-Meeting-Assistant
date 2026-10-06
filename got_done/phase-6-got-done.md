# Phase 6 — Frontend Foundation

## Status

**Phase 6 is complete, verified, and accepted.**

- **Backend Test Suite Status**: **50 passed, 0 failed, 0 skipped, 0 errors** across all backend test suites (`tests/`).
- **Frontend Test Suite Status**: **2 passed, 0 failed** in Vitest covering the event reducer and live SSE event replay.
- **Production Build Status**: `npm run build` succeeds cleanly in 1.16s, outputting to `backend/verbatim/static/`.
- **Dev-only Fake Pipeline**: `backend/verbatim/dev_fake.py` implemented and verified under `VERBATIM_FAKE=1`.

---

## 1. What Was Implemented in Phase 6

### A. Dev Fake Pipeline (`backend/verbatim/dev_fake.py`)
* Replays realistic meeting fixture events with small delays without requiring GPU or Ollama models.
* Sets `meta.fake = true` and displays the persistent warning banner: **"Demo data, not produced from this audio"**.
* Connected to `backend/verbatim/pipeline.py` via `os.environ.get("VERBATIM_FAKE") == "1"`.

### B. Frontend Scaffolding (`frontend/`)
* Scaffolding: Vite + React 19 + TypeScript.
* Dependencies:
  - `wouter`: Lightweight declarative client-side routing.
  - `zustand`: State management with minimal boilerplate.
  - `wavesurfer.js`: Audio waveform rendering.
  - `lucide-react`: Clean SVG icons.
  - `@fontsource-variable/literata` & `@fontsource-variable/hanken-grotesk`: Bundled fonts for offline operation.
* Dev & Testing:
  - `vitest`, `@testing-library/react`, `jsdom`.
* Configuration (`frontend/vite.config.ts`):
  - Dev proxy `/api` $\rightarrow$ `http://127.0.0.1:8000`.
  - Build output $\rightarrow$ `backend/verbatim/static` with `emptyOutDir: true`.

### C. Design Tokens & Proofreading Aesthetic (`frontend/src/styles/`)
* `tokens.css`:
  - Curated palette: `--paper`, `--sheet`, `--ink`, `--ink-soft`, `--rule`.
  - Proofreading marks: `--blue` (`#2A44D4`) for insertions/actions, `--marker` (`#FFD84A`) for evidence/playback.
  - Full dark mode support toggled via `data-theme` on `<html>`.
* `base.css`:
  - Reset, font declarations, tabular numbers, `.ins-mark`, `.del-mark`, `.unspecified-pill`.
  - Accessible 2px `--blue` focus rings with 2px offset.
* `layout.css`:
  - App shell, Topbar, StageRail, SplitPane with draggable separator handle, ErrorPanel, StaleBanner.

### D. TypeScript Data Contracts & API Layer (`frontend/src/api/`)
* `types.ts`: TypeScript mirrors of backend Pydantic models (`RunState`, `Segment`, `Word`, `Correction`, `Span`, `RefinedSegment`, `MeetingRecord`, `Decision`, `ActionItem`, `Unresolved`, `MinutesTopic`, `AppError`, `HealthResponse`, `RunEvent`).
* `client.ts`: Fetch wrappers for `/api/health`, `/api/runs`, `/api/runs/{id}`, `/api/runs/sample`, `/api/runs/{id}/corrections/{cid}`, `/api/runs/{id}/rerun`.
* `events.ts`: `subscribeToRunEvents` managing monotonic `seq`, `after=N`, ping keep-alives, and clean closure on `run.done` / `run.failed`.

### E. State Management & Pure Reducer (`frontend/src/state/`)
* `runStore.ts`:
  - Pure `applyEvent(state, event)` reducer handling all 14 pipeline event types.
  - `useRunStore` hook orchestrating initial GET and real-time SSE event consumption.
* `uiStore.ts`:
  - Theme toggling with local storage persistence and system preference detection.
  - Split pane ratio (default 46% / 54%) persisted in local storage.

### F. Shell Components & Routing (`frontend/src/components/shell/` & `pages/`)
* `Topbar`: Brand link, active run breadcrumb, health pill indicators, and theme toggle.
* `HealthPill`: Auto-polling `/api/health` displaying status dots for Whisper, Refiner, and Documenter.
* `StageRail`: 3-stage progress rail (Transcribe, Correct terms, Write the record) with live elapsed seconds and status.
* `SplitPane`: Resizable 46/54 split pane with mouse drag handle and responsive collapse below 960px.
* `ErrorPanel`: Actionable catalogue error banner with copyable command button and retry triggers.
* `StaleBanner`: Dynamic warning when transcript corrections change, offering one-click "Rewrite record".
* `ThemeToggle`: Sun/Moon toggle switching between light and dark themes.
* `Home.tsx`: Upload drop target, Try Sample button, and recent runs list.
* `RunView.tsx`: Live workspace shell rendering Left Record pane and Right Transcript pane.

---

## 2. Test Verification

### A. Frontend Vitest Tests
Command: `npm test` (in `frontend/`)
```text
 ✓ src/state/__tests__/runStore.test.ts (2 tests) 3ms
   ✓ RunStore Reducer (applyEvent) (2)
     ✓ processes a full pipeline event sequence sequentially into comprehensive RunState
     ✓ handles run.failed and warning events gracefully

 Test Files  1 passed (1)
      Tests  2 passed (2)
```

### B. Frontend Production Build
Command: `npm run build` (in `frontend/`)
```text
✓ built in 1.16s
Output: ../backend/verbatim/static/ (index.html, assets/...)
```

### C. Backend Full Test Suite
Command: `python3 -m pytest tests/ -v`
```text
============================= 50 passed in 13.69s ==============================
```

### D. Offline Fake Pipeline Verification
Verified with `VERBATIM_FAKE=1` end-to-end:
```text
Created sample fake run: 20261006-165018-b14j
Final status: done fake: True raw segments: 18
Record title: Orion payments weekly sync
VERBATIM_FAKE test completely verified!
```

---

## 3. Handoff for Phase 7 (Home and Live Workspace)

Phase 6 provides the complete foundation. Phase 7 can now build the full interactive components:
* `DropStage` with audio drag-and-drop animation.
* `ChipInput` for glossary terms and participant chips.
* `TranscriptPane` with live streaming line animations and Raw tab.
* `RecordPane` sections filling progressively as `record.section` events arrive.
