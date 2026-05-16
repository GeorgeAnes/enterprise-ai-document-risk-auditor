import type { CSSProperties } from "react";

interface RiskScoreRingProps {
  score: number;
  band: string;
}

function RiskScoreRing({ score, band }: RiskScoreRingProps) {
  return (
    <div className="risk-ring-wrap" aria-label={`Overall risk score ${score} out of 100, ${band}`}>
      <div className="risk-ring" style={{ "--score": `${score}%` } as CSSProperties}>
        <div>
          <span>{score}</span>
          <small>/100</small>
        </div>
      </div>
      <div>
        <p className="eyebrow">Risk posture</p>
        <h2>{band}</h2>
        <p className="muted">Transparent deterministic score derived from claim support, vagueness, citation signals, and evidence retrieval.</p>
      </div>
    </div>
  );
}

export default RiskScoreRing;
