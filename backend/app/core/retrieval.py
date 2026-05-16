from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from backend.app.core.chunk import DocumentChunk
from backend.app.core.claim_extraction import ExtractedClaim


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "will",
}


@dataclass(frozen=True)
class EvidenceMatch:
    chunk_id: str
    text: str
    source: str
    score: float
    heading: str | None = None


def retrieve_evidence(
    claims: list[ExtractedClaim],
    chunks: list[DocumentChunk],
    top_k: int = 3,
) -> dict[str, list[EvidenceMatch]]:
    if not claims or not chunks:
        return {claim.id: [] for claim in claims}

    idf = _build_idf([chunk.text for chunk in chunks])
    chunk_vectors = {chunk.id: _tfidf_vector(chunk.text, idf) for chunk in chunks}
    results: dict[str, list[EvidenceMatch]] = {}

    for claim in claims:
        claim_vector = _tfidf_vector(claim.text, idf)
        scored: list[EvidenceMatch] = []

        for chunk in chunks:
            if chunk.id == claim.source_chunk_id:
                continue
            score = _cosine(claim_vector, chunk_vectors[chunk.id])
            if score <= 0:
                continue
            scored.append(
                EvidenceMatch(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    source=chunk.source,
                    score=round(score, 3),
                    heading=chunk.heading,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        results[claim.id] = scored[:top_k]

    return results


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9-]+", text.lower())
        if token not in STOPWORDS and len(token) > 2
    ]


def _build_idf(texts: list[str]) -> dict[str, float]:
    documents = [_tokens(text) for text in texts]
    total = max(len(documents), 1)
    document_frequency: Counter[str] = Counter()

    for tokens in documents:
        document_frequency.update(set(tokens))

    return {
        token: math.log((total + 1) / (frequency + 1)) + 1.0
        for token, frequency in document_frequency.items()
    }


def _tfidf_vector(text: str, idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(_tokens(text))
    if not counts:
        return {}

    vector = {token: count * idf.get(token, 1.0) for token, count in counts.items()}
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm == 0:
        return vector

    return {token: value / norm for token, value in vector.items()}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    smaller, larger = (left, right) if len(left) < len(right) else (right, left)
    return sum(value * larger.get(token, 0.0) for token, value in smaller.items())
