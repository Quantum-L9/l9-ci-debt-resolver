from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FINDING_FIELDS = {
    "schema_version",
    "source",
    "repo",
    "finding_id",
    "failure_type",
    "root_cause",
    "outcome",
    "created_at",
}
REQUIRED_TRACE_FIELDS = {
    "schema_version",
    "repo",
    "trace_id",
    "started_at",
    "status",
    "steps",
}
VALID_OUTCOMES = {"repaired", "failed", "blocked", "unknown", "observed"}
VALID_CONFIDENCE = {"low", "medium", "high", "unknown"}
VALID_TRACE_STATUS = {"pass", "fail", "blocked", "unknown"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{lineno}: JSONL row must be an object")
        rows.append(row)
    return rows


def required_errors(row: dict[str, Any], required: set[str], where: str) -> list[str]:
    errors: list[str] = []
    missing = sorted(required - set(row))
    if missing:
        errors.append(f"{where}: missing required fields: {', '.join(missing)}")
    for field in sorted(required):
        if field not in row:
            continue
        value = row[field]
        if value is None:
            errors.append(f"{where}: {field} must be non-null")
        elif isinstance(value, str) and not value.strip():
            errors.append(f"{where}: {field} must be non-empty")
    return errors


def validate_finding(row: dict[str, Any], where: str) -> list[str]:
    errors = required_errors(row, REQUIRED_FINDING_FIELDS, where)
    if row.get("schema_version") != "1.0":
        errors.append(f"{where}: schema_version must be 1.0")
    if row.get("source") != "l9-ci-debt-resolver":
        errors.append(f"{where}: source must be l9-ci-debt-resolver")
    if row.get("outcome") not in VALID_OUTCOMES:
        errors.append(f"{where}: invalid outcome")
    if row.get("confidence", "unknown") not in VALID_CONFIDENCE:
        errors.append(f"{where}: invalid confidence")
    return errors


def validate_trace(row: dict[str, Any], where: str) -> list[str]:
    errors = required_errors(row, REQUIRED_TRACE_FIELDS, where)
    if row.get("schema_version") != "1.0":
        errors.append(f"{where}: schema_version must be 1.0")
    if row.get("status") not in VALID_TRACE_STATUS:
        errors.append(f"{where}: invalid status")
    if not isinstance(row.get("steps"), list):
        errors.append(f"{where}: steps must be a list")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate exported CI debt corpus JSONL files.")
    parser.add_argument("--findings", type=Path, default=Path("dist/corpus/CI_DEBT_FINDINGS.jsonl"))
    parser.add_argument("--traces", type=Path, default=Path("dist/corpus/REMEDIATION_TRACES.jsonl"))
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    findings = read_jsonl(args.findings)
    traces = read_jsonl(args.traces)

    if not findings and not args.allow_empty:
        errors.append(f"{args.findings}: no findings exported")

    for index, row in enumerate(findings, start=1):
        errors.extend(validate_finding(row, f"{args.findings}:{index}"))
    for index, row in enumerate(traces, start=1):
        errors.extend(validate_trace(row, f"{args.traces}:{index}"))

    if errors:
        print("CI debt corpus validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "pass",
                "findings_count": len(findings),
                "traces_count": len(traces),
                "findings_path": str(args.findings),
                "traces_path": str(args.traces),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
