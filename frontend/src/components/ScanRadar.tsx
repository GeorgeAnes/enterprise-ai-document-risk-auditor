import { Radar } from "lucide-react";

interface ScanRadarProps {
  active: boolean;
}

function ScanRadar({ active }: ScanRadarProps) {
  return (
    <section className={`radar-panel ${active ? "active" : ""}`} aria-label="Scan status visualization">
      <div className="radar-disc">
        <div className="radar-sweep" />
        <div className="radar-ring one" />
        <div className="radar-ring two" />
        <div className="radar-core">
          <Radar size={30} />
        </div>
      </div>
      <div>
        <p className="eyebrow">Scan engine</p>
        <h2>{active ? "Evidence retrieval in progress" : "Ready to initiate audit"}</h2>
        <p>
          The deterministic pipeline extracts factual-looking claims, retrieves nearby evidence, and assigns transparent
          risk labels.
        </p>
      </div>
    </section>
  );
}

export default ScanRadar;
