# AGENTS.md - l9-ci-debt-resolver

## Role

This repo is Layer 1 of the L9 CI Debt trio: the Sensor. It detects CI failures, classifies root causes, emits normalized findings, and hands those findings downstream to `l9-ci-debt-intelligence`.

Data flow is one way:

```text
l9-ci-debt-resolver -> l9-ci-debt-intelligence -> l9-ci-debt-lsp
```

Resolver may dispatch corpus readiness downstream. Resolver must not read from or depend on Intelligence or LSP to complete its own local validation.

## Authority Order

1. Actual CI logs and resolver run artifacts.
2. Repo source files and scripts.
3. Schemas in `schemas/`.
4. This AGENTS.md.
5. Model inference, only for explanation and never to invent findings.

## Allowed Actions

- Add or update finding/trace schemas.
- Export observed findings from `outputs/findings/*.jsonl`.
- Export remediation traces from `outputs/traces/*.jsonl`.
- Validate exported JSONL before dispatch.
- Upload corpus artifacts.
- Dispatch `ci_debt_resolver_corpus_ready` to `Quantum-L9/l9-ci-debt-intelligence` when `L9_INTELLIGENCE_DISPATCH_TOKEN` exists.
- Skip dispatch cleanly when the token is missing.

## Forbidden Actions

- Do not weaken CI gates.
- Do not fake findings, traces, repair commits, timestamps, or metrics.
- Do not force-push.
- Do not amend after push.
- Do not patch downstream repos.
- Do not call LSP.
- Do not require PR_Repair or LLM-Router for this repo's corpus export path.
- Do not fail the resolver corpus export merely because downstream dispatch credentials are absent.

## Validation Gates

Run before commit:

```bash
bash scripts/export_findings.sh dist/corpus
python tools/validation/validate_findings.py --findings dist/corpus/CI_DEBT_FINDINGS.jsonl --traces dist/corpus/REMEDIATION_TRACES.jsonl --allow-empty
python -m py_compile tools/validation/validate_findings.py
python -m json.tool schemas/ci_debt_finding.schema.json >/dev/null
python -m json.tool schemas/remediation_trace.schema.json >/dev/null
python -m json.tool dist/corpus/CORPUS_MANIFEST.json >/dev/null
```

## Handoff Artifacts

- `dist/corpus/CI_DEBT_FINDINGS.jsonl`
- `dist/corpus/REMEDIATION_TRACES.jsonl`
- `dist/corpus/CORPUS_MANIFEST.json`
- GitHub artifact name: `ci-debt-resolver-corpus`
- Dispatch event: `ci_debt_resolver_corpus_ready`
