import { useEffect, useMemo, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { auditDocument, fetchSample, fetchSamples } from "./api";
import AuditDashboard from "./components/AuditDashboard";
import Sidebar from "./components/Sidebar";
import type { AuditResponse, ClaimAudit, LabelFilter, SampleInfo } from "./types";

function App() {
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [activeSampleId, setActiveSampleId] = useState<string>("");
  const [documentTitle, setDocumentTitle] = useState("pasted-document.md");
  const [documentText, setDocumentText] = useState("");
  const [evidenceText, setEvidenceText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");
  const [filter, setFilter] = useState<LabelFilter>("All");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then(async (sampleList) => {
        setSamples(sampleList);
        if (sampleList[0]) {
          await handleSampleSelect(sampleList[0].id);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const filteredClaims = useMemo(() => {
    if (!audit) {
      return [];
    }
    if (filter === "All") {
      return audit.claims;
    }
    return audit.claims.filter((claim) => claim.label === filter);
  }, [audit, filter]);

  const selectedClaim: ClaimAudit | null = useMemo(() => {
    if (!audit) {
      return null;
    }
    return audit.claims.find((claim) => claim.id === selectedClaimId) ?? audit.claims[0] ?? null;
  }, [audit, selectedClaimId]);

  async function handleSampleSelect(sampleId: string) {
    setError(null);
    setActiveSampleId(sampleId);
    setFile(null);
    const sample = await fetchSample(sampleId);
    setDocumentText(sample.content);
    setDocumentTitle(sample.title);
    setAudit(null);
    setSelectedClaimId("");
  }

  function handleFileChange(nextFile: File | null) {
    setFile(nextFile);
    if (nextFile) {
      setActiveSampleId("");
      setDocumentTitle(nextFile.name);
    }
  }

  async function handleAudit() {
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
      setFilter("All");
      setSelectedClaimId(result.claims[0]?.id ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <ShieldAlert size={22} />
          </div>
          <div>
            <p className="eyebrow">Responsible AI Review Console</p>
            <h1>Enterprise AI Document Risk Auditor</h1>
          </div>
        </div>
        <div className="status-pill">Deterministic no-LLM mode</div>
      </header>

      <div className="workspace">
        <Sidebar
          samples={samples}
          activeSampleId={activeSampleId}
          documentText={documentText}
          evidenceText={evidenceText}
          file={file}
          loading={loading}
          error={error}
          onSelectSample={handleSampleSelect}
          onDocumentTextChange={setDocumentText}
          onEvidenceTextChange={setEvidenceText}
          onFileChange={handleFileChange}
          onAudit={handleAudit}
        />
        <AuditDashboard
          audit={audit}
          filteredClaims={filteredClaims}
          selectedClaim={selectedClaim}
          filter={filter}
          loading={loading}
          onFilterChange={setFilter}
          onClaimSelect={setSelectedClaimId}
        />
      </div>
    </div>
  );
}

export default App;
