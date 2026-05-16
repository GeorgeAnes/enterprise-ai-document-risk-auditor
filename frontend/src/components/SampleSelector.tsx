import { FileText } from "lucide-react";
import { useAudit } from "../context/AuditContext";

function SampleSelector() {
  const { samples, activeSampleId, loadSample } = useAudit();

  return (
    <section className="glass-panel">
      <div className="panel-title">
        <FileText size={18} />
        <div>
          <p className="eyebrow">Sample corpus</p>
          <h2>Load a controlled document</h2>
        </div>
      </div>
      <div className="sample-grid">
        {samples.map((sample) => (
          <button
            className={`sample-tile ${activeSampleId === sample.id ? "active" : ""}`}
            key={sample.id}
            onClick={() => void loadSample(sample.id)}
            type="button"
          >
            <span>{sample.title}</span>
            <small>{sample.description}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

export default SampleSelector;
