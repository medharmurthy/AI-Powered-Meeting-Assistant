# Verbatim: build plan

*An AI meeting assistant where every decision and task links back to the exact moment in the recording.*
Inter IIT Bootcamp, Phase 2, ML PS. Deadline: 7 Oct (confirm the cutoff time today). Team: 1–3.

---

## 0. How to use this plan

- Follow sections 10 (phases) in order. Everything before it is the spec those phases refer to.
- Every phase ends with an **Accept** check. Do not start the next phase until it passes.
- Anything marked **VERIFY** is something I could not confirm from here (a model tag, a library option name). Check it the first time you touch it and fix the plan, not the symptom.
- Time is the biggest risk. Section 11 has a schedule and a **cut line**: what to drop, in order, if you fall behind.

---

## 1. What we are building and why it can win

Every team will ship the same three-model chain (Whisper → LLM → LLM). The rubric (100 pts) rewards correct outputs, and all strong teams will score similarly there. Two things still separate submissions: **how easy it is for a reviewer to verify the output against the recording**, and **how reliably the app runs on someone else's machine**.

So the product is built around three ideas:

1. **Evidence follows you.** Every decision, task, minute and correction is linked to transcript line IDs. Click any item: the transcript scrolls to the lines, the lines get a highlighter mark, the waveform shows the range and the audio plays those few seconds. The reviewer's job ("compare against the recording") becomes one click per item.
2. **The workspace is the progress screen.** No spinner page. From the moment the audio is accepted, the two-pane workspace is on screen. Transcript lines stream in as Whisper produces them, corrections land on the lines as the refiner finds them, and the record fills in section by section.
3. **Honest by construction.** The refiner can only propose *edits* (find/replace spans), and code applies them after safety checks. The documenter's output is checked against the transcript by deterministic rules. Missing owners/deadlines render as an explicit **Unspecified** state, and "discussed, not settled" items get their own section instead of being passed off as decisions.

### 1.1 What changed from SOLUTION.md

| Topic | SOLUTION.md | This plan | Why |
|---|---|---|---|
| UI | Streamlit, tabs, sidebar | FastAPI + custom React app with SSE streaming | Streamlit cannot do click-to-seek transcripts, waveform, resizable panes or a distinctive look; every team will use it or Gradio |
| Refinement output | LLM rewrites the whole transcript, `difflib` guesses the diff | LLM returns only corrections (`segment_id`, `original`, `corrected`); code applies them | Cannot drop or rewrite sentences, output is tiny and fast, diff is exact, per-correction undo is trivial, guardrails act on single edits instead of reverting whole segments |
| STT stack | WhisperX + wav2vec2 alignment + pyannote | faster-whisper only (built-in VAD and word timestamps) | WhisperX pins heavy torch/pyannote versions; pyannote needs gated Hugging Face models and a token. One failed install = 0 on the end-to-end criterion |
| Diarization | Core | Optional last phase | Not in the rubric. Labels like `SPEAKER_01` are not names, and a wrong label could fabricate an owner |
| Long meetings | Map-reduce | Duration cap per profile with a clear error | Cut scope; the unseen test recording is almost certainly short |
| Doc calls | 2 calls + optional self-check | 4 section calls + 1 verify call, streamed section by section | Feeds the progressive UI; the verify call also checks owner/deadline claims |
| Tentative tasks | `status` mixed in | Separate `unresolved` list (`possible_task`) | `action_items` then only ever contains real commitments |
| Grounding | rapidfuzz on quotes at 80 | Segment-ID support + lexical overlap + owner/deadline presence checks | Simpler, deterministic, explainable in the UI |
| Models | Qwen2.5 7B, Gemma 3 12B (with a 32k context on 8 GB) | Config-driven profiles, defaults below, plus a bake-off step | Newer families (Gemma 4, Qwen 3.5/3.6) exist in Ollama now; Gemma 3 12B plus a long context will not sit fully in 8 GB VRAM |
| Platform | Assumes a Lenovo LOQ with an RTX 4060 | Profiles (`lite` / `standard` / `quality`), CPU fallback, health checks with copy-paste fixes | Reviewers' machines differ |
| Offline | Hard requirement | Default, not a requirement (LLM client is an interface) | Insurance if a demo machine has no GPU |

---

## 2. Locked decisions

