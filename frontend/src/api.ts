import type { AuditResponse, SampleDocument, SampleInfo } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010";
export const BACKEND_START_COMMAND = "python -m uvicorn backend.app.main:app --reload --port 8010";
export const BACKEND_UNAVAILABLE_MESSAGE = `Backend unavailable. Start FastAPI with: ${BACKEND_START_COMMAND}`;

// The deployed backend runs on Azure Container Apps with min_replicas = 0,
// so the first request after an idle period pays a container cold start
// (measured at ~21s; warm requests are ~0.26s). Rather than hide that behind
// a generic spinner -- which reads as "this app is broken" -- we say what is
// happening and why the tradeoff was chosen.
export const COLD_START_MESSAGE =
  "Waking the backend — this deployment scales to zero when idle, so the first request after a quiet period takes ~20s. Subsequent requests are under 300ms. That tradeoff is why this runs at €0/month.";

// Long enough that ordinary warm requests never trip it, short enough that
// the explanation appears well before a visitor concludes nothing happened.
export const SLOW_REQUEST_THRESHOLD_MS = 1500;

type SlowRequestListener = (slow: boolean) => void;

const slowRequestListeners = new Set<SlowRequestListener>();

export function onSlowRequest(listener: SlowRequestListener): () => void {
  slowRequestListeners.add(listener);
  return () => slowRequestListeners.delete(listener);
}

function emitSlowRequest(slow: boolean): void {
  for (const listener of slowRequestListeners) {
    listener(slow);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // Every API call funnels through here, so the cold-start signal is wired in
  // one place rather than repeated per screen.
  const slowTimer = setTimeout(() => emitSlowRequest(true), SLOW_REQUEST_THRESHOLD_MS);
  const settle = () => {
    clearTimeout(slowTimer);
    emitSlowRequest(false);
  };

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    // Clear on failure too -- a stuck "Waking the backend..." banner after an
    // error would be worse than never showing one.
    settle();
    throw new Error(BACKEND_UNAVAILABLE_MESSAGE);
  }

  if (!response.ok) {
    settle();
    const detail = await readErrorDetail(response);
    throw new Error(detail || `Backend request failed with status ${response.status}.`);
  }

  try {
    return (await response.json()) as T;
  } finally {
    settle();
  }
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
