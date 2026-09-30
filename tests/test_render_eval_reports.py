from __future__ import annotations

import json

from scripts.render_eval_reports import render_reports


def test_cuad_report_still_renders(tmp_path):
    summary = tmp_path / "cuad_summary.json"
    summary.write_text(
        json.dumps(
            {
                "contracts_written": 1,
                "audits": [
                    {
                        "title": "Sample contract",
                        "total_claims": 2,
                        "overall_risk_score": 40,
                        "high_risk_findings": [
                            {
                                "label": "Unsupported",
                                "risk_score": 80,
                                "claim": "The supplier guarantees uninterrupted service.",
                                "evidence": [{"text": "Scheduled maintenance is excluded."}],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    written = render_reports(summary, tmp_path / "out")

    report = (tmp_path / "out" / "cuad_gemini_contract_review.md").read_text(encoding="utf-8")
    assert "guarantees uninterrupted service" in report
    assert set(written) == {"cuad", "index"}