- **Backend:** Python 3.11, FastAPI, uvicorn, Pydantic v2. One worker, one job at a time (GPU is a single resource).
- **STT:** `faster-whisper`. Default model `large-v3` on GPU (fp16), `distil-large-v3` int8 on CPU.
- **LLM runtime:** Ollama via the native `ollama` Python client (needed for `num_ctx`, `keep_alive`, structured output).
- **Refiner (LLM #1) default:** `qwen3:8b`, thinking off. **Documenter (LLM #2) default:** `gemma3:12b`. Different families on purpose. **VERIFY** by the Day-1 bake-off (section 10, Phase 0).
- **Frontend:** Vite + React 18 + TypeScript, `zustand`, `wouter`, `wavesurfer.js` v7, `lucide-react`, fonts bundled via `@fontsource-variable/*` (works offline). Plain CSS with design tokens. No UI kit, no Tailwind.
- **Transport:** REST + Server-Sent Events. The event log on disk is the source of truth for in-flight runs.
- **Delivery:** the built frontend is committed into `backend/verbatim/static/`, so reviewers only need Python and Ollama. `python run.py` starts everything at `http://localhost:8000`.
- **Determinism:** temperature 0, fixed seed, prompts are versioned files in `prompts/`.
- **No hardcoded results anywhere.** A dev-only fake pipeline exists for UI work (section 6.10); it is off by default and the UI shows a visible "Demo data" banner when it is on.

---

## 3. Repository layout

```
verbatim/
├── README.md                     # setup + run (section 12)
├── plan.md
├── run.py                        # entry: sets CUDA lib paths, starts uvicorn, opens browser
├── requirements.txt
├── config.yaml
├── prompts/
│   ├── refine_profile.v1.md
│   ├── refine_corrections.v1.md
│   ├── doc_system.v1.md
│   ├── doc_summary.v1.md
│   ├── doc_minutes.v1.md
│   ├── doc_decisions.v1.md
│   ├── doc_actions.v1.md
│   └── doc_verify.v1.md
├── backend/verbatim/
│   ├── main.py                   # FastAPI app, routes, SSE, static + SPA fallback
│   ├── config.py                 # load config.yaml, resolve profile, env overrides
│   ├── errors.py                 # AppError + catalogue
│   ├── schemas.py                # all Pydantic models (section 5)
│   ├── store.py                  # run dirs, JSON files, event log
│   ├── jobs.py                   # single-worker queue, progress callback
│   ├── health.py                 # GPU / Ollama / model checks
│   ├── gpu.py                    # CUDA lib discovery, device pick, free memory
│   ├── ingest.py                 # validate, decode to 16 kHz wav, peaks
│   ├── stt.py                    # faster-whisper stage
│   ├── llm/{base.py,ollama_client.py}
│   ├── refine/{hints.py,stage.py,guardrails.py,apply.py}
│   ├── document/{stage.py,grounding.py,verify.py}
│   ├── pipeline.py               # orchestrates stages, emits events
│   ├── export/{exporter.py,templates/meeting_record.md.j2}
│   ├── dev_fake.py               # dev only
│   ├── cli.py                    # python -m verbatim.cli file.mp3
│   └── static/                   # built frontend (committed)
├── frontend/
│   ├── package.json  vite.config.ts  tsconfig.json  index.html
│   └── src/ (section 8.4)
├── tests/                        # pytest
├── eval/                         # check_sample.py, wer.py (optional)
├── samples/                      # meeting_script.md, sample_meeting.mp3, expected.json, outputs/
├── docs/{TECHNICAL.md,DEMO_SCRIPT.md}
└── runs/                         # gitignored, one folder per run
```

---

## 4. Configuration (`config.yaml`)

```yaml
profile: auto          # auto | lite | standard | quality. auto picks from VRAM; env VERBATIM_PROFILE overrides

limits:
  max_upload_mb: 500
  allowed_ext: [wav, mp3, m4a, aac, flac, ogg, opus, webm, mp4, mov, mkv]
  min_duration_s: 2
  silence_dbfs: -55            # whole-file RMS below this => SILENT_AUDIO

stt:
  language: en
  beam_size: 5
  vad_min_silence_ms: 500
  cpu_model: distil-large-v3

llm:
  provider: ollama
  host: http://127.0.0.1:11434
  temperature: 0
  seed: 7
  timeout_s: 600
  unload_after_stage: true

refine:
  window: 40                   # editable segments per call
  context: 4                   # read-only segments on each side
  max_original_words: 6
  hint_min_score: 72

document:
  support_threshold: 0.4       # min share of item words found in cited lines (+-1)
  owner_window: 4              # owner name must appear within +-4 lines of cited lines
  deadline_window: 2
  verify_pass: true

profiles:
  lite:       # <= 6 GB VRAM or CPU only
    stt:        {model: distil-large-v3}
    refiner:    {model: "qwen3:4b",  num_ctx: 8192,  think: false, supports_think: true}
    documenter: {model: "gemma3:4b", num_ctx: 12288, supports_think: false}
    max_minutes: 30
  standard:   # 8 GB VRAM
    stt:        {model: large-v3}
    refiner:    {model: "qwen3:8b",   num_ctx: 8192,  think: false, supports_think: true}
    documenter: {model: "gemma3:12b", num_ctx: 16384, supports_think: false}
    max_minutes: 45
  quality:    # >= 12 GB VRAM
    stt:        {model: large-v3}
    refiner:    {model: "qwen3:14b",  num_ctx: 8192,  think: false, supports_think: true}
    documenter: {model: "gemma3:12b", num_ctx: 32768, supports_think: false}
    max_minutes: 90
```

`supports_think` exists because passing `think` to a model that has no thinking mode may be rejected by Ollama. **VERIFY** on first call.

---

## 5. Data contracts (`schemas.py`, Pydantic v2)

```python
class Word(BaseModel):  w: str; start: float; end: float; p: float | None = None
class Segment(BaseModel):
    id: int; start: float; end: float; text: str
    speaker: str | None = None          # null unless optional diarization is on
    words: list[Word] = []
class RawTranscript(BaseModel):
    segments: list[Segment]; duration: float; language: str; model: str; device: str

class DomainProfile(BaseModel):
    topic: str; domain: str; likely_terms: list[str]; names: list[str]

class Correction(BaseModel):
    id: str                              # "c1", "c2", ...
    segment_id: int; original: str; corrected: str; reason: str
    status: Literal["applied", "reverted", "blocked"]   # reverted = user turned it off
    block_reason: str | None = None      # plain-language, shown in UI
    source: Literal["model", "propagated"] = "model"

class Span(BaseModel):  start: int; end: int; correction_id: str   # offsets into refined text
class RefinedSegment(BaseModel):
    id: int; start: float; end: float; text: str; spans: list[Span] = []
class RefinedTranscript(BaseModel):
    segments: list[RefinedSegment]; corrections: list[Correction]
    profile: DomainProfile; model: str

class Point(BaseModel):     text: str; segment_ids: list[int]
class MinutesTopic(BaseModel): title: str; points: list[Point]
class Decision(BaseModel):
    id: str; text: str; rationale: str | None = None
    segment_ids: list[int]; quote: str | None = None
class Unresolved(BaseModel):
    id: str; kind: Literal["proposal", "question", "deferred", "possible_task"]
    text: str; segment_ids: list[int]
class ActionItem(BaseModel):
    id: str; task: str
    owner: str | None = None; deadline: str | None = None   # null => "Unspecified"
    segment_ids: list[int]; quote: str | None = None
class Dropped(BaseModel): section: str; text: str; reason: str

class MeetingRecord(BaseModel):
    schema_version: str = "1.0"
    title: str; summary: str; attendees: list[str]
    minutes: list[MinutesTopic]
    decisions: list[Decision]; unresolved: list[Unresolved]; action_items: list[ActionItem]
    models: dict[str, str]               # stt, refiner, documenter
    source_file: str; generated_at: str
    dropped: list[Dropped] = []          # audit trail of removed model output

class AppError(BaseModel):
    code: str; title: str; detail: str; fix: str | None = None
    stage: str | None = None; retryable: bool = False
```

Rules: owner/deadline are `null` in JSON and render as the literal text **Unspecified** in the UI and Markdown. Segment IDs are the same in raw, refined and record, so everything aligns by ID.

---

## 6. Backend specification

### 6.1 Errors (`errors.py`)

One exception, `AppError`-carrying: `raise PipelineError(code=...)`. Every code has a fixed title, plain-language detail and fix. The same shape goes over HTTP and SSE, and the UI renders it directly.

| Code | Trigger | Title | Fix shown |
|---|---|---|---|
| UNSUPPORTED_TYPE | extension not allowed | That file type isn't supported | Use wav, mp3, m4a, aac, flac, ogg, opus, webm, mp4, mov or mkv |
| EMPTY_FILE | 0 bytes | That file is empty | Choose a different file |
| TOO_LARGE | > `max_upload_mb` | The file is larger than 500 MB | Trim or compress the recording |
| UNREADABLE_FILE | PyAV cannot open/decode (also a text file renamed `.mp3`) | We couldn't read this audio | Re-export the recording and try again |
| NO_AUDIO_STREAM | container without audio | This file has no audio track | Upload the audio or a video that has sound |
| TOO_SHORT / TOO_LONG | duration vs limits | Recording is too short / longer than N minutes for this setup | Trim it, or switch profile in config |
| SILENT_AUDIO | RMS below `silence_dbfs` | The recording is silent | Check the microphone/source |
| NO_SPEECH | VAD yields no segments | No speech was detected | Check the recording contains spoken English |
| NOT_ENGLISH | language detection (warning, not fatal) | This doesn't sound like English | Results may be poor |
| GPU_FALLBACK | CUDA init fails (warning) | Running on CPU | Install the CUDA 12 libraries for faster processing |
| OLLAMA_UNREACHABLE | connection refused | Ollama isn't running | Start Ollama (`ollama serve`) |
| MODEL_MISSING | model not in `ollama list` | Model `X` isn't installed | `ollama pull X` (copy button) |
| LLM_BAD_OUTPUT | schema validation fails twice | The model returned something we couldn't use | Retry; try another model in config |
| LLM_TIMEOUT | > `timeout_s` | The model took too long | Use the lite profile or a smaller model |
| INTERNAL | anything else | Something went wrong | Show the short message, log the traceback |

Rule: fatal errors keep every earlier stage's output on disk and in the UI; the run gets `status: failed` and a **Retry from this step** button (`rerun`, section 6.8).

### 6.2 Ingest (`ingest.py`)

Order matters; the first failure wins:

1. Extension allow-list → `UNSUPPORTED_TYPE`. Stream the upload to `runs/<id>/original.<ext>` while counting bytes; abort past the limit (`TOO_LARGE`); zero bytes → `EMPTY_FILE`.
2. `av.open(path)`; failure → `UNREADABLE_FILE`; no audio stream → `NO_AUDIO_STREAM`.
3. Decode everything to **16 kHz mono int16** with `av.AudioResampler(format="s16", layout="mono", rate=16000)`; write `runs/<id>/audio.wav` (stdlib `wave`). This single file is used for ASR, for browser playback, and for the waveform. (PyAV bundles FFmpeg, so no system ffmpeg is needed.)
4. Duration checks (`TOO_SHORT`, `TOO_LONG` using the active profile's `max_minutes`).
5. `rms_dbfs = 20*log10(sqrt(mean(x²))/32768)`; below `silence_dbfs` → `SILENT_AUDIO`.
6. Waveform peaks, 1600 bins, one value per bin (max absolute amplitude, 0–1, 3 decimals):

```python
def peaks(pcm, bins=1600):
    n = len(pcm)//bins*bins
    x = np.abs(pcm[:n].reshape(bins, -1).astype(np.float32))/32768
    return x.max(axis=1).round(3).tolist()
```
Save as `peaks.json` = `{"duration": s, "peaks": [...]}`. Emit `audio.ready`.

### 6.3 Speech-to-text (`stt.py`, `gpu.py`)

- `gpu.prepare_cuda()` runs before importing `faster_whisper`. **Windows:** for `nvidia.cublas` and `nvidia.cudnn` (pip packages `nvidia-cublas-cu12`, `nvidia-cudnn-cu12==9.*`) call `os.add_dll_directory(<pkg>/bin)`. **Linux:** `LD_LIBRARY_PATH` must be set before the process starts, so `run.py` computes the paths and re-execs itself once with the variable set. faster-whisper's GPU path needs CUDA 12 with cuDNN 9. **VERIFY** the package layout on your OS.
- Device choice: `torch`-free. Try `WhisperModel(model, device="cuda", compute_type="float16")`; on any `RuntimeError` mentioning cuda/cudnn/cublas/out of memory, retry with `compute_type="int8_float16"`, then fall back to `device="cpu", compute_type="int8"` with `stt.cpu_model`. Emit a `warning` event (`GPU_FALLBACK`) when falling back.
- Language: before transcribing, call `model.detect_language()` on the first 30 s of speech; if not `en` with probability > 0.6, emit a `NOT_ENGLISH` warning and continue with `language="en"`.
- Transcribe:

```python
segments, info = model.transcribe(
    audio_path, language="en", beam_size=5,
    vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
    word_timestamps=True, condition_on_previous_text=False,
    initial_prompt=build_prompt(glossary, participants),   # None if both empty
    hotwords=" ".join(glossary) or None,                   # VERIFY supported by installed version
)
for s in segments:            # lazy generator: emit each one as it arrives
    ...
```
- `build_prompt`: `"Meeting transcript. Participants: A, B. Terms: X, Y, Z."` Only user-supplied terms go here. **Do not** feed the refiner's inferred terms back into STT: the refiner stage must have real work to do on unseen audio.
- Drop hallucinations: `no_speech_prob > 0.6 and avg_logprob < -1.0`; collapse runs of ≥ 3 identical consecutive texts to one.
- Emit `transcript.segment` per kept segment (`id` = running index from 0). Progress = `last_end / duration`.
- No segments at all → `NO_SPEECH`.
- After the stage: `del model; gc.collect()`.

### 6.4 LLM client (`llm/`)

```python
class LLM(Protocol):
    def structured(self, *, model, system, user, schema: type[BaseModel], role) -> BaseModel: ...
    def unload(self, model) -> None: ...
    def available_models(self) -> set[str]: ...
```
`OllamaClient.structured`:
- `client.chat(model=..., messages=[system,user], format=schema.model_json_schema(), options={"temperature":0,"seed":7,"num_ctx":N,"num_predict":2048}, keep_alive="10m", think=False if role cfg.supports_think else omitted)`.
- Parse with `schema.model_validate_json`. On failure, retry **once** with the validation error appended to the user message; second failure → `LLM_BAD_OUTPUT`.
- Map `ConnectionError` → `OLLAMA_UNREACHABLE`; "model not found" → `MODEL_MISSING`.
- `unload(model)` = `client.generate(model=model, prompt="", keep_alive=0)`; called at the end of each LLM stage so the two models never compete for VRAM.

### 6.5 Refinement stage (LLM #1)

**Step A: domain profile** (`refine_profile.v1.md`). Input: the full transcript if ≤ 5k tokens, otherwise the first 3k tokens plus 4 evenly spaced 500-token samples. Output `DomainProfile`. User glossary terms are merged into `likely_terms`; participants into `names`. Emit `refine.profile`.

**Step B: hints** (`refine/hints.py`): deterministic candidate mishearings, handed to the model as a list. This is what lets a small model fix "cooper netties".

```python
def hints(segments, terms, min_score=72):
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    out = {}
    for seg in segments:
        toks = re.findall(r"[A-Za-z0-9'.\-]+", seg.text)
        for n in (1, 2, 3):
            for i in range(len(toks) - n + 1):
                heard = " ".join(toks[i:i+n]); h = norm(heard)
                if len(h) < 4: continue
                for t in terms:
                    if heard.lower() == t.lower(): continue
                    score = max(fuzz.ratio(h, norm(t)),
                                fuzz.ratio(jellyfish.metaphone(h), jellyfish.metaphone(norm(t))))
                    if score >= min_score: out[(seg.id, heard, t)] = score
    return sorted(out, key=lambda k: -out[k])
```

**Step C: corrections.** Windows of `window` editable segments with `context` read-only segments either side. Render lines as `[id] text` (context lines marked `CONTEXT`). Prompt: `refine_corrections.v1.md`. Output:

```python
class Proposal(BaseModel): segment_id: int; original: str; corrected: str; reason: str
class ProposalList(BaseModel): corrections: list[Proposal]
```
Emit `stage.progress` per window and `refine.correction` per accepted correction (so the UI can animate it onto the line).

**Step D: guardrails** (`refine/guardrails.py`), run on every proposal, first failing rule blocks it and sets a plain-language `block_reason`:

| # | Rule | `block_reason` |
|---|---|---|
| 1 | `segment_id` exists and is in the editable range | "Referred to a line that doesn't exist" |
| 2 | `original` occurs verbatim in the raw segment (exact, then case-insensitive) | "Quoted text that isn't in the recording" |
| 3 | `original != corrected`, `len(original.split()) <= max_original_words`, `len(corrected.split()) <= len(original.split()) + 3` | "Edit was too large" |
| 4 | Number tokens equal: multiset of `\d[\d.,]*` and number words (`zero…ninety`, `hundred`, `thousand`, `million`, ordinals) | "Would change a number" |
| 5 | Negations equal: multiset over `{not,no,never,none,nothing,nobody,neither,nor,cannot,without}` plus any `n't` | "Would change a negation" |
| 6 | Modal/commitment words equal: `{will,won't,shall,should,must,can,could,might,may,need,needs,going}` | "Would change a commitment" |
| 7 | If `original` contains a token from `participants` (case-insensitive) it must still contain it in `corrected` | "Would change a person's name" |

**Step E: apply** (`refine/apply.py`). For each segment, apply `applied` corrections left to right, non-overlapping, building refined text and `spans` with offsets in the *refined* text:

```python
def apply(text, corrs):
    items = []
    for c in corrs:
        i = text.find(c.original)
        if i < 0: i = text.lower().find(c.original.lower())
        if i >= 0: items.append((i, i + len(c.original), c))
    items.sort(key=lambda t: t[0])
    out, spans, pos, cur = [], [], 0, 0
    for s, e, c in items:
        if s < pos: continue                      # overlap: skip
        out.append(text[pos:s]); cur += s - pos
        spans.append(Span(start=cur, end=cur + len(c.corrected), correction_id=c.id))
        out.append(c.corrected); cur += len(c.corrected); pos = e
    out.append(text[pos:])
    return "".join(out), spans
```
**Step F: propagate.** For each distinct accepted `(original, corrected)` pair, find other segments containing `original` as a whole word (case-insensitive) that have no correction at that spot; add `source="propagated"` corrections, run guardrails again, apply. This makes terminology consistent across the transcript.

Finally `refined.json` is written and `unload(refiner)` is called. `PATCH` on a correction (section 6.8) flips `applied ↔ reverted` and re-runs only Step E.

### 6.6 Documentation stage (LLM #2)

Transcript block format (from the refined transcript, same IDs): `[12] [03:41] text`. System prompt `doc_system.v1.md` + transcript are **identical across the four calls**, and the task text comes last, so Ollama can reuse the cached prefix. Do not reorder.

Calls, in order, each emitting `record.section` as soon as it is validated:

| # | Prompt | Output schema | Event section |
|---|---|---|---|
| 1 | `doc_summary` | `{title, summary, attendees[]}` | `summary` |
| 2 | `doc_minutes` | `{topics:[{title, points:[{text, segment_ids}]}]}` | `minutes` |
| 3 | `doc_decisions` | `{decisions:[{text, rationale, segment_ids, quote}], unresolved:[{kind, text, segment_ids}]}` | `decisions` |
| 4 | `doc_actions` | `{actions:[{task, owner, deadline, segment_ids, quote}], possible_tasks:[{text, segment_ids}]}` | `actions` |
| 5 | `doc_verify` (if `verify_pass`) | verdict per item (below) | `verified` |

**Grounding** (`document/grounding.py`), deterministic, applied to calls 2–4 before emitting:

- `segment_ids` must all exist; empty after filtering → drop the item (log to `dropped` with reason `"no valid source lines"`).
- **Support:** tokens = lowercase words, stopwords removed, length ≥ 3, crude stem (strip `s/es/ed/ing`). `support = |tokens(item) ∩ tokens(cited ±1 lines)| / |tokens(item)|`. Below `support_threshold` → drop (`"not supported by the cited lines"`).
- **Owner:** if not null, each token of the owner must appear in the refined transcript within `owner_window` lines of the cited lines, or in `participants`. Generic owners (`I, me, we, us, team, everyone, someone, somebody, speaker`, any `SPEAKER_nn`) → null. Failure → set `owner = null` and log `"owner not stated"`.
- **Deadline:** the content tokens of the deadline phrase must appear in cited lines ±`deadline_window`. Otherwise null. The deadline is kept **as spoken** ("by Thursday"); never convert to a calendar date.
- `quote`: if given, `fuzz.partial_ratio(quote, cited text) >= 85`, else set `quote = null` (keep the item).
- De-duplicate within a list: `fuzz.token_set_ratio >= 88` → keep the one with more `segment_ids`.
- Assign stable IDs: `D1…`, `T1…`, `U1…`.

**Verify pass** (call 5): for every decision and action (cited lines ±2 attached), the model answers per item:
`{id, verdict, owner_stated: bool, deadline_stated: bool}` where decision verdicts are `agreed | proposal_only | unsupported` and action verdicts are `committed | tentative | unsupported`. Apply: `unsupported` → drop; `proposal_only` → move to `unresolved(kind="proposal")`; `tentative` → move to `unresolved(kind="possible_task")`; `owner_stated=false` → owner null; `deadline_stated=false` → deadline null. Each move/drop is logged to `dropped` or recorded as an event note.

After the stage: `record.json` written, `unload(documenter)`.

### 6.7 Pipeline, jobs, events

- `pipeline.run(run_id, from_stage="ingest")`: `ingest → transcribe → refine → document → export`. Each stage: emit `stage.started{stage, model}`, run, emit `stage.done{stage, seconds}`; write its output file; catch `PipelineError` → `run.failed{error}`; unexpected exceptions become `INTERNAL`.
- `jobs.py`: a `ThreadPoolExecutor(max_workers=1)`. Runs enter as `queued` with a position, then `running`. An in-memory list plus `events.jsonl` per run holds events `{seq, type, data, t}`, with `seq` monotonic across reruns.
- On server start, any run left `running` becomes `interrupted` (failed with a retryable `INTERNAL` "Interrupted by a restart").
- SSE (`GET /api/runs/{id}/events?after=N`, also honours the `Last-Event-ID` header):

```python
async def gen():
    seq, idle = after, 0
    while True:
        evs = store.events_since(rid, seq)
        for ev in evs:
            seq = ev["seq"]
            yield f"id: {seq}\nevent: {ev['type']}\ndata: {json.dumps(ev['data'])}\n\n"
            if ev["type"] in ("run.done", "run.failed"): return
        idle = 0 if evs else idle + 1
        if idle % 60 == 0: yield ": ping\n\n"          # ~15 s keep-alive
        if await request.is_disconnected(): return
        await asyncio.sleep(0.25)
# StreamingResponse(gen(), media_type="text/event-stream",
#                   headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

Event types and payloads:

| Event | Payload |
|---|---|
| `run.queued` | `{position}` |
| `run.started` | `{from_stage, models:{stt,refiner,documenter}, profile}` |
| `stage.started` / `stage.done` | `{stage, model?}` / `{stage, seconds}` |
| `stage.progress` | `{stage, done, total, label}` (e.g. `label: "Listening 08:12 of 24:31"`) |
| `audio.ready` | `{duration, audio_url, peaks_url}` |
| `transcript.segment` | `Segment` |
| `refine.profile` | `DomainProfile` |
| `refine.correction` | `Correction` (applied) |
| `refine.blocked` | `Correction` (blocked) |
| `refine.done` | `{segments:[RefinedSegment], corrections:[Correction]}` (final, replaces live state) |
| `record.section` | `{section: summary\|minutes\|decisions\|actions\|verified, data}` |
| `warning` | `AppError` |
| `run.done` | `{}` |
| `run.failed` | `AppError` |

### 6.8 HTTP API

| Method + path | Body / params | Returns |
|---|---|---|
| `GET /api/health` | none | `{profile, gpu:{available,name,vram_gb}, stt:{model,device}, llm:{reachable, refiner:{model,installed}, documenter:{model,installed}}, issues:[AppError]}` |
| `POST /api/runs` | multipart: `file`; `glossary` (JSON string[]); `participants` (JSON string[]) | `202 {run_id}`; validation failures return `4xx {error: AppError}` synchronously |
| `POST /api/runs/sample` | none | `202 {run_id}`, runs the real pipeline on `samples/sample_meeting.*` |
| `GET /api/runs` | none | list of `{id, filename, created_at, duration, status, title}` newest first |
| `GET /api/runs/{id}` | none | `RunState` (see 8.5) built from files |
| `GET /api/runs/{id}/events` | `after` | SSE stream |
| `GET /api/runs/{id}/audio` | Range supported | `audio.wav` |
| `GET /api/runs/{id}/peaks` | none | `peaks.json` |
| `PATCH /api/runs/{id}/corrections/{cid}` | `{applied: bool}` | updated `refined` + `record_stale: true` |
| `POST /api/runs/{id}/rerun` | `{from_stage: "refine"\|"document"}` | `202` |
| `DELETE /api/runs/{id}` | none | `204` |
| `GET /api/runs/{id}/export/{name}` | `name` from a whitelist (section 6.9) | file download (`Content-Disposition: attachment`) |
| `GET /*` | none | SPA fallback → `static/index.html` (for `/r/<id>`) |

Run ids: `YYYYMMDD-HHMMSS-<4 random chars>`; validate with `^[0-9A-Za-z-]+$` before touching the filesystem (path traversal).

### 6.9 Exports (`export/exporter.py`)

Everything is derived from the same `MeetingRecord` / `RefinedTranscript` objects.

`raw_transcript.txt` (`[00:01:12] text`), `raw_transcript.srt`, `raw_transcript.json`, `refined_transcript.txt`, `refined_transcript.json`, `corrections.csv` (`segment_id,time,original,corrected,reason,status`), `meeting_record.json`, `meeting_record.md`, `bundle.zip` (all of the above).

`meeting_record.md.j2` structure (fixed ids and shapes so it can be parsed back):

```
# {title}
{source_file} · {date} · {duration}

## Summary
## Attendees
## Minutes
### {topic}
- {point} [mm:ss]
## Decisions
- **D1.** {text} [mm:ss]
## Discussed, not settled
- **U1.** ({kind}) {text} [mm:ss]
## Action items
| # | Task | Owner | Deadline | Source |
|---|------|-------|----------|--------|
| T1 | ... | Dan | by Thursday | [04:12] |
| T3 | ... | Unspecified | before the audit on the 15th | [06:40] |
## How this was made
STT / refiner / documenter models, generated_at
```
Empty sections print "None were agreed in this recording." / "None were assigned in this recording." Escape `|` in cell text.

**Parity check** (`verify_parity(record, md_text)`): parse `^- \*\*D(\d+)\.\*\* (.*?) \[` lines and `^\| T(\d+) \|` rows from the Markdown; assert same ids and same text as the JSON. It runs after every export and in a unit test; the result `{decisions: n, tasks: m, ok: bool}` is shown in the UI.

### 6.10 Dev-only fake pipeline (`dev_fake.py`)

Enabled by env `VERBATIM_FAKE=1`. It replays a hand-written fixture through the same event pipeline with small delays, so the whole frontend can be built without a GPU. Every run it creates has `meta.fake = true`; the UI shows a persistent **"Demo data, not produced from this audio"** banner. It must never be enabled in the submitted demo. Replace the fixture with a real run's output (`runs/<id>/*.json`) as soon as Phase 5 passes.

### 6.11 Health (`health.py`)

`GET /api/health` returns quickly (cache for 10 s): GPU name/VRAM via `ctranslate2.get_cuda_device_count()` and `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` if present; Ollama via `client.list()` (match model names ignoring `:latest`). Produce `issues` using the error catalogue (`OLLAMA_UNREACHABLE`, `MODEL_MISSING`, `GPU_FALLBACK`). Profile `auto`: ≥ 11 GB → quality, ≥ 7 GB → standard, else lite.

---

## 7. Prompts (full text; Jinja2 templates, `{{ }}` placeholders)

### `refine_profile.v1.md`
```
SYSTEM
You prepare notes for an editor who will proofread a meeting transcript produced by speech recognition.
Read the excerpt. Return JSON only.

USER
Participants (may be empty): {{ participants }}
Terms the user says may come up (may be empty): {{ glossary }}

Transcript excerpt:
{{ excerpt }}

Return:
- topic: one sentence on what the meeting is about
- domain: 1-3 words (for example "backend engineering", "clinical trial", "retail finance")
- likely_terms: up to 40 correctly spelled technical terms, product names, acronyms and jargon this meeting probably contains, including ones the recognizer may have misspelled
- names: people and organisations mentioned
```

### `refine_corrections.v1.md`
```
SYSTEM
You fix speech-recognition mistakes in a meeting transcript. You do not rewrite it.

Report a fix only when the recognizer clearly misheard a technical term, product name, acronym or proper noun, and the right form is evident from the term list, the context, or standard spelling.

Rules
1. Give the exact words to replace ("original", copied character for character from the line) and the replacement ("corrected"). Use the shortest span that contains the error (1-6 words).
2. Never change numbers, dates, amounts, negations (not, no, never, n't), words that express commitment (will, won't, should, must, can, need to, going to), or the names of people.
3. Never fix grammar, wording, filler words or style. Never add or remove information. Never touch lines marked CONTEXT.
4. If a phrase is odd but could be what the speaker really said, leave it.
5. Returning an empty list is correct and common.
Return JSON only: {"corrections":[{"segment_id":int,"original":str,"corrected":str,"reason":str}]}. "reason" is at most 12 words.

Examples
[3] we deploy it on cooper netties next week   (term list: Kubernetes)
-> {"segment_id":3,"original":"cooper netties","corrected":"Kubernetes","reason":"Misheard Kubernetes"}
[8] the post gress Q L upgrade is not happening
-> {"segment_id":8,"original":"post gress Q L","corrected":"PostgreSQL","reason":"Misheard PostgreSQL"}   (note: "not" untouched)
[11] we will ship it on the 14th, no later
-> no corrections (numbers, "will" and "no" must never change)
[15] that sounds fine to me
-> no corrections

USER
Domain: {{ profile.domain }}. Topic: {{ profile.topic }}.
Terms likely to appear: {{ terms }}
Participants (never alter their names): {{ participants }}
Possible mishearings found by a spelling check (verify before using): 
{% for h in hints %}- line {{ h.segment_id }}: "{{ h.heard }}" may be "{{ h.term }}"
{% endfor %}
Lines (fix only those not marked CONTEXT):
{{ lines }}
```

### `doc_system.v1.md` (shared by calls 1–5; do not edit per call)
```
You are the secretary of a meeting. You write records that a reader can check against the recording.

Transcript lines look like: [12] [03:41] text. [12] is the line number, [03:41] the time.

Rules for everything you write:
1. Use only what the speakers said. Add no background knowledge, causes or consequences nobody mentioned.
2. Every item cites the supporting line numbers in "segment_ids" (1-4 numbers, the most relevant lines).
3. Keep numbers, amounts, dates and negations exactly as spoken. "Not" and "no" must survive.
4. Be concise: plain sentences, no filler.
5. An empty list is correct when nothing qualifies. Never pad a list.
Return JSON only.
```

### `doc_summary.v1.md` (task text, appended after the transcript)
```
Participants given by the user (may be empty): {{ participants }}
Return {"title","summary","attendees"}.
- title: at most 10 words naming the topic.
- summary: 3-5 sentences: why the group met, the main outcomes, and anything left open.
- attendees: names that are spoken in the transcript or listed above. Do not invent names.
```

### `doc_minutes.v1.md`
```
Group the discussion into 3-7 topics in the order they occurred. For each: a short title and 2-6 points.
A point is one sentence about what was reported, discussed or concluded, with segment_ids.
Return {"topics":[{"title","points":[{"text","segment_ids"}]}]}.
```

### `doc_decisions.v1.md`
```
Find the decisions, and separately the things discussed but not settled.

A DECISION is something the group explicitly agreed, confirmed or settled ("let's go with", "agreed", "it's decided", a proposal followed by confirmation or no objection plus acknowledgement). Negative decisions count ("we will not upgrade this quarter").
NOT a decision: a suggestion, an idea, a question, a preference of one person, something put off ("let's revisit next sprint"), or a statement of fact.

Return {"decisions":[{"text","rationale","segment_ids","quote"}],"unresolved":[{"kind","text","segment_ids"}]}.
- rationale: the reason given in the meeting, or null.
- quote: a short exact quote (at most 20 words) from a cited line, or null.
- unresolved.kind: "proposal" (suggested, not agreed), "question" (asked, not answered), or "deferred" (explicitly postponed).

Examples
"Any objections to Redis?" "None." "Then it's decided: Redis." -> decision.
"I'd suggest moving everything to gRPC." "I don't want to decide that today." -> unresolved, kind "deferred".
```

### `doc_actions.v1.md`
```
Find the action items.

A TASK is work someone committed to ("I'll do X"), was asked to do and accepted, or that the group clearly agreed must be done.
Owner: set only when a person is named as responsible (addressed by name and accepted, or named as taking it). Never infer an owner from role or seniority. If a speaker says "I'll do it" and no name is available, owner is null. 
Deadline: copy the words used ("by Thursday", "before the audit on the 15th"). Do not compute calendar dates. If none was said, null.
NOT a task: an idea, "maybe someone could", "if you have time", "we'll see". Put those in possible_tasks.

Return {"actions":[{"task","owner","deadline","segment_ids","quote"}],"possible_tasks":[{"text","segment_ids"}]}.
task: start with a verb, say what is to be done. quote: short exact quote from a cited line, or null.

Examples
"Dan, can you write the module?" "Yes, I'll have it done by Thursday." -> task owner "Dan", deadline "by Thursday".
"Someone has to rotate the credentials before the audit on the 15th." (nobody volunteers) -> task, owner null, deadline "before the audit on the 15th".
"Maybe Dan could look at the dashboards if he has time." "We'll see." -> possible_tasks, not an action.
```

### `doc_verify.v1.md`
```
Check these items against the lines cited for each. Answer strictly from the lines.

{% for it in items %}
Item {{ it.id }} ({{ it.kind }}): {{ it.text }}{% if it.owner %} | owner: {{ it.owner }}{% endif %}{% if it.deadline %} | deadline: {{ it.deadline }}{% endif %}
Lines:
{{ it.lines }}
{% endfor %}

For each item return {"id","verdict","owner_stated","deadline_stated"}.
Decision verdicts: "agreed" (the group settled it), "proposal_only" (only suggested or still open), "unsupported".
Task verdicts: "committed", "tentative" (maybe/if time/we'll see), "unsupported".
owner_stated: true only if a person is named as responsible in the lines. deadline_stated: true only if a time limit was spoken.
Return {"results":[...]}.
```

---

## 8. Frontend specification

### 8.1 Stack and structure

`npm create vite@latest frontend -- --template react-ts`. Dependencies: `react react-dom wouter zustand wavesurfer.js lucide-react @fontsource-variable/literata @fontsource-variable/hanken-grotesk`. Dev: `vitest @testing-library/react`. `vite.config.ts`: dev proxy `/api → http://127.0.0.1:8000`; `build.outDir = "../backend/verbatim/static"`, `emptyOutDir: true`.

```
src/
├── main.tsx  App.tsx
├── styles/{tokens.css, base.css, layout.css, components.css}
├── api/{client.ts, events.ts, types.ts}      # fetch wrappers, SSE subscribe, TS mirrors of schemas
├── state/{runStore.ts, playerStore.ts, focusStore.ts, uiStore.ts}
├── lib/{time.ts, segments.ts, diffSpans.ts}
├── pages/{Home.tsx, RunView.tsx}
└── components/
    ├── shell/{Topbar, StageRail, HealthPill, ThemeToggle, SplitPane, ErrorPanel, StaleBanner}
    ├── home/{DropStage, Preflight, ChipInput, HealthList, RecentRuns}
    ├── record/{RecordPane, RecordNav, SummarySection, MinutesSection, DecisionsSection,
    │           UnresolvedSection, TasksSection, ExportSection, EvidenceChip, Unspecified}
    ├── transcript/{TranscriptPane, ViewTabs, SegmentRow, CompareRow, CorrectionPopover, ChangesSummary}
    └── player/{PlayerDock, Waveform}
```

### 8.2 Design system

**Concept.** The product sits between audio and paper. Editing marks are drawn from proofreading: the blue pencil for corrections, the yellow highlighter for evidence. The record reads like a document (serif, rules, no boxed cards); the transcript reads like a script; the player is a docked transport bar like an audio editor. The one memorable thing is the evidence highlight. Everything else stays quiet.

**Avoid:** identical rounded cards with shadows, gradient washes, ALL-CAPS eyebrow labels, monospace data labels, "→" in buttons, fade-up animation on every section, a big-number hero.

`tokens.css`:
```css
:root {
  --paper:#F3F5F7;  --sheet:#FFFFFF;  --ink:#16222B;  --ink-soft:#55646F;  --rule:#D8DEE3;
  --blue:#2A44D4;   --blue-wash:#E6EBFC;           /* blue pencil: actions, insertions */
  --marker:#FFD84A; --marker-wash:#FFF1B8;         /* highlighter: evidence, playback */
  --alert:#B3261E;  --alert-wash:#FBE9E7;  --ok:#1F7A4D;
  --font-ui:"Hanken Grotesk Variable","Hanken Grotesk",system-ui,sans-serif;
  --font-doc:"Literata Variable","Literata",Georgia,serif;
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px;
  --r-chip:999px; --r-ctl:6px; --r-sheet:2px;
  --t-xs:12.5px; --t-sm:14px; --t-md:16px; --t-lg:19px; --t-xl:24px; --t-2xl:32px;
  --measure:68ch;
}
:root[data-theme="dark"]{
  --paper:#0E171D; --sheet:#15222A; --ink:#E8EFF3; --ink-soft:#9AABB6; --rule:#26363F;
  --blue:#7C9BFF;  --blue-wash:#1C2A52; --marker:#FFD84A; --marker-wash:#3C3510;
  --alert:#FF8A80; --alert-wash:#3A1C1A; --ok:#5FD39A;
}
```
Theme: `data-theme` on `<html>`, initial from `prefers-color-scheme`, toggle persisted in `localStorage`. Marker highlight text colour is always `var(--ink)` in light and `#16222B` on the solid `--marker` in dark.

**Type.**
- Record and transcript text: Literata, 16/1.65 (record), 15.5/1.6 (transcript), max `68ch`. Headings in Literata 600 at 19/24/32.
- Interface (buttons, chips, labels, timestamps): Hanken Grotesk, 14/1.4. Labels are sentence case and semi-bold. Timestamps use `font-variant-numeric: tabular-nums`, not a monospace font.
- Import `@fontsource-variable/literata` (plus its italic file) and `@fontsource-variable/hanken-grotesk` in `main.tsx`. **VERIFY** the exact import paths in the installed package.

**Shapes and marks.** Sheets have a 1px `--rule` border and `--r-sheet`. Chips are pills. Buttons and inputs 6px. No drop shadows except popovers (`0 8px 24px rgb(0 0 0 / .16)`) and the player dock's top border. Insertion = `--blue` text with 2px underline in `--blue`. Deletion (original shown in Compare/popovers) = `--ink-soft` with strike-through. Evidence/active = `--marker-wash` background with a 3px `--marker` left bar. Meaning never relies on colour alone (underline/strike/bar/labels).

**Unspecified state.** A pill with a dashed `--ink-soft` 1px border, transparent background, `--ink-soft` text, the literal word **Unspecified**. Never greyed-out empty cells.

**Motion.** Exactly one orchestrated moment: when a correction event arrives, the corrected words flash `--marker` for 600 ms, then settle to the blue underline. Everything else only responds to a user action (expand/collapse 150 ms, seek highlight fades after 1.5 s). `prefers-reduced-motion`: no flash, no scroll animation.

**Quality floor.** 2px `--blue` focus ring with 2px offset on every focusable element; contrast ≥ 4.5:1; minimum hit area 36×36; responsive to 360 px; `aria-live="polite"` region announcing stage changes.

### 8.3 Screens

**Home (`/`).** The drop target is the page.

```
┌ Verbatim ─────────────────────────────── ● Whisper  ● qwen3:8b  ● gemma3:12b   ☾ ┐
│                                                                                   │
│        ╭───────────────────────────────────────────────────────────╮              │
│        │    ▁▂▁▁▂▃▂▁▁▁▂▁▃▅▃▂▁▁▁▂▁▁▂▁▁▁▂▃▂▁▁▁▂▁                    │ flat tape,   │
│        │    Drop a meeting recording                               │ bars rise    │
│        │    or choose a file · wav mp3 m4a flac ogg mp4 · up to 500 MB│ on drag-over │
│        ╰───────────────────────────────────────────────────────────╯              │
│  Terms to listen for (optional)  [Kubernetes ×] [OAuth ×] [ add… ]                 │
│  Who's in the meeting (optional) [Priya ×] [Dan ×] [ add… ]                        │
│  [ Process recording ]   Try the sample recording                                  │
│                                                                                   │
│  Recent recordings                                                                 │
│  Orion payments sync · 4:52 · Done · 5 Oct                                         │
└───────────────────────────────────────────────────────────────────────────────────┘
```
- Left-aligned content column (max 880 px) centred in the viewport. Health issues appear under the drop stage as actionable lines with a copy button for commands, e.g. "gemma3:12b isn't installed. `ollama pull gemma3:12b`".
- The file is validated on selection (type, size, empty) with the exact catalogue messages; invalid files never enter the upload.
- **Process recording** is disabled until a valid file is chosen. Submitting creates the run and navigates to `/r/<id>` immediately.

**Run workspace (`/r/:id`).** Same layout during and after processing.

```
┌ Verbatim ▸ Orion payments sync ▾                                 ☾ ┐
│ ① Transcribe ✓ 1:12   ② Correct terms ● chunk 3 of 9   ③ Write the record ○   │  StageRail
├──────────────────────────────┬──────────────────────────────────────┤
│ Orion payments weekly sync   │ [Raw] [Refined] [Compare]   Search /  │
│ Summary …                    │ 00:12  Okay, let's get started …      │
│ Minutes                      │ 00:31  On the session cache we're …   │
│ Decisions  2                 │ ▌01:05  Then it's decided: Redis.    │ ← evidence
│  D1 Migrate the session …    │ 01:20  Dan, can you write the …      │
│     ▶ 01:03                  │                                       │
│ Discussed, not settled  2    │                                       │
│ Action items  3              │                                       │
│  Task | Owner | Deadline     │                                       │
│ Export                       │                                       │
├──────────────────────────────┴──────────────────────────────────────┤
│ ▶  01:05 / 04:52   ▁▂▃▅▃▂▁▂▃▆▅▃▂▁   (yellow range = evidence)   1×    │  PlayerDock
└──────────────────────────────────────────────────────────────────────┘
```
- Split pane, default 46 / 54 %, draggable handle (persist in `localStorage`). Below 960 px: one pane at a time with a two-item switch (Record | Transcript); dock stays at the bottom.
- **During processing**, each region shows its true state: the transcript streams lines (newest line has a subtle caret, no fade-up); the record column shows each section heading with a quiet "Waiting" / "Writing…" line, and a section fills when its `record.section` event arrives. No skeleton shimmer.
- **StageRail:** three nodes with the stage label, model name (secondary text), a status (waiting / running with live label / done with seconds / failed). It collapses to a single line under 960 px. Clicking a finished node scrolls the relevant pane to the top.
- **Failure:** `ErrorPanel` slides into the top of the affected pane: title (bold), detail, the fix (with a copy button for commands) and **Retry from this step**. Earlier panes stay fully usable and exportable.

### 8.4 Components (behaviour)

- **`DropStage`:** whole stage is a drop target (`dragenter/over/leave/drop`) plus a visually hidden `<input type=file>`; keyboard-activatable. On drag-over, the bar heights transition from flat to a waveform (CSS `transform: scaleY`, staggered), and revert on leave. After selection show filename, duration (read via an `<audio>` element's metadata when possible) and a remove button.
- **`ChipInput`:** Enter or comma adds, Backspace removes the last, paste of comma/newline-separated text adds many. Max 40 chips.
- **`RecordPane`:** a single sheet (not stacked cards). Sticky `RecordNav` (Summary, Minutes, Decisions, Not settled, Tasks, Export) highlights the section in view. Header shows title, source filename, duration, and, if `record.dropped.length`, a text button "N model suggestions removed" that opens a small popover listing each dropped item with its reason.
- **`DecisionsSection`:** each decision: text (Literata 16), rationale in `--ink-soft` below, `EvidenceChip`. Empty state: "No decisions were agreed in this recording."
- **`UnresolvedSection`** "Discussed, not settled": rows with a kind label (Proposal / Open question / Deferred / Possible task, as plain text pills) plus text and `EvidenceChip`.
- **`TasksSection`:** semantic `<table>`, rules only, no row boxes. Columns: Task, Owner, Deadline, Source. Missing values render `Unspecified`. Empty state: "No tasks were assigned in this recording."
- **`EvidenceChip`:** pill showing the time of the first cited line (`▶ 01:05`; more lines show `+2`). Hover/focus → soft highlight (`--marker-wash`) on the cited transcript lines. Click → pinned highlight (marker bar), the transcript scrolls to the first line (centre), and `playRange(start-1s, end+0.5s)` plays once and stops. A second click on the same chip clears the pin.
- **`TranscriptPane`:** tabs **Raw**, **Refined**, **Compare**; search box (`/` focuses it) that filters/highlights matches. A "Follow playback" toggle keeps the active line in view; manual scrolling pauses it and shows a "Jump to playback" pill.
- **`SegmentRow`:** time gutter (60 px, tabular numerals, click to seek), text. Active line (current playback) gets a 3px `--blue` left bar. In **Raw** view, words of the active line gain `.spoken` as `currentTime` passes `word.end`. In **Refined** view, spans render as `<ins>` (blue underline); hover or focus shows `CorrectionPopover`: original struck-through → corrected, the reason, a switch "Applied", which calls `PATCH`.
- **`CompareRow`:** two columns, raw left and refined right, aligned by segment id, the same time gutter. Unchanged rows are collapsed into a single quiet row "12 lines unchanged" (click to expand). Below the list, `ChangesSummary`: "7 corrections applied, 2 blocked by safety checks"; the blocked group is expandable and shows each proposed edit with its plain-language `block_reason` (this makes the guardrails visible to reviewers).
- **`StaleBanner`:** shown above the record when `record_stale`: "You changed the transcript. The record still reflects the earlier version." + button **Rewrite record** (`rerun from document`).
- **`ExportSection`:** a ruled list of files with name, format and size and a download link each; two preview tabs (**Readable** = rendered Markdown, **Structured** = JSON, both from the server's export files); a parity line: "Markdown and JSON contain the same 2 decisions and 3 tasks" (from the server `parity` result, with an error state if `ok` is false); a **Download everything (.zip)** button.
- **`PlayerDock`:** wavesurfer instance created from the run's `peaks` and `audio_url` so it never has to decode the file.

```ts
WaveSurfer.create({
  container, url: audioUrl, peaks: [peaks], duration,
  height: 56, barWidth: 2, barGap: 1, barRadius: 1, normalize: true,
  waveColor: css("--ink-soft"), progressColor: css("--blue"), cursorColor: css("--ink"),
  plugins: [RegionsPlugin.create()],
})
```
Re-create on theme change (colours are resolved from CSS variables). Draw segment ticks as an overlaid absolutely-positioned layer (`left = start/duration*100%`). The evidence range is a region with `--marker` at 35 % alpha. Controls: play/pause, time, speed (0.75× / 1× / 1.25× / 1.5×), back 5 s. **VERIFY** option names against the installed wavesurfer version.

### 8.5 State

```ts
type Stage = "ingest" | "transcribe" | "refine" | "document";
interface RunState {
  id: string; filename: string; fake?: boolean;
  status: "queued" | "running" | "done" | "failed";
  stage: Stage | null; queuePosition?: number;
  duration?: number; audioUrl?: string; peaks?: number[];
  models: { stt: string; refiner: string; documenter: string };
  timings: Partial<Record<Stage, number>>;
  progress: Partial<Record<Stage, { done: number; total: number; label: string }>>;
  raw: Segment[]; refined: RefinedSegment[] | null; corrections: Correction[];
  profile?: DomainProfile;
  record: Partial<{ summary; minutes; decisions; unresolved; actions }> & { dropped?: Dropped[] };
  recordStale: boolean; warnings: AppError[]; error?: AppError;
}
```
- `runStore.load(id)`: `GET /api/runs/{id}`. If `status` is `queued|running`, instead subscribe to SSE from `after=0` and rebuild by reducing events. On `run.done|run.failed`, close the EventSource (otherwise it auto-reconnects), then do one final `GET` to replace state with the server's materialised version.
- Reducer (`applyEvent`) is a pure function covered by unit tests with a recorded event list.
- `playerStore`: `{ time, playing, duration, rate, seek(t), playRange(a,b), toggle() }`. The `PlayerDock` is the only owner of the wavesurfer instance.
- `focusStore`: `{ hoverIds, pinnedIds, setHover, pin, clear }`. `SegmentRow` reads it to render highlights.
- `lib/segments.ts`: `segmentAt(time)` by binary search; `rangeFor(ids)` → `[min start, max end]`.

### 8.6 Interactions and shortcuts

| Action | Result |
|---|---|
| Click evidence chip | Pin lines, scroll, play the range once |
| Hover evidence chip | Soft highlight on cited lines |
| Click time gutter | Seek and play from that line |
| Toggle a correction | `PATCH`, refined text updates, stale banner appears |
| `Space` | Play/pause (not while typing) |
| `←` / `→` | Back / forward 5 s |
| `J` / `K` | Next / previous transcript line |
| `1` / `2` / `3` | Raw / Refined / Compare |
| `/` | Focus transcript search |
| `Esc` | Clear pin and search |

### 8.7 Microcopy (use verbatim)

- Home title: **Drop a meeting recording**. Sub: "Get a transcript, corrected technical terms, decisions and tasks. Each one links back to the audio."
- Buttons: **Process recording**, **Retry from this step**, **Rewrite record**, **Download everything (.zip)**. Same verb in toasts: "Record rewritten."
- Stage labels: **Transcribe**, **Correct terms**, **Write the record**. Progress labels: "Listening 08:12 of 24:31", "Checking terms, chunk 3 of 9", "Writing summary / minutes / decisions / tasks / checking claims".
- Empty states: see 8.4. Errors: titles and fixes from the catalogue in 6.1. Errors never apologise and always say what to do.
- Warnings (non-blocking) appear as a single quiet line under the StageRail, with a dismiss.

### 8.8 Responsive and accessibility checks

360 px width has no horizontal scroll; every control is reachable by keyboard; screen reader hears stage changes through the live region; the table has proper `<th scope>`; focus is visible; reduced motion verified by toggling the OS setting.

---

## 9. Sample recording and evaluation

**Record this yourselves** (three voices read the script, ~5 min, quiet room, phone mic is fine; you own the rights so it can ship in `samples/`). Save as `samples/sample_meeting.mp3` and the script as `samples/meeting_script.md`. Names are Maya (lead), Priya, Dan.

```
Maya:  Okay, let's get started. Thanks for joining, Priya and Dan. Three things today: the session cache, the gRPC question, and audit prep.
Priya: On the session cache, we're still on Memcached, and p99 latency on login is around three hundred forty milliseconds. Our SLA says under two hundred fifty.
Dan:   Redis would fix that. In staging we saw p99 drop to about ninety milliseconds.
Maya:  Any objections to moving the session cache to Redis?
Priya: None from me.
Dan:   Same, none.
Maya:  Okay, then it's decided. We migrate the session cache from Memcached to Redis.
Maya:  Dan, can you write the Terraform module for the Redis cluster?
Dan:   Yes, I'll have the Terraform module done by Thursday.
Maya:  Great. We'll roll it out on the Kubernetes staging cluster first with a canary deployment, five percent of traffic.
Priya: Sounds right. I'd also suggest we move all internal services from REST to gRPC.
Dan:   That would cut serialization overhead, but it's a big change for the mobile team.
Maya:  I don't want to decide that today. Let's revisit gRPC next sprint, once we have numbers.
Priya: Fine by me.
Maya:  On PostgreSQL, we are not going to upgrade to version sixteen this quarter. The risk is too high before the audit.
Dan:   Agreed.
Priya: Right, the upgrade waits until next quarter.
Maya:  Priya, can you update the OAuth scopes documentation?
Priya: Sure, I'll take that. No date yet, I need to see how big it is.
Maya:  Fine. Now audit prep. The audit is on the fifteenth. Someone has to rotate the staging database credentials before then.
Dan:   Yeah, that needs doing.
Maya:  Okay, I'll leave that open for now. We need to work out who has time.
Maya:  Dan, maybe you could also look at the Grafana dashboards if you get time.
Dan:   We'll see.
Priya: One more thing: the Kafka consumer lag alert fired twice last week.
Maya:  Noted. No action on that for now.
Maya:  Last thing, we have twelve thousand dollars approved for the Redis cluster, and we must not exceed that.
Dan:   Understood.
Maya:  Thanks everyone. That's it.
```

**`samples/expected.json`** (written by hand from the script; used by `eval/check_sample.py`):

| Check | Expectation |
|---|---|
| Decision present | Move session cache from Memcached to Redis |
| Decision present, negation intact | Do not upgrade PostgreSQL to 16 this quarter |
| Not a decision | gRPC migration (must appear in `unresolved`, kind `deferred` or `proposal`) |
| Not a decision | Kafka alert, Grafana dashboards |
| Task | Terraform module for Redis, owner **Dan**, deadline **"by Thursday"** |
| Task | Update OAuth scopes documentation, owner **Priya**, deadline **null** |
| Task | Rotate staging DB credentials, owner **null**, deadline contains "audit" / "fifteenth" |
| Not a task | Grafana dashboards (must be `possible_task`) |
| Never | an owner on the credentials task; a deadline on the OAuth task; any calendar date |
| Numbers | 250, 340/ninety, 5 percent, 12,000 / sixteen all survive refinement unchanged |
| Terms | Kubernetes, PostgreSQL, OAuth, Terraform, gRPC, Memcached, Grafana, Kafka spelled correctly in the refined transcript |

**Run it two ways and keep both outputs.**
1. With the terms box filled, which is the realistic user flow.
2. With the terms box **empty**. This is what reviewers will do with unseen audio, and it is when the refiner has real work to do. If STT already gets every term right, say so in the technical write-up (that is a success, not a gap), and also record a short second clip speaking the jargon quickly and unclearly so there are real corrections to show.

Also test one external recording you have not seen (any public meeting audio you are allowed to use) before submitting; this is the closest rehearsal of the evaluation.

`eval/check_sample.py runs/<id>`: loads `meeting_record.json` + `refined_transcript.json`, evaluates each row above, prints PASS/FAIL, exits non-zero on failure.

---

## 10. Build phases

Each phase lists what to build and how to prove it.

### Phase 0: Environment and model bake-off (45–60 min)
1. Create the repo, venv, `requirements.txt`: `fastapi uvicorn[standard] python-multipart pydantic>=2 pyyaml faster-whisper av numpy ollama rapidfuzz jellyfish jinja2 pytest httpx nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*` (the last two only on GPU machines).
2. Install Ollama; `ollama pull` the three profile models you will use (`qwen3:8b`, `gemma3:12b` for standard). Check `ollama list` for the tags actually available and also try newer ones (Gemma 4 and Qwen 3.5/3.6 sizes that fit your VRAM). **VERIFY** all tags.
3. Quick bake-off (30 min max): paste the section 9 transcript (typed by hand) into each candidate with the `doc_decisions` and `doc_actions` prompts; keep the pair that gets the section 9 table right and is fast enough. Update `config.yaml` only.
4. Confirm `faster-whisper` runs on the GPU for a 10 s clip; if not, solve it now or accept the CPU profile.

**Accept:** a script transcribes a clip, and `ollama` returns schema-valid JSON for a toy schema.

### Phase 1: Backend skeleton
Write `config.py`, `errors.py`, `schemas.py`, `store.py`, `ingest.py`, `health.py`, `gpu.py`, `main.py` (health, runs list, static, SPA fallback), `run.py`.
**Accept:** `pytest tests/test_ingest.py` passes: empty file → `EMPTY_FILE`; a text file renamed `.mp3` → `UNREADABLE_FILE`; a generated silent wav → `SILENT_AUDIO`; `.txt` → `UNSUPPORTED_TYPE`; a 3 s 440 Hz tone → ok, produces `audio.wav` and 1600 peaks. `GET /api/health` returns a sensible body.

### Phase 2: Speech stage
`stt.py` with lazy segment streaming, fallbacks and hallucination filter; `cli.py` that runs a stage and prints segments.
**Accept:** `python -m verbatim.cli samples/sample_meeting.mp3 --stage stt` prints a readable transcript; timings logged; GPU memory released afterwards (`nvidia-smi`).

### Phase 3: Refinement stage
`llm/`, `refine/{hints,guardrails,apply,stage}.py`, `prompts/refine_*.md`.
**Accept:** `tests/test_guardrails.py` (each of the 7 rules blocks a crafted proposal; a valid one passes), `tests/test_apply.py` (spans offsets correct for 0, 1, 2 and overlapping corrections; propagation), `tests/test_hints.py` ("post gress Q L" → PostgreSQL, "cooper netties" → Kubernetes). A manual run on the sample transcript with the glossary box empty produces corrections and none of them touch a number or negation.

### Phase 4: Documentation stage
`document/{stage,grounding,verify}.py`, `prompts/doc_*.md`.
**Accept:** `tests/test_grounding.py` (invented owner → null, invented deadline → null, unsupported decision dropped, generic owner "we" → null, duplicates merged). Manual run on the sample passes every row of the section 9 table with `eval/check_sample.py`. Tune prompts here, not the code.

### Phase 5: Pipeline, jobs, API, exports
`pipeline.py`, `jobs.py`, SSE and all routes in 6.8, `export/*`, `tests/test_exporter.py` (JSON and Markdown contain the same decisions and tasks; `Unspecified` appears for null; empty lists render the empty-state sentences), `tests/test_api.py` (upload invalid files → 4xx with an `AppError`; SSE replay after reconnect continues at `after`).
**Accept:** `curl -F file=@samples/sample_meeting.mp3 localhost:8000/api/runs` → `run_id`; `curl -N .../events` shows the full event sequence ending with `run.done`; all export files download; `bundle.zip` opens; `eval/check_sample.py` passes. **Checkpoint: the whole ML requirement set now works through an API.**

### Phase 6: Frontend foundation (can start in parallel with Phases 2–5 using `VERBATIM_FAKE=1`)
Scaffold Vite, tokens/base CSS, fonts, `Topbar`, theme toggle, router, `api/` (client + SSE), `runStore` + reducer with unit tests, `SplitPane`, `StageRail`, `ErrorPanel`.
**Accept:** `npm run dev` with the fake backend shows the empty workspace shell in light and dark themes; reducer tests pass using an event list recorded from the fake pipeline.

### Phase 7: Home and live workspace
`Home` (`DropStage`, `ChipInput`, `Preflight`, `HealthList`, `RecentRuns`, sample button), `RunView` with `TranscriptPane` (Raw view streaming), `RecordPane` sections filling from `record.section` events.
**Accept:** with the fake backend, dropping a file moves to `/r/<id>`, transcript lines appear one at a time, sections fill in order; refreshing the page mid-run rebuilds the same state from the event log; invalid files show catalogue errors without any upload.

### Phase 8: Player and evidence linking (the selling point)
`PlayerDock` (wavesurfer with peaks, regions, ticks), `playerStore`, `focusStore`, `EvidenceChip`, active-line follow, word highlighting, keyboard shortcuts, Refined and Compare views, `CorrectionPopover`, `ChangesSummary`, `StaleBanner`.
**Accept:** the section 8.6 interaction table passes manually; click a decision → correct lines highlight, the waveform region shows and exactly that range plays; toggle a correction → refined line changes and the stale banner appears; **Rewrite record** reruns only the document stage.

### Phase 9: Export, polish, resilience
`ExportSection` with previews and parity, dropped-items popover, warning line, error states for every catalogue code (trigger each one at least once), 360 px layout, reduced motion, focus rings, empty states, run history, delete.
**Accept:** the checklist in 8.8; kill Ollama mid-run → `OLLAMA_UNREACHABLE` panel with earlier output intact and **Retry from this step** works once Ollama is back; remove the GPU libs → CPU warning and a completed run.

### Phase 10: Sample, docs, demo (reserve at least 3 hours)
1. Record the sample (section 9), process it for real through the UI, copy `runs/<id>/*` outputs to `samples/outputs/`.
2. `README.md` (section 12), `docs/TECHNICAL.md`, `docs/DEMO_SCRIPT.md`.
3. Fresh-machine dry run: new venv, follow the README literally, process an unseen recording. Fix whatever the README missed.
4. Record the demo video.

### Phase 11: Optional extras, only with time to spare (in this order)
1. **Speaker labels:** `pyannote.audio` diarization when `HF_TOKEN` is set (needs the user to accept the model terms on Hugging Face), assigning `speaker` per segment by maximum overlap; show a speaker column only when labels exist, with a rename table; never use a raw `SPEAKER_nn` as an owner.
2. **OpenAI-compatible LLM adapter** (`llm/openai_client.py`) selected by `llm.provider`, for machines without a GPU.
3. **Word export** (`python-docx`, rendered from the same record).
4. WER check (`jiwer`) on a public meeting excerpt with a reference transcript.

---

## 11. Team split, schedule, cut line

**Split for three people**
- **A, ML backend:** Phases 0, 2, 3, 4 (STT, refiner, documenter, prompts, guardrails, grounding).
- **B, Frontend:** Phases 6, 7, 8, 9 (starts against the fake backend as soon as the schemas and event list in sections 5 and 6.7 are agreed).
- **C, Integration:** Phases 1, 5, 10 (ingest, jobs, API, exports, tests, sample recording, README, tech description, demo video).
Two people: merge A and C. One person: do 1 → 5 first, then 6 → 9, skip Phase 11.

**Schedule** (today is Mon 5 Oct, deadline Wed 7 Oct)
- Mon evening: Phase 0, 1, started 2/3 and 6. Sample script recorded.
- Tue: Phases 2–5 done by early afternoon (**end-to-end through the API**), Phases 7–8 done by night.
- Wed morning: Phase 9, 10, buffer, submit well before the cutoff. Do not start new features on Wednesday.

**Cut line, in this order, if behind**
1. Phase 11 entirely.
2. Propagation (Step F), word-level highlighting, dropped-items popover.
3. Compare view (keep Raw and Refined tabs; the corrections list in `ChangesSummary` stays).
4. Verify pass (call 5).
5. Resizable panes (fixed 46/54 split).
Never cut: the evidence chips, guardrails, grounding, Unspecified rendering, both export formats, the error catalogue, the README.

---

## 12. Deliverables checklist

- [ ] Repo/archive with source, `prompts/`, `requirements.txt`, `config.yaml`, built `static/`, README.
- [ ] README: prerequisites (Python 3.11, Ollama, optional NVIDIA driver + CUDA 12 libs), `pip install -r requirements.txt`, `ollama pull …` (exact commands for each profile), `python run.py`, what the health indicators mean, troubleshooting (GPU fallback, Windows DLLs, port in use), how to swap models in `config.yaml`, how to run tests, how to rebuild the frontend.
- [ ] `docs/TECHNICAL.md` (short): the three models and their roles, a data-flow diagram (audio → `audio.wav` → raw transcript → corrections → refined transcript → four record sections → verify → exports), prompt design, the guardrails table (6.5), the grounding rules (6.6), known limits (English only, duration caps, no speaker names unless said), and how outputs move between stages.
- [ ] `samples/`: the recording, `meeting_script.md`, and the real outputs (raw/refined transcripts, `corrections.csv`, `meeting_record.md`/`.json`).
- [ ] Demo video (3–4 min): see below.
- [ ] Working app on the demo machine; run `eval/check_sample.py` on the final build.

**Demo script (3–4 min)**
1. Home: show the health line (models ready). Drop `sample_meeting.mp3`; enter participants only.
2. Narrate while it runs: transcript streams, corrections land on the lines (the one flash), sections fill in.
3. Click the Redis decision: lines highlight, audio plays those seconds.
4. Open Compare: show applied corrections and one **blocked** edit with its reason ("Would change a number").
5. Show Tasks: Dan/Thursday, Priya with Unspecified deadline, credentials task with Unspecified owner. Show "Discussed, not settled": gRPC and the Grafana possible task.
6. Toggle one correction off, show the stale banner, click **Rewrite record**.
7. Export: show the parity line, open Markdown and JSON previews, download the zip.
8. Error moment: upload a renamed `.txt` file → clear message, no crash.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| GPU libraries fail on the reviewer's machine | Automatic CPU fallback, health panel with exact fix commands, tested on a clean venv in Phase 10 |
| Ollama model tags or sizes differ from this plan | All tags in `config.yaml`; Phase 0 bake-off; `MODEL_MISSING` shows the pull command |
| 8 GB VRAM too small for the documenter with a long context | `num_ctx` per profile, explicit unload between stages, duration caps, `lite` profile |
| Small LLM invents owners/deadlines | Prompt rules + grounding + verify pass + UI shows what was removed |
| STT is so accurate there is nothing for the refiner to fix | Only user-supplied terms go to STT; refiner profile infers terms itself; show the guardrail-blocked list; add a jargon-heavy second clip |
| Streaming/SSE reconnect bugs | Event log on disk with monotonic `seq`; client closes on terminal events; final authoritative `GET` |
| Time | Cut line in section 11; end-to-end through the API by Tuesday afternoon |
| Reviewer cannot build the frontend | Built `static/` is committed; Node is only needed to modify the UI |
