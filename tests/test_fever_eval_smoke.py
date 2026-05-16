from __future__ import annotations

import json

from scripts.evaluate_fever_risk import evaluate_fever_subset
from scripts.prepare_fever_subset import prepare_fever_subset


def test_fever_subset_preparation_and_relative_risk(tmp_path):
    raw_path = tmp_path / "fever.jsonl"
    prepared_path = tmp_path / "fever_subset.jsonl"
    summary_path = tmp_path / "fever_eval_summary.json"

    records = [
        {
            "id": 1,
            "claim": "The supplier performs quarterly access reviews.",
            "label": "SUPPORTS",
            "evidence": [[["ann", 1, "Supplier_Security", 4]]],
            "evidence_text": ["The supplier performs quarterly access reviews for all active user accounts."],
        },
        {
            "id": 2,
            "claim": "The service is guaranteed to be uninterrupted at all times.",
            "label": "REFUTES",
            "evidence": [[["ann", 2, "Service_Agreement", 8]]],
            "evidence_text": [
                "However, scheduled maintenance is allowed and the supplier does not guarantee uninterrupted service."
            ],
        },
        {
            "id": 3,
            "claim": "The supplier completed 40 independent audits in 2025.",
            "label": "NOT ENOUGH INFO",
            "evidence": [],
        },
    ]
    raw_path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    prep_summary = prepare_fever_subset(raw_path, prepared_path, max_per_label=1)
    assert prep_summary["examples_written"] == 3

    eval_summary = evaluate_fever_subset(prepared_path, summary_path)
    risks = eval_summary["average_risk_by_label"]
    assert risks["SUPPORTS"] < risks["REFUTES"]
    assert risks["SUPPORTS"] < risks["NOT ENOUGH INFO"]
    assert eval_summary["supported_lower_than_refuted"] is True
    assert eval_summary["supported_lower_than_not_enough_info"] is True
