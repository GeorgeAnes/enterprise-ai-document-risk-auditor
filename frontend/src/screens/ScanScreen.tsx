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
  const { documentText, file, loading, error, backendStatus, backendMessage, runAudit, clearError } = useAudit();
  const canScan = Boolean(file || documentText.trim());
  const disabledReason = canScan ? "" : "Load a sample, paste document text, or upload a file to enable the scan.";

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
          {disabledReason && <p className="inline-hint">{disabledReason}</p>}
          {backendStatus === "offline" && <p className="inline-hint warning">{backendMessage}</p>}
        </div>
        <button
          aria-describedby={!canScan ? "scan-disabled-reason" : undefined}
          className="scan-cta"
          type="button"
          onClick={() => void handleScan()}
          disabled={!canScan || loading}
          title={disabledReason || undefined}
        >
          <Play size={18} />
          <span>{loading ? "Scanning document" : "Run risk scan"}</span>
        </button>
        {!canScan && (
          <span className="sr-only" id="scan-disabled-reason">
            {disabledReason}
          </span>
        )}
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
