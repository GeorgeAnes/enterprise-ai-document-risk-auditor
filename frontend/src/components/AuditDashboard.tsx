import type { AuditResponse, ClaimAudit, LabelFilter } from "../types";
import ClaimTable from "./ClaimTable";
import EvidencePanel from "./EvidencePanel";
import ReportExport from "./ReportExport";
import SummaryCards from "./SummaryCards";

interface AuditDashboardProps {
  audit: AuditResponse | null;
  filteredClaims: ClaimAudit[];
  selectedClaim: ClaimAudit | null;
  filter: LabelFilter;
  loading: boolean;
  onFilterChange: (filter: LabelFilter) => void;
  onClaimSelect: (claimId: string) => void;
}

function AuditDashboard({
  audit,
  filteredClaims,
  selectedClaim,
  filter,
  loading,
  onFilterChange,
  onClaimSelect
}: AuditDashboardProps) {
  if (!audit) {
    return (
      <main className="dashboard empty-state">
        <div>
          <p className="eyebrow">Ready</p>
          <h2>{loading ? "Running document audit" : "Select a sample or paste a document"}</h2>
          <p>
            The audit will extract claims, retrieve nearby evidence, classify support level, and produce a review-ready
            report.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Audit dashboard</p>
          <h2>{audit.document_title}</h2>
        </div>
        <ReportExport audit={audit} />
      </div>

      <SummaryCards summary={audit.summary} />

      <section className="executive-band">
        <div>
          <p className="eyebrow">Executive summary</p>
          <p>{audit.summary.executive_summary}</p>
        </div>
        <div>
          <p className="eyebrow">Review checklist</p>
          <ul>
            {audit.summary.review_checklist.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>

      <div className="review-grid">
        <ClaimTable
          claims={filteredClaims}
          activeClaimId={selectedClaim?.id ?? ""}
          filter={filter}
          onFilterChange={onFilterChange}
          onClaimSelect={onClaimSelect}
        />
        <EvidencePanel claim={selectedClaim} />
      </div>
    </main>
  );
}

export default AuditDashboard;
