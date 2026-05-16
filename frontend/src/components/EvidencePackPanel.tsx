import { DatabaseZap } from "lucide-react";
import { useAudit } from "../context/AuditContext";

function EvidencePackPanel() {
  const { evidenceText, setEvidenceText } = useAudit();

  async function handleEvidenceFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setEvidenceText(await file.text());
  }

  return (
    <section className="glass-panel">
      <div className="panel-title">
        <DatabaseZap size={18} />
        <div>
          <p className="eyebrow">Evidence pack</p>
          <h2>Optional grounding material</h2>
        </div>
      </div>
      <label className="compact-upload">
        <input
          accept=".txt,.md,.markdown,.csv"
          type="file"
          onChange={(event) => void handleEvidenceFile(event.target.files?.[0])}
        />
        <span>Upload evidence text</span>
      </label>
      <textarea
        aria-label="Evidence pack text"
        className="terminal-textarea evidence-input"
        placeholder="Paste policy excerpts, source notes, benchmark text, or supporting passages."
        value={evidenceText}
        onChange={(event) => setEvidenceText(event.target.value)}
        spellCheck={false}
      />
    </section>
  );
}

export default EvidencePackPanel;
