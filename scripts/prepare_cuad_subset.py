from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.audit_pipeline import run_audit_text


HIGH_RISK_LABELS = {"Unsupported", "Vague / non-verifiable", "Needs human review"}


def prepare_cuad_subset(
    input_path: str | Path,
    output_path: str | Path,
    summary_output_path: str | Path,
    max_docs: int = 3,
) -> dict[str, Any]:
    records = load_contract_records(Path(input_path), max_docs=max_docs)
    output_path = Path(output_path)
    summary_output_path = Path(summary_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    audits = []
    for record in records:
        audit = run_audit_text(record["text"], title=record["title"])
        high_risk = [
            {
                "id": claim.id,
                "label": claim.label,
                "risk_score": claim.risk_score,
                "claim": claim.text,
                "explanation": claim.explanation,
                "evidence": [
                    {
                        "chunk_id": evidence.chunk_id,
                        "score": evidence.score,
                        "text": evidence.text,
                    }
                    for evidence in claim.evidence[:2]
                ],
            }
            for claim in audit.claims
            if claim.label in HIGH_RISK_LABELS
        ]
        audits.append(
            {
                "id": record["id"],
                "title": record["title"],
                "total_claims": audit.summary.total_claims,
                "overall_risk_score": audit.summary.overall_risk_score,
                "llm_review_status": audit.llm_review.status if audit.llm_review else "disabled",
                "llm_reviewer_notes": audit.llm_review.reviewer_notes if audit.llm_review else [],
                "llm_summary": audit.llm_review.summary if audit.llm_review else None,
                "high_risk_findings": high_risk[:10],
            }
        )

    summary = {
        "output_path": str(output_path),
        "summary_output_path": str(summary_output_path),
        "contracts_written": len(records),
        "audits": audits,
        "note": "CUAD is used here as a contract-review stress test, not a hallucination benchmark.",
    }
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def load_contract_records(input_path: Path, max_docs: int) -> list[dict[str, str]]:
    if input_path.is_dir():
        records = []
        for path in sorted(input_path.glob("*")):
            if path.suffix.lower() in {".txt", ".md"}:
                records.append(_contract_record(path.stem, path.name, path.read_text(encoding="utf-8")))
            elif path.suffix.lower() == ".json":
                records.extend(_records_from_json(path))
            if len(records) >= max_docs:
                return records[:max_docs]
        return records

    if input_path.suffix.lower() in {".txt", ".md"}:
        return [_contract_record(input_path.stem, input_path.name, input_path.read_text(encoding="utf-8"))]
    if input_path.suffix.lower() == ".json":
        return _records_from_json(input_path)[:max_docs]

    raise ValueError("CUAD input must be a directory, .txt/.md contract file, or JSON file.")


def _records_from_json(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [_record_from_mapping(item, index) for index, item in enumerate(payload, start=1)]
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        records = []
        for index, item in enumerate(payload["data"], start=1):
            title = str(item.get("title") or item.get("contract_name") or f"contract-{index}")
            text = _text_from_cuad_item(item)
            records.append(_contract_record(f"contract-{index}", title, text))
        return records
    if isinstance(payload, dict):
        return [_record_from_mapping(payload, 1)]
    raise ValueError("Unsupported CUAD JSON structure.")


def _record_from_mapping(item: dict[str, Any], index: int) -> dict[str, str]:
    title = str(item.get("title") or item.get("contract_name") or item.get("file_name") or f"contract-{index}")
    text = _text_from_cuad_item(item)
    return _contract_record(str(item.get("id") or f"contract-{index}"), title, text)


def _text_from_cuad_item(item: dict[str, Any]) -> str:
    for field in ("text", "contract_text", "context", "document"):
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    paragraphs = item.get("paragraphs")
    if isinstance(paragraphs, list):
        contexts = [str(paragraph.get("context", "")).strip() for paragraph in paragraphs if isinstance(paragraph, dict)]
        text = "\n\n".join(context for context in contexts if context)
        if text:
            return text

    raise ValueError("Could not find contract text in CUAD JSON entry.")


def _contract_record(record_id: str, title: str, text: str) -> dict[str, str]:
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(cleaned) < 80:
        raise ValueError(f"Contract '{title}' is too short for an audit.")
    return {"id": record_id, "title": title, "text": cleaned}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and audit a small CUAD contract-review subset.")
    parser.add_argument("--input", required=True, help="Path to CUAD .txt/.md/.json file or directory.")
    parser.add_argument("--output", default="data/eval/cuad_subset.jsonl", help="Output contract subset JSONL.")
    parser.add_argument("--summary-output", default="data/eval/cuad_audit_summary.json", help="Audit summary JSON path.")
    parser.add_argument("--max-docs", type=int, default=3, help="Maximum contracts to include.")
    args = parser.parse_args()
    prepare_cuad_subset(args.input, args.output, args.summary_output, args.max_docs)


if __name__ == "__main__":
    main()
