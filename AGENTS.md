# Agent Handoff Notes

Read this file after every context compaction before making changes in this repository.

## Project

Repository: `enterprise-ai-document-risk-auditor`

Purpose: polished GitHub portfolio project for responsible AI, document-grounded review, claim extraction, evidence retrieval, risk scoring, and human-review workflow. The audience is AI engineering, data science, responsible-AI, and consulting-technology recruiters.

Default local app:

- Backend: FastAPI on `http://127.0.0.1:8010`
- Frontend: React/Vite on `http://127.0.0.1:5173`
- Default UI demo: `data/samples/consulting_report_sample.md`

Port `8000` was blocked on this Windows machine, so the repo uses backend port `8010`.

## Safety Rules

- Do not commit private data, coursework, client files, API keys, `.env`, raw datasets, generated benchmark outputs, `.venv`, `node_modules`, or `frontend/dist`.
- Raw datasets go under `data/raw/`, which is ignored.
- Generated evaluation outputs go under `data/eval/`, except `data/eval/README.md`, which is tracked.
- Keep the app runnable with included synthetic samples even when no dataset or API key is available.

## Current Architecture

Backend modules:

- `backend/app/core/audit_pipeline.py`: shared deterministic audit entry point used by API and scripts.
- `ingest.py`, `chunk.py`, `claim_extraction.py`, `retrieval.py`, `risk_scoring.py`, `report_generation.py`: deterministic pipeline.
- `llm_provider.py`: optional Gemini reviewer layer via REST `generateContent`; deterministic audit remains the baseline.

Frontend:

- React/Vite dashboard in `frontend/src`.
- Use `npm.cmd`, not `npm`, in PowerShell because `npm.ps1` can be blocked.
- Browser verification was done with the in-app Browser plugin / Playwright workflow.

Dataset scripts:

- `scripts/prepare_fever_subset.py`
- `scripts/evaluate_fever_risk.py`
- `scripts/prepare_cuad_subset.py`

## Gemini Setup

Gemini is optional and disabled by default.

To test it locally:

1. Copy `.env.example` to `.env`.
2. Set `LLM_MODE=gemini`.
3. Replace `GEMINI_API_KEY=replace-with-your-gemini-api-key` with the real student key.
4. Keep `GEMINI_MODEL=gemini-2.5-flash-lite` unless the key only permits another model.
5. Restart the backend.

The frontend shows a Gemini reviewer panel only when Gemini mode is configured, not configured, completed, or errored. If disabled, the panel is hidden.

## Verification Commands

From repo root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest
```

Frontend:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
npm.cmd audit
```

End-to-end smoke:

- Start backend on `8010`.
- Start frontend on `5173`.
- Open `http://127.0.0.1:5173`.
- Select the consulting report sample.
- Click `Run audit`.
- Confirm claims, evidence snippets, export controls, and optional Gemini reviewer state render.

## GitHub Workflow

This repo is a standalone public portfolio repo, not a monorepo dump. Use clean commits with recruiter-readable project scope. If remote is configured:

```powershell
git status
git add <changed files>
git commit -m "Concise change summary"
git push
```

Remote currently used during setup:

```text
https://github.com/GeorgeAnes/enterprise-ai-document-risk-auditor.git
```

## Development Notes

- Prefer deterministic logic and transparent scoring first; optional LLMs should explain or review, not replace the baseline.
- Do not make paid API calls in tests.
- Tests mock LLM calls.
- Keep README commands portable; avoid absolute local OneDrive paths.
- If adding screenshots, save small useful images under `docs/`.
