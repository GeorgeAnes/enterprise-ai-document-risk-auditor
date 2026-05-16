from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from starlette.datastructures import UploadFile

from backend.app.core.chunk import chunk_text
from backend.app.core.claim_extraction import extract_claims
from backend.app.core.ingest import IngestError, document_from_text, text_from_bytes
from backend.app.core.report_generation import build_summary, to_markdown_report
from backend.app.core.retrieval import retrieve_evidence
from backend.app.core.risk_scoring import score_claims
from backend.app.schemas import AuditRequest, AuditResponse, ExportRequest, SampleDocument, SampleInfo


REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = REPO_ROOT / "data" / "samples"

SAMPLES = {
    "consulting_report": SampleInfo(
        id="consulting_report",
        title="Consulting Report Sample",
        description="Synthetic operating model report with mixed support quality.",
        filename="consulting_report_sample.md",
    ),
    "contract_review": SampleInfo(
        id="contract_review",
        title="Contract Review Sample",
        description="Synthetic contract-like document with vague obligations and clause references.",
        filename="contract_review_sample.md",
    ),
    "ai_policy": SampleInfo(
        id="ai_policy",
        title="AI Policy Sample",
        description="Synthetic AI governance policy with evidence and control gaps.",
        filename="ai_policy_sample.md",
    ),
}

app = FastAPI(
    title="Enterprise AI Document Risk Auditor",
    version="0.1.0",
    description="Local-first audit API for claim grounding and document risk review.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/samples", response_model=list[SampleInfo])
def list_samples() -> list[SampleInfo]:
    return list(SAMPLES.values())


@app.get("/samples/{sample_id}", response_model=SampleDocument)
def get_sample(sample_id: str) -> SampleDocument:
    info = _sample_info(sample_id)
    content = _read_sample(info)
    return SampleDocument(**info.model_dump(), content=content)


@app.post("/audit", response_model=AuditResponse)
async def audit(request: Request) -> AuditResponse:
    try:
        payload = await _parse_audit_request(request)
        document = _resolve_document(payload)
        evidence_text = payload.evidence_text or ""

        document_chunks = chunk_text(document.text, source="document")
        evidence_chunks = list(document_chunks)
        if evidence_text.strip():
            evidence_document = document_from_text(evidence_text, title="Evidence pack")
            evidence_chunks.extend(chunk_text(evidence_document.text, source="evidence"))

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
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/export", response_model=None)
def export_report(payload: ExportRequest) -> Response:
    if payload.format == "json":
        return JSONResponse(content=json.loads(payload.audit.model_dump_json()))

    return PlainTextResponse(content=to_markdown_report(payload.audit), media_type="text/markdown")


async def _parse_audit_request(request: Request) -> AuditRequest:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        text = _form_value(form.get("text"))
        evidence_text = _form_value(form.get("evidence_text"))
        sample_id = _form_value(form.get("sample_id"))
        filename = _form_value(form.get("filename"))

        uploaded = form.get("file")
        if isinstance(uploaded, UploadFile) and uploaded.filename:
            content = await uploaded.read()
            document = text_from_bytes(uploaded.filename, content)
            text = document.text
            filename = document.title

        evidence_upload = form.get("evidence_file")
        if isinstance(evidence_upload, UploadFile) and evidence_upload.filename:
            content = await evidence_upload.read()
            evidence_text = text_from_bytes(evidence_upload.filename, content).text

        return AuditRequest(text=text, evidence_text=evidence_text, filename=filename, sample_id=sample_id)

    data = await request.json()
    return AuditRequest.model_validate(data)


def _resolve_document(payload: AuditRequest):
    if payload.sample_id:
        info = _sample_info(payload.sample_id)
        return document_from_text(_read_sample(info), title=info.title)

    return document_from_text(payload.text, title=payload.filename or "Uploaded document")


def _sample_info(sample_id: str) -> SampleInfo:
    if sample_id not in SAMPLES:
        raise HTTPException(status_code=404, detail=f"Unknown sample '{sample_id}'.")
    return SAMPLES[sample_id]


def _read_sample(info: SampleInfo) -> str:
    path = SAMPLE_DIR / info.filename
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Sample file missing: {info.filename}")
    return path.read_text(encoding="utf-8")


def _form_value(value: object) -> str | None:
    if value is None or isinstance(value, UploadFile):
        return None
    text = str(value).strip()
    return text or None
