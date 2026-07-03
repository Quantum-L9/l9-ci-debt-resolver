#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-dist/corpus}"
mkdir -p "$OUT_DIR"

FINDINGS_OUT="$OUT_DIR/CI_DEBT_FINDINGS.jsonl"
TRACES_OUT="$OUT_DIR/REMEDIATION_TRACES.jsonl"
MANIFEST_OUT="$OUT_DIR/CORPUS_MANIFEST.json"

: > "$FINDINGS_OUT"
: > "$TRACES_OUT"

if compgen -G "outputs/findings/*.jsonl" >/dev/null; then
  cat outputs/findings/*.jsonl >> "$FINDINGS_OUT"
fi

if compgen -G "outputs/traces/*.jsonl" >/dev/null; then
  cat outputs/traces/*.jsonl >> "$TRACES_OUT"
fi

"${PYTHON_BIN:-python3}" tools/validation/validate_findings.py \
  --findings "$FINDINGS_OUT" \
  --traces "$TRACES_OUT" \
  --allow-empty

"${PYTHON_BIN:-python3}" - "$FINDINGS_OUT" "$TRACES_OUT" "$MANIFEST_OUT" <<'INNER_PY'
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json
import os
import sys

findings = Path(sys.argv[1])
traces = Path(sys.argv[2])
manifest = Path(sys.argv[3])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

payload = {
    "schema_version": "1.0",
    "producer": "l9-ci-debt-resolver",
    "source_repo": os.environ.get("GITHUB_REPOSITORY", "Unknown"),
    "source_sha": os.environ.get("GITHUB_SHA", "Unknown"),
    "run_id": os.environ.get("GITHUB_RUN_ID", "Unknown"),
    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "Unknown"),
    "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    "files": {
        findings.name: {
            "path": str(findings),
            "rows": count_jsonl(findings),
            "sha256": sha256(findings),
        },
        traces.name: {
            "path": str(traces),
            "rows": count_jsonl(traces),
            "sha256": sha256(traces),
        },
    },
}
manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Wrote {manifest}")
INNER_PY

echo "Exported findings: $FINDINGS_OUT"
echo "Exported traces: $TRACES_OUT"
echo "Exported manifest: $MANIFEST_OUT"
