import { Link, useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { useAudit } from "../context/AuditContext";

function RouteBreadcrumbs() {
  const { selectedClaim } = useAudit();
  const { pathname } = useLocation();
  const current = pathname.startsWith("/findings")
    ? selectedClaim?.id ?? "Finding"
    : pathname.includes("overview")
      ? "Threat overview"
      : "Ingestion";

  return (
    <div className="breadcrumbs" aria-label="Breadcrumb">
      <Link to="/scan">Console</Link>
      <ChevronRight size={14} />
      <span>{current}</span>
    </div>
  );
}

export default RouteBreadcrumbs;
