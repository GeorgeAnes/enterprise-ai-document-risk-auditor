# Evaluation Data

This folder is reserved for small local evaluation artifacts generated from public datasets. Only this README is tracked in Git.

Generated files such as `fever_subset.jsonl`, `fever_eval_summary.json`, `cuad_subset.jsonl`, and `cuad_audit_summary.json` are ignored by `.gitignore`.

## Default Demo Data

The UI default remains the included synthetic consulting report in `data/samples/consulting_report_sample.md`. FEVER and CUAD are optional evaluation workflows and are not required to run the app.

## Expected Local Layout

```text
data/
  samples/                 tracked synthetic demo documents
  eval/                    generated small benchmark artifacts, ignored
  raw/                     optional downloaded public datasets, ignored
```

Do not commit full public datasets, private contracts, client documents, raw FEVER Wikipedia pages, API keys, or generated benchmark outputs.
