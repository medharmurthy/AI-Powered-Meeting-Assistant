from __future__ import annotations

import logging
from typing import Any, TypeVar
import httpx
import ollama
from pydantic import BaseModel, ValidationError

from verbatim.config import get_config
from verbatim.errors import PipelineError
from verbatim.health import normalize_model_name

logger = logging.getLogger("verbatim.llm")

T = TypeVar("T", bound=BaseModel)


class OllamaClient:
    def __init__(self, host: str | None = None):
        cfg = get_config()
        self.host = host or cfg.llm.host
        self.client = ollama.Client(host=self.host)

    def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        role: str | None = None,
    ) -> T:
        cfg = get_config()

        # Determine num_ctx and thinking settings based on role config
        num_ctx = 8192
        think_kwarg: dict[str, Any] = {}

        if role == "refiner":
            ref_cfg = cfg.active_profile_config.refiner
            num_ctx = ref_cfg.num_ctx
            if ref_cfg.supports_think:
                think_kwarg["think"] = ref_cfg.think
        elif role == "documenter":
            doc_cfg = cfg.active_profile_config.documenter
            num_ctx = doc_cfg.num_ctx
            if doc_cfg.supports_think:
                think_kwarg["think"] = False

        options: dict[str, Any] = {
            "temperature": cfg.llm.temperature,
            "seed": cfg.llm.seed,
            "num_predict": 2048,
            "num_ctx": num_ctx,
        }

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        def _call_chat(msgs: list[dict[str, str]]) -> str:
            try:
                resp = self.client.chat(
                    model=model,
                    messages=msgs,
                    format=schema.model_json_schema(),
                    options=options,
                    keep_alive="10m",
                    **think_kwarg,
                )
                msg_content = resp.message.content if hasattr(resp, "message") else resp.get("message", {}).get("content", "")
                return msg_content or ""
            except ollama.ResponseError as exc:
                if exc.status_code == 404 or "not found" in str(exc).lower():
                    raise PipelineError(
                        code="MODEL_MISSING",
                        detail=f"Model '{model}' is not available in Ollama: {exc}",
                        fix=f"ollama pull {model}",
                    ) from exc
                raise PipelineError(
                    code="INTERNAL",
                    detail=f"Ollama response error: {exc}",
                ) from exc
            except (ollama.RequestError, httpx.ConnectError, ConnectionError, OSError) as exc:
                raise PipelineError(
                    code="OLLAMA_UNREACHABLE",
                    detail=f"Could not connect to Ollama at {self.host}: {exc}",
                ) from exc
            except httpx.TimeoutException as exc:
                raise PipelineError(
                    code="LLM_TIMEOUT",
                    detail=f"Request to Ollama timed out: {exc}",
                ) from exc

        # First attempt
        raw_text = _call_chat(messages)
        try:
            return schema.model_validate_json(raw_text)
        except (ValidationError, Exception) as first_err:
            logger.warning(
                "Initial schema validation failed for model '%s': %s. Retrying once...",
                model,
                first_err,
            )

            # Retry once with error appended
            retry_messages = [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"{user}\n\n"
                        f"CRITICAL: Your previous response failed schema validation with error:\n{first_err}\n"
                        f"Return strictly valid JSON that validates against the required schema."
                    ),
                },
            ]
            raw_text_retry = _call_chat(retry_messages)
            try:
                return schema.model_validate_json(raw_text_retry)
            except (ValidationError, Exception) as second_err:
                raise PipelineError(
                    code="LLM_BAD_OUTPUT",
                    detail=f"Model '{model}' output failed schema validation twice: {second_err}",
                ) from second_err

    def unload(self, model: str) -> None:
        """Unload model from VRAM by setting keep_alive=0."""
        try:
            self.client.generate(model=model, prompt="", keep_alive=0)
            logger.info("Unloaded model '%s' from Ollama VRAM.", model)
        except Exception as exc:
            logger.warning("Failed to unload model '%s': %s", model, exc)

    def available_models(self) -> set[str]:
        """Return set of available model names."""
        try:
            resp = self.client.list()
            models_set: set[str] = set()
            raw_list = getattr(resp, "models", resp)
            if isinstance(raw_list, list):
                for m in raw_list:
                    m_str = getattr(m, "model", None)
                    if not m_str and isinstance(m, dict):
                        m_str = m.get("model") or m.get("name")
                    if m_str:
                        models_set.add(m_str.strip().lower())
                        models_set.add(normalize_model_name(m_str))
            return models_set
        except Exception as exc:
            logger.warning("Could not list Ollama models: %s", exc)
            return set()
