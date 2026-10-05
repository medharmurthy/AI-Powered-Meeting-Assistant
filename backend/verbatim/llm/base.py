from __future__ import annotations

from typing import Protocol, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLM(Protocol):
    def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        role: str | None = None,
    ) -> T:
        """Call LLM with structured output adhering to schema."""
        ...

    def unload(self, model: str) -> None:
        """Explicitly unload model from VRAM."""
        ...

    def available_models(self) -> set[str]:
        """Return available model tags."""
        ...
