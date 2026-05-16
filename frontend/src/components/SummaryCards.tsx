import { AlertTriangle, CheckCircle2, FileSearch, Gauge } from "lucide-react";
import type { AuditSummary } from "../types";

interface SummaryCardsProps {
  summary: AuditSummary;
}

function SummaryCards({ summary }: SummaryCardsProps) {
  const unsupported = summary.label_counts.Unsupported ?? 0;
  const review = summary.label_counts["Needs human review"] ?? 0;
  const supported = summary.label_counts.Supported ?? 0;

  return (
    <section className="summary-grid">
      <article className="metric-card">
        <Gauge size={20} />
        <span>Overall risk</span>
        <strong>{summary.overall_risk_score}/100</strong>
      </article>
      <article className="metric-card">
        <FileSearch size={20} />
        <span>Claims extracted</span>
        <strong>{summary.total_claims}</strong>
      </article>
      <article className="metric-card">
        <AlertTriangle size={20} />
        <span>Unsupported</span>
        <strong>{unsupported}</strong>
      </article>
      <article className="metric-card">
        <CheckCircle2 size={20} />
        <span>Supported</span>
        <strong>{supported}</strong>
      </article>
      <article className="metric-card">
        <AlertTriangle size={20} />
        <span>Human review</span>
        <strong>{review}</strong>
      </article>
    </section>
  );
}

export default SummaryCards;
