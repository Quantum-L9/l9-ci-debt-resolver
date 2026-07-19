#!/usr/bin/env bash
set -euo pipefail
###############################################################################
# Quantum-L9/l9-ci-debt-resolver
# RESOLVER-P1 - Authoritative Failed-Log Acquisition
#
# Incremental build over RESOLVER-P0.
#
# Implements:
#   - GitHub Actions failed-run acquisition
#   - failed-job discovery with pagination
#   - per-job log retrieval
#   - redirect-safe binary/text downloads
#   - bounded retries with Retry-After support
#   - log-size limits
#   - log completeness assessment
#   - truncation-marker detection
#   - secret, credential, email, and path redaction
#   - deterministic evidence identities
#   - artifact provenance
#   - acquisition reports
#   - fail-closed terminal-state behavior
#   - CLI acquisition command
#   - architecture, privacy, resilience, and contract tests
#
# Does not implement:
#   - SDK repository correlation          (RESOLVER-P2)
#   - root-cause classification runtime   (RESOLVER-P2)
#   - bounded remediation                 (RESOLVER-P3)
#   - branch push or CI rerun observation (RESOLVER-P4)
###############################################################################
fail() {
  printf 'RESOLVER-P1: %s\n' "$*" >&2
  exit 1
}
require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "required command not found: $1"
}
require_command python3
[[ -d .git ]] \
  || fail "run from the l9-ci-debt-resolver repository root"
[[ -f .l9/repo-spec.yaml ]] \
  || fail "RESOLVER-P0 foundation is missing"
[[ -f src/l9_debt_resolver/contracts/models.py ]] \
  || fail "RESOLVER-P0 Python package is missing"
if ! grep -q 'RESOLVER-P0' .l9/repo-spec.yaml; then
  fail "repository does not appear to contain RESOLVER-P0"
fi
mkdir -p \
  schemas/resolver \
  src/l9_debt_resolver/acquisition \
  src/l9_debt_resolver/providers/github \
  tests/acquisition \
  tests/providers/github \
  tests/privacy \
  tests/resilience \
  tests/fixtures/github \
  docs/architecture/ADRs \
  .github/workflows
###############################################################################
# 1. Acquisition contract
###############################################################################
cat > .l9/log-acquisition-contract.yaml <<'EOF'
schema: l9.resolver-log-acquisition-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P1
  status: authoritative
authority:
  primary: actual_failed_log
  precedence:
    - actual_failed_log
    - failed_job_metadata
    - SDK_repository_evidence
    - historical_context
  invariants:
    - Job names alone cannot establish root cause.
    - Missing logs cannot establish a clean result.
    - Incomplete logs cannot authorize remediation.
    - All retrieved logs must have cryptographic provenance.
    - Raw logs must not be emitted to corpus consumers.
providers:
  github_actions:
    run_endpoint: /repos/{owner}/{repo}/actions/runs/{run_id}
    jobs_endpoint: /repos/{owner}/{repo}/actions/runs/{run_id}/jobs
    job_logs_endpoint: /repos/{owner}/{repo}/actions/jobs/{job_id}/logs
    authentication:
      accepted:
        - GITHUB_TOKEN
        - GH_TOKEN
      token_persistence: prohibited
      token_logging: prohibited
pagination:
  page_size: 100
  maximum_pages: 100
  fail_on_limit: true
retry:
  maximum_attempts: 4
  retryable_statuses:
    - 408
    - 425
    - 429
    - 500
    - 502
    - 503
    - 504
  exponential_backoff:
    initial_seconds: 0.25
    maximum_seconds: 4.0
  retry_after:
    honored: true
    maximum_seconds: 30
limits:
  maximum_jobs_per_run: 1000
  maximum_log_bytes_per_job: 52428800
  maximum_total_log_bytes: 524288000
  maximum_redacted_log_bytes_in_memory: 52428800
completeness:
  states:
    - complete
    - possibly_truncated
    - truncated
    - unavailable
  unavailable_when:
    - provider returns not found
    - provider denies access
    - response body is empty
    - download fails after bounded retries
  truncated_when:
    - downloaded bytes exceed configured maximum
    - explicit truncation marker is detected
    - content length exceeds consumed bytes
    - archive entry cannot be read completely
  possibly_truncated_when:
    - expected terminal markers are absent
    - provider metadata is internally inconsistent
    - an unknown log serialization is received
redaction:
  required_before:
    - local durable persistence
    - diagnostic output
    - test fixture capture
    - corpus event generation
  removes:
    - bearer credentials
    - GitHub credentials
    - cloud credentials
    - private keys
    - assignment-form secrets
    - email addresses
    - absolute Unix paths
    - absolute Windows paths
    - configured repository root
  replacement_format: "[REDACTED:<CLASS>]"
provenance:
  required:
    - provider
    - API version
    - repository reference
    - run ID
    - job ID
    - retrieval ID
    - retrieval timestamp
    - HTTP ETag when available
    - HTTP content length when available
    - raw SHA-256
    - redacted SHA-256
    - raw byte count
    - redacted byte count
    - completeness assessment
    - limitations
failure_behavior:
  no_failed_jobs:
    terminal_state: clean
    condition: run conclusion is successful and no failed jobs exist
  failed_job_without_complete_log:
    terminal_state: insufficient_log_evidence
    remediation: prohibited
  provider_failure:
    terminal_state: remote_operation_failed
    remediation: prohibited
  partial_run_acquisition:
    terminal_state: insufficient_log_evidence
    remediation: prohibited
