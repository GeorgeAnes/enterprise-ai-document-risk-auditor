from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def render_reports(
    fever_summary_path: str | Path = "data/eval/fever_eval_summary.json",
    cuad_summary_path: str | Path = "data/eval/cuad_audit_summary.json",
    output_dir: str | Path = "docs/evaluation_results",
) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    fever_path = Path(fever_summary_path)
    if fever_path.exists():
        fever = json.loads(fever_path.read_text(encoding="utf-8"))
        target = output_dir / "fever_gemini_risk_eval.md"
        target.write_text(render_fever_markdown(fever), encoding="utf-8")
        written["fever"] = str(target)

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


def render_fever_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# FEVER Gemini Risk Evaluation",
        "",
        "Small FEVER subset run through the deterministic auditor with optional Gemini reviewer notes.",
        "",
        f"- Examples evaluated: {summary.get('examples_evaluated', 0)}",
        f"- Supported lower than refuted: {summary.get('supported_lower_than_refuted')}",
        f"- Supported lower than not-enough-info: {summary.get('supported_lower_than_not_enough_info')}",
        f"- LLM review status counts: `{summary.get('llm_review_status_counts', {})}`",
        "",
        "## Average Risk By FEVER Label",
        "",
        "| Label | Average risk |",
        "|---|---:|",
    ]
    for label, value in summary.get("average_risk_by_label", {}).items():
        lines.append(f"| {label} | {value} |")

    lines.extend(["", "## Example Findings", "", "| FEVER label | Risk | Auditor label | Claim | Gemini note |", "|---|---:|---|---|---|"])
    for result in summary.get("results", [])[:12]:
        note = first_note(result)
        lines.append(
            f"| {result.get('label')} | {result.get('risk_score')} | {result.get('auditor_label')} | "
            f"{safe_cell(result.get('claim', ''))} | {safe_cell(note)} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- FEVER is used here to check relative risk behavior across support labels.",
            "- This is not a full FEVER leaderboard benchmark.",
            "- Only a small subset should be committed as rendered summary, never the raw dataset.",
        ]
    )
    return "\n".join(lines) + "\n"


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
    if "fever" in written:
        lines.append("- [FEVER Gemini Risk Evaluation](fever_gemini_risk_eval.md)")
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


def first_note(result: dict[str, Any]) -> str:
    notes = result.get("llm_reviewer_notes") or []
    for note in notes:
        text = str(note).replace("**", "")
        if not text.lower().startswith("here are"):
            return text
    return str(result.get("llm_summary") or result.get("llm_review_status") or "")


def safe_cell(value: str, max_length: int = 220) -> str:
    cleaned = " ".join(str(value).split())
    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3].rstrip() + "..."
    return cleaned.replace("|", "\\|")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render FEVER/CUAD evaluation JSON into GitHub Markdown reports.")
    parser.add_argument("--fever-summary", default="data/eval/fever_eval_summary.json")
    parser.add_argument("--cuad-summary", default="data/eval/cuad_audit_summary.json")
    parser.add_argument("--output-dir", default="docs/evaluation_results")
    args = parser.parse_args()
    render_reports(args.fever_summary, args.cuad_summary, args.output_dir)


if __name__ == "__main__":
    main()
