import pytest


@pytest.fixture(autouse=True)
def disable_external_llm_calls_by_default(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "off")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