EOF
###############################################################################
# 2. Schemas
###############################################################################
cat > schemas/resolver/failed-run-reference.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/failed-run-reference/v1",
  "title": "L9 Resolver Failed Run Reference",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "provider",
    "repository",
    "run_id",
    "requested_at"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.failed-run-reference/v1"
    },
    "provider": {
      "const": "github_actions"
    },
    "repository": {
      "type": "string",
      "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    },
    "run_id": {
      "type": "string",
      "pattern": "^[0-9]+$"
    },
    "requested_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
EOF
cat > schemas/resolver/failed-job.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/failed-job/v1",
  "title": "L9 Resolver Failed Job",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "provider",
    "run_id",
    "job_id",
    "name",
    "status",
    "conclusion",
    "started_at",
    "completed_at",
    "runner_name",
    "labels",
    "failed_steps"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.failed-job/v1"
    },
    "provider": {
      "const": "github_actions"
    },
    "run_id": {
      "type": "string",
      "minLength": 1
    },
    "job_id": {
      "type": "string",
      "minLength": 1
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "status": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "conclusion": {
      "enum": [
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
        "startup_failure",
        "stale",
        "neutral",
        "unknown"
      ]
    },
    "started_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "completed_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "runner_name": {
      "type": [
        "string",
        "null"
      ],
      "maxLength": 500
    },
    "labels": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 200
      },
      "uniqueItems": true
    },
    "failed_steps": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "number",
          "name",
          "conclusion"
        ],
        "properties": {
          "number": {
            "type": "integer",
            "minimum": 0
          },
          "name": {
            "type": "string",
            "maxLength": 500
          },
          "conclusion": {
            "type": "string",
            "maxLength": 100
          }
        }
      }
    }
  }
}
EOF
cat > schemas/resolver/log-provenance.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/log-provenance/v1",
  "title": "L9 Resolver Log Provenance",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "provider",
    "api_version",
    "repository",
    "run_id",
    "job_id",
    "retrieval_id",
    "retrieved_at",
    "etag",
    "content_length",
    "content_type",
    "raw_sha256",
    "redacted_sha256",
    "raw_byte_count",
    "redacted_byte_count",
    "completeness",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.log-provenance/v1"
    },
    "provider": {
      "const": "github_actions"
    },
    "api_version": {
      "type": "string",
      "minLength": 1
    },
    "repository": {
      "type": "string",
      "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    },
    "run_id": {
      "type": "string",
      "minLength": 1
    },
    "job_id": {
      "type": "string",
      "minLength": 1
    },
    "retrieval_id": {
      "type": "string",
      "pattern": "^retrieval_[0-9a-f]{64}$"
    },
    "retrieved_at": {
      "type": "string",
      "format": "date-time"
    },
    "etag": {
      "type": [
        "string",
        "null"
      ],
      "maxLength": 500
    },
    "content_length": {
      "type": [
        "integer",
        "null"
      ],
      "minimum": 0
    },
    "content_type": {
      "type": [
        "string",
        "null"
      ],
      "maxLength": 500
    },
    "raw_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "redacted_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "raw_byte_count": {
      "type": "integer",
      "minimum": 0
    },
    "redacted_byte_count": {
      "type": "integer",
      "minimum": 0
    },
    "completeness": {
      "enum": [
        "complete",
        "possibly_truncated",
        "truncated",
        "unavailable"
      ]
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 1000
      },
      "uniqueItems": true
    }
  }
}
EOF
cat > schemas/resolver/acquisition-report.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/acquisition-report/v1",
  "title": "L9 Resolver Acquisition Report",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "acquisition_id",
    "provider",
    "repository",
    "run_id",
    "run_status",
    "run_conclusion",
    "failed_job_count",
    "evidence_count",
    "complete_evidence_count",
    "total_raw_bytes",
    "terminal_state",
    "started_at",
    "completed_at",
    "evidence",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.acquisition-report/v1"
    },
    "acquisition_id": {
      "type": "string",
      "pattern": "^acquisition_[0-9a-f]{64}$"
    },
    "provider": {
      "const": "github_actions"
    },
    "repository": {
      "type": "string",
      "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    },
    "run_id": {
      "type": "string",
      "minLength": 1
    },
    "run_status": {
      "type": "string",
      "minLength": 1
    },
    "run_conclusion": {
      "type": [
        "string",
        "null"
      ]
    },
    "failed_job_count": {
      "type": "integer",
      "minimum": 0
    },
    "evidence_count": {
      "type": "integer",
      "minimum": 0
    },
    "complete_evidence_count": {
      "type": "integer",
      "minimum": 0
    },
    "total_raw_bytes": {
      "type": "integer",
      "minimum": 0
    },
    "terminal_state": {
      "enum": [
        "evidence_ready",
        "clean",
        "insufficient_log_evidence",
        "remote_operation_failed"
      ]
    },
    "started_at": {
      "type": "string",
      "format": "date-time"
    },
    "completed_at": {
      "type": "string",
      "format": "date-time"
    },
    "evidence": {
      "type": "array",
      "items": {
        "$ref": "l9://resolver/ci-run-evidence/v1"
      }
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 1000
      },
      "uniqueItems": true
    }
  }
}
EOF
###############################################################################
# 3. Acquisition package
###############################################################################
cat > src/l9_debt_resolver/acquisition/__init__.py <<'EOF'
"""Authoritative CI failure evidence acquisition."""
EOF
cat > src/l9_debt_resolver/acquisition/errors.py <<'EOF'
from __future__ import annotations
class AcquisitionError(RuntimeError):
    """Base failed-log acquisition error."""
class AuthenticationError(AcquisitionError):
    """Provider authentication is unavailable or rejected."""
class AuthorizationError(AcquisitionError):
    """Provider denied access to a required resource."""
class RemoteResponseError(AcquisitionError):
    """Provider returned an invalid or terminal response."""
class RetryExhaustedError(AcquisitionError):
    """A retryable operation exhausted its bounded attempts."""
class PaginationLimitError(AcquisitionError):
    """Provider pagination exceeded the configured safety limit."""
class JobLimitError(AcquisitionError):
    """A run exceeded the configured failed-job safety limit."""
class LogSizeLimitError(AcquisitionError):
    """A log or run exceeded the configured byte limit."""
class UnsupportedLogFormatError(AcquisitionError):
    """A downloaded log uses an unsupported serialization."""
EOF
cat > src/l9_debt_resolver/acquisition/config.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class RetryPolicy:
    maximum_attempts: int = 4
    initial_backoff_seconds: float = 0.25
    maximum_backoff_seconds: float = 4.0
    maximum_retry_after_seconds: float = 30.0
    retryable_statuses: frozenset[int] = frozenset(
        {
            408,
            425,
            429,
            500,
            502,
            503,
            504,
        }
    )
    def __post_init__(self) -> None:
        if self.maximum_attempts < 1:
            raise ValueError("maximum_attempts must be positive")
        if self.initial_backoff_seconds < 0:
            raise ValueError(
                "initial_backoff_seconds cannot be negative"
            )
        if (
            self.maximum_backoff_seconds
            < self.initial_backoff_seconds
        ):
            raise ValueError(
                "maximum_backoff_seconds cannot be smaller "
                "than initial_backoff_seconds"
            )
@dataclass(frozen=True)
class AcquisitionLimits:
    page_size: int = 100
    maximum_pages: int = 100
    maximum_jobs_per_run: int = 1000
    maximum_log_bytes_per_job: int = 50 * 1024 * 1024
    maximum_total_log_bytes: int = 500 * 1024 * 1024
    def __post_init__(self) -> None:
        positive = {
            "page_size": self.page_size,
            "maximum_pages": self.maximum_pages,
            "maximum_jobs_per_run": self.maximum_jobs_per_run,
            "maximum_log_bytes_per_job": (
                self.maximum_log_bytes_per_job
            ),
            "maximum_total_log_bytes": (
                self.maximum_total_log_bytes
            ),
        }
        for name, value in positive.items():
            if value < 1:
                raise ValueError(f"{name} must be positive")
@dataclass(frozen=True)
class AcquisitionConfig:
    retry: RetryPolicy = RetryPolicy()
    limits: AcquisitionLimits = AcquisitionLimits()
    api_version: str = "2022-11-28"
    user_agent: str = "l9-ci-debt-resolver/0.2.0"
EOF
cat > src/l9_debt_resolver/acquisition/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from l9_debt_resolver.contracts.models import CIRunEvidence
@dataclass(frozen=True)
class FailedRun:
    provider: str
    repository: str
    run_id: str
    status: str
    conclusion: str | None
    head_sha: str
    event: str
    workflow_id: str | None
    created_at: str | None
    updated_at: str | None
    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "repository": self.repository,
            "run_id": self.run_id,
            "status": self.status,
            "conclusion": self.conclusion,
            "head_sha": self.head_sha,
            "event": self.event,
            "workflow_id": self.workflow_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
@dataclass(frozen=True)
class FailedStep:
    number: int
    name: str
    conclusion: str
@dataclass(frozen=True)
class FailedJob:
    provider: str
    run_id: str
    job_id: str
    name: str
    status: str
    conclusion: str
    started_at: str | None
    completed_at: str | None
    runner_name: str | None
    labels: tuple[str, ...]
    failed_steps: tuple[FailedStep, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.failed-job/v1",
            "provider": self.provider,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "name": self.name,
            "status": self.status,
            "conclusion": self.conclusion,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "runner_name": self.runner_name,
            "labels": list(self.labels),
            "failed_steps": [
                {
                    "number": step.number,
                    "name": step.name,
                    "conclusion": step.conclusion,
                }
                for step in self.failed_steps
            ],
        }
@dataclass(frozen=True)
class LogProvenance:
    provider: str
    api_version: str
    repository: str
    run_id: str
    job_id: str
    retrieval_id: str
    retrieved_at: str
    etag: str | None
    content_length: int | None
    content_type: str | None
    raw_sha256: str
    redacted_sha256: str
    raw_byte_count: int
    redacted_byte_count: int
    completeness: str
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.log-provenance/v1",
            "provider": self.provider,
            "api_version": self.api_version,
            "repository": self.repository,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "retrieval_id": self.retrieval_id,
            "retrieved_at": self.retrieved_at,
            "etag": self.etag,
            "content_length": self.content_length,
            "content_type": self.content_type,
            "raw_sha256": self.raw_sha256,
            "redacted_sha256": self.redacted_sha256,
            "raw_byte_count": self.raw_byte_count,
            "redacted_byte_count": self.redacted_byte_count,
            "completeness": self.completeness,
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class AcquiredLog:
    evidence: CIRunEvidence
    provenance: LogProvenance
    redacted_text: str
