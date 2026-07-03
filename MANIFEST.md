# Hardened Commit Pack Manifest: l9-ci-debt-resolver

## Purpose

Make Resolver emit a validated corpus artifact for downstream Intelligence ingestion.

## Responsibility Map

- `AGENTS.md`: repo operating contract and no-drift rules.
- `schemas/ci_debt_finding.schema.json`: normalized resolver finding event schema.
- `schemas/remediation_trace.schema.json`: resolver trace event schema.
- `outputs/findings/.gitkeep`: preserves finding output directory.
- `outputs/traces/.gitkeep`: preserves trace output directory.
- `tools/validation/validate_findings.py`: validates JSONL findings and traces.
- `scripts/export_findings.sh`: exports findings/traces, validates them, and writes a corpus manifest.
- `.github/workflows/dispatch-intelligence.yml`: uploads corpus and dispatches Intelligence with run coordinates.
- `VALIDATION.md`: exact commands required before PR.
- `REGRESSION_GUARD.md`: anti-regression rules.
- `TRACEABILITY_MAP.yaml`: file-to-purpose mapping.
