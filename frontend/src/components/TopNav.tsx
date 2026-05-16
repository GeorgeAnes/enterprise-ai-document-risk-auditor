import { NavLink } from "react-router-dom";
import { FileScan, LayoutDashboard, LockKeyhole, SearchCode } from "lucide-react";
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
      <NavLink
        to="/overview"
        className={!audit ? "locked-link" : undefined}
        title={!audit ? "Run a scan first to unlock overview and deep dive." : undefined}
      >
        {!audit ? <LockKeyhole size={17} /> : <LayoutDashboard size={17} />}
        <span>Overview</span>
        {!audit && <small>Run scan first</small>}
      </NavLink>
      <NavLink
        to={findingPath}
        className={!audit ? "locked-link" : undefined}
        title={!audit ? "Run a scan first to unlock overview and deep dive." : undefined}
      >
        {!audit ? <LockKeyhole size={17} /> : <SearchCode size={17} />}
        <span>Deep dive</span>
        {!audit && <small>Locked</small>}
      </NavLink>
    </nav>
  );
}

export default TopNav;