@dataclass(frozen=True)
class AcquisitionReport:
    acquisition_id: str
    provider: str
    repository: str
    run_id: str
    run_status: str
    run_conclusion: str | None
    failed_job_count: int
    evidence: tuple[CIRunEvidence, ...]
    total_raw_bytes: int
    terminal_state: str
    started_at: str
    completed_at: str
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        complete_count = sum(
            item.log_completeness == "complete"
            for item in self.evidence
        )
        return {
            "schema_version": "l9.acquisition-report/v1",
            "acquisition_id": self.acquisition_id,
            "provider": self.provider,
            "repository": self.repository,
            "run_id": self.run_id,
            "run_status": self.run_status,
            "run_conclusion": self.run_conclusion,
            "failed_job_count": self.failed_job_count,
            "evidence_count": len(self.evidence),
            "complete_evidence_count": complete_count,
            "total_raw_bytes": self.total_raw_bytes,
            "terminal_state": self.terminal_state,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "evidence": [
                item.as_dict()
                for item in self.evidence
            ],
            "limitations": list(self.limitations),
        }
EOF
cat > src/l9_debt_resolver/acquisition/redaction.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
import re
@dataclass(frozen=True)
class RedactionResult:
    text: str
    classes: tuple[str, ...]
_PATTERN_DEFINITIONS: tuple[
    tuple[str, re.Pattern[str]],
    ...
] = (
    (
        "PRIVATE_KEY",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
            r".*?"
            r"-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    (
        "GITHUB_TOKEN",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}"
            r"|github_pat_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    (
        "AWS_ACCESS_KEY",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "BEARER_TOKEN",
        re.compile(
            r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"
        ),
    ),
    (
        "ASSIGNMENT_SECRET",
        re.compile(
            r"(?i)\b("
            r"token|secret|password|passwd|api[_-]?key"
            r"|access[_-]?key|client[_-]?secret"
            r")\s*[:=]\s*"
            r"([\"']?)[^\s,\"']{8,}\2"
        ),
    ),
    (
        "EMAIL",
        re.compile(
            r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
            r"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?)+\b"
        ),
    ),
    (
        "WINDOWS_PATH",
        re.compile(
            r"(?<![A-Za-z0-9_.-])"
            r"[A-Za-z]:\$begin:math:text$\?\:\[\^\\\\\\r\\n\\t \]\+\\$end:math:text$*"
            r"[^\\\r\n\t ]*"
        ),
    ),
    (
        "UNIX_PATH",
        re.compile(
            r"(?<![A-Za-z0-9_.-])"
            r"/(?:home|Users|private|tmp|var|opt|workspace"
            r"|github/workspace)"
            r"(?:/[^\s:'\"<>|]+)+"
        ),
    ),
)
class LogRedactor:
    def __init__(
        self,
        repository_root: str | None = None,
    ) -> None:
        self._repository_root = (
            repository_root.rstrip("/\\")
            if repository_root
            else None
        )
    def redact(self, text: str) -> RedactionResult:
        value = text
        classes: set[str] = set()
        if self._repository_root:
            replacement = "[REDACTED:REPOSITORY_ROOT]"
            if self._repository_root in value:
                value = value.replace(
                    self._repository_root,
                    replacement,
                )
                classes.add("REPOSITORY_ROOT")
        for redaction_class, pattern in _PATTERN_DEFINITIONS:
            value, count = pattern.subn(
                f"[REDACTED:{redaction_class}]",
                value,
            )
            if count:
                classes.add(redaction_class)
        return RedactionResult(
            text=value,
            classes=tuple(sorted(classes)),
        )
EOF
cat > src/l9_debt_resolver/acquisition/completeness.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
import re
@dataclass(frozen=True)
class CompletenessAssessment:
    state: str
    limitations: tuple[str, ...]
_EXPLICIT_TRUNCATION_MARKERS = (
    re.compile(r"(?i)\blog output truncated\b"),
    re.compile(r"(?i)\btruncated to last \d+ lines\b"),
    re.compile(r"(?i)\bmaximum log length exceeded\b"),
    re.compile(r"(?i)\blog exceeded .* limit\b"),
    re.compile(r"(?i)\btoo much output\b"),
    re.compile(r"(?i)\boutput has been truncated\b"),
)
_TERMINAL_MARKERS = (
    re.compile(r"(?im)^##$begin:math:display$error$end:math:display$"),
    re.compile(r"(?im)^Error: Process completed with exit code"),
    re.compile(r"(?im)^Process completed with exit code"),
    re.compile(r"(?im)^##$begin:math:display$section$end:math:display$Finishing:"),
    re.compile(r"(?im)^Post job cleanup\."),
)
def assess_log_completeness(
    *,
    raw: bytes,
    content_length: int | None,
    exceeded_limit: bool,
    download_complete: bool,
) -> CompletenessAssessment:
    limitations: list[str] = []
    if not raw:
        return CompletenessAssessment(
            state="unavailable",
            limitations=("provider returned an empty log",),
        )
    text = raw.decode("utf-8", errors="replace")
    if exceeded_limit:
        limitations.append(
            "log exceeded the configured per-job byte limit"
        )
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if not download_complete:
        limitations.append(
            "provider response did not complete successfully"
        )
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if (
        content_length is not None
        and content_length > len(raw)
    ):
        limitations.append(
            "HTTP content length exceeds downloaded bytes"
        )
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if any(
        pattern.search(text)
        for pattern in _EXPLICIT_TRUNCATION_MARKERS
    ):
        limitations.append(
            "an explicit truncation marker was detected"
        )
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if "\ufffd" in text:
        limitations.append(
            "log contained undecodable byte sequences"
        )
    terminal_marker_present = any(
        pattern.search(text)
        for pattern in _TERMINAL_MARKERS
    )
    if not terminal_marker_present:
        limitations.append(
            "no recognized terminal log marker was detected"
        )
        return CompletenessAssessment(
            state="possibly_truncated",
            limitations=tuple(limitations),
        )
    return CompletenessAssessment(
        state="complete",
        limitations=tuple(limitations),
    )
EOF
cat > src/l9_debt_resolver/acquisition/retry.py <<'EOF'
from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import TypeVar
from .config import RetryPolicy
from .errors import RetryExhaustedError
T = TypeVar("T")
@dataclass(frozen=True)
class RetrySignal(Exception):
    status: int
    retry_after: str | None = None
def retry_after_seconds(
    value: str | None,
    *,
    now: datetime | None = None,
) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    try:
        return max(0.0, float(stripped))
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(stripped)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    return max(
        0.0,
        (parsed - reference).total_seconds(),
    )
