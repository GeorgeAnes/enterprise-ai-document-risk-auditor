import urllib.error

from backend.app.core import llm_provider
from backend.app.schemas import ClaimAudit, EvidenceSnippet


def test_llm_off_keeps_deterministic_audit_available(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "off")

    claim = _claim()
    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [claim])

    assert review.status == "disabled"
    assert review.enabled is False
    assert claim.llm_review is None


def test_openai_compatible_structured_claim_review(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "openai_compatible")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "lm-studio")
    monkeypatch.setenv("OPENAI_MODEL", "google/gemma-4-e4b")

    def fake_call(settings, prompt, timeout_seconds):
        assert settings.provider == "openai_compatible"
        assert "return only a JSON object" in prompt
        return """
        {
          "claim_id": "C001",
          "reviewer_status": "completed",
          "reviewer_note": "The claim is too absolute for the retrieved evidence.",
          "suggested_rewrite": "The pilot suggests manual rework may decrease within the tested teams.",
          "missing_evidence_questions": ["Which teams were in scope?", "Is there post-pilot validation?"],
          "business_impact": "Overstating automation benefits can mislead rollout decisions.",
          "human_review_priority": "High",
          "confidence": 0.82
        }
        """

    monkeypatch.setattr(llm_provider, "_call_openai_compatible", fake_call)
    claim = _claim()
    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [claim])

    assert review.status == "completed"
    assert review.enabled is True
    assert claim.llm_review is not None
    assert claim.llm_review.reviewer_status == "completed"
    assert claim.llm_review.suggested_rewrite is not None
    assert len(claim.llm_review.missing_evidence_questions) == 2


def test_malformed_llm_json_falls_back_to_text(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "openai_compatible")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "lm-studio")
    monkeypatch.setenv("OPENAI_MODEL", "google/gemma-4-e4b")

    monkeypatch.setattr(llm_provider, "_call_openai_compatible", lambda settings, prompt, timeout_seconds: "plain note")
    claim = _claim()
    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [claim])

    assert review.status == "completed"
    assert claim.llm_review is not None
    assert claim.llm_review.reviewer_status == "fallback_text"
    assert claim.llm_review.reviewer_note == "plain note"


def test_openai_compatible_unavailable_does_not_crash(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "openai_compatible")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "lm-studio")
    monkeypatch.setenv("OPENAI_MODEL", "google/gemma-4-e4b")

    def fake_call(settings, prompt, timeout_seconds):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(llm_provider, "_call_openai_compatible", fake_call)
    claim = _claim()
    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [claim])

    assert review.status == "unavailable"
    assert "Deterministic audit remains available" in (review.summary or "")
    assert claim.llm_review is None


def test_gemini_placeholder_is_not_configured(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "replace-with-your-gemini-api-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    review = llm_provider.generate_optional_llm_review("Demo", "Summary", [_claim()])

    assert review.status == "not_configured"
    assert review.enabled is False


def _claim() -> ClaimAudit:
    return ClaimAudit(
        id="C001",
        text="The new operating model is guaranteed to eliminate manual rework.",
        source_chunk_id="D001",
        label="Needs human review",
        risk_score=90,
        confidence=0.8,
        explanation="The claim uses absolute language and has weak evidence.",
        factors=["Strong certainty language", "Low support evidence"],
        evidence=[
            EvidenceSnippet(
                chunk_id="E001",
                text="The pilot only covered two teams and showed mixed outcomes.",
                source="document",
                score=0.34,
            )
        ],
    )
