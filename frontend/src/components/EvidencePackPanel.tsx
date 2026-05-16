import { DatabaseZap } from "lucide-react";
import { useState } from "react";
import { useAudit } from "../context/AuditContext";

const SUPPORTED_EVIDENCE_EXTENSIONS = [".txt", ".md", ".markdown", ".csv", ".json", ".jsonl"];

function EvidencePackPanel() {
  const { evidenceText, setEvidenceText } = useAudit();
  const [dragActive, setDragActive] = useState(false);
  const [filename, setFilename] = useState("");
  const [dropError, setDropError] = useState("");

  async function handleEvidenceFile(file: File | undefined) {
    if (!file) {
      return;
    }

    if (!isSupportedEvidence(file.name)) {
      setDropError("Unsupported evidence file. Drop .txt, .md, .csv, .json, or .jsonl text evidence.");
      return;
    }

    setDropError("");
    setFilename(file.name);
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
      <label
        className={`compact-upload ${dragActive ? "drag-active" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragActive(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          void handleEvidenceFile(event.dataTransfer.files[0]);
        }}
      >
        <input
          accept=".txt,.md,.markdown,.csv,.json,.jsonl"
          type="file"
          onChange={(event) => void handleEvidenceFile(event.target.files?.[0])}
        />
        <span>{filename ? `Evidence loaded: ${filename}` : "Drop or upload evidence text"}</span>
      </label>
      {dropError && <p className="drop-error">{dropError}</p>}
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

function isSupportedEvidence(filename: string) {
  const lower = filename.toLowerCase();
  return SUPPORTED_EVIDENCE_EXTENSIONS.some((extension) => lower.endsWith(extension));
}

export default EvidencePackPanel;
