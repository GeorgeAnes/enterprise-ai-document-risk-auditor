# Downloading Optional Evaluation Datasets

The app runs immediately with the tracked synthetic sample files in `data/samples/`. CUAD is an optional local evaluation dataset. It should be downloaded only when you want to run the evaluation script.

Store raw downloads under `data/raw/`. That folder is ignored by Git.

## CUAD

Official project page: https://www.atticusprojectai.org/cuad/

Zenodo record: https://zenodo.org/records/4595826

CUAD v1 is about 105.9 MB as a zip file on Zenodo. It contains 510 commercial legal contracts with expert annotations. In this project, CUAD is used as a contract-review stress test, not a hallucination benchmark.

Download:

```powershell
New-Item -ItemType Directory -Force data\raw\cuad
Invoke-WebRequest `
  -Uri "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1" `
  -OutFile "data\raw\cuad\CUAD_v1.zip"
Expand-Archive `
  -Path "data\raw\cuad\CUAD_v1.zip" `
  -DestinationPath "data\raw\cuad\CUAD_v1" `
  -Force
```

The CUAD zip has multiple files and folders. To run this repo's stress test, point the script at a folder containing a few `.txt` or `.md` contract files, or at a JSON file with contract text fields:

```powershell
python scripts\prepare_cuad_subset.py `
  --input data\raw\cuad\sample_contracts `
  --output data\eval\cuad_subset.jsonl `
  --summary-output data\eval\cuad_audit_summary.json `
  --max-docs 3
```

If the extracted CUAD folder uses a different path for contract text files, adjust the `--input` path after inspecting the unzipped folder.

## Safety

- Do not commit `data/raw/` or generated files under `data/eval/`.
- Do not upload private contracts or client documents.
- Keep dataset licenses and terms with the raw dataset files.
- Use small subsets for portfolio demos.
