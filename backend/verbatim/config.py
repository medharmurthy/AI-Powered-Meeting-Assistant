from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field

from verbatim.gpu import get_gpu_info


class ProfileSTT(BaseModel):
    model: str


class ProfileRefiner(BaseModel):
    model: str
    num_ctx: int = 8192
    think: bool = False
    supports_think: bool = True


class ProfileDocumenter(BaseModel):
    model: str
    num_ctx: int = 16384
    supports_think: bool = False


class ProfileConfig(BaseModel):
    stt: ProfileSTT
    refiner: ProfileRefiner
    documenter: ProfileDocumenter
    max_minutes: int = 30


class LimitsConfig(BaseModel):
    max_upload_mb: int = 500
    allowed_ext: list[str] = Field(
        default_factory=lambda: [
            "wav", "mp3", "m4a", "aac", "flac", "ogg", "opus", "webm", "mp4", "mov", "mkv"
        ]
    )
    min_duration_s: float = 2.0
    silence_dbfs: float = -55.0


class STTConfig(BaseModel):
    language: str = "en"
    beam_size: int = 5
    vad_min_silence_ms: int = 500
    cpu_model: str = "distil-large-v3"


class LLMConfig(BaseModel):
    provider: str = "ollama"
    host: str = "http://127.0.0.1:11434"
    temperature: float = 0.0
    seed: int = 7
    timeout_s: int = 600
    unload_after_stage: bool = True
    num_predict: int = 4096


class RefineConfig(BaseModel):
    window: int = 40
    context: int = 4
    max_original_words: int = 6
    hint_min_score: int = 72


class DocumentConfig(BaseModel):
    support_threshold: float = 0.4
    owner_window: int = 4
    deadline_window: int = 2
    verify_pass: bool = True


class AppConfig(BaseModel):
    raw_profile: str = "auto"
    active_profile: str = "lite"
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    refine: RefineConfig = Field(default_factory=RefineConfig)
    document: DocumentConfig = Field(default_factory=DocumentConfig)
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)
    active_profile_config: ProfileConfig


def find_repo_root() -> Path:
    env_root = os.getenv("VERBATIM_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # If running from repo root or backend/verbatim
    cur = Path(__file__).resolve().parent
    for p in [cur, cur.parent, cur.parent.parent]:
        if (p / "config.yaml").exists() or (p / "plan.md").exists():
            return p
    return Path.cwd().resolve()


def resolve_profile_name(configured_profile: str) -> str:
    env_override = os.getenv("VERBATIM_PROFILE")
    if env_override and env_override.strip():
        return env_override.strip().lower()

    if configured_profile != "auto":
        return configured_profile.strip().lower()

    gpu_info = get_gpu_info()
    if not gpu_info.available or gpu_info.vram_gb is None:
        return "lite"

    vram = gpu_info.vram_gb
    if vram >= 11.0:
        return "quality"
    elif vram >= 7.0:
        return "standard"
    else:
        return "lite"


_cached_config: AppConfig | None = None


def load_config(config_path: Path | str | None = None, reload: bool = False) -> AppConfig:
    global _cached_config
    if _cached_config is not None and not reload and config_path is None:
        return _cached_config

    if config_path is None:
        env_cfg = os.getenv("VERBATIM_CONFIG")
        if env_cfg:
            config_path = Path(env_cfg).resolve()
        else:
            config_path = find_repo_root() / "config.yaml"
    else:
        config_path = Path(config_path).resolve()

    raw: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    raw_profile = raw.get("profile", "auto")
    active_profile = resolve_profile_name(raw_profile)

    limits = LimitsConfig(**raw.get("limits", {}))
    stt = STTConfig(**raw.get("stt", {}))
    llm = LLMConfig(**raw.get("llm", {}))
    refine = RefineConfig(**raw.get("refine", {}))
    document = DocumentConfig(**raw.get("document", {}))

    profiles_raw = raw.get("profiles", {})
    profiles: dict[str, ProfileConfig] = {}
    for name, pcfg in profiles_raw.items():
        profiles[name] = ProfileConfig(**pcfg)

    # Fallback default profiles if not present in yaml
    if "lite" not in profiles:
        profiles["lite"] = ProfileConfig(
            stt=ProfileSTT(model="distil-large-v3"),
            refiner=ProfileRefiner(model="qwen3:4b", num_ctx=8192, think=False, supports_think=True),
            documenter=ProfileDocumenter(model="gemma3:4b", num_ctx=12288, supports_think=False),
            max_minutes=30,
        )
    if "standard" not in profiles:
        profiles["standard"] = ProfileConfig(
            stt=ProfileSTT(model="large-v3"),
            refiner=ProfileRefiner(model="qwen3:8b", num_ctx=8192, think=False, supports_think=True),
            documenter=ProfileDocumenter(model="gemma3:12b", num_ctx=16384, supports_think=False),
            max_minutes=45,
        )
    if "quality" not in profiles:
        profiles["quality"] = ProfileConfig(
            stt=ProfileSTT(model="large-v3"),
            refiner=ProfileRefiner(model="qwen3:14b", num_ctx=8192, think=False, supports_think=True),
            documenter=ProfileDocumenter(model="gemma3:12b", num_ctx=32768, supports_think=False),
            max_minutes=90,
        )

    active_profile_cfg = profiles.get(active_profile, profiles["lite"])

    cfg = AppConfig(
        raw_profile=raw_profile,
        active_profile=active_profile,
        limits=limits,
        stt=stt,
        llm=llm,
        refine=refine,
        document=document,
        profiles=profiles,
        active_profile_config=active_profile_cfg,
    )

    if config_path is None or str(config_path).endswith("config.yaml"):
        _cached_config = cfg
    return cfg


def get_config() -> AppConfig:
    return load_config()
