import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { BACKEND_UNAVAILABLE_MESSAGE, auditDocument, checkHealth, fetchSample, fetchSamples } from "../api";
import { FALLBACK_SAMPLE, FALLBACK_SAMPLES, fallbackSampleById } from "../data/fallbackSamples";
import type { AuditResponse, ClaimAudit, SampleInfo } from "../types";

interface AuditContextValue {
  samples: SampleInfo[];
  activeSampleId: string;
  documentTitle: string;
  documentText: string;
  evidenceText: string;
  file: File | null;
  audit: AuditResponse | null;
  selectedClaimId: string;
  loading: boolean;
  error: string | null;
  backendStatus: BackendStatus;
  backendMessage: string;
  usingFallbackSample: boolean;
  highestRiskClaims: ClaimAudit[];
  selectedClaim: ClaimAudit | null;
  riskBand: RiskBand;
  categoryRows: CategoryRow[];
  setDocumentText: (value: string) => void;
  setEvidenceText: (value: string) => void;
  setSelectedClaimId: (value: string) => void;
  loadSample: (sampleId: string) => Promise<void>;
  setInputFile: (file: File | null) => void;
  runAudit: () => Promise<AuditResponse | null>;
  clearError: () => void;
}

export interface CategoryRow {
  label: string;
  count: number;
  tone: string;
}

export type RiskBand = "Nominal" | "Elevated" | "High" | "Critical";
export type BackendStatus = "checking" | "online" | "offline";

const AuditContext = createContext<AuditContextValue | null>(null);

export function AuditProvider({ children }: { children: ReactNode }) {
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [activeSampleId, setActiveSampleId] = useState("");
  const [documentTitle, setDocumentTitle] = useState("pasted-document.md");
  const [documentText, setDocumentTextState] = useState("");
  const [evidenceText, setEvidenceText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [selectedClaimId, setSelectedClaimId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [backendMessage, setBackendMessage] = useState("Checking FastAPI backend...");
  const [usingFallbackSample, setUsingFallbackSample] = useState(false);

  useEffect(() => {
    void bootstrapSamples();
  }, []);

  const highestRiskClaims = useMemo(() => {
    if (!audit) {
      return [];
    }
    return [...audit.claims].sort((a, b) => b.risk_score - a.risk_score).slice(0, 6);
  }, [audit]);

  const selectedClaim = useMemo(() => {
    if (!audit) {
      return null;
    }
    return audit.claims.find((claim) => claim.id === selectedClaimId) ?? highestRiskClaims[0] ?? audit.claims[0] ?? null;
  }, [audit, highestRiskClaims, selectedClaimId]);

  const riskBand = useMemo(() => toRiskBand(audit?.summary.overall_risk_score ?? 0), [audit]);

  const categoryRows = useMemo(() => {
    const counts = audit?.summary.label_counts ?? {};
    return [
      { label: "Supported", count: counts.Supported ?? 0, tone: "supported" },
      { label: "Weakly supported", count: counts["Weakly supported"] ?? 0, tone: "weak" },
      { label: "Unsupported", count: counts.Unsupported ?? 0, tone: "danger" },
      { label: "Vague / non-verifiable", count: counts["Vague / non-verifiable"] ?? 0, tone: "vague" },
      { label: "Needs human review", count: counts["Needs human review"] ?? 0, tone: "review" }
    ];
  }, [audit]);

  async function loadSampleById(sampleId: string) {
    setError(null);
    setActiveSampleId(sampleId);
    setFile(null);

    const fallbackSample = fallbackSampleById(sampleId);
    if (fallbackSample) {
      applySample(fallbackSample.title, fallbackSample.content);
      setUsingFallbackSample(true);
      return;
    }

    try {
      const sample = await fetchSample(sampleId);
      setUsingFallbackSample(false);
      applySample(sample.title, sample.content);
    } catch (err) {
      const message = err instanceof Error ? err.message : BACKEND_UNAVAILABLE_MESSAGE;
      setError(message);
      setBackendStatus("offline");
      setBackendMessage(BACKEND_UNAVAILABLE_MESSAGE);
      loadFallbackSample();
    }
  }

  async function bootstrapSamples() {
    setBackendStatus("checking");
    setBackendMessage("Checking FastAPI backend...");
    try {
      await checkHealth();
      setBackendStatus("online");
      setBackendMessage("FastAPI backend connected on port 8010.");

      const sampleList = await fetchSamples();
      const nextSamples = sampleList.length > 0 ? sampleList : FALLBACK_SAMPLES;
      setSamples(nextSamples);
      if (sampleList[0]) {
        await loadSampleById(sampleList[0].id);
      } else {
        loadFallbackSample();
      }
    } catch (err) {
      setBackendStatus("offline");
      setBackendMessage(BACKEND_UNAVAILABLE_MESSAGE);
      setError(BACKEND_UNAVAILABLE_MESSAGE);
      setSamples(FALLBACK_SAMPLES);
      loadFallbackSample();
    }
  }

  function loadFallbackSample() {
    setActiveSampleId(FALLBACK_SAMPLE.id);
    setFile(null);
    setUsingFallbackSample(true);
    applySample(FALLBACK_SAMPLE.title, FALLBACK_SAMPLE.content);
  }

  function applySample(title: string, content: string) {
    setDocumentTitle(title);
    setDocumentTextState(content);
    setAudit(null);
    setSelectedClaimId("");
  }

  function setDocumentText(value: string) {
    setFile(null);
    setActiveSampleId("");
    setDocumentTitle("pasted-document.md");
    setDocumentTextState(value);
    setAudit(null);
    setSelectedClaimId("");
  }

  function setInputFile(nextFile: File | null) {
    setFile(nextFile);
    if (nextFile) {
      setActiveSampleId("");
      setDocumentTitle(nextFile.name);
      setAudit(null);
      setSelectedClaimId("");
    }
  }

  async function runAudit() {
    setLoading(true);
    setError(null);
    try {
      const result = await auditDocument({
        text: documentText,
        evidenceText,
        filename: file?.name || documentTitle || "document.md",
        file
      });
      setAudit(result);
      setSelectedClaimId(result.claims[0]?.id ?? "");
      setBackendStatus("online");
      setBackendMessage("FastAPI backend connected on port 8010.");
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Audit failed.";
      setError(message);
      if (message.includes("Backend unavailable")) {
        setBackendStatus("offline");
        setBackendMessage(BACKEND_UNAVAILABLE_MESSAGE);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }

  const value: AuditContextValue = {
    samples,
    activeSampleId,
    documentTitle,
    documentText,
    evidenceText,
    file,
    audit,
    selectedClaimId,
    loading,
    error,
    backendStatus,
    backendMessage,
    usingFallbackSample,
    highestRiskClaims,
    selectedClaim,
    riskBand,
    categoryRows,
    setDocumentText,
    setEvidenceText,
    setSelectedClaimId,
    loadSample: loadSampleById,
    setInputFile,
    runAudit,
    clearError: () => setError(null)
  };

  return <AuditContext.Provider value={value}>{children}</AuditContext.Provider>;
}

export function useAudit() {
  const context = useContext(AuditContext);
  if (!context) {
    throw new Error("useAudit must be used within AuditProvider");
  }
  return context;
}

function toRiskBand(score: number): RiskBand {
  if (score >= 75) return "Critical";
  if (score >= 55) return "High";
  if (score >= 30) return "Elevated";
  return "Nominal";
}
