from __future__ import annotations

import io
import math
from pathlib import Path
from typing import BinaryIO
import wave

import av
import numpy as np

from verbatim.config import get_config
from verbatim.errors import PipelineError
from verbatim.store import (
    append_event,
    get_run_dir,
    save_json,
    save_meta,
)


def compute_peaks(pcm: np.ndarray, bins: int = 1600) -> list[float]:
    """Compute peak amplitude bins normalized to 0-1 with 3 decimals."""
    if len(pcm) < bins:
        # If fewer samples than bins, pad or repeat
        pad = np.zeros(bins - len(pcm), dtype=pcm.dtype)
        pcm = np.concatenate([pcm, pad])
    n = (len(pcm) // bins) * bins
    if n == 0:
        return [0.0] * bins
    x = np.abs(pcm[:n].reshape(bins, -1).astype(np.float32)) / 32768.0
    return x.max(axis=1).round(3).tolist()


def compute_rms_dbfs(pcm: np.ndarray) -> float:
    """Compute whole-file RMS in dBFS for 16-bit PCM."""
    if len(pcm) == 0:
        return -120.0
    # Mean of squared amplitude
    mean_sq = np.mean(pcm.astype(np.float64) ** 2)
    if mean_sq <= 1e-12:
        return -120.0
    rms = np.sqrt(mean_sq)
    return float(20.0 * np.log10(rms / 32768.0))


def validate_file_extension(filename: str, allowed_ext: list[str]) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not ext or ext not in allowed_ext:
        raise PipelineError(
            code="UNSUPPORTED_TYPE",
            detail=f"File extension '.{ext}' is not supported.",
        )
    return ext


def save_stream_to_file(
    stream: BinaryIO,
    destination: Path,
    max_bytes: int,
) -> int:
    """Save an incoming binary stream to disk, enforcing size limits."""
    bytes_written = 0
    chunk_size = 64 * 1024  # 64KB chunks

    with open(destination, "wb") as out:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > max_bytes:
                out.close()
                destination.unlink(missing_ok=True)
                raise PipelineError(
                    code="TOO_LARGE",
                    detail=f"Uploaded file exceeds {max_bytes // (1024 * 1024)} MB limit.",
                )
            out.write(chunk)

    if bytes_written == 0:
        destination.unlink(missing_ok=True)
        raise PipelineError(code="EMPTY_FILE", detail="Uploaded file is 0 bytes.")

    return bytes_written


def process_audio_file(run_id: str, original_path: Path) -> dict[str, Any]:
    """Decode audio using PyAV to 16 kHz mono int16, validate duration and volume, write audio.wav and peaks.json."""
    cfg = get_config()
    run_dir = get_run_dir(run_id, must_exist=True)

    # 1. Open with PyAV
    try:
        container = av.open(str(original_path))
    except Exception as exc:
        raise PipelineError(
            code="UNREADABLE_FILE",
            detail=f"Could not open media container: {exc}",
        ) from exc

    try:
        audio_streams = [s for s in container.streams if s.type == "audio"]
        if not audio_streams:
            raise PipelineError(
                code="NO_AUDIO_STREAM",
                detail="No audio stream found in the uploaded file.",
            )

        stream = audio_streams[0]
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)

        pcm_chunks: list[bytes] = []
        try:
            for frame in container.decode(stream):
                resampled = resampler.resample(frame)
                if isinstance(resampled, list):
                    for r in resampled:
                        pcm_chunks.append(r.to_ndarray().tobytes())
                elif resampled is not None:
                    pcm_chunks.append(resampled.to_ndarray().tobytes())

            flushed = resampler.resample(None)
            if isinstance(flushed, list):
                for r in flushed:
                    pcm_chunks.append(r.to_ndarray().tobytes())
            elif flushed is not None:
                pcm_chunks.append(flushed.to_ndarray().tobytes())
        except Exception as exc:
            raise PipelineError(
                code="UNREADABLE_FILE",
                detail=f"Error decoding audio frames: {exc}",
            ) from exc
    finally:
        container.close()

    raw_bytes = b"".join(pcm_chunks)
    if len(raw_bytes) == 0:
        raise PipelineError(
            code="UNREADABLE_FILE",
            detail="Decoded audio produced zero audio samples.",
        )

    pcm = np.frombuffer(raw_bytes, dtype=np.int16)
    duration = float(len(pcm) / 16000.0)

    # 2. Duration checks
    if duration < cfg.limits.min_duration_s:
        raise PipelineError(
            code="TOO_SHORT",
            detail=f"Duration {duration:.1f}s is shorter than {cfg.limits.min_duration_s}s minimum.",
        )

    max_seconds = float(cfg.active_profile_config.max_minutes * 60)
    if duration > max_seconds:
        raise PipelineError(
            code="TOO_LONG",
            detail=f"Duration {duration / 60.0:.1f}m exceeds {cfg.active_profile_config.max_minutes}m profile limit.",
        )

    # 3. Silence check
    rms_dbfs = compute_rms_dbfs(pcm)
    if rms_dbfs < cfg.limits.silence_dbfs:
        raise PipelineError(
            code="SILENT_AUDIO",
            detail=f"Audio volume ({rms_dbfs:.1f} dBFS) is below silence threshold ({cfg.limits.silence_dbfs} dBFS).",
        )

    # 4. Write audio.wav
    audio_wav_path = run_dir / "audio.wav"
    with wave.open(str(audio_wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm.tobytes())

    # 5. Compute peaks and save peaks.json
    peaks = compute_peaks(pcm, bins=1600)
    peaks_payload = {
        "duration": round(duration, 3),
        "peaks": peaks,
    }
    save_json(run_id, "peaks.json", peaks_payload)

    # 6. Update metadata
    save_meta(
        run_id,
        {
            "duration": round(duration, 3),
            "rms_dbfs": round(rms_dbfs, 2),
        },
    )

    # 7. Emit audio.ready event
    audio_url = f"/api/runs/{run_id}/audio"
    peaks_url = f"/api/runs/{run_id}/peaks"
    append_event(
        run_id,
        "audio.ready",
        {
            "duration": round(duration, 3),
            "audio_url": audio_url,
            "peaks_url": peaks_url,
        },
    )

    return {
        "duration": round(duration, 3),
        "peaks": peaks,
        "audio_path": audio_wav_path,
        "rms_dbfs": rms_dbfs,
    }
