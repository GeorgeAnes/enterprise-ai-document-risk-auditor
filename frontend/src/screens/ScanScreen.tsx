import { useNavigate } from "react-router-dom";
import { Play, ShieldCheck } from "lucide-react";
import { useAudit } from "../context/AuditContext";
import SampleSelector from "../components/SampleSelector";
import DocumentDropzone from "../components/DocumentDropzone";
import EvidencePackPanel from "../components/EvidencePackPanel";
import ScanRadar from "../components/ScanRadar";
import ScanReadinessChecklist from "../components/ScanReadinessChecklist";

function ScanScreen() {
  const navigate = useNavigate();
  const { documentText, file, loading, error, runAudit, clearError } = useAudit();
  const canScan = Boolean(file || documentText.trim());

  async function handleScan() {
    clearError();
    const result = await runAudit();
    if (result) {
      navigate("/overview");
    }
  }

  return (
    <div className="screen scan-screen">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Ingestion / scan</p>
          <h2>Audit enterprise documents for unsupported claims and grounding risk.</h2>
          <p>
            Load a safe sample, upload a document, or paste source text. The scan runs locally against the existing
            deterministic audit pipeline.
          </p>
        </div>
        <button className="scan-cta" type="button" onClick={() => void handleScan()} disabled={!canScan || loading}>
          <Play size={18} />
          <span>{loading ? "Scanning document" : "Run risk scan"}</span>
        </button>
      </section>

      <div className="scan-grid">
        <div className="scan-left">
          <SampleSelector />
          <DocumentDropzone />
        </div>
        <div className="scan-right">
          <ScanRadar active={loading} />
          <ScanReadinessChecklist />
          <EvidencePackPanel />
          {error && (
            <div className="error-banner" role="alert" aria-live="assertive">
              <ShieldCheck size={16} />
              <span>{error}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ScanScreen;
