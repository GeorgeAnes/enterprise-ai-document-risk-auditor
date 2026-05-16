from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from backend.app.schemas import ClaimAudit, LLMReview

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
}


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
    return settings.mode == "gemini" and _has_real_key(settings.api_key) and bool(settings.model)


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
        return LLMReview(enabled=False, provider="none", status="disabled")

    if settings.mode != "gemini":
        return LLMReview(
            enabled=False,
            provider=settings.provider,
            model=settings.model,
            status="disabled",
            summary="This repository currently implements Gemini as the optional non-deterministic reviewer.",
        )

    if not _has_real_key(settings.api_key) or not settings.model:
        return LLMReview(
            enabled=False,
            provider="gemini",
            model=settings.model,
            status="not_configured",
            summary="Gemini mode is selected, but GEMINI_API_KEY still needs to be set to a real key.",
        )

    prompt = _build_reviewer_prompt(document_title, executive_summary, claims)
    try:
        text = _call_gemini(settings, prompt, timeout_seconds=timeout_seconds)
        notes = _notes_from_text(text)
        return LLMReview(
            enabled=True,
            provider="gemini",
            model=settings.model,
            status="completed",
            summary=notes[0] if notes else text[:500],
            reviewer_notes=notes,
            raw_text=text,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return LLMReview(
            enabled=True,
            provider="gemini",
            model=settings.model,
            status="error",
            summary="Gemini reviewer failed. The deterministic audit result is still valid.",
            error=str(exc),
        )


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


def _build_reviewer_prompt(document_title: str, executive_summary: str, claims: list[ClaimAudit]) -> str:
    high_risk = sorted(claims, key=lambda claim: claim.risk_score, reverse=True)[:8]
    claim_lines = []
    for claim in high_risk:
        evidence = claim.evidence[0].text if claim.evidence else "No retrieved evidence."
        claim_lines.append(
            f"- {claim.id} | {claim.label} | risk={claim.risk_score}: {claim.text}\n"
            f"  Evidence: {evidence}\n"
            f"  Deterministic reason: {claim.explanation}"
        )

    return (
        "You are a responsible-AI document review assistant. "
        "Do not decide legal truth. Give a concise second opinion on the deterministic audit.\n\n"
        f"Document title: {document_title}\n"
        f"Deterministic executive summary: {executive_summary}\n\n"
        "High-risk claims:\n"
        + "\n".join(claim_lines)
        + "\n\nReturn 3-5 short reviewer notes. Focus on evidence gaps, vague claims, and human-review priorities."
    )


def _notes_from_text(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        cleaned = raw_line.strip().lstrip("-*0123456789. ").strip()
        if cleaned:
            lines.append(cleaned)
    return lines[:5] or [text.strip()]


def _has_real_key(value: str | None) -> bool:
    return bool(value and value.strip().lower() not in PLACEHOLDER_VALUES)
