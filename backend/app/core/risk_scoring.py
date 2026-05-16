from __future__ import annotations

import re

from backend.app.core.claim_extraction import ExtractedClaim
from backend.app.core.retrieval import EvidenceMatch
from backend.app.schemas import ClaimAudit, EvidenceSnippet, SupportLabel


STRONG_LANGUAGE = {
    "always",
    "guaranteed",
    "guarantee",
    "proven",
    "never",
    "no risk",
    "fully compliant",
    "eliminates",
    "all cases",
    "without exception",
}

VAGUE_LANGUAGE = {
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
    "efficient",
    "effective",
}

CONTRADICTION_TERMS = {
    "however",
    "except",
    "unless",
    "not yet",
    "pending",
    "failed",
    "missing",
    "unverified",
    "manual review",
}


def score_claims(
    claims: list[ExtractedClaim],
    evidence_by_claim: dict[str, list[EvidenceMatch]],
) -> list[ClaimAudit]:
    audits: list[ClaimAudit] = []

    for claim in claims:
        evidence = evidence_by_claim.get(claim.id, [])
        top_score = evidence[0].score if evidence else 0.0
        label = _classify(claim.text, top_score, evidence)
        risk_score = _risk_score(claim.text, top_score, label, evidence)
        factors = _factors(claim.text, top_score, evidence)

        audits.append(
            ClaimAudit(
                id=claim.id,
                text=claim.text,
                source_chunk_id=claim.source_chunk_id,
                label=label,
                risk_score=risk_score,
                confidence=_confidence(top_score, label),
                explanation=_explanation(label, top_score, factors),
                factors=factors,
                evidence=[
                    EvidenceSnippet(
                        chunk_id=item.chunk_id,
                        text=item.text,
                        source=item.source,
                        score=item.score,
                        heading=item.heading,
                    )
                    for item in evidence
                ],
            )
        )

    return audits


def _classify(text: str, top_score: float, evidence: list[EvidenceMatch]) -> SupportLabel:
    vague = _has_vague_language(text) and not _has_numeric_specificity(text)
    strong = _has_strong_language(text)
    contradictory = _has_contradictory_evidence(evidence)

    if vague and top_score < 0.24:
        return "Vague / non-verifiable"
    if contradictory:
        return "Needs human review"
    if top_score >= 0.36 and not strong:
        return "Supported"
    if top_score >= 0.42 and strong:
        return "Weakly supported"
    if 0.18 <= top_score < 0.36:
        return "Weakly supported"
    if strong and 0.10 <= top_score < 0.18:
        return "Needs human review"
    return "Unsupported"


def _risk_score(text: str, top_score: float, label: SupportLabel, evidence: list[EvidenceMatch]) -> int:
    base_by_label = {
        "Supported": 18,
        "Weakly supported": 48,
        "Unsupported": 86,
        "Vague / non-verifiable": 72,
        "Needs human review": 68,
    }
    score = base_by_label[label]

    if _has_strong_language(text):
        score += 10
    if _has_numeric_specificity(text) and top_score < 0.22:
        score += 8
    if _has_citation_marker(text):
        score -= 8
    if evidence and top_score > 0.45:
        score -= 6
    if _has_contradictory_evidence(evidence):
        score += 12

    return max(0, min(100, score))


def _confidence(top_score: float, label: SupportLabel) -> float:
    if label == "Supported":
        return min(0.95, 0.58 + top_score)
    if label == "Unsupported":
        return 0.72 if top_score < 0.08 else 0.62
    return min(0.86, 0.45 + top_score)


def _factors(text: str, top_score: float, evidence: list[EvidenceMatch]) -> list[str]:
    factors: list[str] = []

    if top_score > 0:
        factors.append(f"Top evidence similarity: {top_score:.2f}")
    else:
        factors.append("No supporting passage found")
    if _has_numeric_specificity(text):
        factors.append("Contains numeric or dated specificity")
    if _has_strong_language(text):
        factors.append("Uses high-certainty language")
    if _has_vague_language(text):
        factors.append("Contains vague business language")
    if _has_citation_marker(text):
        factors.append("Contains citation or clause marker")
    if _has_contradictory_evidence(evidence):
        factors.append("Retrieved evidence contains caution or exception language")

    return factors


def _explanation(label: SupportLabel, top_score: float, factors: list[str]) -> str:
    if label == "Supported":
        return "The claim has a close supporting passage and no major risk language was detected."
    if label == "Weakly supported":
        return "The claim has some related evidence, but the match is not strong enough for high confidence."
    if label == "Unsupported":
        return "The claim is specific or assertive, but the document does not provide a close supporting passage."
    if label == "Vague / non-verifiable":
        return "The claim uses broad language that is difficult to verify without clearer metrics or evidence."
    return "The claim has mixed signals and should be checked by a human reviewer."


def _has_numeric_specificity(text: str) -> bool:
    return bool(re.search(r"\b\d+(?:\.\d+)?%?\b|\b20\d{2}\b|\bQ[1-4]\b", text))


def _has_citation_marker(text: str) -> bool:
    return bool(re.search(r"(\[[0-9]+\]|\(source:|clause\s+\d+|section\s+\d+)", text.lower()))


def _has_strong_language(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in STRONG_LANGUAGE)


def _has_vague_language(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in VAGUE_LANGUAGE)


def _has_contradictory_evidence(evidence: list[EvidenceMatch]) -> bool:
    combined = " ".join(item.text.lower() for item in evidence[:2])
    return any(term in combined for term in CONTRADICTION_TERMS)
