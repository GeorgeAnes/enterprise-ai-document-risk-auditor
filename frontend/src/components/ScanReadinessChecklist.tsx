import { CheckCircle2, CircleAlert } from "lucide-react";
import { useAudit } from "../context/AuditContext";

function ScanReadinessChecklist() {
  const { documentText, file, evidenceText } = useAudit();
  const hasDocument = Boolean(file || documentText.trim());
  const hasEvidence = Boolean(evidenceText.trim());

  return (
    <section className="glass-panel readiness-panel">
      <p className="eyebrow">Pre-scan checklist</p>
      <ul>
        <li className={hasDocument ? "ready" : ""}>
          {hasDocument ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}
          <span>Document payload available</span>
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
