import { FileSearch } from "lucide-react";
import type { ClaimAudit } from "../types";

interface EvidencePanelProps {
  claim: ClaimAudit | null;
}

function EvidencePanel({ claim }: EvidencePanelProps) {
  if (!claim) {
    return (
      <aside className="evidence-panel">
        <div className="muted-empty">Select a claim to inspect evidence.</div>
      </aside>
    );
  }

  return (
    <aside className="evidence-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Evidence viewer</p>
          <h3>{claim.id}</h3>
        </div>
        <div className="confidence">{Math.round(claim.confidence * 100)}%</div>
      </div>

      <div className="selected-claim">
        <span className="label">Claim</span>
        <p>{claim.text}</p>
      </div>

      <div className="selected-claim">
        <span className="label">Reason</span>
        <p>{claim.explanation}</p>
      </div>

      <div className="factor-list">
        {claim.factors.map((factor) => (
          <span key={factor}>{factor}</span>
        ))}
      </div>

      <div className="evidence-list">
        <div className="section-title compact">
          <FileSearch size={16} />
          <span>Retrieved passages</span>
        </div>
        {claim.evidence.map((item) => (
          <article className="evidence-item" key={item.chunk_id}>
            <div>
              <strong>{item.chunk_id}</strong>
              <span>{item.source}</span>
              <em>{item.score.toFixed(2)}</em>
            </div>
            <p>{item.text}</p>
          </article>
        ))}
        {claim.evidence.length === 0 && <div className="muted-empty">No supporting passage retrieved.</div>}
      </div>
    </aside>
  );
}

export default EvidencePanel;
