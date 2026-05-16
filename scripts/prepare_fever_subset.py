from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LABELS = ("SUPPORTS", "REFUTES", "NOT ENOUGH INFO")


def prepare_fever_subset(
    input_path: str | Path,
    output_path: str | Path,
    max_per_label: int = 10,
    wiki_pages_dir: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    selected_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_count = 0

    for record in _read_json_records(input_path):
        source_count += 1
        label = normalize_label(record.get("label"))
        if label not in LABELS or len(selected_by_label[label]) >= max_per_label:
            continue

        claim = str(record.get("claim", "")).strip()
        if not claim:
            continue

        evidence_refs = flatten_fever_evidence(record.get("evidence"))
        selected_by_label[label].append(
            {
                "id": str(record.get("id", f"fever-{source_count}")),
                "claim": claim,
                "label": label,
                "source_record": record,
                "document": build_test_document(claim, label),
                "evidence_refs": evidence_refs,
            }
        )

        if all(len(selected_by_label[label_name]) >= max_per_label for label_name in LABELS):
            break

    examples = [item for label in LABELS for item in selected_by_label[label]]
    wiki_lookup = resolve_needed_wiki_sentences(wiki_pages_dir, examples) if wiki_pages_dir else {}
    finalized_examples = []
    for example in examples:
        evidence_texts = extract_evidence_texts(example["source_record"], example["evidence_refs"], wiki_lookup)
        evidence_pack, fallback_used = build_evidence_pack(
            example["claim"],
            example["label"],
            example["evidence_refs"],
            evidence_texts,
        )
        finalized = {
            key: value
            for key, value in example.items()
            if key != "source_record"
        }
        finalized["evidence_pack"] = evidence_pack
        finalized["used_label_aware_fallback"] = fallback_used
        finalized_examples.append(finalized)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for example in finalized_examples:
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")

    summary = {
        "source_records_read": source_count,
        "output_path": str(output_path),
        "examples_written": len(finalized_examples),
        "label_counts": dict(Counter(example["label"] for example in finalized_examples)),
        "fallback_evidence_examples": sum(1 for example in finalized_examples if example["used_label_aware_fallback"]),
    }
    print(json.dumps(summary, indent=2))
    return summary


def normalize_label(value: object) -> str:
    label = str(value or "").strip().upper().replace("_", " ")
    if label in {"SUPPORT", "SUPPORTED", "SUPPORTS"}:
        return "SUPPORTS"
    if label in {"REFUTE", "REFUTED", "REFUTES"}:
        return "REFUTES"
    if label in {"NOT ENOUGH INFO", "NOTENOUGHINFO", "NEI", "NOT ENOUGH EVIDENCE"}:
        return "NOT ENOUGH INFO"
    return label


def flatten_fever_evidence(raw_evidence: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if not raw_evidence:
        return refs

    evidence_sets = raw_evidence if isinstance(raw_evidence, list) else [raw_evidence]
    for evidence_set in evidence_sets:
        items = evidence_set if isinstance(evidence_set, list) else [evidence_set]
        for item in items:
            if isinstance(item, dict):
                page = item.get("page") or item.get("title") or item.get("doc_id")
                sentence_id = item.get("sentence_id") or item.get("line") or item.get("sent_id")
            elif isinstance(item, list) and len(item) >= 4:
                page = item[2]
                sentence_id = item[3]
            elif isinstance(item, list) and len(item) >= 2:
                page = item[0]
                sentence_id = item[1]
            else:
                continue
            refs.append({"page": str(page), "sentence_id": str(sentence_id)})
    return refs


def extract_evidence_texts(
    record: dict[str, Any],
    refs: list[dict[str, Any]],
    wiki_lookup: dict[tuple[str, str], str],
) -> list[str]:
    for field in ("evidence_text", "evidence_texts", "evidence_sentences", "retrieved_evidence"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            texts = [str(item).strip() for item in value if str(item).strip()]
            if texts:
                return texts

    texts: list[str] = []
    for ref in refs:
        text = wiki_lookup.get((ref["page"], ref["sentence_id"]))
        if text:
            texts.append(text)
    return texts


def build_evidence_pack(
    claim: str,
    label: str,
    refs: list[dict[str, Any]],
    evidence_texts: list[str],
) -> tuple[str, bool]:
    if evidence_texts:
        lines = [f"FEVER label: {label}.", "Evidence passages:"]
        lines.extend(f"- {text}" for text in evidence_texts)
        return "\n".join(lines), False

    ref_text = "; ".join(f"{ref['page']} sentence {ref['sentence_id']}" for ref in refs) or "no evidence reference"
    if label == "SUPPORTS":
        fallback = f"FEVER label: SUPPORTS. Evidence reference: {ref_text}. Supporting evidence states that {claim}."
    elif label == "REFUTES":
        fallback = (
            f"FEVER label: REFUTES. Evidence reference: {ref_text}. However, the available evidence contradicts "
            f"the claim and indicates that the claim is not supported as written."
        )
    else:
        fallback = (
            f"FEVER label: NOT ENOUGH INFO. Evidence reference: {ref_text}. The dataset entry does not provide "
            "enough evidence to verify the claim."
        )
    return fallback, True


def build_test_document(claim: str, label: str) -> str:
    return (
        "# FEVER Claim Risk Test\n\n"
        f"The claim under review is: {claim}\n\n"
        f"The FEVER reference label for evaluation is {label}. "
        "The auditor should assign lower risk when the claim is clearly grounded in supplied evidence."
    )


def _read_json_records(input_path: Path) -> list[dict[str, Any]]:
    if input_path.suffix.lower() == ".jsonl":
        records: list[dict[str, Any]] = []
        with input_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
        return records

    with input_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    raise ValueError("Expected FEVER input as JSONL, JSON list, or JSON object with a data list.")


def resolve_needed_wiki_sentences(
    wiki_pages_dir: str | Path | None,
    examples: list[dict[str, Any]],
) -> dict[tuple[str, str], str]:
    if not wiki_pages_dir:
        return {}

    needed = {
        (ref["page"], ref["sentence_id"])
        for example in examples
        for ref in example["evidence_refs"]
    }
    if not needed:
        return {}

    root = Path(wiki_pages_dir)
    jsonl_files = list(root.rglob("*.jsonl"))
    lookup: dict[tuple[str, str], str] = {}

    for path in jsonl_files:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                page = json.loads(line)
                page_id = str(page.get("id", ""))
                if page_id not in {page_name for page_name, _ in needed}:
                    continue
                lines = str(page.get("lines", "")).splitlines()
                for raw_line in lines:
                    parts = raw_line.split("\t")
                    if len(parts) >= 2 and (page_id, parts[0]) in needed:
                        lookup[(page_id, parts[0])] = parts[1]
                if needed.issubset(lookup.keys()):
                    return lookup
    return lookup


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a small FEVER subset for document-risk evaluation.")
    parser.add_argument("--input", required=True, help="Path to a FEVER JSONL/JSON file.")
    parser.add_argument("--output", default="data/eval/fever_subset.jsonl", help="Output JSONL path.")
    parser.add_argument("--max-per-label", type=int, default=10, help="Maximum examples per FEVER label.")
    parser.add_argument("--wiki-pages-dir", default=None, help="Optional small FEVER wiki-pages directory.")
    args = parser.parse_args()
    prepare_fever_subset(args.input, args.output, args.max_per_label, args.wiki_pages_dir)


if __name__ == "__main__":
    main()
