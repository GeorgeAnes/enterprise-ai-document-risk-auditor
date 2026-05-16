from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMSettings:
    mode: str
    base_url: str | None
    api_key: str | None
    model: str | None


def load_llm_settings() -> LLMSettings:
    mode = os.getenv("LLM_MODE", "off").strip().lower()
    return LLMSettings(
        mode=mode,
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL"),
    )


def llm_is_enabled() -> bool:
    settings = load_llm_settings()
    return settings.mode in {"openai", "openai_compatible"} and bool(settings.api_key and settings.model)


def deterministic_mode_note() -> str:
    if llm_is_enabled():
        return "Optional LLM mode is configured, but deterministic scoring remains the default audit baseline."
    return "Running in deterministic no-LLM mode."
