# AI-Powered Meeting Assistant — Solution Document

*Requirements, architecture and design · ML Bootcamp AI Challenge · Version 1.0 (2026-10-04)*

## 0. Overview & Assumptions

**Problem.** Build a local, open-source app that turns a recorded English meeting into an accurate written record. It runs three coordinated model stages:
1. A speech-to-text model produces the raw transcript.
2. LLM #1 refines domain terminology in that transcript.
3. A separate LLM #2 generates structured minutes, key decisions and action items.

The app has an interactive UI that shows raw transcript, refined transcript and the generated record, with all outputs downloadable.

**Guiding principle.** Outputs must reflect only what was said. The system never invents decisions, owners or deadlines; anything not stated is shown as *Unspecified*. Each design choice below is also checked against the evaluation rubric:

| Criterion | Points |
|---|---|
| Transcription | 20 |
| Refinement | 20 |
| Minutes and decisions | 25 |
| Action items | 15 |
| End-to-end app | 15 |
| Submission quality | 5 |

**Scope:**
- English meeting audio or video files, processed from upload to downloadable results in one run.
- Speaker diarization is included.
- Fully offline inference with open-source models.

**Target platform:**
- Lenovo LOQ (14th-gen Intel) with an NVIDIA RTX GPU.
- Reference configuration: RTX 4060 Laptop, 8 GB VRAM, 16–32 GB RAM, CUDA 12.x.
- Configuration profiles for 6 GB and 12 GB+ GPUs.
- Automatic CPU fallback, slower but working.
- Only one model is on the GPU at a time.

**Technology choices:**
- Python
- Streamlit UI
- WhisperX (faster-whisper) + pyannote for speech
- Ollama for the two LLMs

**Out of scope:**
- Real-time or live transcription
- Languages other than English
- Multi-user accounts and cloud deployment

---

## 1. Requirements

### 1.1 Functional requirements
| ID | Requirement | Source |
|---|---|---|
| FR-1 | Upload one English meeting audio or video file (wav, mp3, m4a, flac, ogg, webm, mp4) | Audio input |
| FR-2 | Convert speech to a raw transcript with timestamps and speaker labels, and show it | STT |
| FR-3 | Refine the raw transcript with LLM #1. Fix terms, acronyms and domain words. Keep names, numbers, negation and commitments unchanged | Refinement |
| FR-4 | Show raw and refined transcripts side by side, with the changes highlighted and listed | Refinement |
| FR-5 | Generate a summary, organized minutes, key decisions and action items with LLM #2, using the refined transcript as input | Documentation |
| FR-6 | Each action item has a description. Owner and deadline appear only when they were stated; otherwise they show as "Unspecified" | Action items |
| FR-7 | Separate agreed decisions from proposals. Never present an unstated assignment as a confirmed task | Decisions |
| FR-8 | Return empty lists when there are no decisions or tasks | Output req. |
| FR-9 | Run STT → refine → document in that order, in one run, with stage-by-stage status | Workflow |
| FR-10 | Download each output: raw transcript, refined transcript, minutes, decisions, actions. Provide the record as both Markdown (human-readable) and JSON (machine-readable) with the same content | Output req. |
| FR-11 | Show clear errors for unsupported, empty, unreadable, silent or too-long files, and for model, GPU or runtime failures | Requirements |
| FR-12 | Optional inputs: a domain glossary and participant names, used to guide STT and refinement. Optionally rename speakers (SPEAKER_00 → "Priya") before documentation runs | Quality |

### 1.2 Non-functional requirements
- **Faithfulness:** every decision and action carries an evidence quote and segment IDs. A deterministic validator removes anything it can't ground.
- **Determinism:** temperature 0 and a fixed seed for both LLMs. Prompts are versioned files.
- **Offline / local:** no cloud inference. Model weights download once; the HF token is used only to download the pyannote weights.
- **Performance target (RTX 4060):** a 30-minute meeting should take **about 3–6 minutes** end to end:
  - STT plus alignment plus diarization: about 1–2 minutes
  - Refinement: about 1–2 minutes
  - Documentation: about 1–2 minutes
- **VRAM safety:** stages run one after another, and GPU memory is freed explicitly between them. If CUDA isn't available, the app falls back to CPU automatically, slower but working.
- **Reproducibility:** every run saves all intermediate files to `runs/<run_id>/`. Nothing is hardcoded.

---

## 2. Model selection (best open-source options for an 8 GB GPU)

