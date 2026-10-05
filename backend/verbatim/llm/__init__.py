"""LLM abstraction layer."""
from verbatim.llm.base import LLM
from verbatim.llm.ollama_client import OllamaClient

__all__ = ["LLM", "OllamaClient"]
