import { ServerCrash, ShieldCheck, Wifi } from "lucide-react";
import { apiBaseUrl } from "../api";
import { useAudit } from "../context/AuditContext";

function BackendStatusPanel() {
  const { backendStatus, backendMessage, usingFallbackSample } = useAudit();
  const Icon = backendStatus === "online" ? Wifi : backendStatus === "checking" ? ShieldCheck : ServerCrash;

  return (
    <section className={`backend-status-card ${backendStatus}`} aria-live="polite">
      <div className="section-title">
        <Icon size={17} />
        <span>{backendStatus === "online" ? "Backend online" : backendStatus === "checking" ? "Checking backend" : "Backend offline"}</span>
      </div>
      <p>{backendMessage}</p>
      <small>API target: {apiBaseUrl()}</small>
      {usingFallbackSample && <small>Fallback sample loaded for frontend inspection.</small>}
    </section>
  );
}

export default BackendStatusPanel;
