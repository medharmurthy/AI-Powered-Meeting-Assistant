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


def parse_structured_json(raw_text: str, schema: type[T]) -> T:
    """Extract, repair, and validate JSON against schema."""
    if not raw_text or not raw_text.strip():
        return schema.model_validate_json(raw_text or "{}")

    # 1. Direct validation attempt
    try:
        return schema.model_validate_json(raw_text)
    except Exception:
        pass

    # 2. Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return schema.model_validate_json(cleaned)
    except Exception:
        pass

    # 3. Extract substring between first '{' and last '}'
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        substring = cleaned[first_brace : last_brace + 1]
        try:
            return schema.model_validate_json(substring)
        except Exception:
            pass

    # 4. Truncated JSON / EOF repair:
    # If JSON was cut off mid-stream, attempt closing open structures after the last complete object
    if first_brace != -1:
        last_obj = cleaned.rfind("}")
        if last_obj > first_brace:
            candidate = cleaned[first_brace : last_obj + 1]
            open_sq = candidate.count("[")
            close_sq = candidate.count("]")
            open_cur = candidate.count("{")
            close_cur = candidate.count("}")

            closing = ""
            if open_sq > close_sq:
                closing += "]" * (open_sq - close_sq)
            if open_cur > close_cur:
                closing += "}" * (open_cur - close_cur)

            try:
                repaired = candidate + closing
                return schema.model_validate_json(repaired)
            except Exception:
                pass

    # Re-raise standard ValidationError on raw_text
    return schema.model_validate_json(raw_text)


class OllamaClient:
    def __init__(
        self,
        host: str | None = None,
        temperature: float | None = None,
        seed: int | None = None,
        timeout_s: int | None = None,
        **kwargs: Any,
    ):
        cfg = get_config()
        self.host = host or cfg.llm.host
        self.temperature = temperature if temperature is not None else cfg.llm.temperature
        self.seed = seed if seed is not None else cfg.llm.seed
        self.timeout_s = timeout_s if timeout_s is not None else cfg.llm.timeout_s
        self.client = ollama.Client(host=self.host, timeout=self.timeout_s)

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

        num_predict = getattr(cfg.llm, "num_predict", 4096)
        options: dict[str, Any] = {
            "temperature": self.temperature,
            "seed": self.seed,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        }

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

        max_attempts = 3
        last_err: Exception | None = None
        current_user_content = user

        for attempt in range(1, max_attempts + 1):
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": current_user_content},
            ]

            raw_text = _call_chat(messages)
            try:
                result = parse_structured_json(raw_text, schema)
                return result
            except (ValidationError, Exception) as err:
                last_err = err
                logger.warning(
                    "Attempt %d/%d for model '%s' failed schema validation (length %d chars, num_predict=%d): %s",
                    attempt,
                    max_attempts,
                    model,
                    len(raw_text),
                    num_predict,
                    err,
                )

                if attempt < max_attempts:
                    logger.info("Retrying structured generation (attempt %d/%d) with model '%s'...", attempt + 1, max_attempts, model)
                    current_user_content = (
                        f"{user}\n\n"
                        f"CRITICAL: Your previous response failed schema validation or was truncated: {err}\n"
                        f"Return strictly valid, complete JSON matching the required schema. Keep the response concise."
                    )

        logger.error(
            "All %d attempts failed schema validation for model '%s' (configured num_predict=%d, num_ctx=%d): %s",
            max_attempts,
            model,
            num_predict,
            num_ctx,
            last_err,
        )
        raise PipelineError(
            code="LLM_BAD_OUTPUT",
            detail=f"Model '{model}' output failed schema validation after {max_attempts} attempts: {last_err}",
            fix="Retry; try another model in config",
        ) from last_err

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
