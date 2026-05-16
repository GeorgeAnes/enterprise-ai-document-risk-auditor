from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.audit_pipeline import run_audit_text
from backend.app.schemas import ClaimAudit


def evaluate_fever_subset(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    examples = _read_jsonl(input_path)
    results: list[dict[str, Any]] = []

    for example in examples:
        audit = run_audit_text(
            example["document"],
            evidence_text=example.get("evidence_pack", ""),
            title=f"FEVER {example['id']}",
        )
        claim = _best_matching_claim(example["claim"], audit.claims)
        results.append(
            {
                "id": example["id"],
                "label": example["label"],
                "claim": example["claim"],
                "auditor_label": claim.label if claim else "No claim extracted",
                "risk_score": claim.risk_score if claim else 100,
                "confidence": claim.confidence if claim else 0.0,
                "top_evidence_score": claim.evidence[0].score if claim and claim.evidence else 0.0,
                "llm_review_status": audit.llm_review.status if audit.llm_review else "disabled",
                "llm_reviewer_notes": audit.llm_review.reviewer_notes if audit.llm_review else [],
                "llm_summary": audit.llm_review.summary if audit.llm_review else None,
            }
        )

    risk_by_label: dict[str, list[int]] = defaultdict(list)
    for result in results:
        risk_by_label[result["label"]].append(int(result["risk_score"]))

    average_risk_by_label = {
        label: round(mean(scores), 2)
        for label, scores in sorted(risk_by_label.items())
        if scores
    }
    supports_risk = average_risk_by_label.get("SUPPORTS")
    refutes_risk = average_risk_by_label.get("REFUTES")
    nei_risk = average_risk_by_label.get("NOT ENOUGH INFO")

    summary = {
        "input_path": str(input_path),
        "examples_evaluated": len(results),
        "average_risk_by_label": average_risk_by_label,
        "supported_lower_than_refuted": supports_risk is not None and refutes_risk is not None and supports_risk < refutes_risk,
        "supported_lower_than_not_enough_info": supports_risk is not None and nei_risk is not None and supports_risk < nei_risk,
        "llm_review_status_counts": dict(Counter(result["llm_review_status"] for result in results)),
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _best_matching_claim(target: str, claims: list[ClaimAudit]) -> ClaimAudit | None:
    if not claims:
        return None
    target_tokens = _tokens(target)
    return max(claims, key=lambda claim: len(target_tokens & _tokens(claim.text)))


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9-]+", text.lower()) if len(token) > 2}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate risk-score separation on a prepared FEVER subset.")
    parser.add_argument("--input", default="data/eval/fever_subset.jsonl", help="Prepared FEVER subset JSONL.")
    parser.add_argument("--output", default="data/eval/fever_eval_summary.json", help="Evaluation summary JSON path.")
    args = parser.parse_args()
    evaluate_fever_subset(args.input, args.output)


if __name__ == "__main__":
    main()
