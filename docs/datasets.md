# Dataset Notes

The default demo uses only small synthetic documents stored in `data/samples`. These files are safe to publish and do not contain private company data, university-restricted material, credentials, or personal information.

## Optional Public Dataset Directions

These datasets are relevant for optional evaluation, but they are not downloaded by default:

- FEVER: useful for claim verification experiments with evidence retrieval and relative risk checks.
- CUAD: useful for contract review, clause-level extraction, vague-clause detection, and long-document stress testing.
- QASPER: useful for evidence-grounded question answering over research papers.

If adding dataset preparation scripts later, keep the default behavior small and explicit:

- require a command-line flag before downloading anything
- store raw data under `data/raw/`, which is ignored by Git
- write only tiny derived examples to `data/samples/`
- document source licenses and dataset terms

Do not commit full public datasets, private evidence packs, or client documents to this repository.

## Included Scripts

- `scripts/prepare_fever_subset.py`: creates a small FEVER JSONL subset for local risk testing.
- `scripts/evaluate_fever_risk.py`: checks whether supported FEVER claims receive lower average risk than refuted or not-enough-info claims.
- `scripts/prepare_cuad_subset.py`: loads a few local CUAD-style contracts and writes a compact audit summary with high-risk clauses and evidence snippets.

CUAD is a contract-review stress test in this project. It is not treated as a hallucination benchmark.

Dataset download commands are documented in `docs/download_datasets.md`.
