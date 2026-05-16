from __future__ import annotations

from backend.app.core.chunk import chunk_text
from backend.app.core.claim_extraction import extract_claims
from backend.app.core.ingest import document_from_text, normalize_text
from backend.app.core.report_generation import build_summary, to_markdown_report
from backend.app.core.retrieval import retrieve_evidence
from backend.app.core.risk_scoring import score_claims
from backend.app.schemas import AuditResponse


def run_audit_text(text: str, evidence_text: str | None = None, title: str = "Document") -> AuditResponse:
    document = document_from_text(text, title=title)
    document_chunks = chunk_text(document.text, source="document")
    evidence_chunks = list(document_chunks)

    if evidence_text and evidence_text.strip():
        evidence_clean = normalize_text(evidence_text)
        if evidence_clean:
            evidence_chunks.extend(chunk_text(evidence_clean, source="evidence"))

    claims = extract_claims(document_chunks)
    evidence_by_claim = retrieve_evidence(claims, evidence_chunks, top_k=3)
    claim_audits = score_claims(claims, evidence_by_claim)
    summary = build_summary(document.title, claim_audits)

    response = AuditResponse(
        document_title=document.title,
        summary=summary,
        claims=claim_audits,
        markdown_report="",
    )
    response.markdown_report = to_markdown_report(response)
    return response
