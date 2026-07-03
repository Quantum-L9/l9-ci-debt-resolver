## Summary

Adds the Resolver side of the CI debt corpus handoff.

This PR makes `l9-ci-debt-resolver` emit validated corpus artifacts that `l9-ci-debt-intelligence` can ingest later.

## What changed

- Adds `AGENTS.md` with resolver role, authority order, allowed actions, forbidden actions, validation gates, and handoff artifacts.
- Adds normalized finding schema.
- Adds remediation trace schema.
- Adds findings/traces output directories.
- Adds corpus export script.
- Adds corpus validator.
- Adds GitHub Actions workflow to export, upload, and optionally dispatch corpus readiness to `Quantum-L9/l9-ci-debt-intelligence`.
- Adds manifest, validation doc, regression guard, traceability map, and commit pack instructions.

## Validation

Run locally:

```bash
bash scripts/export_findings.sh dist/corpus
python tools/validation/validate_findings.py --findings dist/corpus/CI_DEBT_FINDINGS.jsonl --traces dist/corpus/REMEDIATION_TRACES.jsonl --allow-empty
python -m py_compile tools/validation/validate_findings.py
python -m json.tool schemas/ci_debt_finding.schema.json >/dev/null
python -m json.tool schemas/remediation_trace.schema.json >/dev/null
python -m json.tool dist/corpus/CORPUS_MANIFEST.json >/dev/null
```

## Safety

- Does not patch downstream repos.
- Does not require PR_Repair.
- Does not require LLM-Router.
- Does not fail corpus export when dispatch secret is missing.
- Does not fabricate findings.
