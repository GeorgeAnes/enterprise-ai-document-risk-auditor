from backend.app.core import llm_provider


def test_gemini_placeholder_is_not_configured(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "replace-with-your-gemini-api-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [])

    assert review.status == "not_configured"
    assert review.enabled is False


def test_gemini_review_can_complete_with_mocked_call(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    def fake_call(settings, prompt, timeout_seconds):
        assert settings.provider == "gemini"
        assert "responsible-AI document review assistant" in prompt
        return "- Check unsupported high-certainty claims.\n- Ask a reviewer to validate source passages."

    monkeypatch.setattr(llm_provider, "_call_gemini", fake_call)
    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [])

    assert review.status == "completed"
    assert review.enabled is True
    assert len(review.reviewer_notes) == 2


def test_openai_compatible_requires_local_endpoint_settings(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "openai_compatible")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")

    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [])

    assert review.status == "not_configured"
    assert review.enabled is False


def test_openai_compatible_review_can_complete_with_mocked_call(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "openai_compatible")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "lm-studio")
    monkeypatch.setenv("OPENAI_MODEL", "local-model")

    def fake_call(settings, prompt, timeout_seconds):
        assert settings.provider == "openai_compatible"
        assert settings.base_url == "http://127.0.0.1:1234/v1"
        assert "responsible-AI document review assistant" in prompt
        return "- Confirm unsupported claims.\n- Check vague business language."

    monkeypatch.setattr(llm_provider, "_call_openai_compatible", fake_call)
    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [])

    assert review.status == "completed"
    assert review.enabled is True
    assert review.provider == "openai_compatible"
    assert len(review.reviewer_notes) == 2
