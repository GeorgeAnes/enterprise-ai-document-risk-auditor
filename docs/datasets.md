# Dataset Notes

The default demo uses only small synthetic documents stored in `data/samples`. These files are safe to publish and do not contain private company data, university-restricted material, credentials, or personal information.

## Optional Public Dataset Directions

These datasets are relevant for future extensions, but they are not downloaded by default:

- FEVER: useful for claim verification experiments with evidence retrieval.
- CUAD: useful for contract review and clause-level extraction tasks.
- QASPER: useful for evidence-grounded question answering over research papers.

If adding dataset preparation scripts later, keep the default behavior small and explicit:

- require a command-line flag before downloading anything
- store raw data under `data/raw/`, which is ignored by Git
- write only tiny derived examples to `data/samples/`
- document source licenses and dataset terms

Do not commit full public datasets, private evidence packs, or client documents to this repository.
