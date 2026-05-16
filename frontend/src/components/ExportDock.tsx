import { Download } from "lucide-react";
import type { AuditResponse } from "../types";

interface ExportDockProps {
  audit: AuditResponse;
}

function ExportDock({ audit }: ExportDockProps) {
  return (
    <section className="export-dock" aria-label="Export audit report">
      <button type="button" onClick={() => download("audit-report.md", audit.markdown_report, "text/markdown")}>
        <Download size={16} />
        <span>Markdown report</span>
      </button>
      <button type="button" onClick={() => download("audit-report.json", JSON.stringify(audit, null, 2), "application/json")}>
        <Download size={16} />
        <span>JSON payload</span>
      </button>
    </section>
  );
}

function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default ExportDock;
