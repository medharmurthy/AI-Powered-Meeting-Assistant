# Phase 9 — Export Polish, Resilience & Responsive UX

## Status

**Completed and merged into `main`.**

- Phase branch: `phase-9`
- Phase 9 commit: `03a4dc4` — `Implement Phase 9 export polish and resilience`
- Merged/pushed to: `main`
- Final working tree: clean
- Phase 1–8 were already complete before this phase

---

## 1. Phase 9 Objective

Phase 9 completed the remaining export, resilience, error-handling, responsive-layout, accessibility, and run-history gaps identified after Phase 8.

The main goals were:

1. Add a complete export section to the record view.
2. Expose export parity information from backend to frontend.
3. Add dropped-item/safety rejection UX.
4. Display non-blocking runtime warnings.
5. Improve run deletion and run-history controls.
6. Make the UI usable at a 360px mobile width.
7. Strengthen accessibility and reduced-motion behavior.
8. Add resilience for mid-run Ollama failures and CUDA fallback.
9. Add dedicated Phase 9 regression tests.

---

## 2. Features Implemented

### A. Export Section

Added:

`frontend/src/components/record/ExportSection.tsx`

The export UI now provides:

- Complete deliverables list.
- File format/type badges.
- File sizes.
- Individual download links.
- Readable Markdown preview.
- Structured JSON preview.
- Server-side export parity indicator.
- Mismatch/error state when parity verification fails.
- **Download everything (.zip)** action.
- Export navigation section via `section-export`.

Expected deliverables include:

- `raw_transcript.txt`
- `raw_transcript.srt`
- `raw_transcript.json`
- `refined_transcript.txt`
- `refined_transcript.json`
- `corrections.csv`
- `meeting_record.json`
- `meeting_record.md`
- `bundle.zip`

Individual files use the existing export API:

`/api/runs/{id}/export/{name}`

---

### B. Backend Export Parity Contract

Modified:

- `backend/verbatim/schemas.py`
- `backend/verbatim/store.py`

`RunState` now exposes:

```text
exportParity
```

with:

```text
decisions: number
tasks: number
ok: boolean
```

`build_run_state()` populates this value from the server's export-parity metadata.

This allows the frontend to display whether the exported Markdown/JSON content matches the server verification result.

---

### C. Record Navigation

Modified:

`frontend/src/components/record/RecordNav.tsx`

Added:

```text
{ id: "section-export", label: "Export" }
```

This makes the export section accessible through sticky record navigation.

---

### D. Dropped-Items Popover

Improved the dropped model-suggestions UX in:

`frontend/src/components/record/RecordPane.tsx`

The popover now supports:

- Singular/plural header text such as:
  - `1 model suggestion removed`
  - `N model suggestions removed`
- Removed suggestion details.
- Section information.
- Safety rejection reason.
- Dismissal through:
  - close button
  - outside click
  - `Esc`

---

### E. Runtime Warning Banner

Added:

`frontend/src/components/shell/WarningBanner.tsx`

Warnings are displayed underneath `StageRail` without blocking the run.

Examples include:

```text
GPU_FALLBACK
NOT_ENGLISH
```

The banner includes a dismiss control.

`RunView.tsx` was updated to render the warning banner and to handle retry-stage resolution more robustly.

---

### F. Run History & Deletion

Modified:

`frontend/src/components/home/RecentRuns.tsx`

Added run deletion through:

```text
DELETE /api/runs/{id}
```

The UI requires confirmation before deleting a run and refreshes the recent-run list after deletion.

The backend deletion behavior removes the associated run data from disk and the run from the returned run history.

---

### G. Responsive 360px Layout

Modified:

- `frontend/src/components/shell/SplitPane.tsx`
- `frontend/src/components/player/PlayerDock.tsx`
- `frontend/src/styles/layout.css`
- `frontend/src/pages/Home.tsx`

Implemented responsive behavior for narrow screens.

Below approximately `960px`:

- Split pane collapses to a single visible pane.
- A two-option switch is available:
  - `Record`
  - `Transcript`
- Player controls remain pinned appropriately.

At approximately `360px` width:

- Horizontal overflow is prevented.
- PlayerDock controls wrap cleanly.
- Topbar controls wrap without clipping.
- Non-essential controls are kept from crowding the viewport.

---

### H. Accessibility

Modified:

`frontend/src/styles/base.css`

Verified/implemented:

- Accessible 2px focus rings using `--blue`.
- 2px focus offset.
- Interactive elements retain visible keyboard focus.
- `prefers-reduced-motion` behavior avoids unnecessary transitions/flashes.
- Empty states remain consistent across sections.

---

### I. Resilience & Mid-Run Recovery

Phase 9 also covers failure behavior during an active run.

#### Ollama failure

If Ollama becomes unavailable during a run:

- The run can fail without destroying earlier completed stage artifacts.
- Existing outputs remain available on disk.
- `OLLAMA_UNREACHABLE` is surfaced.
- The affected step can be retried without retranscribing from the beginning.

#### CUDA fallback

If CUDA is unavailable:

- Processing falls back to CPU.
- `GPU_FALLBACK` warning is exposed to the UI.
- The run can still complete instead of failing solely because GPU acceleration is unavailable.

---

## 3. Tests Added

