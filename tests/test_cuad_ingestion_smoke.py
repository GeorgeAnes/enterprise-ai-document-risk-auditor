from __future__ import annotations

import json

from scripts.prepare_cuad_subset import prepare_cuad_subset


def test_cuad_text_ingestion_and_contract_audit(tmp_path):
    contract_dir = tmp_path / "contracts"
    contract_dir.mkdir()
    contract_path = contract_dir / "sample_contract.txt"
    contract_path.write_text(
        """
        Master Services Agreement

        The supplier must provide monthly security reports within five business days after each calendar month.
        The supplier will maintain 99.5 percent platform availability, excluding scheduled maintenance windows.
        The supplier guarantees uninterrupted service without exception.
        Customer data must be encrypted in transit and at rest.
        The supplier follows robust privacy practices, but the agreement does not define a privacy framework.
        The customer may request one annual audit report unless a material security incident occurs.
        """,
        encoding="utf-8",
    )
    output_path = tmp_path / "cuad_subset.jsonl"
    summary_path = tmp_path / "cuad_summary.json"

    summary = prepare_cuad_subset(contract_dir, output_path, summary_path, max_docs=1)

    assert summary["contracts_written"] == 1
    assert output_path.exists()
    assert summary_path.exists()

    saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    audit = saved_summary["audits"][0]
    assert audit["total_claims"] >= 3
    assert audit["high_risk_findings"]
    assert any("guarantees uninterrupted service" in finding["claim"] for finding in audit["high_risk_findings"])
