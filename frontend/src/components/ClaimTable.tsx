import type { ClaimAudit, LabelFilter, SupportLabel } from "../types";

const FILTERS: LabelFilter[] = [
  "All",
  "Supported",
  "Weakly supported",
  "Unsupported",
  "Vague / non-verifiable",
  "Needs human review"
];

interface ClaimTableProps {
  claims: ClaimAudit[];
  activeClaimId: string;
  filter: LabelFilter;
  onFilterChange: (filter: LabelFilter) => void;
  onClaimSelect: (claimId: string) => void;
}

function ClaimTable({ claims, activeClaimId, filter, onFilterChange, onClaimSelect }: ClaimTableProps) {
  return (
    <section className="claims-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Claim review</p>
          <h3>Extracted claims</h3>
        </div>
        <select value={filter} onChange={(event) => onFilterChange(event.target.value as LabelFilter)}>
          {FILTERS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="claim-list">
        {claims.map((claim) => (
          <button
            className={`claim-row ${activeClaimId === claim.id ? "active" : ""}`}
            key={claim.id}
            onClick={() => onClaimSelect(claim.id)}
            type="button"
          >
            <span className={`risk-badge ${badgeClass(claim.label)}`}>{claim.label}</span>
            <span className="claim-text">{claim.text}</span>
            <span className="risk-score">{claim.risk_score}</span>
          </button>
        ))}
        {claims.length === 0 && <div className="muted-empty">No claims match this filter.</div>}
      </div>
    </section>
  );
}

function badgeClass(label: SupportLabel): string {
  return label.toLowerCase().replace(/\s+/g, "-").replace(/\//g, "").replace(/--/g, "-");
}

export default ClaimTable;
