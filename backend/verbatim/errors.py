from __future__ import annotations

from typing import Any
from verbatim.schemas import AppError

CATALOGUE: dict[str, dict[str, Any]] = {
    "UNSUPPORTED_TYPE": {
        "title": "That file type isn't supported",
        "detail": "The uploaded file format is not supported.",
        "fix": "Use wav, mp3, m4a, aac, flac, ogg, opus, webm, mp4, mov or mkv",
        "retryable": False,
    },
    "EMPTY_FILE": {
        "title": "That file is empty",
        "detail": "The uploaded file has a size of 0 bytes.",
        "fix": "Choose a different file",
        "retryable": False,
    },
    "TOO_LARGE": {
        "title": "The file is larger than 500 MB",
        "detail": "File size exceeds the configured upload limit.",
        "fix": "Trim or compress the recording",
        "retryable": False,
    },
    "UNREADABLE_FILE": {
        "title": "We couldn't read this audio",
        "detail": "The audio file could not be opened or decoded.",
        "fix": "Re-export the recording and try again",
        "retryable": False,
    },
    "NO_AUDIO_STREAM": {
        "title": "This file has no audio track",
        "detail": "The uploaded media container has no valid audio stream.",
        "fix": "Upload the audio or a video that has sound",
        "retryable": False,
    },
    "TOO_SHORT": {
        "title": "Recording is too short",
        "detail": "The recording duration is shorter than the minimum threshold (2 seconds).",
        "fix": "Trim it, or switch profile in config",
        "retryable": False,
    },
    "TOO_LONG": {
        "title": "Recording is longer than the limit for this setup",
        "detail": "The recording exceeds the maximum supported duration for the current profile.",
        "fix": "Trim it, or switch profile in config",
        "retryable": False,
    },
    "SILENT_AUDIO": {
        "title": "The recording is silent",
        "detail": "Whole-file RMS volume is below the silence threshold.",
        "fix": "Check the microphone/source",
        "retryable": False,
    },
    "NO_SPEECH": {
        "title": "No speech was detected",
        "detail": "VAD produced no speech segments from the recording.",
        "fix": "Check the recording contains spoken English",
        "retryable": False,
    },
    "NOT_ENGLISH": {
        "title": "This doesn't sound like English",
        "detail": "Language detection suggests the speech is not English.",
        "fix": "Results may be poor",
        "retryable": False,
    },
    "GPU_FALLBACK": {
        "title": "Running on CPU",
        "detail": "GPU initialization was unavailable or failed; running on CPU.",
        "fix": "Install the CUDA 12 libraries for faster processing",
        "retryable": False,
    },
    "OLLAMA_UNREACHABLE": {
        "title": "Ollama isn't running",
        "detail": "Could not connect to the Ollama server at http://127.0.0.1:11434.",
        "fix": "Start Ollama (`ollama serve`)",
        "retryable": True,
    },
    "MODEL_MISSING": {
        "title": "Model isn't installed",
        "detail": "The required model is not available in Ollama.",
        "fix": "ollama pull <model>",
        "retryable": True,
    },
    "LLM_BAD_OUTPUT": {
        "title": "The model returned something we couldn't use",
        "detail": "Model output failed schema validation twice.",
        "fix": "Retry; try another model in config",
        "retryable": True,
    },
    "LLM_TIMEOUT": {
        "title": "The model took too long",
        "detail": "The LLM request exceeded the configured timeout limit.",
        "fix": "Use the lite profile or a smaller model",
        "retryable": True,
    },
    "INTERNAL": {
        "title": "Something went wrong",
        "detail": "An internal unexpected error occurred.",
        "fix": "Show the short message, log the traceback",
        "retryable": False,
    },
}


def make_app_error(
    code: str,
    detail: str | None = None,
    title: str | None = None,
    fix: str | None = None,
    stage: str | None = None,
    retryable: bool | None = None,
) -> AppError:
    item = CATALOGUE.get(code, CATALOGUE["INTERNAL"])
    return AppError(
        code=code,
        title=title or item.get("title", "Error"),
        detail=detail or item.get("detail", ""),
        fix=fix if fix is not None else item.get("fix"),
        stage=stage,
        retryable=retryable if retryable is not None else item.get("retryable", False),
    )


class PipelineError(Exception):
    def __init__(
        self,
        code: str,
        detail: str | None = None,
        title: str | None = None,
        fix: str | None = None,
        stage: str | None = None,
        retryable: bool | None = None,
    ):
        self.error = make_app_error(
            code=code,
            detail=detail,
            title=title,
            fix=fix,
            stage=stage,
            retryable=retryable,
        )
        super().__init__(f"[{self.error.code}] {self.error.title}: {self.error.detail}")
