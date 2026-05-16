import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import type { ClaimAudit } from "../types";
import { labelTone } from "../utils/risk";

interface TopRiskStackProps {
  claims: ClaimAudit[];
}

function TopRiskStack({ claims }: TopRiskStackProps) {
  return (
    <section className="glass-panel top-risk-panel">
      <div className="panel-title compact">
        <div>
          <p className="eyebrow">Priority findings</p>
          <h2>Top risks</h2>
        </div>
      </div>
      <div className="top-risk-stack">
        {claims.map((claim) => (
          <Link className="risk-card" key={claim.id} to={`/findings/${claim.id}`}>
            <span className={`label-pill ${labelTone(claim.label)}`}>{claim.label}</span>
            <p>{claim.text}</p>
            <div>
              <strong>{claim.risk_score}</strong>
              <span>{claim.id}</span>
              <ArrowUpRight size={16} />
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default TopRiskStack;