async def with_retry(
    operation: Callable[[int], Awaitable[T]],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    last_signal: RetrySignal | None = None
    for attempt in range(1, policy.maximum_attempts + 1):
        try:
            return await operation(attempt)
        except RetrySignal as signal:
            last_signal = signal
            if signal.status not in policy.retryable_statuses:
                raise
            if attempt >= policy.maximum_attempts:
                break
            server_delay = retry_after_seconds(
                signal.retry_after
            )
            exponential_delay = min(
                policy.maximum_backoff_seconds,
                policy.initial_backoff_seconds
                * (2 ** (attempt - 1)),
            )
            delay = (
                min(
                    server_delay,
                    policy.maximum_retry_after_seconds,
                )
                if server_delay is not None
                else exponential_delay
            )
            await sleep(delay)
    status = (
        last_signal.status
        if last_signal is not None
        else "unknown"
    )
    raise RetryExhaustedError(
        "provider operation exhausted bounded retries "
        f"after status {status}"
    )
EOF
cat > src/l9_debt_resolver/acquisition/service.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
from typing import Protocol
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.contracts.models import CIRunEvidence
from .models import (
    AcquiredLog,
    AcquisitionReport,
    FailedJob,
    FailedRun,
)
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
class AcquisitionProvider(Protocol):
    async def identify_failed_run(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> FailedRun:
        """Retrieve provider run metadata."""
    async def retrieve_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> tuple[FailedJob, ...]:
        """Retrieve all failed jobs."""
    async def retrieve_failed_log(
        self,
        *,
        repository: str,
        run_id: str,
        job: FailedJob,
    ) -> AcquiredLog:
        """Retrieve and sanitize one failed job log."""
class FailedLogAcquisitionService:
    def __init__(
        self,
        provider: AcquisitionProvider,
        *,
        clock: callable = utc_now,
    ) -> None:
        self._provider = provider
        self._clock = clock
    async def acquire(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> AcquisitionReport:
        started_at = self._clock()
        run = await self._provider.identify_failed_run(
            repository=repository,
            run_id=run_id,
        )
        jobs = await self._provider.retrieve_failed_jobs(
            repository=repository,
            run_id=run_id,
        )
        if not jobs:
            terminal_state = (
                "clean"
                if run.conclusion == "success"
                else "insufficient_log_evidence"
            )
            completed_at = self._clock()
            return AcquisitionReport(
                acquisition_id=namespaced_identity(
                    "acquisition_",
                    {
                        "repository": repository,
                        "run_id": run_id,
                        "started_at": started_at,
                    },
                ),
                provider=run.provider,
                repository=repository,
                run_id=run_id,
                run_status=run.status,
                run_conclusion=run.conclusion,
                failed_job_count=0,
                evidence=(),
                total_raw_bytes=0,
                terminal_state=terminal_state,
                started_at=started_at,
                completed_at=completed_at,
                limitations=(
                    ()
                    if terminal_state == "clean"
                    else (
                        "failed run contained no retrievable "
                        "failed jobs",
                    )
                ),
            )
        acquired: list[AcquiredLog] = []
        for job in jobs:
            acquired.append(
                await self._provider.retrieve_failed_log(
                    repository=repository,
                    run_id=run_id,
                    job=job,
                )
            )
        evidence = tuple(
            sorted(
                (
                    item.evidence
                    for item in acquired
                ),
                key=lambda item: (
                    item.run_id,
                    item.job_id,
                    item.evidence_id,
                ),
            )
        )
        complete_count = sum(
            item.log_completeness == "complete"
            for item in evidence
        )
        all_complete = complete_count == len(jobs)
        limitations = sorted(
            {
                limitation
                for item in evidence
                for limitation in item.limitations
            }
        )
        if not all_complete:
            limitations.append(
                "one or more failed jobs lack complete logs"
            )
        completed_at = self._clock()
        return AcquisitionReport(
            acquisition_id=namespaced_identity(
                "acquisition_",
                {
                    "repository": repository,
                    "run_id": run_id,
                    "evidence_ids": [
                        item.evidence_id
                        for item in evidence
                    ],
                },
            ),
            provider=run.provider,
            repository=repository,
            run_id=run_id,
            run_status=run.status,
            run_conclusion=run.conclusion,
            failed_job_count=len(jobs),
            evidence=evidence,
            total_raw_bytes=sum(
                item.provenance.raw_byte_count
                for item in acquired
            ),
            terminal_state=(
                "evidence_ready"
                if all_complete
                else "insufficient_log_evidence"
            ),
            started_at=started_at,
            completed_at=completed_at,
            limitations=tuple(sorted(set(limitations))),
        )
EOF
###############################################################################
# 4. GitHub provider
###############################################################################
cat > src/l9_debt_resolver/providers/__init__.py <<'EOF'
"""CI provider adapters."""
EOF
cat > src/l9_debt_resolver/providers/github/__init__.py <<'EOF'
"""GitHub Actions provider adapter."""
EOF
cat > src/l9_debt_resolver/providers/github/transport.py <<'EOF'
from __future__ import annotations
import asyncio
from dataclasses import dataclass
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
)
from l9_debt_resolver.acquisition.errors import (
    AuthenticationError,
    AuthorizationError,
    RemoteResponseError,
)
from l9_debt_resolver.acquisition.retry import (
    RetrySignal,
    with_retry,
)
@dataclass(frozen=True)
class HTTPResponse:
    status: int
    headers: dict[str, str]
    body: bytes
class GitHubTransport:
    def __init__(
        self,
        *,
        token: str,
        config: AcquisitionConfig,
        base_url: str = "https://api.github.com",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not token.strip():
            raise AuthenticationError(
                "GitHub token is required"
            )
        self._token = token
        self._config = config
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
    async def get_json(
        self,
        path: str,
    ) -> tuple[dict[str, Any], HTTPResponse]:
        response = await self.get_bytes(
            path,
            accept="application/vnd.github+json",
        )
        try:
            document = json.loads(
                response.body.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RemoteResponseError(
                "GitHub returned invalid JSON"
            ) from error
        if not isinstance(document, dict):
            raise RemoteResponseError(
                "GitHub JSON response must be an object"
            )
        return document, response
    async def get_bytes(
        self,
        path: str,
        *,
        accept: str = "application/vnd.github+json",
    ) -> HTTPResponse:
        async def operation(attempt: int) -> HTTPResponse:
            del attempt
            return await asyncio.to_thread(
                self._request,
                path,
                accept,
            )
        try:
            return await with_retry(
                operation,
                policy=self._config.retry,
            )
        except RetrySignal as signal:
            raise RemoteResponseError(
                f"GitHub returned HTTP {signal.status}"
            ) from signal
    def _request(
        self,
        path: str,
        accept: str,
    ) -> HTTPResponse:
        request = Request(
            self._base_url + path,
            method="GET",
            headers={
                "Accept": accept,
                "Authorization": f"Bearer {self._token}",
                "User-Agent": self._config.user_agent,
                "X-GitHub-Api-Version": (
                    self._config.api_version
                ),
            },
        )
        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                return HTTPResponse(
                    status=int(response.status),
                    headers={
                        key.casefold(): value
                        for key, value in response.headers.items()
                    },
                    body=response.read(),
                )
        except HTTPError as error:
            status = int(error.code)
            if status == 401:
                raise AuthenticationError(
                    "GitHub authentication failed"
                ) from error
            if status in {403, 404}:
                raise AuthorizationError(
                    "GitHub denied access or the resource "
                    "does not exist"
                ) from error
            retry_after = error.headers.get("Retry-After")
            if status in self._config.retry.retryable_statuses:
                raise RetrySignal(
                    status=status,
                    retry_after=retry_after,
                ) from error
            body = error.read(4096).decode(
                "utf-8",
                errors="replace",
            )
            raise RemoteResponseError(
                f"GitHub returned HTTP {status}: {body}"
            ) from error
        except URLError as error:
            raise RetrySignal(status=503) from error
EOF
cat > src/l9_debt_resolver/providers/github/parser.py <<'EOF'
from __future__ import annotations
from typing import Any
from l9_debt_resolver.acquisition.errors import (
    RemoteResponseError,
)
from l9_debt_resolver.acquisition.models import (
    FailedJob,
    FailedRun,
    FailedStep,
)
_FAILED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
}
def parse_run(
    document: dict[str, Any],
    *,
    repository: str,
) -> FailedRun:
    run_id = document.get("id")
    status = document.get("status")
    head_sha = document.get("head_sha")
    event = document.get("event")
    if run_id is None or not isinstance(status, str):
        raise RemoteResponseError(
            "GitHub run metadata is incomplete"
        )
    if not isinstance(head_sha, str) or not head_sha:
        raise RemoteResponseError(
            "GitHub run lacks a head SHA"
        )
    if not isinstance(event, str) or not event:
        raise RemoteResponseError(
            "GitHub run lacks an event"
        )
    conclusion = document.get("conclusion")
    if conclusion is not None and not isinstance(
        conclusion,
        str,
    ):
        raise RemoteResponseError(
            "GitHub run conclusion is invalid"
        )
    workflow_id = document.get("workflow_id")
    return FailedRun(
        provider="github_actions",
        repository=repository,
        run_id=str(run_id),
        status=status,
        conclusion=conclusion,
        head_sha=head_sha,
        event=event,
        workflow_id=(
            str(workflow_id)
            if workflow_id is not None
            else None
        ),
        created_at=_optional_string(
            document.get("created_at")
        ),
        updated_at=_optional_string(
            document.get("updated_at")
        ),
    )
def parse_failed_jobs(
    document: dict[str, Any],
    *,
    run_id: str,
) -> tuple[FailedJob, ...]:
    jobs = document.get("jobs")
    if not isinstance(jobs, list):
        raise RemoteResponseError(
            "GitHub jobs response lacks jobs"
        )
    parsed: list[FailedJob] = []
    for item in jobs:
        if not isinstance(item, dict):
            raise RemoteResponseError(
                "GitHub returned an invalid job"
            )
        conclusion = item.get("conclusion")
        if conclusion not in _FAILED_CONCLUSIONS:
            continue
        job_id = item.get("id")
        name = item.get("name")
        status = item.get("status")
        if (
            job_id is None
            or not isinstance(name, str)
            or not isinstance(status, str)
        ):
            raise RemoteResponseError(
                "GitHub failed-job metadata is incomplete"
            )
        steps_value = item.get("steps", [])
        failed_steps: list[FailedStep] = []
        if not isinstance(steps_value, list):
            raise RemoteResponseError(
                "GitHub job steps are invalid"
            )
        for step in steps_value:
            if not isinstance(step, dict):
                continue
            step_conclusion = step.get("conclusion")
            if step_conclusion not in _FAILED_CONCLUSIONS:
                continue
            number = step.get("number", 0)
            step_name = step.get("name", "")
            failed_steps.append(
                FailedStep(
                    number=(
                        int(number)
                        if isinstance(number, int)
                        else 0
                    ),
                    name=(
                        step_name
                        if isinstance(step_name, str)
                        else ""
                    ),
                    conclusion=str(step_conclusion),
                )
            )
        labels = item.get("labels", [])
        parsed.append(
            FailedJob(
                provider="github_actions",
                run_id=run_id,
                job_id=str(job_id),
                name=name,
                status=status,
                conclusion=str(conclusion),
                started_at=_optional_string(
                    item.get("started_at")
                ),
                completed_at=_optional_string(
                    item.get("completed_at")
                ),
                runner_name=_optional_string(
                    item.get("runner_name")
                ),
                labels=tuple(
                    sorted(
                        {
                            label
                            for label in labels
                            if isinstance(label, str)
                        }
                    )
                ),
                failed_steps=tuple(
                    sorted(
                        failed_steps,
                        key=lambda step: (
                            step.number,
                            step.name,
                        ),
                    )
                ),
            )
        )
    return tuple(
        sorted(
            parsed,
            key=lambda job: (
                job.name,
                job.job_id,
            ),
        )
    )
def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None
EOF
cat > src/l9_debt_resolver/providers/github/provider.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import os
from typing import Any
from urllib.parse import quote
from l9_debt_resolver.acquisition.completeness import (
    assess_log_completeness,
)
from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
)
from l9_debt_resolver.acquisition.errors import (
    JobLimitError,
    LogSizeLimitError,
    PaginationLimitError,
    RemoteResponseError,
)
from l9_debt_resolver.acquisition.models import (
    AcquiredLog,
    FailedJob,
    FailedRun,
    LogProvenance,
)
from l9_debt_resolver.acquisition.redaction import (
    LogRedactor,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.contracts.models import CIRunEvidence
from .parser import parse_failed_jobs, parse_run
from .transport import GitHubTransport
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
class GitHubActionsProvider:
    def __init__(
        self,
        *,
        token: str,
        config: AcquisitionConfig | None = None,
        repository_root: str | None = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        self._config = config or AcquisitionConfig()
        self._transport = GitHubTransport(
            token=token,
            config=self._config,
            base_url=base_url,
        )
        self._redactor = LogRedactor(repository_root)
    @classmethod
    def from_environment(
        cls,
        *,
        config: AcquisitionConfig | None = None,
        repository_root: str | None = None,
        base_url: str = "https://api.github.com",
    ) -> "GitHubActionsProvider":
        token = (
            os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
            or ""
        )
        return cls(
            token=token,
            config=config,
            repository_root=repository_root,
            base_url=base_url,
        )
    async def identify_failed_run(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> FailedRun:
        owner, name = _repository_parts(repository)
        document, _ = await self._transport.get_json(
            f"/repos/{quote(owner)}/{quote(name)}"
            f"/actions/runs/{quote(run_id)}"
        )
        return parse_run(
            document,
            repository=repository,
        )
    async def retrieve_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> tuple[FailedJob, ...]:
        owner, name = _repository_parts(repository)
        jobs: list[FailedJob] = []
        for page in range(
            1,
            self._config.limits.maximum_pages + 1,
        ):
            document, _ = await self._transport.get_json(
                f"/repos/{quote(owner)}/{quote(name)}"
                f"/actions/runs/{quote(run_id)}/jobs"
                f"?filter=latest"
                f"&per_page={self._config.limits.page_size}"
                f"&page={page}"
            )
            page_jobs = parse_failed_jobs(
                document,
                run_id=run_id,
            )
            jobs.extend(page_jobs)
            if (
                len(jobs)
                > self._config.limits.maximum_jobs_per_run
            ):
                raise JobLimitError(
                    "run exceeded the configured job limit"
                )
            raw_jobs = document.get("jobs")
            if not isinstance(raw_jobs, list):
                raise RemoteResponseError(
                    "GitHub jobs page is invalid"
                )
            if (
                len(raw_jobs)
                < self._config.limits.page_size
            ):
                break
        else:
            raise PaginationLimitError(
                "GitHub jobs pagination exceeded "
                "the configured page limit"
            )
        unique = {
            job.job_id: job
            for job in jobs
        }
        return tuple(
            sorted(
                unique.values(),
                key=lambda job: (
                    job.name,
                    job.job_id,
                ),
            )
        )
    async def retrieve_failed_log(
        self,
        *,
        repository: str,
        run_id: str,
        job: FailedJob,
    ) -> AcquiredLog:
        owner, name = _repository_parts(repository)
        response = await self._transport.get_bytes(
            f"/repos/{quote(owner)}/{quote(name)}"
            f"/actions/jobs/{quote(job.job_id)}/logs",
            accept="application/vnd.github+json",
        )
        raw = response.body
        limit = (
            self._config.limits.maximum_log_bytes_per_job
        )
        exceeded_limit = len(raw) > limit
        if exceeded_limit:
            raw = raw[:limit]
        content_length = _content_length(
            response.headers.get("content-length")
        )
        assessment = assess_log_completeness(
            raw=raw,
            content_length=content_length,
            exceeded_limit=exceeded_limit,
            download_complete=True,
        )
        decoded = raw.decode(
            "utf-8",
            errors="replace",
        )
        redaction = self._redactor.redact(decoded)
        redacted_bytes = redaction.text.encode("utf-8")
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        redacted_sha256 = hashlib.sha256(
            redacted_bytes
        ).hexdigest()
        retrieved_at = utc_now()
        retrieval_material: dict[str, Any] = {
            "provider": "github_actions",
            "repository": repository,
            "run_id": run_id,
            "job_id": job.job_id,
            "raw_sha256": raw_sha256,
            "retrieved_at": retrieved_at,
        }
        retrieval_id = namespaced_identity(
            "retrieval_",
            retrieval_material,
        )
        limitations = tuple(
            sorted(
                {
                    *assessment.limitations,
                    *(
                        (
                            "log redaction classes: "
                            + ",".join(redaction.classes),
                        )
                        if redaction.classes
                        else ()
                    ),
                }
            )
        )
        provenance = LogProvenance(
            provider="github_actions",
            api_version=self._config.api_version,
            repository=repository,
            run_id=run_id,
            job_id=job.job_id,
            retrieval_id=retrieval_id,
            retrieved_at=retrieved_at,
            etag=response.headers.get("etag"),
            content_length=content_length,
            content_type=response.headers.get(
                "content-type"
            ),
            raw_sha256=raw_sha256,
            redacted_sha256=redacted_sha256,
            raw_byte_count=len(raw),
            redacted_byte_count=len(redacted_bytes),
            completeness=assessment.state,
            limitations=limitations,
        )
        failed_command = (
            job.failed_steps[0].name
            if job.failed_steps
            else None
        )
        evidence_material = {
            "provider": "github_actions",
            "run_id": run_id,
            "job_id": job.job_id,
            "raw_sha256": raw_sha256,
            "completeness": assessment.state,
        }
        evidence = CIRunEvidence(
            evidence_id=namespaced_identity(
                "evidence_",
                evidence_material,
            ),
            provider="github_actions",
            run_id=run_id,
            job_id=job.job_id,
            job_name=job.name,
            failed_command=failed_command,
            conclusion=_normalize_conclusion(
                job.conclusion
            ),
            log_sha256=raw_sha256,
            log_size_bytes=len(raw),
            log_completeness=assessment.state,
            authority_class="RUNTIME_LOG",
            artifact_provenance={
                "source": (
                    "github_actions_job_log"
                ),
                "retrieval_id": retrieval_id,
                "retrieved_at": retrieved_at,
            },
            observed_at=retrieved_at,
            limitations=limitations,
        )
        return AcquiredLog(
            evidence=evidence,
            provenance=provenance,
            redacted_text=redaction.text,
        )
def _repository_parts(
    repository: str,
) -> tuple[str, str]:
    parts = repository.split("/")
    if (
        len(parts) != 2
        or not parts[0]
        or not parts[1]
    ):
        raise ValueError(
            "repository must use owner/name format"
        )
    return parts[0], parts[1]
def _content_length(
    value: str | None,
) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None
def _normalize_conclusion(
    value: str,
) -> str:
    allowed = {
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
    }
    return value if value in allowed else "unknown"
EOF
###############################################################################
# 5. Safe artifact persistence
###############################################################################
cat > src/l9_debt_resolver/acquisition/store.py <<'EOF'
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from .models import AcquiredLog, AcquisitionReport
class AcquisitionArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root
    def persist(
        self,
        *,
        report: AcquisitionReport,
        logs: tuple[AcquiredLog, ...] = (),
    ) -> Path:
        destination = (
            self._root
            / report.acquisition_id
        )
        destination.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )
        _atomic_json(
            destination / "report.json",
            report.as_dict(),
        )
        for log in logs:
            job_root = (
                destination
                / "jobs"
                / log.evidence.job_id
            )
            job_root.mkdir(
                parents=True,
                exist_ok=True,
                mode=0o700,
            )
            _atomic_json(
                job_root / "evidence.json",
                log.evidence.as_dict(),
            )
            _atomic_json(
                job_root / "provenance.json",
                log.provenance.as_dict(),
            )
            _atomic_text(
                job_root / "redacted.log",
                log.redacted_text,
            )
        return destination
def _atomic_json(
    path: Path,
    value: Any,
) -> None:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    _atomic_text(path, text)
def _atomic_text(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
EOF
###############################################################################
# 6. Runtime capabilities
###############################################################################
cat > src/l9_debt_resolver/runtime/capabilities.py <<'EOF'
from __future__ import annotations
from typing import Any
def resolver_capabilities() -> dict[str, Any]:
    return {
        "schema_version": "l9.resolver-capabilities/v1",
        "phase": "RESOLVER-P1",
        "capabilities": {
            "contract_validation": True,
            "typed_CI_evidence": True,
            "attempt_lifecycle": True,
            "terminal_states": True,
            "corpus_safe_events": True,
            "failed_run_acquisition": True,
            "failed_job_acquisition": True,
            "failed_log_acquisition": True,
            "pagination": True,
            "bounded_retries": True,
            "retry_after": True,
            "truncation_detection": True,
            "artifact_provenance": True,
            "secret_redaction": True,
            "path_redaction": True,
            "corpus_log_exclusion": True,
            "SDK_repository_correlation": False,
            "root_cause_classification": False,
            "bounded_remediation": False,
            "SDK_validation_execution": False,
            "branch_mutation": False,
            "CI_rerun_observation": False
        },
        "limitations": [
            "Repository correlation begins in RESOLVER-P2.",
            "Root-cause classification begins in RESOLVER-P2.",
            "Bounded remediation begins in RESOLVER-P3.",
            "Remote branch interaction begins in RESOLVER-P4.",
            "CI rerun observation begins in RESOLVER-P4."
        ]
    }
EOF
###############################################################################
# 7. CLI
###############################################################################
cat > src/l9_debt_resolver/cli.py <<'EOF'
from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
from .acquisition.service import (
    FailedLogAcquisitionService,
)
from .contracts.schema import SchemaValidator
from .providers.github.provider import (
    GitHubActionsProvider,
)
from .runtime.capabilities import resolver_capabilities
def emit(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
def schema_root() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "resolver"
    )
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="l9-debt-resolver"
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )
    commands.add_parser("capabilities")
    validate = commands.add_parser("validate")
    validate.add_argument(
        "schema",
        choices=[
            "ci-run-evidence",
            "ci-failure-classification",
            "resolver-attempt",
            "resolver-terminal-state",
            "remediation-record",
            "resolution-event",
            "failed-run-reference",
            "failed-job",
            "log-provenance",
            "acquisition-report",
        ],
    )
    validate.add_argument("document", type=Path)
    acquire = commands.add_parser(
        "acquire-github-run"
    )
    acquire.add_argument(
        "--repository",
        required=True,
        help="GitHub owner/name repository",
    )
    acquire.add_argument(
        "--run-id",
        required=True,
    )
    acquire.add_argument(
        "--repository-root",
        default=None,
        help=(
            "Optional checkout root to redact from logs"
        ),
    )
    acquire.add_argument(
        "--api-url",
        default="https://api.github.com",
    )
    return parser
async def acquire_github_run(
    *,
    repository: str,
    run_id: str,
    repository_root: str | None,
    api_url: str,
) -> dict[str, Any]:
    provider = GitHubActionsProvider.from_environment(
        repository_root=repository_root,
        base_url=api_url,
    )
    service = FailedLogAcquisitionService(provider)
    report = await service.acquire(
        repository=repository,
        run_id=run_id,
    )
    return report.as_dict()
def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "capabilities":
        emit(resolver_capabilities())
        return 0
    if arguments.command == "acquire-github-run":
        report = asyncio.run(
            acquire_github_run(
                repository=arguments.repository,
                run_id=arguments.run_id,
                repository_root=(
                    arguments.repository_root
                ),
                api_url=arguments.api_url,
            )
        )
        emit(report)
        terminal = report["terminal_state"]
        return 0 if terminal in {
            "evidence_ready",
            "clean",
        } else 2
    schema_path = (
        schema_root()
        / f"{arguments.schema}.schema.json"
    )
    document = json.loads(
        arguments.document.read_text(
            encoding="utf-8"
        )
    )
    SchemaValidator(schema_path).validate(document)
    emit(
        {
            "schema_version": (
                "l9.resolver-contract-validation/v1"
            ),
            "status": "valid",
            "schema": arguments.schema,
        }
    )
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
EOF
###############################################################################
# 8. Version
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("pyproject.toml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    'version = "0.1.0"',
    'version = "0.2.0"',
)
path.write_text(content, encoding="utf-8")
init = Path("src/l9_debt_resolver/__init__.py")
content = init.read_text(encoding="utf-8")
content = content.replace(
    '__version__ = "0.1.0"',
    '__version__ = "0.2.0"',
)
init.write_text(content, encoding="utf-8")
PY
###############################################################################
# 9. Tests
###############################################################################
cat > tests/acquisition/test_completeness.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.acquisition.completeness import (
    assess_log_completeness,
)
def test_complete_log_requires_terminal_marker() -> None:
    result = assess_log_completeness(
        raw=(
            b"tests failed\n"
            b"Error: Process completed with exit code 1.\n"
        ),
        content_length=None,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "complete"
def test_empty_log_is_unavailable() -> None:
    result = assess_log_completeness(
        raw=b"",
        content_length=0,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "unavailable"
def test_explicit_marker_is_truncated() -> None:
    result = assess_log_completeness(
        raw=b"log output truncated\n",
        content_length=None,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "truncated"
def test_content_length_mismatch_is_truncated() -> None:
    result = assess_log_completeness(
        raw=b"short",
        content_length=100,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "truncated"
def test_missing_terminal_marker_is_uncertain() -> None:
    result = assess_log_completeness(
        raw=b"failure happened",
        content_length=None,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "possibly_truncated"
EOF
cat > tests/privacy/test_log_redaction.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.acquisition.redaction import (
    LogRedactor,
)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "[REDACTED:BEARER_TOKEN]",
        ),
        (
            "token=github_pat_abcdefghijklmnopqrstuvwxyz123456",
            "[REDACTED:GITHUB_TOKEN]",
        ),
        (
            "email alice@example.com",
            "[REDACTED:EMAIL]",
        ),
        (
            "failed at /home/alice/repository/file.py",
            "[REDACTED:UNIX_PATH]",
        ),
        (
            r"failed at C:\Users\alice\repository\file.py",
            "[REDACTED:WINDOWS_PATH]",
        ),
    ],
)
def test_sensitive_content_is_redacted(
    raw: str,
    expected: str,
) -> None:
    result = LogRedactor().redact(raw)
    assert expected in result.text
    assert raw != result.text
def test_repository_root_is_redacted() -> None:
    result = LogRedactor(
        "/workspace/project"
    ).redact(
        "/workspace/project/src/module.py failed"
    )
    assert "/workspace/project" not in result.text
    assert "[REDACTED:REPOSITORY_ROOT]" in result.text
EOF
cat > tests/resilience/test_retry.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.acquisition.config import (
    RetryPolicy,
)
from l9_debt_resolver.acquisition.errors import (
    RetryExhaustedError,
)
from l9_debt_resolver.acquisition.retry import (
    RetrySignal,
    with_retry,
)
@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failure() -> None:
    attempts = 0
    sleeps: list[float] = []
    async def operation(attempt: int) -> str:
        nonlocal attempts
        attempts = attempt
        if attempt < 3:
            raise RetrySignal(status=503)
        return "ok"
    async def sleep(value: float) -> None:
        sleeps.append(value)
    result = await with_retry(
        operation,
        policy=RetryPolicy(
            maximum_attempts=4,
            initial_backoff_seconds=0.1,
            maximum_backoff_seconds=1,
        ),
        sleep=sleep,
    )
    assert result == "ok"
    assert attempts == 3
    assert sleeps == [0.1, 0.2]
@pytest.mark.asyncio
async def test_retry_is_bounded() -> None:
    async def operation(attempt: int) -> str:
        del attempt
        raise RetrySignal(status=503)
    async def sleep(value: float) -> None:
        del value
    with pytest.raises(RetryExhaustedError):
        await with_retry(
            operation,
            policy=RetryPolicy(
                maximum_attempts=2,
                initial_backoff_seconds=0,
                maximum_backoff_seconds=0,
            ),
            sleep=sleep,
        )
EOF
cat > tests/providers/github/test_parser.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.providers.github.parser import (
    parse_failed_jobs,
    parse_run,
)
def test_parse_run() -> None:
    run = parse_run(
        {
            "id": 100,
            "status": "completed",
            "conclusion": "failure",
            "head_sha": "a" * 40,
            "event": "pull_request",
            "workflow_id": 10,
            "created_at": "2026-07-18T00:00:00Z",
            "updated_at": "2026-07-18T00:01:00Z",
        },
        repository="Quantum-L9/example",
    )
    assert run.run_id == "100"
    assert run.conclusion == "failure"
def test_only_failed_jobs_are_returned() -> None:
    jobs = parse_failed_jobs(
        {
            "jobs": [
                {
                    "id": 1,
                    "name": "passing",
                    "status": "completed",
                    "conclusion": "success",
                    "steps": [],
                    "labels": ["ubuntu-latest"],
                },
                {
                    "id": 2,
                    "name": "failing",
                    "status": "completed",
                    "conclusion": "failure",
                    "steps": [
                        {
                            "number": 1,
                            "name": "pytest",
                            "conclusion": "failure",
                        }
                    ],
                    "labels": ["ubuntu-latest"],
                },
            ]
        },
        run_id="100",
    )
    assert len(jobs) == 1
    assert jobs[0].job_id == "2"
    assert jobs[0].failed_steps[0].name == "pytest"
EOF
cat > tests/acquisition/test_service.py <<'EOF'
from __future__ import annotations
import hashlib
import pytest
from l9_debt_resolver.acquisition.models import (
    AcquiredLog,
    FailedJob,
    FailedRun,
    FailedStep,
    LogProvenance,
)
from l9_debt_resolver.acquisition.service import (
    FailedLogAcquisitionService,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)
class Provider:
    def __init__(self, completeness: str) -> None:
        self.completeness = completeness
    async def identify_failed_run(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> FailedRun:
        return FailedRun(
            provider="github_actions",
            repository=repository,
            run_id=run_id,
            status="completed",
            conclusion="failure",
            head_sha="a" * 40,
            event="pull_request",
            workflow_id="10",
            created_at=None,
            updated_at=None,
        )
    async def retrieve_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> tuple[FailedJob, ...]:
        del repository
        return (
            FailedJob(
                provider="github_actions",
                run_id=run_id,
                job_id="200",
                name="test",
                status="completed",
                conclusion="failure",
                started_at=None,
                completed_at=None,
                runner_name=None,
                labels=(),
                failed_steps=(
                    FailedStep(
                        number=1,
                        name="pytest",
                        conclusion="failure",
                    ),
                ),
            ),
        )
    async def retrieve_failed_log(
        self,
        *,
        repository: str,
        run_id: str,
        job: FailedJob,
    ) -> AcquiredLog:
        raw_hash = hashlib.sha256(b"log").hexdigest()
        evidence = CIRunEvidence(
            evidence_id="evidence_" + "a" * 64,
            provider="github_actions",
            run_id=run_id,
            job_id=job.job_id,
            job_name=job.name,
            failed_command="pytest",
            conclusion="failure",
            log_sha256=raw_hash,
            log_size_bytes=3,
            log_completeness=self.completeness,
            authority_class="RUNTIME_LOG",
            artifact_provenance={
                "source": "github_actions_job_log",
                "retrieval_id": (
                    "retrieval_" + "b" * 64
                ),
                "retrieved_at": (
                    "2026-07-18T00:00:00Z"
                ),
            },
            observed_at="2026-07-18T00:00:00Z",
            limitations=(),
        )
        provenance = LogProvenance(
            provider="github_actions",
            api_version="2022-11-28",
            repository=repository,
            run_id=run_id,
            job_id=job.job_id,
            retrieval_id="retrieval_" + "b" * 64,
            retrieved_at="2026-07-18T00:00:00Z",
            etag=None,
            content_length=3,
            content_type="text/plain",
            raw_sha256=raw_hash,
            redacted_sha256=raw_hash,
            raw_byte_count=3,
            redacted_byte_count=3,
            completeness=self.completeness,
            limitations=(),
        )
        return AcquiredLog(
            evidence=evidence,
            provenance=provenance,
            redacted_text="log",
        )
@pytest.mark.asyncio
async def test_complete_evidence_is_ready() -> None:
    service = FailedLogAcquisitionService(
        Provider("complete"),
        clock=lambda: "2026-07-18T00:00:00Z",
    )
    report = await service.acquire(
        repository="Quantum-L9/example",
        run_id="100",
    )
    assert report.terminal_state == "evidence_ready"
@pytest.mark.asyncio
async def test_incomplete_evidence_fails_closed() -> None:
    service = FailedLogAcquisitionService(
        Provider("truncated"),
        clock=lambda: "2026-07-18T00:00:00Z",
    )
    report = await service.acquire(
        repository="Quantum-L9/example",
        run_id="100",
    )
    assert (
        report.terminal_state
        == "insufficient_log_evidence"
    )
EOF
cat > tests/architecture/test_log_privacy_boundary.py <<'EOF'
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
ALLOWED_RAW_LOG_MODULES = {
    (
        SOURCE
        / "acquisition"
        / "redaction.py"
    ).resolve(),
    (
        SOURCE
        / "providers"
        / "github"
        / "provider.py"
    ).resolve(),
}
PROHIBITED_PERSISTENCE_TERMS = (
    "raw.log",
    "unredacted.log",
    "raw_log_path",
    "persist_raw_log",
)
def test_raw_log_persistence_is_absent() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED_PERSISTENCE_TERMS:
            assert term not in content, (
                f"{path} contains prohibited raw-log "
                f"persistence term {term}"
            )
def test_store_only_persists_redacted_log() -> None:
    path = (
        SOURCE
        / "acquisition"
        / "store.py"
    )
    content = path.read_text(encoding="utf-8")
    assert '"redacted.log"' in content
    assert '"raw.log"' not in content
EOF
###############################################################################
# 10. Test dependencies
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("pyproject.toml")
content = path.read_text(encoding="utf-8")
if '"pytest-asyncio' not in content:
    content = content.replace(
        '  "pytest-cov>=5,<7",',
        '  "pytest-cov>=5,<7",\n'
        '  "pytest-asyncio>=0.24,<1",',
    )
content = content.replace(
    'addopts = "-ra --strict-markers"',
    'addopts = "-ra --strict-markers"\n'
    'asyncio_mode = "strict"',
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 11. Documentation
###############################################################################
cat > docs/architecture/ADRs/ADR-RESOLVER-006-direct-provider-log-acquisition.md <<'EOF'
# ADR-RESOLVER-006: Failed logs are acquired through provider APIs
- Status: Accepted
- Phase: RESOLVER-P1
## Decision
The resolver uses explicit CI-provider API contracts for failed-run metadata,
failed-job discovery, and individual job-log retrieval.
Human-oriented CLI output is not treated as a canonical machine contract.
## Consequences
- provider metadata remains structured;
- pagination is explicit;
- retries are bounded;
- provenance includes API response metadata;
- each failed job receives an independently verifiable evidence record.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-007-incomplete-logs-fail-closed.md <<'EOF'
# ADR-RESOLVER-007: Missing and incomplete logs fail closed
- Status: Accepted
- Phase: RESOLVER-P1
## Decision
A failed job without a complete failed log produces
`insufficient_log_evidence`.
It cannot authorize classification-driven remediation.
## Rationale
A partial log may omit the originating command, first failure, stack trace,
compiler context, or provider termination marker.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-008-raw-logs-are-ephemeral.md <<'EOF'
# ADR-RESOLVER-008: Raw CI logs are ephemeral
- Status: Accepted
- Phase: RESOLVER-P1
## Decision
Raw failed logs exist only in bounded acquisition memory.
Only redacted logs, hashes, typed evidence, and provenance may be persisted.
## Excluded data
- credentials;
- tokens;
- private keys;
- email addresses;
- absolute paths;
- repository checkout roots.
EOF
cat >> README.md <<'EOF'
## RESOLVER-P1: failed-log acquisition
The resolver now retrieves:
# 1. workflow-run metadata;
# 2. all failed jobs using bounded pagination;
# 3. each failed job log independently;
# 4. response provenance and content hashes;
# 5. a completeness assessment;
# 6. redacted evidence suitable for local persistence.
```text
GitHub Actions
      ↓
run metadata
      ↓
failed jobs
      ↓
per-job logs
      ↓
size and completeness checks
      ↓
secret and path redaction
      ↓
typed CI evidence
      ↓
evidence_ready
or
insufficient_log_evidence

Authentication

Set one of:

export GITHUB_TOKEN='...'
export GH_TOKEN='...'

Tokens are read from the environment and are never persisted.

Acquire one run

l9-debt-resolver acquire-github-run \
  --repository Quantum-L9/example \
  --run-id 123456789

Exit codes:

* 0: evidence is ready or the run is clean;
* 2: evidence is incomplete and remediation is prohibited;
* nonzero exception: provider or contract failure.

Privacy

Raw logs are ephemeral. The resolver may persist only:

* redacted logs;
* SHA-256 hashes;
* typed evidence;
* provenance;
* completeness limitations.

It does not persist unredacted CI logs.
EOF

python3 - <<'PY'
from pathlib import Path

path = Path("ROADMAP.md")
content = path.read_text(encoding="utf-8")

content = content.replace(
"""## RESOLVER-P1 - Log acquisition

Status: Planned

* GitHub failed-run discovery
* complete failed-job retrieval
* complete failed-log retrieval
* truncation detection
* artifact provenance
* secret and path redaction
* acquisition retry policy""",
    """## RESOLVER-P1 - Log acquisition

Status: Implemented

* GitHub failed-run discovery
* complete failed-job retrieval
* complete failed-log retrieval
* bounded pagination
* bounded retries
* Retry-After handling
* truncation detection
* artifact provenance
* deterministic evidence identity
* secret and path redaction
* fail-closed incomplete evidence""",
    )

path.write_text(content, encoding="utf-8")
PY

###############################################################################

# 12. Update repository specification

###############################################################################

python3 - <<'PY'
from pathlib import Path

path = Path(".l9/repo-spec.yaml")
content = path.read_text(encoding="utf-8")

content = content.replace(
"phase: RESOLVER-P0",
"phase: RESOLVER-P1",
1,
)

content = content.replace(
"phase_name: contract_alignment",
"phase_name: log_acquisition",
1,
)

content = content.replace(
"""  - phase: RESOLVER-P1
name: log_acquisition
priority: critical
status: planned""",
"""  - phase: RESOLVER-P1
name: log_acquisition
priority: critical
status: implemented""",
)

path.write_text(content, encoding="utf-8")
PY

###############################################################################

# 13. CI

###############################################################################

cat > .github/workflows/phase-1-log-acquisition.yml <<'EOF'
name: RESOLVER-P1 Log Acquisition

on:
pull_request:
push:
branches:
- main

permissions:
contents: read

jobs:
log-acquisition:
runs-on: ubuntu-latest
timeout-minutes: 15

steps:
  - name: Checkout
    uses: actions/checkout@v4
  - name: Python
    uses: actions/setup-python@v5
    with:
      python-version: "3.11"
      cache: pip
  - name: Install
    run: |
      python -m pip install --upgrade pip
      python -m pip install -e '.[dev]'
  - name: Validate schemas
    run: |
      python - <<'PY'
      import json
      from pathlib import Path
      from jsonschema import Draft202012Validator
      for path in sorted(
          Path("schemas/resolver").glob("*.json")
      ):
          schema = json.loads(
              path.read_text(encoding="utf-8")
          )
          Draft202012Validator.check_schema(schema)
          print(path)
PY
  - name: Acquisition tests
    run: pytest tests/acquisition
  - name: Provider tests
    run: pytest tests/providers
  - name: Privacy tests
    run: pytest tests/privacy
  - name: Resilience tests
    run: pytest tests/resilience
  - name: Architecture tests
    run: pytest tests/architecture
  - name: Full suite
    run: |
      pytest \
        --cov=l9_debt_resolver \
        --cov-report=term-missing \
        --cov-fail-under=85
  - name: Ruff
    run: ruff check .
  - name: Mypy
    run: mypy src
  - name: Capabilities
    run: l9-debt-resolver capabilities
EOF
###############################################################################

# 14. Final acceptance gates

###############################################################################

cat > .l9/phase-1-acceptance-gates.yaml <<'EOF'
schema: l9.phase-acceptance-gates/v1

repository: Quantum-L9/l9-ci-debt-resolver
phase: RESOLVER-P1

gates:

  - id: p1-run-acquisition
    requirement: >
    Failed-run metadata is retrieved through the provider API.
  - id: p1-job-pagination
    requirement: >
    All failed jobs are retrieved with bounded explicit pagination.
  - id: p1-per-job-logs
    requirement: >
    Each failed job is assigned an independently retrieved log.
  - id: p1-log-hash
    requirement: >
    Every acquired log has a deterministic SHA-256 hash.
  - id: p1-provenance
    requirement: >
    Every log includes provider, run, job, retrieval, API, HTTP, hash,
    size, completeness, and limitation provenance.
  - id: p1-truncation
    requirement: >
    Size overflow, content-length mismatch, explicit markers, incomplete
    downloads, and missing terminal markers are visible.
  - id: p1-fail-closed
    requirement: >
    Any failed job without complete evidence produces
    insufficient_log_evidence.
  - id: p1-redaction
    requirement: >
    Credentials, private keys, email addresses, absolute paths, and checkout
    roots are removed before durable persistence.
  - id: p1-no-raw-persistence
    requirement: >
    No raw or unredacted log persistence path exists.
  - id: p1-retry-bounds
    requirement: >
    Provider retries are finite and honor bounded Retry-After values.
  - id: p1-no-remediation
    requirement: >
    RESOLVER-P1 does not mutate repositories or select remediation.
EOF
###############################################################################


printf "phase generation complete\n"
