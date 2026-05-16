import type { ClaimAudit } from "../types";
import { labelTone, riskSeverity } from "../utils/risk";

interface ClaimRiskHeaderProps {
  claim: ClaimAudit;
}

function ClaimRiskHeader({ claim }: ClaimRiskHeaderProps) {
  return (
    <section className="claim-risk-header">
      <div>
        <p className="eyebrow">Finding {claim.id}</p>
        <h2>{claim.text}</h2>
      </div>
      <div className="claim-score-stack">
        <span className={`label-pill ${labelTone(claim.label)}`}>{claim.label}</span>
        <strong>{claim.risk_score}</strong>
        <small>{riskSeverity(claim.risk_score)} risk</small>
      </div>
    </section>
  );
}

export default ClaimRiskHeader;
