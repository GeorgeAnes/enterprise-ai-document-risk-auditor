from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.core.chunk import DocumentChunk


FACTUAL_VERBS = {
    "is",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "will",
    "can",
    "must",
    "reduces",
    "increases",
    "improves",
    "decreases",
    "achieves",
    "requires",
    "supports",
    "contains",
    "covers",
    "protects",
}

CLAIM_KEYWORDS = {
    "risk",
    "cost",
    "revenue",
    "compliance",
    "accuracy",
    "performance",
    "uptime",
    "sla",
    "contract",
    "audit",
    "privacy",
    "security",
    "model",
    "process",
    "policy",
    "evidence",
    "control",
    "customer",
    "supplier",
}

VAGUE_TERMS = {
    "best-in-class",
    "world-class",
    "significant",
    "robust",
    "seamless",
    "state-of-the-art",
    "industry-leading",
    "optimized",
    "high-quality",
    "substantial",
}


@dataclass(frozen=True)
class ExtractedClaim:
    id: str
    text: str
    source_chunk_id: str
    indicators: list[str]


def extract_claims(chunks: list[DocumentChunk], max_claims: int = 30) -> list[ExtractedClaim]:
    claims: list[ExtractedClaim] = []
    seen: set[str] = set()

    for chunk in chunks:
        text = _clean_candidate(chunk.text)
        if not _is_candidate_claim(text):
            continue

        key = text.lower()
        if key in seen:
            continue
        seen.add(key)

        indicators = _claim_indicators(text)
        claims.append(
            ExtractedClaim(
                id=f"C{len(claims) + 1:03d}",
                text=text,
                source_chunk_id=chunk.id,
                indicators=indicators,
            )
        )
        if len(claims) >= max_claims:
            break

    return claims


def _clean_candidate(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" -")


def _is_candidate_claim(text: str) -> bool:
    if len(text) < 30 or len(text) > 320:
        return False
    if text.endswith("?"):
        return False

    lowered = text.lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z-]+", lowered)
    token_set = set(tokens)

    has_number = bool(re.search(r"\b\d+(?:\.\d+)?%?\b", text))
    has_factual_verb = bool(token_set & FACTUAL_VERBS)
    has_keyword = bool(token_set & CLAIM_KEYWORDS)
    has_vague_term = any(term in lowered for term in VAGUE_TERMS)
    has_citation = bool(re.search(r"(\[[0-9]+\]|\(source:|clause\s+\d+|section\s+\d+)", lowered))

    return has_number or has_factual_verb or has_keyword or has_vague_term or has_citation


def _claim_indicators(text: str) -> list[str]:
    lowered = text.lower()
    indicators: list[str] = []

    if re.search(r"\b\d+(?:\.\d+)?%?\b", text):
        indicators.append("specific numeric or dated claim")
    if any(term in lowered for term in VAGUE_TERMS):
        indicators.append("contains vague business language")
    if re.search(r"(\[[0-9]+\]|\(source:|clause\s+\d+|section\s+\d+)", lowered):
        indicators.append("contains a citation marker")
    if any(verb in lowered.split() for verb in FACTUAL_VERBS):
        indicators.append("assertive factual statement")

    return indicators or ["candidate factual statement"]
