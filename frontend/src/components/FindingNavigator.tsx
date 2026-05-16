import { Link } from "react-router-dom";
import type { ClaimAudit } from "../types";
import { labelTone } from "../utils/risk";

interface FindingNavigatorProps {
  claims: ClaimAudit[];
  activeClaimId: string;
}

function FindingNavigator({ claims, activeClaimId }: FindingNavigatorProps) {
  return (
    <section className="glass-panel finding-nav">
      <p className="eyebrow">Finding index</p>
      <div>
        {claims.map((claim) => (
          <Link className={claim.id === activeClaimId ? "active" : ""} key={claim.id} to={`/findings/${claim.id}`}>
            <span className={`label-dot ${labelTone(claim.label)}`} />
            <strong>{claim.id}</strong>
            <small>{claim.risk_score}</small>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default FindingNavigator;
