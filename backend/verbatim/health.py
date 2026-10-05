from __future__ import annotations

import time
from typing import Any
import ollama

from verbatim.config import get_config
from verbatim.errors import make_app_error
from verbatim.gpu import get_gpu_info
from verbatim.schemas import (
    AppError,
    GpuInfo,
    HealthResponse,
    LlmInfo,
    ModelInfo,
    SttInfo,
)

_cached_health: tuple[float, HealthResponse] | None = None
CACHE_TTL_SECONDS = 10.0


def normalize_model_name(name: str) -> str:
    n = name.strip().lower()
    if n.endswith(":latest"):
        n = n[:-7]
    return n


def check_health(force_refresh: bool = False) -> HealthResponse:
    global _cached_health
    now = time.time()
    if not force_refresh and _cached_health is not None:
        last_time, cached_resp = _cached_health
        if now - last_time < CACHE_TTL_SECONDS:
            return cached_resp

    cfg = get_config()
    gpu = get_gpu_info()

    issues: list[AppError] = []

    # STT info
    stt_device = "cuda" if gpu.available else "cpu"
    stt_model = (
        cfg.active_profile_config.stt.model
        if gpu.available
        else cfg.stt.cpu_model
    )
    stt_info = SttInfo(model=stt_model, device=stt_device)

    if not gpu.available:
        issues.append(make_app_error("GPU_FALLBACK"))

    # LLM info
    refiner_target = cfg.active_profile_config.refiner.model
    doc_target = cfg.active_profile_config.documenter.model

    ollama_reachable = False
    refiner_installed = False
    doc_installed = False

    try:
        client = ollama.Client(host=cfg.llm.host)
        models_resp = client.list()
        ollama_reachable = True

        # Extract model tags
        installed_names: set[str] = set()
        raw_list = getattr(models_resp, "models", models_resp)
        if isinstance(raw_list, list):
            for m in raw_list:
                m_str = getattr(m, "model", None)
                if not m_str and isinstance(m, dict):
                    m_str = m.get("model") or m.get("name")
                if not m_str:
                    m_str = str(m)
                if m_str:
                    installed_names.add(normalize_model_name(m_str))
                    # Also keep full raw tag
                    installed_names.add(m_str.strip().lower())

        target_ref_norm = normalize_model_name(refiner_target)
        target_doc_norm = normalize_model_name(doc_target)

        refiner_installed = (
            target_ref_norm in installed_names
            or refiner_target.lower() in installed_names
        )
        doc_installed = (
            target_doc_norm in installed_names
            or doc_target.lower() in installed_names
        )

        if not refiner_installed:
            issues.append(
                make_app_error(
                    code="MODEL_MISSING",
                    title=f"Model '{refiner_target}' isn't installed",
                    detail=f"Refiner model '{refiner_target}' was not found in Ollama.",
                    fix=f"ollama pull {refiner_target}",
                )
            )

        if not doc_installed and doc_target != refiner_target:
            issues.append(
                make_app_error(
                    code="MODEL_MISSING",
                    title=f"Model '{doc_target}' isn't installed",
                    detail=f"Documenter model '{doc_target}' was not found in Ollama.",
                    fix=f"ollama pull {doc_target}",
                )
            )

    except Exception:
        ollama_reachable = False
        issues.append(make_app_error("OLLAMA_UNREACHABLE"))

    response = HealthResponse(
        profile=cfg.active_profile,
        gpu=gpu,
        stt=stt_info,
        llm=LlmInfo(
            reachable=ollama_reachable,
            refiner=ModelInfo(model=refiner_target, installed=refiner_installed),
            documenter=ModelInfo(model=doc_target, installed=doc_installed),
        ),
        issues=issues,
    )

    _cached_health = (now, response)
    return response
