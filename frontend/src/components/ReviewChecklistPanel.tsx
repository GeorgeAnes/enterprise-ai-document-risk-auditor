import { CheckSquare } from "lucide-react";

interface ReviewChecklistPanelProps {
  items: string[];
}

function ReviewChecklistPanel({ items }: ReviewChecklistPanelProps) {
  return (
    <section className="glass-panel checklist-panel">
      <div className="panel-title compact">
        <CheckSquare size={18} />
        <div>
          <p className="eyebrow">Human review</p>
          <h2>Checklist</h2>
        </div>
      </div>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export default ReviewChecklistPanel;
