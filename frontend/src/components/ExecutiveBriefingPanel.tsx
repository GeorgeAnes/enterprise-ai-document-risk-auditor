import type { AuditResponse } from "../types";

interface ExecutiveBriefingPanelProps {
  audit: AuditResponse;
}

function ExecutiveBriefingPanel({ audit }: ExecutiveBriefingPanelProps) {
  return (
    <section className="glass-panel briefing-panel">
      <p className="eyebrow">Executive briefing</p>
      <h2>{audit.document_title}</h2>
      <p>{audit.summary.executive_summary}</p>
    </section>
  );
}

export default ExecutiveBriefingPanel;
