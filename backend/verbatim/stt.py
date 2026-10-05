from __future__ import annotations

import gc
import logging
import time
import wave
from pathlib import Path
from typing import Callable, Generator

import numpy as np

from verbatim.config import get_config
from verbatim.errors import PipelineError, make_app_error
from verbatim.gpu import get_gpu_info, prepare_cuda
from verbatim.schemas import RawTranscript, Segment, Word
from verbatim.store import (
    append_event,
    get_run_dir,
    load_meta,
    save_json,
    save_meta,
)

logger = logging.getLogger("verbatim.stt")


def format_time(seconds: float) -> str:
    """Format seconds to MM:SS or HH:MM:SS."""
    s = max(0, int(round(seconds)))
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def build_prompt(
    glossary: list[str] | None = None,
    participants: list[str] | None = None,
) -> str | None:
    """Build initial prompt for STT containing only user-supplied terms and participants."""
    parts = []
    if participants:
        clean_parts = [p.strip() for p in participants if p.strip()]
        if clean_parts:
            parts.append(f"Participants: {', '.join(clean_parts)}.")
    if glossary:
        clean_terms = [t.strip() for t in glossary if t.strip()]
        if clean_terms:
            parts.append(f"Terms: {', '.join(clean_terms)}.")
    if not parts:
        return None
    return "Meeting transcript. " + " ".join(parts)


def load_audio_for_detection(audio_path: Path, max_seconds: float = 30.0) -> np.ndarray:
    """Read up to max_seconds of 16kHz mono audio as float32 array in [-1.0, 1.0]."""
    with wave.open(str(audio_path), "rb") as wf:
        framerate = wf.getframerate()
        n_frames = min(int(max_seconds * framerate), wf.getnframes())
        raw = wf.readframes(n_frames)
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return pcm


def load_whisper_model(
    model_name: str | None = None,
    cpu_model_name: str | None = None,
    on_warning: Callable[[dict], None] | None = None,
):
    """Load WhisperModel with GPU-first strategy and automatic CPU fallback."""
    prepare_cuda()
    from faster_whisper import WhisperModel

    cfg = get_config()
    target_model = model_name or cfg.active_profile_config.stt.model
    fallback_model = cpu_model_name or cfg.stt.cpu_model

    gpu_info = get_gpu_info()
    if gpu_info.available:
        try:
            logger.info("Attempting to load WhisperModel '%s' on CUDA (float16)...", target_model)
            model = WhisperModel(target_model, device="cuda", compute_type="float16")
            return model, "cuda", target_model
        except RuntimeError as e:
            err_msg = str(e).lower()
            if any(term in err_msg for term in ("cuda", "cudnn", "cublas", "out of memory")):
                logger.warning("CUDA float16 failed (%s); trying int8_float16...", e)
                try:
                    model = WhisperModel(target_model, device="cuda", compute_type="int8_float16")
                    return model, "cuda", target_model
                except RuntimeError as e2:
                    logger.warning("CUDA int8_float16 failed (%s); falling back to CPU...", e2)
            else:
                logger.warning("Unexpected RuntimeError on CUDA: %s; falling back to CPU", e)

    # Fallback to CPU
    if on_warning:
        on_warning(make_app_error("GPU_FALLBACK").model_dump())

    logger.info("Loading WhisperModel '%s' on CPU (int8)...", fallback_model)
    try:
        model = WhisperModel(fallback_model, device="cpu", compute_type="int8")
    except Exception:
        logger.info("int8 compute_type failed on CPU, falling back to default/float32...")
        model = WhisperModel(fallback_model, device="cpu", compute_type="default")

    return model, "cpu", fallback_model


def collapse_repeated_runs(
    segments_iter: Generator[tuple[Any, str], None, None],
) -> Generator[tuple[Any, str], None, None]:
    """Collapse runs of >= 3 identical consecutive texts to one single segment."""
    run_buffer: list[tuple[Any, str]] = []
    current_key: str | None = None

    for raw_seg, clean_text in segments_iter:
        key = clean_text.lower().strip()
        if key == current_key:
            run_buffer.append((raw_seg, clean_text))
        else:
            if run_buffer:
                if len(run_buffer) >= 3:
                    # Collapse to the first segment
                    yield run_buffer[0]
                else:
                    for item in run_buffer:
                        yield item
            run_buffer = [(raw_seg, clean_text)]
            current_key = key

    if run_buffer:
        if len(run_buffer) >= 3:
            yield run_buffer[0]
        else:
            for item in run_buffer:
                yield item


