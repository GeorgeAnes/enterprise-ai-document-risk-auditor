# Evaluation Data

This folder is reserved for small local evaluation artifacts generated from public datasets. Only this README is tracked in Git.

Generated files such as `cuad_subset.jsonl` and `cuad_audit_summary.json` are ignored by `.gitignore`.

## Default Demo Data

The UI default remains the included synthetic consulting report in `data/samples/consulting_report_sample.md`. CUAD is an optional evaluation workflow and is not required to run the app.

## Expected Local Layout

```text
data/
  samples/                 tracked synthetic demo documents
  eval/                    generated small benchmark artifacts, ignored
  raw/                     optional downloaded public datasets, ignored
```

Do not commit full public datasets, private contracts, client documents, API keys, or generated benchmark outputs.
