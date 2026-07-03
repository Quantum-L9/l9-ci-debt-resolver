# Validation

Run from the repo root:

```bash
bash scripts/export_findings.sh dist/corpus
python tools/validation/validate_findings.py --findings dist/corpus/CI_DEBT_FINDINGS.jsonl --traces dist/corpus/REMEDIATION_TRACES.jsonl --allow-empty
python -m py_compile tools/validation/validate_findings.py
python -m json.tool schemas/ci_debt_finding.schema.json >/dev/null
python -m json.tool schemas/remediation_trace.schema.json >/dev/null
python -m json.tool dist/corpus/CORPUS_MANIFEST.json >/dev/null
git diff --stat
```

Expected local result: validation pass JSON with `findings_count` and `traces_count`, plus valid JSON schemas and manifest.