| Stage | Primary model | Runtime | VRAM | Why |
|---|---|---|---|---|
| Speech-to-text | **Whisper `large-v3`** (the most accurate open Whisper) | **WhisperX** (faster-whisper / CTranslate2 backend, fp16, batched) | ~4–5 GB | Best open-source English WER. WhisperX adds VAD-based batching (fast, and fewer hallucination loops on silence) |
| Word alignment | `wav2vec2` English alignment model (WhisperX default) | WhisperX | ~1 GB | Precise word timestamps, so speakers can be assigned word by word |
| Diarization | **`pyannote/speaker-diarization-3.1`** | pyannote.audio on CUDA | ~1–2 GB | The leading open diarization pipeline. Speaker labels let the documenter attribute "I'll do it" to the right owner |
| LLM #1 – refinement | **Qwen2.5-14B-Instruct** (Q4_K_M, ~9 GB) on 12 GB+; **Qwen2.5-7B-Instruct** (Q6_K, ~6.3 GB) on 8 GB, the default | Ollama (llama.cpp, CUDA) | fits in 8 GB | Strong at technical, scientific and coding vocabulary. Reliable at following instructions and producing JSON |
| LLM #2 – documentation | **Gemma-3-12B-it** (QAT Q4_0, ~8 GB, 128k context) as the default; fallback **Llama-3.1-8B-Instruct** (Q5_K_M) on 6 GB | Ollama | about 8 GB (a few layers offload to CPU if needed) | A different model family from LLM #1, so the stages are clearly distinct. Strong at long-context summarization and extraction |

Notes:
- The two LLM roles use **different models from different families**, which clearly satisfies "a separate language model". Both are named in the UI and the docs.
- Ollama's **JSON-schema structured output** (`format=<pydantic schema>`) means every response parses and matches its schema.
- `keep_alive=0` unloads each LLM after its stage. WhisperX and pyannote models are deleted, followed by `torch.cuda.empty_cache()`, before the LLM stages start.
- All model tags live in `config.yaml`, so a newer or stronger model (for example Qwen3) can be swapped in without code changes. The README explains how to benchmark a swap.

---

## 3. Architecture

```
┌──────────────────────── Streamlit UI (app.py) ─────────────────────────┐
│ Upload · glossary/participants · options · Run · live status · tabs ·   │
│ speaker renaming · downloads                                            │
└──────────────┬─────────────────────────────────────────────▲───────────┘
               │ PipelineRequest                             │ RunResult + progress events
┌──────────────▼─────────────── Pipeline Orchestrator ───────┴───────────┐
│ validate → transcribe → align → diarize → [GPU free] → refine →         │
│ [unload] → document → ground/validate → export                          │
│ each stage: typed I/O, timing, GPU cleanup, StageError(user_message)    │
└──┬───────────┬────────────────┬────────────────┬──────────────┬────────┘
   │           │                │                │              │
 Audio-      Speech Service   Refiner (LLM#1)   Documenter      Exporter
 Validator   WhisperX large-v3 Ollama Qwen2.5    (LLM#2) Ollama  MD/JSON/TXT/
 (PyAV/ffmpeg) + wav2vec2 align + guardrails     Gemma-3-12B     SRT/CSV/ZIP
             + pyannote 3.1                      + grounding        │
                                                                     ▼
                                                              runs/<run_id>/
```

Data flow, with every artifact saved to disk:
`audio` → `raw_transcript.json` (segments: id, start, end, speaker, text, words[]) → `refined_transcript.json` (same segment IDs, plus `corrections[]`) → `meeting_record.json` → `meeting_record.md` + `.txt`/`.srt` transcripts + `bundle.zip`.

---

## 4. Detailed design

### 4.1 Data models (`meeting_assistant/schemas.py`, Pydantic v2)
- `Segment {id:int, start:float, end:float, speaker:str|None, text:str}`
- `Transcript {segments:[Segment], language:str, duration:float, models:{asr, align, diarization}}`
- `Correction {segment_id, original, corrected, reason}`
- `RefinedTranscript {segments:[Segment], corrections:[Correction], reverted:[int], model:str}`
- `Decision {decision:str, rationale:str|None, evidence:str, segment_ids:[int]}`
- `ActionItem {task:str, owner:str|None, deadline:str|None, evidence:str, segment_ids:[int]}`
- `MeetingRecord {title, summary, attendees:[str], minutes:[{topic, points:[str]}], decisions:[Decision], action_items:[ActionItem], open_questions:[str], models:{stt, refiner, documenter}, generated_at}`

In the UI and Markdown export, a `None` owner or deadline shows as **"Unspecified"**. In JSON it stays `null`.

