import { UploadCloud } from "lucide-react";
import { useState } from "react";
import { useAudit } from "../context/AuditContext";

const SUPPORTED_DOCUMENT_EXTENSIONS = [".txt", ".md", ".markdown", ".pdf"];

function DocumentDropzone() {
  const { documentText, documentTitle, file, usingFallbackSample, setDocumentText, setInputFile } = useAudit();
  const [dragActive, setDragActive] = useState(false);
  const [dropError, setDropError] = useState("");

  function handleFile(nextFile: File | undefined) {
    if (!nextFile) {
      return;
    }

    if (!isSupportedDocument(nextFile.name)) {
      setDropError("Unsupported file type. Drop a .txt, .md, .markdown, or .pdf document.");
      return;
    }

    setDropError("");
    setInputFile(nextFile);
  }

  return (
    <section className="glass-panel document-panel">
      <div className="panel-title">
        <UploadCloud size={18} />
        <div>
          <p className="eyebrow">Primary document</p>
          <h2>{documentTitle || "Document payload"}</h2>
        </div>
      </div>
      {usingFallbackSample && <p className="panel-note">Synthetic fallback content is loaded for local UI testing.</p>}
      <label
        className={`dropzone ${dragActive ? "drag-active" : ""}`}
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
          handleFile(event.dataTransfer.files[0]);
        }}
      >
        <input
          accept=".txt,.md,.markdown,.pdf"
          type="file"
          onChange={(event) => handleFile(event.target.files?.[0])}
        />
        <span>{file ? file.name : "Drop or upload .md, .txt, or .pdf"}</span>
        <small>Drop one document here. Files are sent to the FastAPI backend for deterministic parsing.</small>
      </label>
      {dropError && <p className="drop-error">{dropError}</p>}
      {file && <p className="panel-note">Ready to audit uploaded file: {file.name}</p>}
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

function isSupportedDocument(filename: string) {
  const lower = filename.toLowerCase();
  return SUPPORTED_DOCUMENT_EXTENSIONS.some((extension) => lower.endsWith(extension));
}

export default DocumentDropzone;
