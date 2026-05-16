import { CheckCircle2, CircleAlert } from "lucide-react";
import { useAudit } from "../context/AuditContext";

function ScanReadinessChecklist() {
  const { documentText, file, evidenceText, backendStatus, usingFallbackSample } = useAudit();
  const hasDocument = Boolean(file || documentText.trim());
  const hasEvidence = Boolean(evidenceText.trim());
  const backendReady = backendStatus === "online";

  return (
    <section className="glass-panel readiness-panel">
      <p className="eyebrow">Pre-scan checklist</p>
      <ul>
        <li className={hasDocument ? "ready" : ""}>
          {hasDocument ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}
          <span>
            {hasDocument
              ? `Document payload available${usingFallbackSample ? " from frontend fallback sample" : ""}`
              : "Load a sample, paste text, or upload a file to enable Run risk scan"}
          </span>
        </li>
        <li className={backendReady ? "ready" : "warning"}>
          {backendReady ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}
          <span>
            {backendReady
              ? "FastAPI backend is reachable for audit execution"
              : "Backend must be started before a real audit can complete"}
          </span>
        </li>
        <li className={hasEvidence ? "ready" : ""}>
          {hasEvidence ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}
          <span>Evidence pack {hasEvidence ? "attached" : "optional"}</span>
        </li>
        <li className="ready">
          <CheckCircle2 size={16} />
          <span>Deterministic audit mode enabled</span>
        </li>
      </ul>
    </section>
  );
}

export default ScanReadinessChecklist;
