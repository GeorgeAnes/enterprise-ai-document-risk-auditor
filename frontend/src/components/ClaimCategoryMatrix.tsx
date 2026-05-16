import type { CategoryRow } from "../context/AuditContext";

interface ClaimCategoryMatrixProps {
  rows: CategoryRow[];
  total: number;
}

function ClaimCategoryMatrix({ rows, total }: ClaimCategoryMatrixProps) {
  return (
    <section className="glass-panel">
      <div className="panel-title compact">
        <div>
          <p className="eyebrow">Claim categories</p>
          <h2>Support distribution</h2>
        </div>
        <strong className="total-chip">{total} claims</strong>
      </div>
      <div className="category-matrix">
        {rows.map((row) => (
          <article className={`category-cell ${row.tone}`} key={row.label}>
            <span>{row.label}</span>
            <strong>{row.count}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}

export default ClaimCategoryMatrix;
