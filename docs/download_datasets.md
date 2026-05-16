# Downloading Optional Evaluation Datasets

The app runs immediately with the tracked synthetic sample files in `data/samples/`. FEVER and CUAD are optional local evaluation datasets. They should be downloaded only when you want to run the evaluation scripts.

Store raw downloads under `data/raw/`. That folder is ignored by Git.

## FEVER

Official dataset page: https://fever.ai/dataset/fever.html

The FEVER page documents the JSONL format and labels: `SUPPORTS`, `REFUTES`, and `NOT ENOUGH INFO`.

Smallest useful file for this repo:

```powershell
New-Item -ItemType Directory -Force data\raw\fever
Invoke-WebRequest `
  -Uri "https://fever.ai/download/fever/paper_dev.jsonl" `
  -OutFile "data\raw\fever\paper_dev.jsonl"
```

Optional Wikipedia evidence pages are much larger. Download them only if you want to resolve evidence sentence text from FEVER page/sentence IDs:

```powershell
Invoke-WebRequest `
  -Uri "https://fever.ai/download/fever/wiki-pages.zip" `
  -OutFile "data\raw\fever\wiki-pages.zip"
Expand-Archive `
  -Path "data\raw\fever\wiki-pages.zip" `
  -DestinationPath "data\raw\fever\wiki-pages" `
  -Force
```

Prepare a tiny local subset:

```powershell
python scripts\prepare_fever_subset.py `
  --input data\raw\fever\paper_dev.jsonl `
  --output data\eval\fever_subset.jsonl `
  --max-per-label 5
```

With local Wikipedia evidence pages:

```powershell
python scripts\prepare_fever_subset.py `
  --input data\raw\fever\paper_dev.jsonl `
  --wiki-pages-dir data\raw\fever\wiki-pages `
  --output data\eval\fever_subset.jsonl `
  --max-per-label 5
```

Evaluate risk separation:

```powershell
python scripts\evaluate_fever_risk.py `
  --input data\eval\fever_subset.jsonl `
  --output data\eval\fever_eval_summary.json
```

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
