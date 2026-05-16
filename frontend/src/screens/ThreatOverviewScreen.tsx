import { Link, Navigate } from "react-router-dom";
import { ArrowRight, ShieldAlert } from "lucide-react";
import { useAudit } from "../context/AuditContext";
import RiskScoreRing from "../components/RiskScoreRing";
import ClaimCategoryMatrix from "../components/ClaimCategoryMatrix";
import TopRiskStack from "../components/TopRiskStack";
import ExecutiveBriefingPanel from "../components/ExecutiveBriefingPanel";
import ReviewChecklistPanel from "../components/ReviewChecklistPanel";
import ExportDock from "../components/ExportDock";
import LLMReviewPanel from "../components/LLMReviewPanel";

function ThreatOverviewScreen() {
  const { audit, riskBand, categoryRows, highestRiskClaims } = useAudit();

  if (!audit) {
    return <Navigate to="/scan" replace />;
  }

  return (
    <div className="screen overview-screen">
      <section className="overview-hero">
        <RiskScoreRing score={audit.summary.overall_risk_score} band={riskBand} />
        <div className="overview-actions">
          <ExportDock audit={audit} />
          {highestRiskClaims[0] && (
            <Link className="next-action" to={`/findings/${highestRiskClaims[0].id}`}>
              <ShieldAlert size={17} />
              <span>Inspect highest risk</span>
              <ArrowRight size={16} />
            </Link>
          )}
        </div>
      </section>

      <div className="overview-grid">
        <ExecutiveBriefingPanel audit={audit} />
        <ClaimCategoryMatrix rows={categoryRows} total={audit.summary.total_claims} />
      </div>

      <div className="overview-grid asym">
        <TopRiskStack claims={highestRiskClaims} />
        <div className="overview-side-stack">
          <LLMReviewPanel review={audit.llm_review} />
          <ReviewChecklistPanel items={audit.summary.review_checklist} />
        </div>
      </div>
    </div>
  );
}

export default ThreatOverviewScreen;
