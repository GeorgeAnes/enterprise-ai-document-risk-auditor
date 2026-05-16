# FEVER Gemini Risk-Score Sanity Check

Small FEVER subset run through the deterministic auditor with optional Gemini reviewer notes. This is a lightweight risk-score separation sanity check, not a full FEVER benchmark.

- Examples evaluated: 3
- Supported lower than refuted: False
- Supported lower than not-enough-info: True
- LLM review status counts: `{'completed': 3}`

## Average Risk By FEVER Label

| Label | Average risk |
|---|---:|
| NOT ENOUGH INFO | 86 |
| REFUTES | 48 |
| SUPPORTS | 48 |

## Example Findings

| FEVER label | Risk | Auditor label | Claim | Gemini note |
|---|---:|---|---|---|
| SUPPORTS | 48 | Weakly supported | Fox 2000 Pictures released the film Soul Food. | C003: The claim "Fox 2000 Pictures released the film Soul Food" is specific, but the audit indicates a lack of close supporting passage. This claim warrants further investigation to locate direct evidence. |
| REFUTES | 48 | Weakly supported | Telemundo is a English-language television network. | Claim C003: The claim "Telemundo is an English-language television network" is unsupported by the provided evidence. The system flagged this as high risk due to a lack of supporting text. |
| NOT ENOUGH INFO | 86 | Unsupported | Colin Kaepernick became a starting quarterback during the 49ers 63rd season in the National Football League. | C001 & C003: The deterministic audit indicates a lack of specific, supporting passages in the provided evidence for these claims. Human review is prioritized to bridge this evidence gap. |

## Notes

- FEVER is used here to check relative risk behavior across support labels.
- This is not a full FEVER benchmark or leaderboard run.
- Only a small subset should be committed as rendered summary, never the raw dataset.
