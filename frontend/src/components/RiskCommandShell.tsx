import type { ReactNode } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Activity, DatabaseZap, ShieldAlert } from "lucide-react";
import TopNav from "./TopNav";
import RouteBreadcrumbs from "./RouteBreadcrumbs";
import { useAudit } from "../context/AuditContext";

interface RiskCommandShellProps {
  children?: ReactNode;
}

function RiskCommandShell({ children }: RiskCommandShellProps) {
  const { audit, riskBand, loading } = useAudit();
  const location = useLocation();
  const isScan = location.pathname === "/scan";

  return (
    <div className="command-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <ShieldAlert size={22} />
          </div>
          <div>
            <p className="eyebrow">AI governance command center</p>
            <h1>Enterprise AI Document Risk Auditor</h1>
          </div>
        </div>
        <div className="system-status" aria-live="polite">
          <span className={loading ? "signal-dot active" : "signal-dot"} />
          <span>{loading ? "Scanning corpus" : audit ? `${riskBand} risk posture` : "Ready for ingestion"}</span>
        </div>
      </header>

      <div className="shell-grid">
        <aside className="control-rail" aria-label="Primary navigation">
          <TopNav />
          <div className="rail-card">
            <Activity size={18} />
            <span>Deterministic baseline</span>
            <strong>No-LLM audit core</strong>
          </div>
          <div className="rail-card">
            <DatabaseZap size={18} />
            <span>Backend contract</span>
            <strong>FastAPI /audit</strong>
          </div>
        </aside>

        <main className={`screen-stage ${isScan ? "scan-stage" : ""}`}>
          <RouteBreadcrumbs />
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}

export default RiskCommandShell;
