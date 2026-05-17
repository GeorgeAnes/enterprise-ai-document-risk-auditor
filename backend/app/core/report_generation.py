from __future__ import annotations

from collections import Counter

from backend.app.schemas import AuditResponse, AuditSummary, ClaimAudit


HIGH_RISK_LABELS = {"Unsupported", "Vague / non-verifiable", "Needs human review"}


def build_summary(title: str, claims: list[ClaimAudit]) -> AuditSummary:
    label_counts = Counter(claim.label for claim in claims)
    total_claims = len(claims)
    overall_risk = round(sum(claim.risk_score for claim in claims) / total_claims) if total_claims else 0
    high_risk_count = sum(1 for claim in claims if claim.label in HIGH_RISK_LABELS)

    if not claims:
        executive_summary = "No auditable claims were detected. Add more substantive document text."
    elif high_risk_count == 0:
        executive_summary = "Most extracted claims have nearby supporting evidence. A reviewer should still check source quality and citation completeness."
    else:
        executive_summary = (
            f"{high_risk_count} of {total_claims} extracted claims require attention because they are unsupported, vague, or need human review."
        )

    return AuditSummary(
        title=title,
        total_claims=total_claims,
        overall_risk_score=overall_risk,
        label_counts=dict(label_counts),
        executive_summary=executive_summary,
        review_checklist=build_review_checklist(claims),
    )


def build_review_checklist(claims: list[ClaimAudit]) -> list[str]:
    checklist = [
        "Confirm that every high-risk claim has a traceable source passage or remove it.",
        "Replace vague language with measurable scope, dates, owners, or assumptions.",
        "Check high-certainty words such as guaranteed, always, and proven.",
        "Verify that cited clauses or references point to the correct evidence.",
    ]

    if any(claim.label == "Needs human review" for claim in claims):
        checklist.insert(0, "Escalate mixed or contradictory claims to a subject-matter reviewer.")
    if any(claim.label == "Unsupported" for claim in claims):
        checklist.insert(0, "Prioritize unsupported claims before publishing the document.")

    return checklist


def to_markdown_report(response: AuditResponse) -> str:
    lines = [
        f"# Document Risk Audit: {response.document_title}",
        "",
        "## Executive Summary",
        response.summary.executive_summary,
        "",
        f"- Total claims: {response.summary.total_claims}",
        f"- Overall risk score: {response.summary.overall_risk_score}/100",
        "",
        "## Claim Findings",
    ]

    for claim in response.claims:
        lines.extend(
            [
                "",
                f"### {claim.id}: {claim.label}",
                "",
                f"**Risk score:** {claim.risk_score}/100",
                "",
                f"**Claim:** {claim.text}",
                "",
                f"**Why it matters:** {claim.explanation}",
                "",
                "**Factors:**",
            ]
        )
        lines.extend(f"- {factor}" for factor in claim.factors)
        lines.append("")
        lines.append("**Top evidence:**")
        if claim.evidence:
            for evidence in claim.evidence[:3]:
                lines.append(f"- `{evidence.chunk_id}` ({evidence.score:.2f}): {evidence.text}")
        else:
            lines.append("- No evidence retrieved.")

        if claim.llm_review:
            lines.extend(["", "**Local reviewer:**"])
            if claim.llm_review.reviewer_note:
                lines.append(f"- Note: {claim.llm_review.reviewer_note}")
            if claim.llm_review.suggested_rewrite:
                lines.append(f"- Suggested rewrite: {claim.llm_review.suggested_rewrite}")
            if claim.llm_review.business_impact:
                lines.append(f"- Business impact: {claim.llm_review.business_impact}")
            if claim.llm_review.missing_evidence_questions:
                lines.append("- Missing evidence questions:")
                lines.extend(f"  - {question}" for question in claim.llm_review.missing_evidence_questions)

    lines.extend(["", "## Review Checklist"])
    lines.extend(f"- {item}" for item in response.summary.review_checklist)

    if response.llm_review and response.llm_review.status == "completed":
        lines.extend(["", "## Local Reviewer Summary"])
        if response.llm_review.summary:
            lines.append(response.llm_review.summary)
        lines.extend(f"- {item}" for item in response.llm_review.reviewer_notes)

    lines.append("")
    return "\n".join(lines)
