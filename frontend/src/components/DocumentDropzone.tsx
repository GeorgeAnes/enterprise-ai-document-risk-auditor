import { UploadCloud } from "lucide-react";
import { useAudit } from "../context/AuditContext";

function DocumentDropzone() {
  const { documentText, documentTitle, file, setDocumentText, setInputFile } = useAudit();

  return (
    <section className="glass-panel document-panel">
      <div className="panel-title">
        <UploadCloud size={18} />
        <div>
          <p className="eyebrow">Primary document</p>
          <h2>{documentTitle || "Document payload"}</h2>
        </div>
      </div>
      <label className="dropzone">
        <input
          accept=".txt,.md,.markdown,.pdf"
          type="file"
          onChange={(event) => setInputFile(event.target.files?.[0] ?? null)}
        />
        <span>{file ? file.name : "Upload .md, .txt, or .pdf"}</span>
        <small>Local-only upload. Files are sent to the FastAPI backend for deterministic parsing.</small>
      </label>
      <textarea
        aria-label="Document text"
        className="terminal-textarea document-input"
        value={documentText}
        onChange={(event) => setDocumentText(event.target.value)}
        spellCheck={false}
      />
    </section>
  );
}

export default DocumentDropzone;
