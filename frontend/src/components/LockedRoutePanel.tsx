import { Link } from "react-router-dom";
import { FileScan, LockKeyhole } from "lucide-react";

interface LockedRoutePanelProps {
  viewName: string;
}

function LockedRoutePanel({ viewName }: LockedRoutePanelProps) {
  return (
    <section className="locked-panel glass-panel" aria-live="polite">
      <LockKeyhole size={28} />
      <p className="eyebrow">{viewName} locked</p>
      <h2>Run a scan first to unlock overview and deep dive.</h2>
      <p>
        These views depend on an audit result. Start on the ingestion screen, load a sample or paste text, then run the
        deterministic scan.
      </p>
      <Link className="next-action" to="/scan">
        <FileScan size={17} />
        <span>Go to scan screen</span>
      </Link>
    </section>
  );
}

export default LockedRoutePanel;