### 4.2 Audio validation (`audio.py`)
- Check that the extension is on the allow-list. Probe the file with ffmpeg/PyAV. Reject it if it can't be decoded, has no audio stream, or has a duration of 0. Enforce size and duration limits from config (for example 500 MB and 3 h).
- Decode to 16 kHz mono. If VAD finds no speech, raise "No speech detected in the recording".
- Whisper language detection: if the language isn't English, show a warning and force `language="en"`.
- Failures raise `AudioError(user_message)`, which the UI shows in `st.error`. CUDA out-of-memory raises `GPUError`, which gives advice (pick a smaller profile or close other GPU apps) and retries with a smaller batch size.

### 4.3 Speech stage (`stt.py`, `diarize.py`)
- `whisperx.load_model("large-v3", device="cuda", compute_type="float16", language="en", asr_options={beam_size:5, temperatures:[0], condition_on_previous_text:False, initial_prompt:<glossary + participant names>})`
  - The initial prompt pushes the decoder toward correct domain spellings and name spellings. This is the first line of defence for terminology.
- `batch_size=16` (8 on the 6 GB profile). Then `whisperx.align(...)` for word timestamps.
- `pyannote/speaker-diarization-3.1` on CUDA, with optional `min_speakers`/`max_speakers` from the UI. `whisperx.assign_word_speakers` then attaches a speaker to each word and segment.
- If the HF token is missing, diarization is skipped with a warning, not an error.
- Free GPU memory after this stage.

### 4.4 Refinement stage, LLM #1 (`refiner.py`, prompt `prompts/refine_v1.md`)
- **Chunking:** windows of about 60 segments (about 2.5k tokens) with an 8-segment overlap. Only the non-overlap part of each window is edited.
- **Context:** the glossary and participant names, plus a short "domain profile" generated once from the whole transcript. The profile covers the topic and a list of likely domain terms, so the model can tell that "cooper netties" should be "Kubernetes".
- **Prompt rules:** fix only likely mis-recognitions of terms, acronyms, product names, names and jargon, plus obvious casing and punctuation. Never add, remove or reorder content. Never change numbers, dates, negations or commitment wording. Never summarize. If unsure, leave the text unchanged. Few-shot examples include one where the right move is "no change".
- **Output schema:** `{segments:[{id, text}], corrections:[{id, original, corrected, reason}]}`.
- **Guardrails (`guardrails.py`), checked deterministically per segment:**
  1. The segment IDs must match the input exactly.
  2. Numbers must match after normalizing spoken numbers to digits (`text2num`).
  3. The count of negation tokens must not change.
  4. Edit ratio must be ≤ 0.35, and length change ≤ 25%.
  5. Proper nouns must be preserved unless the model explicitly listed them as a correction.

  A segment that fails is **reverted to the raw text** and recorded in `reverted[]`.
- **UI:** a word-level diff (`difflib`) with highlights, a corrections table, and a count of reverted segments.

### 4.5 Documentation stage, LLM #2 (`documenter.py`, prompts `document_v1.md`, `reduce_v1.md`)
- **Input:** the refined transcript as `[id] [mm:ss] Speaker: text`, using the renamed speakers when the user renamed them.
- **Context size:** `num_ctx=32768`. A meeting of about 90 minutes fits in one pass. Longer meetings use map-reduce: extract candidates per chunk, then merge and remove duplicates in a reduce pass.
- **Two focused calls, which are more accurate than one large one:**
  - (a) summary + minutes + open questions
  - (b) decisions + action items
- **Prompt rules:**
  - A decision counts only if it was explicitly agreed or confirmed. Proposals go to open questions or minutes.
  - A task counts only if someone committed to it or was assigned it.
  - Owner is set only if a person was named, or if the speaker said "I'll…" and a speaker label exists. Otherwise it is null.
  - Deadline is copied as said ("by Friday"), never turned into a computed date.
  - Every item has a verbatim `evidence` quote and `segment_ids`. Empty lists are allowed.
- **Grounding validator (`grounding.py`):**
  - The evidence quote must fuzzy-match the cited segments (rapidfuzz ≥ 80). If it doesn't, the item is dropped.
  - The owner must appear in the transcript text, the speaker labels or the renamed participants. If not, owner is set to null.
  - The deadline must appear in the cited segments. If not, deadline is set to null.
  - If validation fails, retry once with error feedback.
