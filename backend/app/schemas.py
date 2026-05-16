from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SupportLabel = Literal[
    "Supported",
    "Weakly supported",
    "Unsupported",
    "Vague / non-verifiable",
    "Needs human review",
]


class AuditRequest(BaseModel):
    text: str | None = Field(default=None, description="Document text to audit.")
    evidence_text: str | None = Field(default=None, description="Optional attached evidence pack text.")
    filename: str | None = Field(default=None, description="Display filename for the audited document.")
    sample_id: str | None = Field(default=None, description="Optional built-in sample identifier.")


class SampleInfo(BaseModel):
    id: str
    title: str
    description: str
    filename: str


class SampleDocument(SampleInfo):
    content: str


class EvidenceSnippet(BaseModel):
    chunk_id: str
    text: str
    source: str
    score: float
    heading: str | None = None


class ClaimAudit(BaseModel):
    id: str
    text: str
    source_chunk_id: str
    label: SupportLabel
    risk_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    factors: list[str]
    evidence: list[EvidenceSnippet]


class AuditSummary(BaseModel):
    title: str
    total_claims: int
    overall_risk_score: int = Field(ge=0, le=100)
    label_counts: dict[str, int]
    executive_summary: str
    review_checklist: list[str]


class AuditResponse(BaseModel):
    document_title: str
    summary: AuditSummary
    claims: list[ClaimAudit]
    markdown_report: str


class ExportRequest(BaseModel):
    audit: AuditResponse
    format: Literal["markdown", "json"] = "markdown"
