import type { AuditResponse, SampleDocument, SampleInfo } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010";
export const BACKEND_START_COMMAND = "python -m uvicorn backend.app.main:app --reload --port 8010";
export const BACKEND_UNAVAILABLE_MESSAGE = `Backend unavailable. Start FastAPI with: ${BACKEND_START_COMMAND}`;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    throw new Error(BACKEND_UNAVAILABLE_MESSAGE);
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || `Backend request failed with status ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

export function apiBaseUrl(): string {
  return API_BASE_URL;
}

export async function checkHealth(): Promise<boolean> {
  await request<{ status: string }>("/health");
  return true;
}

export function fetchSamples(): Promise<SampleInfo[]> {
  return request<SampleInfo[]>("/samples");
}

export function fetchSample(sampleId: string): Promise<SampleDocument> {
  return request<SampleDocument>(`/samples/${sampleId}`);
}

export async function auditDocument(params: {
  text: string;
  evidenceText: string;
  filename?: string;
  file?: File | null;
}): Promise<AuditResponse> {
  if (params.file) {
    const formData = new FormData();
    formData.append("file", params.file);
    if (params.evidenceText.trim()) {
      formData.append("evidence_text", params.evidenceText);
    }

    return request<AuditResponse>("/audit", {
      method: "POST",
      body: formData
    });
  }

  return request<AuditResponse>("/audit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: params.text,
      evidence_text: params.evidenceText || null,
      filename: params.filename ?? "pasted-document.md"
    })
  });
}

async function readErrorDetail(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return "";
  }

  try {
    const payload = JSON.parse(text) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    return text;
  }

  return text;
}
