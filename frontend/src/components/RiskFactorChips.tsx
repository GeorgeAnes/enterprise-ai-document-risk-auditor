interface RiskFactorChipsProps {
  factors: string[];
}

function RiskFactorChips({ factors }: RiskFactorChipsProps) {
  return (
    <div className="factor-chips" aria-label="Risk factors">
      {factors.map((factor) => (
        <span key={factor}>{factor}</span>
      ))}
    </div>
  );
}

export default RiskFactorChips;
