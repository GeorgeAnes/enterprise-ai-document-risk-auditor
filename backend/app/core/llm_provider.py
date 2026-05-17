from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

from backend.app.schemas import ClaimAudit, ClaimLLMReview, LLMReview

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is included in requirements.
    load_dotenv = None


GEMINI_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PLACEHOLDER_VALUES = {
    "",
    "replace-with-your-gemini-api-key",
    "your-gemini-api-key-here",
    "paste-your-gemini-api-key-here",
    "replace-with-your-openai-compatible-key",
}
MAX_REVIEWED_CLAIMS = 5


@dataclass(frozen=True)
class LLMSettings:
    mode: str
    provider: str
    base_url: str | None
    api_key: str | None
    model: str | None


def load_llm_settings() -> LLMSettings:
    if load_dotenv:
        load_dotenv()

    mode = os.getenv("LLM_MODE", "off").strip().lower()
    if mode == "gemini":
        return LLMSettings(
            mode=mode,
            provider="gemini",
            base_url=GEMINI_ENDPOINT_TEMPLATE,
            api_key=os.getenv("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        )

    return LLMSettings(
        mode=mode,
        provider="openai_compatible" if mode in {"openai", "openai_compatible"} else "none",
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL"),
    )


def llm_is_enabled() -> bool:
    settings = load_llm_settings()
    if settings.mode == "gemini":
        return _has_real_key(settings.api_key) and bool(settings.model)
    if settings.mode in {"openai_compatible", "openai"}:
        return bool(settings.base_url and settings.api_key and settings.model)
    return False


def deterministic_mode_note() -> str:
    if llm_is_enabled():
        return "Optional LLM mode is configured, but deterministic scoring remains the default audit baseline."
    return "Running in deterministic no-LLM mode."


def generate_optional_llm_review(
    document_title: str,
    executive_summary: str,
    claims: list[ClaimAudit],
    timeout_seconds: int = 30,
) -> LLMReview:
    settings = load_llm_settings()
    if settings.mode == "off":
        return LLMReview(
            enabled=False,
            provider="none",
            status="disabled",
            summary="Local reviewer disabled. Deterministic audit remains available.",
        )

    if settings.mode in {"openai_compatible", "openai"}:
        if not settings.base_url or not settings.api_key or not settings.model:
            return LLMReview(
                enabled=False,
                provider=settings.provider,
                model=settings.model,
                status="not_configured",
                summary="Local reviewer unavailable. Deterministic audit remains available.",
            )
        return _generate_structured_claim_reviews(settings, document_title, executive_summary, claims, timeout_seconds)

    if settings.mode != "gemini":
        return LLMReview(
            enabled=False,
            provider=settings.provider,
            model=settings.model,
            status="disabled",
            summary="Local reviewer disabled. Deterministic audit remains available.",
        )

    if not _has_real_key(settings.api_key) or not settings.model:
        return LLMReview(
            enabled=False,
            provider="gemini",
            model=settings.model,
            status="not_configured",
            summary="Local reviewer unavailable. Deterministic audit remains available.",
        )

    return _generate_structured_claim_reviews(settings, document_title, executive_summary, claims, timeout_seconds)


def _generate_structured_claim_reviews(
    settings: LLMSettings,
    document_title: str,
    executive_summary: str,
    claims: list[ClaimAudit],
    timeout_seconds: int,
) -> LLMReview:
    review_targets = sorted(claims, key=lambda claim: claim.risk_score, reverse=True)[:MAX_REVIEWED_CLAIMS]
    if not review_targets:
        return LLMReview(
            enabled=True,
            provider=settings.provider,
            model=settings.model,
            status="completed",
            summary="No high-risk claims were available for local reviewer notes.",
        )

    reviewer_notes: list[str] = []
    completed = 0
    fallback_count = 0

    for claim in review_targets:
        prompt = _build_claim_review_prompt(document_title, executive_summary, claim)
        try:
            text = _call_provider(settings, prompt, timeout_seconds=timeout_seconds)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            return LLMReview(
                enabled=True,
                provider=settings.provider,
                model=settings.model,
                status="unavailable",
                summary="Local reviewer unavailable. Deterministic audit remains available.",
            )

        review = _parse_claim_review(claim, text)
        claim.llm_review = review
        reviewer_notes.append(review.reviewer_note or f"{claim.id}: local reviewer returned no note.")
        if review.reviewer_status == "completed":
            completed += 1
        else:
            fallback_count += 1

    summary = f"Gemma reviewer completed structured notes for {completed} claim(s)."
    if fallback_count:
        summary += f" {fallback_count} claim(s) used fallback text because structured JSON was unavailable."

    return LLMReview(
        enabled=True,
        provider=settings.provider,
        model=settings.model,
        status="completed",
        summary=summary,
        reviewer_notes=reviewer_notes[:5],
    )


def _call_provider(settings: LLMSettings, prompt: str, timeout_seconds: int) -> str:
    if settings.provider == "gemini":
        return _call_gemini(settings, prompt, timeout_seconds=timeout_seconds)
    return _call_openai_compatible(settings, prompt, timeout_seconds=timeout_seconds)


def _call_gemini(settings: LLMSettings, prompt: str, timeout_seconds: int) -> str:
    assert settings.api_key is not None
    assert settings.model is not None
    url = GEMINI_ENDPOINT_TEMPLATE.format(model=settings.model)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "topP": 0.9,
            "maxOutputTokens": 700,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_payload = json.loads(response.read().decode("utf-8"))

    parts = response_payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(str(part.get("text", "")).strip() for part in parts if part.get("text"))
    if not text:
        raise ValueError("Gemini returned no text.")
    return text.strip()


def _call_openai_compatible(settings: LLMSettings, prompt: str, timeout_seconds: int) -> str:
    assert settings.base_url is not None
    assert settings.api_key is not None
    assert settings.model is not None

    base_url = settings.base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": settings.model,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise responsible-AI document review assistant. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 700,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_payload = json.loads(response.read().decode("utf-8"))

    choices = response_payload.get("choices", [])
    if not choices:
        raise ValueError("OpenAI-compatible endpoint returned no choices.")

    text = str(choices[0].get("message", {}).get("content", "")).strip()
    if not text:
        raise ValueError("OpenAI-compatible endpoint returned no text.")
    return text


def _build_claim_review_prompt(document_title: str, executive_summary: str, claim: ClaimAudit) -> str:
    evidence_lines = []
    for evidence in claim.evidence[:3]:
        evidence_lines.append(f"- {evidence.chunk_id} | score={evidence.score:.2f} | {evidence.text}")
    evidence_text = "\n".join(evidence_lines) if evidence_lines else "No retrieved evidence."
    return (
        "You are a responsible-AI document review assistant. "
        "Do not decide legal truth and do not invent evidence. "
        "Review the deterministic audit output and return only a JSON object with this exact shape:\n"
        "{\n"
        '  "claim_id": "string",\n'
        '  "reviewer_status": "completed",\n'
        '  "reviewer_note": "1-2 sentence note",\n'
        '  "suggested_rewrite": "safer scoped rewrite or null",\n'
        '  "missing_evidence_questions": ["question 1", "question 2"],\n'
        '  "business_impact": "why this matters for an enterprise reviewer",\n'
        '  "human_review_priority": "Low|Medium|High|Critical",\n'
        '  "confidence": 0.0\n'
        "}\n\n"
        f"Document title: {document_title}\n"
        f"Deterministic executive summary: {executive_summary}\n\n"
        f"Claim id: {claim.id}\n"
        f"Claim text: {claim.text}\n"
        f"Deterministic label: {claim.label}\n"
        f"Risk score: {claim.risk_score}/100\n"
        f"Deterministic explanation: {claim.explanation}\n"
        f"Deterministic factors: {', '.join(claim.factors)}\n\n"
        f"Retrieved evidence:\n{evidence_text}\n\n"
        "Focus on evidence gaps, safer wording, business risk, and human-review priority."
    )


class _ClaimReviewPayload(BaseModel):
    claim_id: str
    reviewer_status: str = "completed"
    reviewer_note: str | None = None
    suggested_rewrite: str | None = None
    missing_evidence_questions: list[str] = Field(default_factory=list)
    business_impact: str | None = None
    human_review_priority: str = "Medium"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def _parse_claim_review(claim: ClaimAudit, text: str) -> ClaimLLMReview:
    try:
        payload = _ClaimReviewPayload.model_validate_json(_extract_json_object(text))
        return ClaimLLMReview(
            claim_id=claim.id,
            reviewer_status="completed",
            reviewer_note=payload.reviewer_note,
            suggested_rewrite=payload.suggested_rewrite,
            missing_evidence_questions=payload.missing_evidence_questions[:4],
            business_impact=payload.business_impact,
            human_review_priority=_normalize_priority(payload.human_review_priority, claim.risk_score),
            confidence=payload.confidence,
        )
    except (ValidationError, ValueError, json.JSONDecodeError):
        return ClaimLLMReview(
            claim_id=claim.id,
            reviewer_status="fallback_text",
            reviewer_note=_fallback_note(text),
            suggested_rewrite=None,
            missing_evidence_questions=[],
            business_impact="Structured local reviewer output was unavailable; use the deterministic explanation and retrieved evidence for review.",
            human_review_priority=_priority_from_score(claim.risk_score),
            confidence=0.0,
        )


def _extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in reviewer response.")
    return cleaned[start : end + 1]


def _fallback_note(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "Local reviewer returned unstructured output. Deterministic audit remains available."
    return cleaned[:700]


def _normalize_priority(value: str, score: int) -> str:
    normalized = value.strip().title()
    if normalized in {"Low", "Medium", "High", "Critical"}:
        return normalized
    return _priority_from_score(score)


def _priority_from_score(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def _has_real_key(value: str | None) -> bool:
    return bool(value and value.strip().lower() not in PLACEHOLDER_VALUES)