### Backend

Added:

`tests/test_phase9_resilience.py`

Coverage includes:

- All 16 catalogue error codes.
- Structured `AppError` creation.
- Correct FastAPI HTTP status mapping.
- Run deletion endpoint.
- Run directory cleanup.
- Run removal from `GET /api/runs`.
- Mid-run failure preserving earlier stage artifacts.
- Ollama failure/retry behavior.
- Export parity failure detection.
- `RunState` including export parity information.

The 16 catalogue error codes covered are:

```text
UNSUPPORTED_TYPE
EMPTY_FILE
TOO_LARGE
UNREADABLE_FILE
NO_AUDIO_STREAM
TOO_SHORT
TOO_LONG
SILENT_AUDIO
NO_SPEECH
NOT_ENGLISH
GPU_FALLBACK
OLLAMA_UNREACHABLE
MODEL_MISSING
LLM_BAD_OUTPUT
LLM_TIMEOUT
INTERNAL
```

### Frontend

Added:

`frontend/src/components/__tests__/export.test.tsx`

Coverage includes:

- All export files rendering.
- `bundle.zip` rendering.
- Correct download URLs.
- Readable/Structured preview tab switching.
- Export parity messaging.
- Matching parity state.
- Failing parity state.

Existing record tests were also updated to verify:

- `ExportSection` appears in the record view.
- Dropped-items popover closes using `Esc`.

---

## 4. Verification Results

Phase 9 implementation was verified with:

### Backend tests

```powershell
.venv\Scripts\pytest -v
```

Result:

**57 backend tests passed**

This includes the existing 52-test baseline plus 5 Phase 9 resilience tests.

### Frontend tests

Result:

**33 frontend tests passed**

This includes the existing baseline tests plus the new Phase 9 tests.

### TypeScript

Result:

**0 TypeScript errors**

### Ground-truth evaluation

```powershell
.venv\Scripts\python eval/check_sample.py runs/<sample_run_id>
```

Result:

**ALL GROUND TRUTH CHECKS PASSED**

The action-item checks verified:

- Correct owners.
- Correct deadlines.
- Correct handling of unspecified owners/deadlines.
- Correct exclusion of non-task items.

### Production frontend build

```powershell
cd frontend
npm run build
cd ..
```

Production assets were rebuilt under:

```text
backend/verbatim/static/
```

The static SPA serving test continued to pass.

---

## 5. Known Limitations / Notes

### Preview network dependency

The live export preview fetches:

```text
/api/runs/{id}/export/{name}
```

via normal HTTP.

In an offline unit-test environment without a running server, the preview may show a loading/placeholder state instead of live content.

### Very narrow waveform

At 360px width, PlayerDock controls wrap into two rows as intended.

Below roughly 300px, wavesurfer timeline ticks may become compact because of canvas width limitations.

### Export preview performance

For long recordings, Markdown and JSON previews should remain inside capped, scrollable/preformatted containers rather than constructing large DOM trees.

---

## 6. Important Files Added/Changed

### New

```text
frontend/src/components/record/ExportSection.tsx
frontend/src/components/shell/WarningBanner.tsx
frontend/src/components/__tests__/export.test.tsx
frontend/src/lib/segments.ts
tests/test_phase9_resilience.py
```

### Major modified files

```text
backend/verbatim/schemas.py
backend/verbatim/store.py
backend/verbatim/static/index.html
frontend/src/api/types.ts
frontend/src/components/home/RecentRuns.tsx
frontend/src/components/player/PlayerDock.tsx
frontend/src/components/record/RecordNav.tsx
frontend/src/components/record/RecordPane.tsx
frontend/src/components/shell/SplitPane.tsx
frontend/src/pages/Home.tsx
frontend/src/pages/RunView.tsx
frontend/src/styles/base.css
frontend/src/styles/layout.css
frontend/package-lock.json
.gitignore
```

---

## 7. Git / Handoff State

Phase 9 was committed as:

```text
03a4dc4 Implement Phase 9 export polish and resilience
```

The branch was pushed:

```text
phase-9 -> origin/phase-9
```

Then merged into `main`.

Final repository state:

```text
HEAD -> main
origin/main
origin/HEAD
```

all point to the Phase 9 commit.

Working tree:

```text
nothing to commit, working tree clean
```

---

## 8. Instructions for the Next Agent / Teammate

Before starting the next phase:

1. Read **all previous files in `got_done/`** for Phases 1–9.
2. Read `plan.md`.
3. Treat Phase 1–9 as completed unless the repository itself contradicts the documentation.
4. Do **not** redo Phase 9.
5. Identify the next phase's requirements from `plan.md`.
6. Inspect the current implementation before modifying anything.
7. Preserve the existing backend tests, frontend tests, production build, and ground-truth evaluation.
8. Work on a dedicated branch for the next phase.
9. Run the relevant test suites before committing.
10. Add a new handoff document under `got_done/` when the next phase is completed.

### Current baseline

At the end of Phase 9:

```text
Backend tests:        57 passed
Frontend tests:       33 passed
TypeScript errors:    0
Ground truth:         100% passed
Working tree:         clean
Main:                 contains Phase 9
```

**Phase 9 is complete. Continue from the Phase 10 requirements in `plan.md`.**
