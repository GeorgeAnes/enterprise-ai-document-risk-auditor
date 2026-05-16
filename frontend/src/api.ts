import type { AuditResponse, SampleDocument, SampleInfo } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
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