- **Optional self-check pass** (on by default, since it's cheap on a GPU): the documenter model gets each decision with its evidence and answers "agreed / proposal / unclear". Anything other than "agreed" moves to open questions.

### 4.6 Orchestrator (`pipeline.py`)
- `run_pipeline(audio_path, options, on_progress) -> RunResult` runs the stages in sequence. Each stage is timed and saved under `runs/<run_id>/`, and GPU memory is cleaned up between stages.
- Typed exceptions (`AudioError`, `GPUError`, `ModelUnavailableError`, `LLMOutputError`) carry user-facing messages. If a later stage fails, results from earlier stages stay visible and downloadable.
- A startup health check covers CUDA availability and the GPU name and VRAM, Ollama reachability and pulled models, and the HF token. Each failure shows the exact command that fixes it.
- A CLI (`python -m meeting_assistant.cli file.mp3 --profile 8gb`) runs the same pipeline. It is used for sample outputs and evaluation.

### 4.7 Streamlit UI (`app.py`)
- **Sidebar:** hardware profile (auto-detected from VRAM), diarization toggle, min and max speakers, glossary, participant names, and model health indicators with the GPU name.
- **Main area:** uploader with an audio player → **Process** → `st.status` live steps (Validating ✓ → Transcribing ✓ → Aligning ✓ → Diarizing ✓ → Refining 4/7 → Generating minutes → Validating ✓), with the time each stage took.
- **Tabs:**
  1. Raw transcript (timestamps and speakers, with an optional speaker-rename table and a "Regenerate record" button)
  2. Refined transcript (diff and corrections)
  3. Summary & minutes
  4. Decisions
  5. Action items (Task / Owner / Deadline / Evidence; "Unspecified" shown greyed out)
  6. Downloads (individual files plus a ZIP)
- Results are kept in `st.session_state`. An "About / Models" panel names all models and their roles.

### 4.8 Exports (`exporter.py`)
- `raw_transcript.{txt,srt,json}`, `refined_transcript.{txt,json}`, `corrections.csv`, `meeting_record.json`, and `meeting_record.md` (also `.docx` via python-docx), all bundled into `bundle.zip`.
- The Markdown and DOCX are **rendered from the same `MeetingRecord` object** (Jinja2), so the human-readable and JSON outputs always match.

---

## 5. Repository layout
```
meeting-assistant/
├── app.py                         # Streamlit UI
├── meeting_assistant/
│   ├── config.py  schemas.py  audio.py  stt.py  diarize.py  gpu.py
│   ├── refiner.py  guardrails.py  documenter.py  grounding.py
│   ├── llm_client.py              # Ollama wrapper: structured output, retries, keep_alive=0
│   ├── pipeline.py  exporter.py  cli.py
│   └── templates/meeting_record.md.j2
├── prompts/ refine_v1.md  domain_profile_v1.md  document_minutes_v1.md  document_actions_v1.md  verify_decisions_v1.md  reduce_v1.md
├── config.yaml                    # profiles: 6gb / 8gb (default) / 12gb+, model tags, thresholds
├── eval/                          # WER (jiwer) + adversarial-script checks
├── tests/                         # guardrails, grounding, exporter parity, audio errors
├── samples/                       # shareable recording + generated outputs
├── docs/SOLUTION.md  docs/TECHNICAL_DESCRIPTION.md
├── requirements.txt / environment.yml   # torch (CUDA 12), whisperx, pyannote.audio, streamlit, pydantic, ollama, rapidfuzz, text2num, jinja2, python-docx, jiwer
└── README.md                      # CUDA/driver setup, `ollama pull ...`, HF token for pyannote, run commands
```

## 6. Implementation plan
1. Scaffold the repo, config profiles, schemas and the GPU helper.
2. Audio validation and the speech stage (WhisperX + pyannote), plus the CLI.
3. The Ollama client and the refiner with its guardrails, plus tests.
4. The documenter with grounding and the self-check, plus tests.
5. The orchestrator, exporter and Streamlit UI.
6. Evaluation scripts, a sample recording with its outputs, the README, the technical description and a demo script.

Unit tests for guardrails, grounding and the exporter don't need a GPU, so they run on any machine, including CPU-only ones.

## 7. Verification
- **Unit tests (pytest, no GPU):**
  - Guardrails reject changed numbers or negations.
  - Grounding sets invented owners and deadlines to null and drops unsupported decisions.
  - Markdown, DOCX and JSON contain the same items.
  - The audio validator handles empty, corrupt, wrong-type and silent files.
- **STT accuracy:** WER with `jiwer` on AMI meeting excerpts with reference transcripts. Compare `large-v3` with `distil-large-v3` to confirm the default.
- **Adversarial script recording:**
  - a proposal that is never agreed
  - a task with no owner
  - a task with an owner and a deadline
  - negations, numbers and names
  - jargon that Whisper tends to mishear

  Check each expected result in the outputs.
- **End to end on the LOQ:** `streamlit run app.py` → upload a new recording → check that every tab works, all downloads work and stage times are shown. Confirm error messages for a `.txt` file, a 0-byte file and a silent wav. Run `nvidia-smi` during the run to confirm peak VRAM stays under budget.
