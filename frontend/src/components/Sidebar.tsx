import { FileText, Play, Upload } from "lucide-react";
import type { SampleInfo } from "../types";

interface SidebarProps {
  samples: SampleInfo[];
  activeSampleId: string;
  documentText: string;
  evidenceText: string;
  file: File | null;
  loading: boolean;
  error: string | null;
  onSelectSample: (sampleId: string) => void;
  onDocumentTextChange: (value: string) => void;
  onEvidenceTextChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  onAudit: () => void;
}

function Sidebar({
  samples,
  activeSampleId,
  documentText,
  evidenceText,
  file,
  loading,
  error,
  onSelectSample,
  onDocumentTextChange,
  onEvidenceTextChange,
  onFileChange,
  onAudit
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <section className="panel-block">
        <div className="section-title">
          <FileText size={17} />
          <span>Sample documents</span>
        </div>
        <div className="sample-list">
          {samples.map((sample) => (
            <button
              className={`sample-button ${activeSampleId === sample.id ? "active" : ""}`}
              key={sample.id}
              onClick={() => onSelectSample(sample.id)}
              type="button"
            >
              <span>{sample.title}</span>
              <small>{sample.description}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="panel-block">
        <div className="section-title">
          <Upload size={17} />
          <span>Upload or paste</span>
        </div>
        <label className="file-drop">
          <input
            accept=".txt,.md,.markdown,.pdf"
            type="file"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          />
          <span>{file ? file.name : "Choose .md, .txt, or .pdf"}</span>
        </label>
        <textarea
          className="document-input"
          value={documentText}
          onChange={(event) => {
            onFileChange(null);
            onDocumentTextChange(event.target.value);
          }}
          spellCheck={false}
        />
      </section>

      <section className="panel-block">
        <div className="section-title">
          <FileText size={17} />
          <span>Evidence pack</span>
        </div>
        <textarea
          className="evidence-input"
          placeholder="Optional supporting evidence, source notes, or excerpts."
          value={evidenceText}
          onChange={(event) => onEvidenceTextChange(event.target.value)}
          spellCheck={false}
        />
      </section>

      {error && <div className="error-banner">{error}</div>}

      <button className="primary-action" type="button" onClick={onAudit} disabled={loading || (!documentText && !file)}>
        <Play size={17} />
        <span>{loading ? "Auditing..." : "Run audit"}</span>
      </button>
    </aside>
  );
}

export default Sidebar;
