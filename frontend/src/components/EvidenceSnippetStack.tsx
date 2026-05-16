import { FileSearch } from "lucide-react";
import type { EvidenceSnippet } from "../types";

interface EvidenceSnippetStackProps {
  evidence: EvidenceSnippet[];
}

function EvidenceSnippetStack({ evidence }: EvidenceSnippetStackProps) {
  return (
    <section className="glass-panel evidence-stack">
      <div className="panel-title compact">
        <FileSearch size={18} />
        <div>
          <p className="eyebrow">Retrieved evidence</p>
          <h2>Grounding snippets</h2>
        </div>
      </div>
      {evidence.map((item) => (
        <article className="evidence-card" key={item.chunk_id}>
          <div>
            <strong>{item.chunk_id}</strong>
            <span>{item.source}</span>
            <em>{item.score.toFixed(2)}</em>
          </div>
          <p>{item.text}</p>
        </article>
      ))}
      {evidence.length === 0 && <div className="empty-panel">No supporting passage retrieved.</div>}
    </section>
  );
}

export default EvidenceSnippetStack;
