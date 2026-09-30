from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def render_reports(
    cuad_summary_path: str | Path = "data/eval/cuad_audit_summary.json",
    output_dir: str | Path = "docs/evaluation_results",
) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    cuad_path = Path(cuad_summary_path)
    if cuad_path.exists():
        cuad = json.loads(cuad_path.read_text(encoding="utf-8"))
        target = output_dir / "cuad_gemini_contract_review.md"
        target.write_text(render_cuad_markdown(cuad), encoding="utf-8")
        written["cuad"] = str(target)

    index = output_dir / "README.md"
    index.write_text(render_index(written), encoding="utf-8")
    written["index"] = str(index)
    print(json.dumps(written, indent=2))
    return written


def render_cuad_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# CUAD Gemini Contract Review Stress Test",
        "",
        "Small CUAD contract subset run through the deterministic auditor with optional Gemini reviewer notes.",
        "",
        f"- Contracts audited: {summary.get('contracts_written', 0)}",
        f"- Note: {summary.get('note', 'CUAD is used as a contract-review stress test.')}",
        "",
    ]

    for audit in summary.get("audits", []):
        lines.extend(
            [
                f"## {audit.get('title')}",
                "",
                f"- Total extracted claims: {audit.get('total_claims')}",
                f"- Overall risk score: {audit.get('overall_risk_score')}/100",
                f"- LLM review status: `{audit.get('llm_review_status', 'disabled')}`",
            ]
        )
        if audit.get("llm_reviewer_notes"):
            lines.append("- Gemini reviewer notes:")
            lines.extend(f"  - {note}" for note in audit["llm_reviewer_notes"][:5])
        lines.extend(["", "| Label | Risk | Clause / claim | Top evidence |", "|---|---:|---|---|"])
        for finding in audit.get("high_risk_findings", [])[:8]:
            evidence = finding.get("evidence", [{}])[0].get("text", "") if finding.get("evidence") else ""
            lines.append(
                f"| {finding.get('label')} | {finding.get('risk_score')} | "
                f"{safe_cell(finding.get('claim', ''))} | {safe_cell(evidence)} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- CUAD is used as a contract-review stress test, not as a hallucination benchmark.",
            "- Rendered snippets are truncated for GitHub readability.",
            "- Raw CUAD files remain ignored under `data/raw/`.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_index(written: dict[str, str]) -> str:
    lines = ["# Evaluation Result Reports", ""]
    if "cuad" in written:
        lines.append("- [CUAD Gemini Contract Review Stress Test](cuad_gemini_contract_review.md)")
    lines.extend(
        [
            "",
            "These reports are small rendered summaries generated from local evaluation runs.",
            "Raw datasets and generated JSON outputs are intentionally not committed.",
        ]
    )
    return "\n".join(lines) + "\n"


def safe_cell(value: str, max_length: int = 220) -> str:
    cleaned = " ".join(str(value).split())
    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3].rstrip() + "..."
    return cleaned.replace("|", "\\|")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render CUAD evaluation JSON into a GitHub Markdown report.")
    parser.add_argument("--cuad-summary", default="data/eval/cuad_audit_summary.json")
    parser.add_argument("--output-dir", default="docs/evaluation_results")
    args = parser.parse_args()
    render_reports(args.cuad_summary, args.output_dir)


if __name__ == "__main__":
    main()
