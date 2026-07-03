# Hardened Commit Pack: l9-ci-debt-resolver

## Branch

```bash
git checkout main
git pull --ff-only
git checkout -b wire/resolver-corpus-export
```

## Validate

```bash
bash scripts/export_findings.sh dist/corpus
python tools/validation/validate_findings.py --findings dist/corpus/CI_DEBT_FINDINGS.jsonl --traces dist/corpus/REMEDIATION_TRACES.jsonl --allow-empty
python -m py_compile tools/validation/validate_findings.py
python -m json.tool schemas/ci_debt_finding.schema.json >/dev/null
python -m json.tool schemas/remediation_trace.schema.json >/dev/null
python -m json.tool dist/corpus/CORPUS_MANIFEST.json >/dev/null
git diff --stat
```

## Commit

```bash
git add AGENTS.md schemas outputs tools scripts .github MANIFEST.md VALIDATION.md REGRESSION_GUARD.md TRACEABILITY_MAP.yaml COMMIT_PACK.md
git commit -m "feat: export validated CI debt corpus"
git push -u origin wire/resolver-corpus-export
```

## PR

```bash
gh pr create \
  --repo Quantum-L9/l9-ci-debt-resolver \
  --base main \
  --head wire/resolver-corpus-export \
  --title "feat: export validated CI debt corpus" \
  --body-file PR_BODY.md
```
