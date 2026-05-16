import { Link, Navigate, useParams } from "react-router-dom";
import { ArrowLeft, Gauge } from "lucide-react";
import { useAudit } from "../context/AuditContext";
import ClaimRiskHeader from "../components/ClaimRiskHeader";
import EvidenceSnippetStack from "../components/EvidenceSnippetStack";
import RiskFactorChips from "../components/RiskFactorChips";
import DocumentContextPanel from "../components/DocumentContextPanel";
import FindingNavigator from "../components/FindingNavigator";
import LockedRoutePanel from "../components/LockedRoutePanel";

function FindingDeepDiveScreen() {
  const { claimId } = useParams();
  const { audit, documentText, highestRiskClaims } = useAudit();

  if (!audit) {
    return <LockedRoutePanel viewName="Deep dive" />;
  }

  const selected = audit.claims.find((claim) => claim.id === claimId) ?? highestRiskClaims[0] ?? audit.claims[0];
  if (!selected) {
    return <Navigate to="/overview" replace />;
  }

  return (
    <div className="screen deep-dive-screen">
      <Link className="back-link" to="/overview">
        <ArrowLeft size={16} />
        <span>Back to overview</span>
      </Link>

      <ClaimRiskHeader claim={selected} />

      <div className="deep-grid">
        <div className="deep-main">
          <section className="glass-panel explanation-panel">
            <div className="panel-title compact">
              <Gauge size={18} />
              <div>
                <p className="eyebrow">Risk explanation</p>
                <h2>Why this claim is flagged</h2>
              </div>
            </div>
            <p>{selected.explanation}</p>
            <RiskFactorChips factors={selected.factors} />
            <div className="confidence-strip">
              <span>Model confidence</span>
              <strong>{Math.round(selected.confidence * 100)}%</strong>
              <span>Source chunk</span>
              <strong>{selected.source_chunk_id}</strong>
            </div>
          </section>
          <EvidenceSnippetStack evidence={selected.evidence} />
          <DocumentContextPanel documentText={documentText} claim={selected} />
        </div>
        <FindingNavigator claims={audit.claims} activeClaimId={selected.id} />
      </div>
    </div>
  );
}

export default FindingDeepDiveScreen;