def transcribe_audio(
    run_id: str,
    model_override: str | None = None,
    progress_callback: Callable[[float, float, str], None] | None = None,
) -> RawTranscript:
    """Run STT stage on ingested audio.wav for run_id."""
    cfg = get_config()
    run_dir = get_run_dir(run_id, must_exist=True)
    audio_wav = run_dir / "audio.wav"

    if not audio_wav.exists():
        raise PipelineError(code="INTERNAL", detail=f"audio.wav missing for run {run_id}")

    meta = load_meta(run_id)
    glossary: list[str] = meta.get("glossary", [])
    participants: list[str] = meta.get("participants", [])

    with wave.open(str(audio_wav), "rb") as wf:
        total_duration = float(wf.getnframes() / wf.getframerate())

    def emit_warning(err_dict: dict):
        append_event(run_id, "warning", err_dict)
        warnings = meta.get("warnings", [])
        warnings.append(err_dict)
        save_meta(run_id, {"warnings": warnings})

    # 1. Load model with GPU/CPU strategy
    model, device, actual_model_name = load_whisper_model(
        model_name=model_override,
        on_warning=emit_warning,
    )

    t0 = time.time()
    append_event(
        run_id,
        "stage.started",
        {"stage": "transcribe", "model": actual_model_name},
    )
    save_meta(run_id, {"stage": "transcribe"})

    try:
        # 2. Language detection on first 30 seconds
        detected_language = "en"
        try:
            audio_detect_pcm = load_audio_for_detection(audio_wav, max_seconds=30.0)
            lang, lang_prob, _ = model.detect_language(audio=audio_detect_pcm)
            if lang != "en" and lang_prob > 0.6:
                not_eng_error = make_app_error(
                    "NOT_ENGLISH",
                    detail=f"Detected language '{lang}' with probability {lang_prob:.2f}.",
                )
                emit_warning(not_eng_error.model_dump())
        except Exception as exc:
            logger.warning("Language detection failed: %s; proceeding with 'en'", exc)

        # 3. Transcribe stream
        initial_prompt = build_prompt(glossary=glossary, participants=participants)
        hotwords = " ".join(glossary) if glossary else None

        raw_segments_gen, info = model.transcribe(
            str(audio_wav),
            language="en",
            beam_size=cfg.stt.beam_size,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": cfg.stt.vad_min_silence_ms},
            word_timestamps=True,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
            hotwords=hotwords,
        )

        # 4. Generator applying hallucination filter
        def filter_generator():
            for s in raw_segments_gen:
                text = s.text.strip()
                if not text:
                    continue
                # Hallucination filter: no_speech_prob > 0.6 and avg_logprob < -1.0
                no_speech_prob = getattr(s, "no_speech_prob", 0.0)
                avg_logprob = getattr(s, "avg_logprob", 0.0)
                if no_speech_prob > 0.6 and avg_logprob < -1.0:
                    logger.debug("Dropped hallucination segment: %r (no_speech=%.2f, logprob=%.2f)", text, no_speech_prob, avg_logprob)
                    continue
                yield s, text

        # 5. Collapse >= 3 repetitions and emit kept segments
        kept_segments: list[Segment] = []
        seg_idx = 0

        for raw_s, text in collapse_repeated_runs(filter_generator()):
            # Parse words
            words_list: list[Word] = []
            if getattr(raw_s, "words", None):
                for w in raw_s.words:
                    words_list.append(
                        Word(
                            w=w.word,
                            start=round(w.start, 2),
                            end=round(w.end, 2),
                            p=round(w.probability, 2) if getattr(w, "probability", None) is not None else None,
                        )
                    )

            seg = Segment(
                id=seg_idx,
                start=round(raw_s.start, 2),
                end=round(raw_s.end, 2),
                text=text,
                words=words_list,
            )
            kept_segments.append(seg)
            seg_idx += 1

            # Emit transcript.segment event
            append_event(run_id, "transcript.segment", seg.model_dump())

            # Emit stage.progress event
            label = f"Listening {format_time(seg.end)} of {format_time(total_duration)}"
            append_event(
                run_id,
                "stage.progress",
                {
                    "stage": "transcribe",
                    "done": round(seg.end, 1),
                    "total": round(total_duration, 1),
                    "label": label,
                },
            )

            if progress_callback:
                progress_callback(seg.end, total_duration, label)

        # 6. Verify non-empty segments
        if not kept_segments:
            raise PipelineError(
                code="NO_SPEECH",
                detail="Voice activity detection found no spoken speech in the audio.",
            )

        duration_s = time.time() - t0
        append_event(
            run_id,
            "stage.done",
            {"stage": "transcribe", "seconds": round(duration_s, 2)},
        )

        timings = meta.get("timings", {})
        timings["transcribe"] = round(duration_s, 2)
        models_meta = meta.get("models", {})
        models_meta["stt"] = actual_model_name
        save_meta(run_id, {"timings": timings, "models": models_meta})

        raw_transcript = RawTranscript(
            segments=kept_segments,
            duration=round(total_duration, 3),
            language=detected_language,
            model=actual_model_name,
            device=device,
        )
        save_json(run_id, "raw_transcript.json", raw_transcript)

        return raw_transcript

    finally:
        del model
        gc.collect()
