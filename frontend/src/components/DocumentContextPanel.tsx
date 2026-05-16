import type { ClaimAudit } from "../types";
import { buildDocumentContext } from "../utils/risk";

interface DocumentContextPanelProps {
  documentText: string;
  claim: ClaimAudit | null;
}

function DocumentContextPanel({ documentText, claim }: DocumentContextPanelProps) {
  return (
    <section className="glass-panel document-context">
      <p className="eyebrow">Document context</p>
      <pre>{buildDocumentContext(documentText, claim)}</pre>
    </section>
  );
}

export default DocumentContextPanel;
