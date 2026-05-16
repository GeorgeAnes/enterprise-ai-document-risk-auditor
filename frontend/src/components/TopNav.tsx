import { NavLink } from "react-router-dom";
import { FileScan, LayoutDashboard, SearchCode } from "lucide-react";
import { useAudit } from "../context/AuditContext";

function TopNav() {
  const { audit, selectedClaim } = useAudit();
  const findingPath = selectedClaim ? `/findings/${selectedClaim.id}` : "/findings/none";

  return (
    <nav className="top-nav">
      <NavLink to="/scan">
        <FileScan size={17} />
        <span>Ingestion</span>
      </NavLink>
      <NavLink to="/overview" className={!audit ? "disabled-link" : undefined}>
        <LayoutDashboard size={17} />
        <span>Overview</span>
      </NavLink>
      <NavLink to={findingPath} className={!audit ? "disabled-link" : undefined}>
        <SearchCode size={17} />
        <span>Deep dive</span>
      </NavLink>
    </nav>
  );
}

export default TopNav;
