# Phase 8 — Player and Evidence Linking

## Status

**Phase 8 is complete, verified, and accepted.**

- **Backend Test Suite Status**: **52 passed, 0 failed, 0 skipped** across all backend test suites (`tests/`).
- **Frontend Test Suite Status**: **28 passed, 0 failed** in Vitest across 6 test suites covering `playerStore`, `runStore`, `PlayerDock`, `record`, `home`, and `transcript` interactions.
- **Production Build Status**: `npm run build` succeeds cleanly in ~320ms, bundling assets to `backend/verbatim/static/`.
- **Interaction Table (Section 8.6)**: 100% implemented and verified according to `plan.md`.

---

## 1. What Was Implemented in Phase 8

### A. Player Store & WaveSurfer Playback (`frontend/src/state/playerStore.ts` & `components/player/PlayerDock.tsx`)
* **`playerStore.ts`**:
  * State: `time`, `playing`, `duration`, `rate`, `activeRegion`, and `followPlayback`.
  * External control actions: `seek(t)`, `playRange(start, end)`, `toggle()`, `setRate(rate)`, `setFollowPlayback(bool)`.
  * Decoupled architecture: registers handlers from the single WaveSurfer owner in `PlayerDock`.
* **`PlayerDock.tsx`**:
  * Integrates **WaveSurfer.js v8** with pre-computed `peaks` and `audio_url` so audio never needs client-side decoding.
  * Re-creates automatically on theme switch (`light` / `dark`) with dynamic CSS variable resolution.
  * Displays segment ticks as an overlaid positioned layer (`left = start / duration * 100%`).
  * Integrates **RegionsPlugin** rendering evidence ranges with yellow `--marker` color at 35% alpha.
  * Playback controls:
    * Play/Pause toggle with Space keyboard shortcut.
    * Seek backward and forward 5s (`RotateCcw`, `RotateCw`, `←` / `→`).
    * Tabular time display: `MM:SS / MM:SS`.
    * Speed multipliers: `0.75×`, `1×`, `1.25×`, `1.5×`.
    * Evidence range badge with one-click dismiss: `yellow range = evidence ×`.
    * `Follow` / `Following` playback toggle.

### B. Evidence Linking (`frontend/src/components/record/EvidenceChip.tsx`)
* Computes bounding time range for cited segments (`rangeFor(ids)`).
* Clicking pins transcript lines, scrolls first cited line into view, and calls `playRange(start - 1.0s, end + 0.5s)` which plays once and pauses.
* Second click on the same chip unpins and clears the active region.
* Hovering softly highlights cited segments in the transcript pane via `focusStore`.

### C. Active-Line Follow & Word Highlighting (`frontend/src/components/transcript/SegmentRow.tsx`)
* Active segment gets a 3px `--blue` left bar.
* In Raw view with word timestamps, words gain spoken styling progressively as `time >= word.start`.
* Clicking the 60px time gutter seeks to segment start time and starts playback.
* Auto-follow scrolls active line into view; manual scrolling pauses follow and presents a floating **"Jump to playback"** pill.

### D. Refined View & Correction Popover (`frontend/src/components/transcript/CorrectionPopover.tsx`)
* Refined transcript segments render replacement spans as `<ins class="ins-mark">` with blue underlines.
* Clicking or hovering a span opens `CorrectionPopover`:
  * Struck-through original: `~original~`
  * Replacement: `corrected`
  * Safety reason: e.g. *"Misheard caching tool"*
  * Interactive switch **"Applied"**:
    * Dispatches `PATCH /api/runs/:id/corrections/:cid`.
    * Updates refined text in real-time.
    * Sets `recordStale = true` and displays the `StaleBanner`.

### E. Compare View & Guardrails Review (`frontend/src/components/transcript/CompareRow.tsx` & `ChangesSummary.tsx`)
* **Two-column layout**: Raw ASR transcript on the left, Refined transcript on the right, aligned by segment ID.
* Consecutive unchanged lines ($\ge 3$) are collapsed into quiet expandable rows: *"N lines unchanged (click to expand)"*.
* **`ChangesSummary`**:
  * Summarizes applied edits vs safety-blocked edits.
  * Expandable list of blocked candidate corrections showing plain-language `block_reason` (e.g. *"Numbers, amounts, and dates must never change"*), exposing guardrails to reviewers.

### F. Stale Banner & Rewrite Record
* `StaleBanner` alerts user when transcript corrections have been modified.
* Button **"Rewrite record"** triggers `POST /api/runs/:id/rerun` with `from_stage="document"`, seamlessly restarting the document stage with updated transcript text.

### G. Keyboard Shortcuts
Implemented according to Section 8.6:
- `Space`: Play / Pause (ignored while typing in input elements).
- `←` / `→`: Back / Forward 5 seconds.
- `J` / `K`: Next / Previous transcript segment.
- `1` / `2` / `3`: Switch views (Raw / Refined / Compare).
- `/`: Focus transcript search box.
- `Esc`: Clear active pin, search filter, and blur focus.

---

## 2. Test Verification

### A. Frontend Vitest Tests (`npm test`)
```text
 ✓ src/state/__tests__/playerStore.test.ts (3 tests)
 ✓ src/state/__tests__/runStore.test.ts (2 tests)
 ✓ src/components/__tests__/player.test.tsx (2 tests)
 ✓ src/components/__tests__/record.test.tsx (8 tests)
 ✓ src/components/__tests__/home.test.tsx (6 tests)
 ✓ src/components/__tests__/transcript.test.tsx (7 tests)

 Test Files  6 passed (6)
      Tests  28 passed (28)
```

### B. Frontend Production Build (`npm run build`)
```text
> frontend@0.0.0 build
> tsc -b && vite build

✓ 1949 modules transformed.
../backend/verbatim/static/index.html                     0.57 kB
../backend/verbatim/static/assets/index-42w1ePQd.css     14.58 kB
../backend/verbatim/static/assets/index-DJWJletH.js     370.46 kB
✓ built in 325ms
```

### C. Backend Full Test Suite (`pytest tests/ -v`)
```text
============================= 52 passed in 14.82s ==============================
```

---

## 3. Git Commits
- Changes staged, committed, and ready for Phase 9 (Export, polish, resilience).
