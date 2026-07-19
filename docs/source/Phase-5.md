RESOLVER-P5 adds privacy-safe Intelligence feedback with deterministic event identities, idempotent delivery, bounded retries, durable outbox state, dead-letter handling, corpus-safe provenance, and repeated-failure telemetry. It does not transmit raw logs, source content, credentials, absolute paths, developer identity, or patch bodies.

Save as build-phase-5.sh and run after P4.

#!/usr/bin/env bash
set -euo pipefail
###############################################################################
# Quantum-L9/l9-ci-debt-resolver
# RESOLVER-P5 — Intelligence Feedback and Corpus-Safe Resolution Events
#
# Incremental build over RESOLVER-P0 through RESOLVER-P4.
#
# Implements:
#   - privacy-safe resolution-event envelopes
#   - repeated-failure telemetry
#   - deterministic event identities
#   - idempotency keys
#   - corpus-safe provenance
#   - bounded delivery retries
#   - Retry-After support
#   - durable local outbox
#   - dead-letter state
#   - delivery receipts
#   - JSON-file and HTTPS transports
#   - event validation and privacy gates
#   - P5 CLI commands
#   - architecture, privacy, retry, and idempotency tests
#
# Does not implement:
#   - Intelligence corpus mining                    (Intelligence-owned)
#   - prevention compilation                        (Core-owned)
#   - editor delivery                               (LSP-owned)
#   - speculative PR planning                       (PR_Repair-owned)
#   - PR_Repair delegation                          (RESOLVER-P6)
###############################################################################
fail() {
  printf 'RESOLVER-P5: %s\n' "$*" >&2
  exit 1
}
require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "required command not found: $1"
}
require_command python3
[[ -d .git ]] \
  || fail "run from the l9-ci-debt-resolver repository root"
[[ -f .l9/remote-resolution-contract.yaml ]] \
  || fail "RESOLVER-P4 remote-resolution contract is missing"
[[ -f src/l9_debt_resolver/runtime/remote_resolution_service.py ]] \
  || fail "RESOLVER-P4 runtime is missing"
mkdir -p \
  .github/workflows \
  .l9 \
  docs/architecture/ADRs \
  schemas/resolver \
  src/l9_debt_resolver/feedback \
  tests/feedback \
  tests/privacy \
  tests/resilience \
  tests/architecture
###############################################################################
# 1. Authoritative P5 contracts
###############################################################################
cat > .l9/intelligence-feedback-contract.yaml <<'EOF'
schema: l9.resolver-intelligence-feedback-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P5
  status: authoritative
ownership:
  resolver:
    owns:
      - resolution-event construction
      - repeated-failure telemetry
      - privacy validation
      - corpus-safe provenance
      - idempotent delivery
      - delivery retries
      - local outbox state
      - delivery receipts
  intelligence:
    owns:
      - event ingestion
      - corpus mining
      - recurrence analysis
      - remediation effectiveness analysis
      - pattern promotion
      - historical evidence retrieval
  resolver_must_not:
    - write directly to Intelligence storage internals
    - create Intelligence findings
    - create prevention artifacts
    - mine historical corpora
    - transmit raw CI logs
    - transmit source content
    - transmit patch content
event_types:
  - resolution_succeeded
  - repeated_failure
  - new_failure
  - attempt_limit_reached
  - remote_operation_failed
  - rerun_timeout
  - validation_failed
  - unsupported
event_identity:
  deterministic_inputs:
    - repository pseudonym
    - failure fingerprint
    - attempt number
    - terminal state
    - rerun identity
    - validation result identity
  excluded_inputs:
    - timestamps
    - credentials
    - raw logs
    - source content
    - developer identity
    - absolute paths
    - access tokens
    - authorization headers
privacy:
  allowed:
    - repository pseudonym
    - provider name
    - failure fingerprint
    - classification category
    - confidence bucket
    - remediation class
    - changed-file count
    - changed-line bucket
    - validation result state
    - validation duration bucket
    - terminal state
    - repeated-failure boolean
    - attempt number
    - SDK canonical finding IDs
    - SDK canonical contract IDs
    - capability profile
    - limitation codes
    - normalized language family
    - corpus-safe provenance hashes
  prohibited:
    - raw log lines
    - source code
    - patch body
    - diff body
    - absolute paths
    - repository-relative file paths
    - branch names
    - commit messages
    - developer names
    - developer email addresses
    - GitHub actor identity
    - IP addresses
    - environment variables
    - credentials
    - secrets
    - authorization tokens
    - URLs containing credentials
    - workflow input values
    - arbitrary provider payloads
repository_identity:
  transport_form: HMAC-SHA256 pseudonym
  raw_repository_name_transmission: prohibited
  secret_source: L9_FEEDBACK_PSEUDONYM_KEY
delivery:
  required:
    - event schema validation
    - privacy validation
    - deterministic event ID
    - deterministic idempotency key
    - durable outbox write before delivery
    - bounded retry
    - delivery receipt
    - dead-letter state after exhaustion
  retry:
    maximum_attempts: 5
    initial_delay_seconds: 1
    maximum_delay_seconds: 30
    exponential_multiplier: 2
    jitter: deterministic
    Retry-After: honored_when_bounded
  success_statuses:
    - 200
    - 201
    - 202
    - 204
    - 409
  retryable_statuses:
    - 408
    - 425
    - 429
    - 500
    - 502
    - 503
    - 504
  permanent_failure:
    - schema rejection
    - privacy rejection
    - authentication rejection
    - unsupported contract version
    - non-retryable HTTP response
outbox:
  states:
    - pending
    - delivering
    - delivered
    - dead_letter
  storage:
    permissions: owner_only
    atomic_writes: required
    raw_logs: prohibited
    source_content: prohibited
corpus_provenance:
  include:
    - event schema version
    - resolver version
    - SDK snapshot identity hash
    - validation result identity hash
    - failure fingerprint
    - evidence identity hashes
    - transport receipt identity
  exclude:
    - raw SDK snapshot content
    - raw evidence content
    - raw validation transcript output
EOF
cat > .l9/feedback-privacy-policy.yaml <<'EOF'
schema: l9.resolver-feedback-privacy-policy/v1
metadata:
  phase: RESOLVER-P5
  enforcement: fail_closed
forbidden_key_fragments:
  - token
  - secret
  - password
  - credential
  - authorization
  - cookie
  - source
  - patch
  - diff
  - log
  - stdout
  - stderr
  - branch
  - commit_message
  - actor
  - developer
  - email
  - absolute_path
  - repository_path
  - environment
forbidden_value_patterns:
  - bearer_token
  - github_token
  - AWS_access_key
  - private_key
  - email_address
  - IPv4_address
  - IPv6_address
  - URL_with_credentials
  - Unix_absolute_path
  - Windows_absolute_path
  - multiline_source_like_content
maximums:
  total_event_bytes: 65536
  string_length: 2000
  array_items: 500
  object_depth: 10
failure_behavior:
  event_construction: rejected
  outbox_write: prohibited
  delivery: prohibited
EOF
###############################################################################
# 2. P5 schemas
###############################################################################
cat > schemas/resolver/intelligence-feedback-event.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/intelligence-feedback-event/v1",
  "title": "L9 Resolver Intelligence Feedback Event",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "event_id",
    "idempotency_key",
    "event_type",
    "repository_pseudonym",
    "provider",
    "resolver_version",
    "occurred_at",
    "failure",
    "resolution",
    "validation",
    "correlation",
    "provenance",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.intelligence-feedback-event/v1"
    },
    "event_id": {
      "type": "string",
      "pattern": "^feedback_event_[0-9a-f]{64}$"
    },
    "idempotency_key": {
      "type": "string",
      "pattern": "^feedback_idempotency_[0-9a-f]{64}$"
    },
    "event_type": {
      "enum": [
        "resolution_succeeded",
        "repeated_failure",
        "new_failure",
        "attempt_limit_reached",
        "remote_operation_failed",
        "rerun_timeout",
        "validation_failed",
        "unsupported"
      ]
    },
    "repository_pseudonym": {
      "type": "string",
      "pattern": "^repository_[0-9a-f]{64}$"
    },
    "provider": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "resolver_version": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "occurred_at": {
      "type": "string",
      "format": "date-time"
    },
    "failure": {
      "$ref": "#/$defs/failure"
    },
    "resolution": {
      "$ref": "#/$defs/resolution"
    },
    "validation": {
      "$ref": "#/$defs/validation"
    },
    "correlation": {
      "$ref": "#/$defs/correlation"
    },
    "provenance": {
      "$ref": "#/$defs/provenance"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 500
      },
      "uniqueItems": true
    }
  },
  "$defs": {
    "failure": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "fingerprint",
        "category",
        "confidence_bucket",
        "repeated",
        "attempt_number",
        "observed_fingerprint_changed"
      ],
      "properties": {
        "fingerprint": {
          "type": "string",
          "pattern": "^failure_[0-9a-f]{64}$"
        },
        "category": {
          "type": "string",
          "maxLength": 100
        },
        "confidence_bucket": {
          "enum": [
            "low",
            "medium",
            "high",
            "very_high"
          ]
        },
        "repeated": {
          "type": "boolean"
        },
        "attempt_number": {
          "type": "integer",
          "minimum": 1
        },
        "observed_fingerprint_changed": {
          "type": [
            "boolean",
            "null"
          ]
        }
      }
    },
    "resolution": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "terminal_state",
        "remediation_class",
        "changed_file_count",
        "changed_line_bucket",
        "remote_push_performed",
        "rerun_observed"
      ],
      "properties": {
        "terminal_state": {
          "type": "string",
          "maxLength": 100
        },
        "remediation_class": {
          "type": [
            "string",
            "null"
          ],
          "maxLength": 100
        },
        "changed_file_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 1000
        },
        "changed_line_bucket": {
          "enum": [
            "0",
            "1_10",
            "11_50",
            "51_100",
            "101_250",
            "251_500",
            "gt_500",
            "unknown"
          ]
        },
        "remote_push_performed": {
          "type": "boolean"
        },
        "rerun_observed": {
          "type": "boolean"
        }
      }
    },
    "validation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "result",
        "result_id_hash",
        "step_count",
        "duration_bucket",
        "graph_delta_accepted"
      ],
      "properties": {
        "result": {
          "enum": [
            "passed",
            "failed",
            "unavailable",
            "incomplete",
            "not_run"
          ]
        },
        "result_id_hash": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "step_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 1000
        },
        "duration_bucket": {
          "enum": [
            "lt_1s",
            "1_10s",
            "10_60s",
            "1_5m",
            "5_15m",
            "gt_15m",
            "unknown"
          ]
        },
        "graph_delta_accepted": {
          "type": [
            "boolean",
            "null"
          ]
        }
      }
    },
    "correlation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "capability_profile",
        "finding_ids",
        "contract_ids",
        "language_families",
        "entity_count",
        "related_test_count"
      ],
      "properties": {
        "capability_profile": {
          "type": "array",
          "items": {
            "type": "string",
            "maxLength": 200
          },
          "uniqueItems": true
        },
        "finding_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "maxLength": 500
          },
          "uniqueItems": true
        },
        "contract_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "maxLength": 500
          },
          "uniqueItems": true
        },
        "language_families": {
          "type": "array",
          "items": {
            "type": "string",
            "maxLength": 100
          },
          "uniqueItems": true
        },
        "entity_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100000
        },
        "related_test_count": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100000
        }
      }
    },
    "provenance": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "snapshot_id_hash",
        "evidence_id_hashes",
        "classification_id_hash",
        "remediation_plan_id_hash",
        "attempt_id_hash",
        "rerun_id_hash"
      ],
      "properties": {
        "snapshot_id_hash": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "evidence_id_hashes": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$"
          },
          "uniqueItems": true
        },
        "classification_id_hash": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "remediation_plan_id_hash": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "attempt_id_hash": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "rerun_id_hash": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        }
      }
    }
  }
}
EOF
cat > schemas/resolver/feedback-delivery-receipt.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/feedback-delivery-receipt/v1",
  "title": "L9 Resolver Feedback Delivery Receipt",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "receipt_id",
    "event_id",
    "idempotency_key",
    "transport",
    "status",
    "attempt_count",
    "provider_status",
    "delivered_at",
    "response_body_sha256",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.feedback-delivery-receipt/v1"
    },
    "receipt_id": {
      "type": "string",
      "pattern": "^feedback_receipt_[0-9a-f]{64}$"
    },
    "event_id": {
      "type": "string",
      "pattern": "^feedback_event_[0-9a-f]{64}$"
    },
    "idempotency_key": {
      "type": "string",
      "pattern": "^feedback_idempotency_[0-9a-f]{64}$"
    },
    "transport": {
      "enum": [
        "https",
        "json_file"
      ]
    },
    "status": {
      "enum": [
        "delivered",
        "duplicate",
        "dead_letter"
      ]
    },
    "attempt_count": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    },
    "provider_status": {
      "type": [
        "integer",
        "null"
      ]
    },
    "delivered_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "response_body_sha256": {
      "type": [
        "string",
        "null"
      ],
      "pattern": "^[0-9a-f]{64}$"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    }
  }
}
EOF
cat > schemas/resolver/feedback-outbox-record.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/feedback-outbox-record/v1",
  "title": "L9 Resolver Feedback Outbox Record",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "record_id",
    "state",
    "event",
    "attempt_count",
    "next_attempt_at",
    "last_error_code",
    "receipt",
    "created_at",
    "updated_at"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.feedback-outbox-record/v1"
    },
    "record_id": {
      "type": "string",
      "pattern": "^feedback_outbox_[0-9a-f]{64}$"
    },
    "state": {
      "enum": [
        "pending",
        "delivering",
        "delivered",
        "dead_letter"
      ]
    },
    "event": {
      "$ref": "l9://resolver/intelligence-feedback-event/v1"
    },
    "attempt_count": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100
    },
    "next_attempt_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "last_error_code": {
      "type": [
        "string",
        "null"
      ],
      "maxLength": 200
    },
    "receipt": {
      "oneOf": [
        {
          "type": "null"
        },
        {
          "$ref": "l9://resolver/feedback-delivery-receipt/v1"
        }
      ]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
EOF
###############################################################################
# 3. Feedback models
###############################################################################
cat > src/l9_debt_resolver/feedback/__init__.py <<'EOF'
"""Privacy-safe Intelligence feedback delivery."""
EOF
cat > src/l9_debt_resolver/feedback/errors.py <<'EOF'
from __future__ import annotations
class FeedbackError(RuntimeError):
    """Base feedback error."""
class FeedbackPrivacyError(FeedbackError):
    """An event contains prohibited or unsafe information."""
class FeedbackSchemaError(FeedbackError):
    """An event violates the public feedback schema."""
class FeedbackDeliveryError(FeedbackError):
    """A feedback event could not be delivered."""
class PermanentDeliveryError(FeedbackDeliveryError):
    """Delivery failed permanently and must not be retried."""
class RetryableDeliveryError(FeedbackDeliveryError):
    """Delivery failed transiently and may be retried."""
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
EOF
cat > src/l9_debt_resolver/feedback/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class FeedbackEvent:
    event_id: str
    idempotency_key: str
    event_type: str
    repository_pseudonym: str
    provider: str
    resolver_version: str
    occurred_at: str
    failure: dict[str, Any]
    resolution: dict[str, Any]
    validation: dict[str, Any]
    correlation: dict[str, Any]
    provenance: dict[str, Any]
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.intelligence-feedback-event/v1"
            ),
            "event_id": self.event_id,
            "idempotency_key": self.idempotency_key,
            "event_type": self.event_type,
            "repository_pseudonym": (
                self.repository_pseudonym
            ),
            "provider": self.provider,
            "resolver_version": self.resolver_version,
            "occurred_at": self.occurred_at,
            "failure": self.failure,
            "resolution": self.resolution,
            "validation": self.validation,
            "correlation": self.correlation,
            "provenance": self.provenance,
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class DeliveryResponse:
    transport: str
    status_code: int | None
    duplicate: bool
    response_body_sha256: str | None
@dataclass(frozen=True)
class DeliveryReceipt:
    receipt_id: str
    event_id: str
    idempotency_key: str
    transport: str
    status: str
    attempt_count: int
    provider_status: int | None
    delivered_at: str | None
    response_body_sha256: str | None
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.feedback-delivery-receipt/v1"
            ),
            "receipt_id": self.receipt_id,
            "event_id": self.event_id,
            "idempotency_key": self.idempotency_key,
            "transport": self.transport,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "provider_status": self.provider_status,
            "delivered_at": self.delivered_at,
            "response_body_sha256": (
                self.response_body_sha256
            ),
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class OutboxRecord:
    record_id: str
    state: str
    event: FeedbackEvent
    attempt_count: int
    next_attempt_at: str | None
    last_error_code: str | None
    receipt: DeliveryReceipt | None
    created_at: str
    updated_at: str
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.feedback-outbox-record/v1"
            ),
            "record_id": self.record_id,
            "state": self.state,
            "event": self.event.as_dict(),
            "attempt_count": self.attempt_count,
            "next_attempt_at": self.next_attempt_at,
            "last_error_code": self.last_error_code,
            "receipt": (
                self.receipt.as_dict()
                if self.receipt
                else None
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
EOF
###############################################################################
# 4. Privacy and pseudonymization
###############################################################################
cat > src/l9_debt_resolver/feedback/privacy.py <<'EOF'
from __future__ import annotations
import ipaddress
import json
import re
from typing import Any
from urllib.parse import urlsplit
from .errors import FeedbackPrivacyError
FORBIDDEN_KEY_FRAGMENTS = (
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "cookie",
    "source",
    "patch",
    "diff",
    "log",
    "stdout",
    "stderr",
    "branch",
    "commit_message",
    "actor",
    "developer",
    "email",
    "absolute_path",
    "repository_path",
    "environment",
)
EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
BEARER = re.compile(
    r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"
)
GITHUB_TOKEN = re.compile(
    r"\b(?:ghp|github_pat|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"
)
AWS_KEY = re.compile(
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
)
PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
UNIX_PATH = re.compile(
    r"(?<![A-Za-z0-9_.-])/(?:home|Users|var|tmp|opt|workspace|github)/"
)
WINDOWS_PATH = re.compile(
    r"\b[A-Za-z]:\\(?:Users|Temp|workspace|runner)\\"
)
MAX_EVENT_BYTES = 65536
MAX_STRING_LENGTH = 2000
MAX_ARRAY_ITEMS = 500
MAX_DEPTH = 10
def validate_feedback_event(
    event: dict[str, Any],
) -> None:
    encoded = json.dumps(
        event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > MAX_EVENT_BYTES:
        raise FeedbackPrivacyError(
            "feedback event exceeds maximum size"
        )
    _validate_value(
        event,
        path="$",
        depth=0,
    )
def _validate_value(
    value: Any,
    *,
    path: str,
    depth: int,
) -> None:
    if depth > MAX_DEPTH:
        raise FeedbackPrivacyError(
            f"feedback event exceeds maximum depth at {path}"
        )
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).casefold()
            if any(
                fragment in normalized_key
                for fragment in FORBIDDEN_KEY_FRAGMENTS
            ):
                raise FeedbackPrivacyError(
                    f"forbidden feedback key at {path}.{key}"
                )
            _validate_value(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_ITEMS:
            raise FeedbackPrivacyError(
                f"feedback array exceeds maximum size at {path}"
            )
        for index, item in enumerate(value):
            _validate_value(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        _validate_string(value, path=path)
        return
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return
    raise FeedbackPrivacyError(
        f"unsupported feedback value at {path}"
    )
def _validate_string(
    value: str,
    *,
    path: str,
) -> None:
    if len(value) > MAX_STRING_LENGTH:
        raise FeedbackPrivacyError(
            f"feedback string exceeds maximum size at {path}"
        )
    patterns = (
        EMAIL,
        BEARER,
        GITHUB_TOKEN,
        AWS_KEY,
        PRIVATE_KEY,
        UNIX_PATH,
        WINDOWS_PATH,
    )
    for pattern in patterns:
        if pattern.search(value):
            raise FeedbackPrivacyError(
                f"sensitive feedback value detected at {path}"
            )
    if "\n" in value and len(value.splitlines()) > 5:
        raise FeedbackPrivacyError(
            f"multiline content is prohibited at {path}"
        )
    if _contains_ip_address(value):
        raise FeedbackPrivacyError(
            f"IP address detected at {path}"
        )
    if _contains_credential_url(value):
        raise FeedbackPrivacyError(
            f"credential-bearing URL detected at {path}"
        )
def _contains_ip_address(value: str) -> bool:
    candidates = re.findall(
        r"(?<![A-Za-z0-9:])"
        r"(?:\d{1,3}\.){3}\d{1,3}"
        r"(?![A-Za-z0-9:])",
        value,
    )
    for candidate in candidates:
        try:
            ipaddress.ip_address(candidate)
            return True
        except ValueError:
            continue
    return False
def _contains_credential_url(value: str) -> bool:
    for candidate in re.findall(
        r"https?://[^\s]+",
        value,
    ):
        parsed = urlsplit(candidate)
        if parsed.username or parsed.password:
            return True
    return False
EOF
cat > src/l9_debt_resolver/feedback/identity.py <<'EOF'
from __future__ import annotations
import hashlib
import hmac
from typing import Any
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
def repository_pseudonym(
    *,
    repository: str,
    pseudonym_key: bytes,
) -> str:
    if len(pseudonym_key) < 32:
        raise ValueError(
            "feedback pseudonym key must be at least 32 bytes"
        )
    digest = hmac.new(
        pseudonym_key,
        repository.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"repository_{digest}"
def stable_hash(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()
def feedback_event_id(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "feedback_event_",
        material,
    )
def idempotency_key(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "feedback_idempotency_",
        material,
    )
EOF
###############################################################################
# 5. Event builder
###############################################################################
cat > src/l9_debt_resolver/feedback/builder.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import (
    RepositoryCorrelation,
)
from l9_debt_resolver.resolution.models import (
    ResolutionOutcome,
)
from .identity import (
    feedback_event_id,
    idempotency_key,
    repository_pseudonym,
    stable_hash,
)
from .models import FeedbackEvent
from .privacy import validate_feedback_event
TERMINAL_EVENT_TYPES = {
    "clean": "resolution_succeeded",
    "repeated_failure": "repeated_failure",
    "new_failure": "new_failure",
    "attempt_limit_reached": "attempt_limit_reached",
    "remote_operation_failed": "remote_operation_failed",
    "rerun_timeout": "rerun_timeout",
    "validation_failed": "validation_failed",
    "unsupported": "unsupported",
}
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
def build_feedback_event(
    *,
    repository: str,
    pseudonym_key: bytes,
    provider: str,
    resolver_version: str,
    attempt_number: int,
    classification_trace: ClassificationTrace,
    correlation: RepositoryCorrelation,
    resolution_outcome: ResolutionOutcome,
    remediation_class: str | None,
    changed_file_count: int,
    changed_line_count: int | None,
    validation_result: str,
    validation_result_id: str | None,
    validation_step_count: int,
    validation_duration_bucket: str,
    graph_delta_accepted: bool | None,
    remediation_plan_id: str | None,
) -> FeedbackEvent:
    classification = (
        classification_trace.classification
    )
    event_type = TERMINAL_EVENT_TYPES.get(
        resolution_outcome.terminal_state,
        "unsupported",
    )
    repository_id = repository_pseudonym(
        repository=repository,
        pseudonym_key=pseudonym_key,
    )
    observed = (
        resolution_outcome
        .observed_failure_fingerprint
    )
    identity_material = {
        "repository_pseudonym": repository_id,
        "failure_fingerprint": (
            classification.failure_fingerprint
        ),
        "attempt_number": attempt_number,
        "terminal_state": (
            resolution_outcome.terminal_state
        ),
        "rerun_id_hash": stable_hash(
            resolution_outcome.rerun_id
        ),
        "validation_result_id_hash": stable_hash(
            validation_result_id
        ),
    }
    event_id = feedback_event_id(
        identity_material
    )
    event = FeedbackEvent(
        event_id=event_id,
        idempotency_key=idempotency_key(
            identity_material
        ),
        event_type=event_type,
        repository_pseudonym=repository_id,
        provider=provider,
        resolver_version=resolver_version,
        occurred_at=utc_now(),
        failure={
            "fingerprint": (
                classification.failure_fingerprint
            ),
            "category": classification.category,
            "confidence_bucket": _confidence_bucket(
                classification.confidence
            ),
            "repeated": (
                resolution_outcome.terminal_state
                == "repeated_failure"
            ),
            "attempt_number": attempt_number,
            "observed_fingerprint_changed": (
                None
                if observed is None
                else observed
                != classification.failure_fingerprint
            ),
        },
        resolution={
            "terminal_state": (
                resolution_outcome.terminal_state
            ),
            "remediation_class": remediation_class,
            "changed_file_count": max(
                0,
                changed_file_count,
            ),
            "changed_line_bucket": (
                _changed_line_bucket(
                    changed_line_count
                )
            ),
            "remote_push_performed": (
                resolution_outcome.commit_sha
                is not None
            ),
            "rerun_observed": (
                resolution_outcome.rerun_id
                is not None
            ),
        },
        validation={
            "result": validation_result,
            "result_id_hash": stable_hash(
                validation_result_id
            ),
            "step_count": max(
                0,
                validation_step_count,
            ),
            "duration_bucket": (
                validation_duration_bucket
            ),
            "graph_delta_accepted": (
                graph_delta_accepted
            ),
        },
        correlation={
            "capability_profile": list(
                sorted(
                    set(
                        correlation
                        .capability_profile
                    )
                )
            ),
            "finding_ids": list(
                sorted(
                    {
                        reference.id
                        for reference in (
                            correlation
                            .finding_references
                        )
                    }
                )
            ),
            "contract_ids": list(
                sorted(
                    {
                        reference.id
                        for reference in (
                            correlation
                            .contract_references
                        )
                    }
                )
            ),
            "language_families": list(
                sorted(
                    {
                        frame.framework
                        for frame in (
                            correlation.stack_frames
                        )
                    }
                )
            ),
            "entity_count": len(
                correlation.entity_references
            ),
            "related_test_count": len(
                correlation
                .related_test_references
            ),
        },
        provenance={
            "snapshot_id_hash": stable_hash(
                correlation
                .repository_snapshot_id
            ),
            "evidence_id_hashes": list(
                sorted(
                    stable_hash(value)
                    for value in (
                        classification.evidence_ids
                    )
                    if stable_hash(value)
                    is not None
                )
            ),
            "classification_id_hash": (
                stable_hash(
                    classification
                    .classification_id
                )
            ),
            "remediation_plan_id_hash": (
                stable_hash(
                    remediation_plan_id
                )
            ),
            "attempt_id_hash": stable_hash(
                resolution_outcome.attempt_id
            ),
            "rerun_id_hash": stable_hash(
                resolution_outcome.rerun_id
            ),
        },
        limitations=tuple(
            sorted(
                {
                    *classification.limitations,
                    *correlation.limitations,
                    *resolution_outcome.limitations,
                }
            )
        ),
    )
    document = event.as_dict()
    validate_feedback_event(document)
    return event
def _confidence_bucket(
    confidence: float,
) -> str:
    if confidence >= 0.95:
        return "very_high"
    if confidence >= 0.90:
        return "high"
    if confidence >= 0.70:
        return "medium"
    return "low"
def _changed_line_bucket(
    count: int | None,
) -> str:
    if count is None:
        return "unknown"
    if count <= 0:
        return "0"
    if count <= 10:
        return "1_10"
    if count <= 50:
        return "11_50"
    if count <= 100:
        return "51_100"
    if count <= 250:
        return "101_250"
    if count <= 500:
        return "251_500"
    return "gt_500"
EOF
###############################################################################
# 6. Feedback transport protocol
###############################################################################
cat > src/l9_debt_resolver/feedback/protocol.py <<'EOF'
from __future__ import annotations
from typing import Protocol
from .models import (
    DeliveryResponse,
    FeedbackEvent,
)
class FeedbackTransport(Protocol):
    name: str
    async def deliver(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        """Deliver one privacy-validated feedback event."""
EOF
###############################################################################
# 7. JSON-file transport
###############################################################################
cat > src/l9_debt_resolver/feedback/file_transport.py <<'EOF'
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile
from .models import (
    DeliveryResponse,
    FeedbackEvent,
)
class JSONFileFeedbackTransport:
    name = "json_file"
    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory
    async def deliver(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        return await asyncio.to_thread(
            self._deliver_sync,
            event,
        )
    def _deliver_sync(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = (
            self._directory
            / f"{event.event_id}.json"
        )
        encoded = (
            json.dumps(
                event.as_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if destination.exists():
            existing = destination.read_bytes()
            if existing == encoded:
                return DeliveryResponse(
                    transport=self.name,
                    status_code=409,
                    duplicate=True,
                    response_body_sha256=(
                        hashlib.sha256(
                            existing
                        ).hexdigest()
                    ),
                )
            raise RuntimeError(
                "event identity collision in file transport"
            )
        descriptor, temporary = tempfile.mkstemp(
            dir=self._directory,
            prefix=".feedback-event.",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(
                descriptor,
                "wb",
            ) as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                destination,
            )
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return DeliveryResponse(
            transport=self.name,
            status_code=201,
            duplicate=False,
            response_body_sha256=(
                hashlib.sha256(
                    encoded
                ).hexdigest()
            ),
        )
EOF
###############################################################################
# 8. HTTPS transport
###############################################################################
cat > src/l9_debt_resolver/feedback/http_transport.py <<'EOF'
from __future__ import annotations
import asyncio
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from .errors import (
    PermanentDeliveryError,
    RetryableDeliveryError,
)
from .models import (
    DeliveryResponse,
    FeedbackEvent,
)
SUCCESS = {
    200,
    201,
    202,
    204,
    409,
}
RETRYABLE = {
    408,
    425,
    429,
    500,
    502,
    503,
    504,
}
class HTTPSFeedbackTransport:
    name = "https"
    def __init__(
        self,
        *,
        endpoint: str,
        bearer_token: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError(
                "feedback endpoint must use HTTPS"
            )
        if not bearer_token:
            raise ValueError(
                "feedback bearer token is required"
            )
        self._endpoint = endpoint
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
    async def deliver(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        return await asyncio.to_thread(
            self._deliver_sync,
            event,
        )
    def _deliver_sync(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        body = json.dumps(
            event.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            method="POST",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": (
                    f"Bearer {self._bearer_token}"
                ),
                "Idempotency-Key": (
                    event.idempotency_key
                ),
                "User-Agent": (
                    "l9-ci-debt-resolver-feedback/1"
                ),
            },
        )
        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                response_body = response.read(
                    1024 * 1024
                )
                if response.status not in SUCCESS:
                    raise PermanentDeliveryError(
                        "feedback endpoint returned "
                        f"HTTP {response.status}"
                    )
                return DeliveryResponse(
                    transport=self.name,
                    status_code=response.status,
                    duplicate=(
                        response.status == 409
                    ),
                    response_body_sha256=(
                        hashlib.sha256(
                            response_body
                        ).hexdigest()
                    ),
                )
        except HTTPError as error:
            response_body = error.read(
                1024 * 1024
            )
            if error.code in SUCCESS:
                return DeliveryResponse(
                    transport=self.name,
                    status_code=error.code,
                    duplicate=(
                        error.code == 409
                    ),
                    response_body_sha256=(
                        hashlib.sha256(
                            response_body
                        ).hexdigest()
                    ),
                )
            if error.code in RETRYABLE:
                raise RetryableDeliveryError(
                    "retryable feedback HTTP response",
                    status_code=error.code,
                    retry_after_seconds=(
                        _retry_after_seconds(
                            error.headers.get(
                                "Retry-After"
                            )
                        )
                    ),
                ) from error
            raise PermanentDeliveryError(
                "non-retryable feedback HTTP response "
                f"{error.code}"
            ) from error
        except URLError as error:
            raise RetryableDeliveryError(
                "feedback endpoint is unavailable"
            ) from error
def _retry_after_seconds(
    value: str | None,
) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return min(parsed, 30.0)
EOF
###############################################################################
# 9. Durable outbox
###############################################################################
cat > src/l9_debt_resolver/feedback/outbox.py <<'EOF'
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from .models import (
    DeliveryReceipt,
    FeedbackEvent,
    OutboxRecord,
)
class FeedbackOutbox:
    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory
    def enqueue(
        self,
        event: FeedbackEvent,
        *,
        now: str,
    ) -> OutboxRecord:
        record = OutboxRecord(
            record_id=namespaced_identity(
                "feedback_outbox_",
                {
                    "event_id": event.event_id,
                    "idempotency_key": (
                        event.idempotency_key
                    ),
                },
            ),
            state="pending",
            event=event,
            attempt_count=0,
            next_attempt_at=now,
            last_error_code=None,
            receipt=None,
            created_at=now,
            updated_at=now,
        )
        existing = self.get(record.record_id)
        if existing is not None:
            if (
                existing.event.event_id
                != event.event_id
            ):
                raise ValueError(
                    "outbox identity collision"
                )
            return existing
        self._write(record)
        return record
    def get(
        self,
        record_id: str,
    ) -> OutboxRecord | None:
        path = self._path(record_id)
        if not path.exists():
            return None
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
        return _parse_record(value)
    def save(
        self,
        record: OutboxRecord,
    ) -> None:
        self._write(record)
    def pending(
        self,
    ) -> tuple[OutboxRecord, ...]:
        if not self._directory.exists():
            return ()
        records = []
        for path in sorted(
            self._directory.glob(
                "feedback_outbox_*.json"
            )
        ):
            record = _parse_record(
                json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            )
            if record.state in {
                "pending",
                "delivering",
            }:
                records.append(record)
        return tuple(records)
    def _path(
        self,
        record_id: str,
    ) -> Path:
        return self._directory / f"{record_id}.json"
    def _write(
        self,
        record: OutboxRecord,
    ) -> None:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = self._path(
            record.record_id
        )
        encoded = (
            json.dumps(
                record.as_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(
            dir=self._directory,
            prefix=".feedback-outbox.",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(
                descriptor,
                "wb",
            ) as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                destination,
            )
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
def _parse_record(
    value: Any,
) -> OutboxRecord:
    if not isinstance(value, dict):
        raise ValueError(
            "outbox record must be an object"
        )
    event_value = value["event"]
    event = FeedbackEvent(
        event_id=event_value["event_id"],
        idempotency_key=(
            event_value["idempotency_key"]
        ),
        event_type=event_value["event_type"],
        repository_pseudonym=(
            event_value["repository_pseudonym"]
        ),
        provider=event_value["provider"],
        resolver_version=(
            event_value["resolver_version"]
        ),
        occurred_at=event_value["occurred_at"],
        failure=dict(event_value["failure"]),
        resolution=dict(event_value["resolution"]),
        validation=dict(event_value["validation"]),
        correlation=dict(event_value["correlation"]),
        provenance=dict(event_value["provenance"]),
        limitations=tuple(
            event_value["limitations"]
        ),
    )
    receipt_value = value.get("receipt")
    receipt = (
        DeliveryReceipt(
            receipt_id=receipt_value["receipt_id"],
            event_id=receipt_value["event_id"],
            idempotency_key=(
                receipt_value["idempotency_key"]
            ),
            transport=receipt_value["transport"],
            status=receipt_value["status"],
            attempt_count=int(
                receipt_value["attempt_count"]
            ),
            provider_status=(
                int(receipt_value["provider_status"])
                if receipt_value.get(
                    "provider_status"
                )
                is not None
                else None
            ),
            delivered_at=receipt_value.get(
                "delivered_at"
            ),
            response_body_sha256=(
                receipt_value.get(
                    "response_body_sha256"
                )
            ),
            limitations=tuple(
                receipt_value["limitations"]
            ),
        )
        if isinstance(receipt_value, dict)
        else None
    )
    return OutboxRecord(
        record_id=value["record_id"],
        state=value["state"],
        event=event,
        attempt_count=int(
            value["attempt_count"]
        ),
        next_attempt_at=value.get(
            "next_attempt_at"
        ),
        last_error_code=value.get(
            "last_error_code"
        ),
        receipt=receipt,
        created_at=value["created_at"],
        updated_at=value["updated_at"],
    )
EOF
###############################################################################
# 10. Retry and delivery service
###############################################################################
cat > src/l9_debt_resolver/feedback/delivery.py <<'EOF'
from __future__ import annotations
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from .errors import (
    PermanentDeliveryError,
    RetryableDeliveryError,
)
from .models import (
    DeliveryReceipt,
    FeedbackEvent,
    OutboxRecord,
)
from .outbox import FeedbackOutbox
from .privacy import validate_feedback_event
from .protocol import FeedbackTransport
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
class FeedbackDeliveryService:
    def __init__(
        self,
        *,
        outbox: FeedbackOutbox,
        transport: FeedbackTransport,
        maximum_attempts: int = 5,
        initial_delay_seconds: float = 1.0,
        maximum_delay_seconds: float = 30.0,
    ) -> None:
        self._outbox = outbox
        self._transport = transport
        self._maximum_attempts = maximum_attempts
        self._initial_delay = initial_delay_seconds
        self._maximum_delay = maximum_delay_seconds
    async def submit(
        self,
        event: FeedbackEvent,
    ) -> DeliveryReceipt:
        validate_feedback_event(
            event.as_dict()
        )
        record = self._outbox.enqueue(
            event,
            now=utc_now(),
        )
        if (
            record.state == "delivered"
            and record.receipt is not None
        ):
            return record.receipt
        return await self._deliver_record(record)
    async def drain(
        self,
    ) -> tuple[DeliveryReceipt, ...]:
        receipts = []
        for record in self._outbox.pending():
            receipts.append(
                await self._deliver_record(
                    record
                )
            )
        return tuple(receipts)
    async def _deliver_record(
        self,
        record: OutboxRecord,
    ) -> DeliveryReceipt:
        current = record
        while (
            current.attempt_count
            < self._maximum_attempts
        ):
            attempt_number = (
                current.attempt_count + 1
            )
            current = replace(
                current,
                state="delivering",
                attempt_count=attempt_number,
                updated_at=utc_now(),
            )
            self._outbox.save(current)
            try:
                response = (
                    await self._transport.deliver(
                        current.event
                    )
                )
                receipt = _receipt(
                    event=current.event,
                    transport=response.transport,
                    attempt_count=attempt_number,
                    status=(
                        "duplicate"
                        if response.duplicate
                        else "delivered"
                    ),
                    provider_status=(
                        response.status_code
                    ),
                    response_body_sha256=(
                        response
                        .response_body_sha256
                    ),
                    limitations=(),
                )
                current = replace(
                    current,
                    state="delivered",
                    next_attempt_at=None,
                    last_error_code=None,
                    receipt=receipt,
                    updated_at=utc_now(),
                )
                self._outbox.save(current)
                return receipt
            except PermanentDeliveryError as error:
                receipt = _receipt(
                    event=current.event,
                    transport=(
                        self._transport.name
                    ),
                    attempt_count=attempt_number,
                    status="dead_letter",
                    provider_status=None,
                    response_body_sha256=None,
                    limitations=(
                        type(error).__name__,
                    ),
                )
                current = replace(
                    current,
                    state="dead_letter",
                    next_attempt_at=None,
                    last_error_code=(
                        type(error).__name__
                    ),
                    receipt=receipt,
                    updated_at=utc_now(),
                )
                self._outbox.save(current)
                return receipt
            except RetryableDeliveryError as error:
                if (
                    attempt_number
                    >= self._maximum_attempts
                ):
                    receipt = _receipt(
                        event=current.event,
                        transport=(
                            self._transport.name
                        ),
                        attempt_count=attempt_number,
                        status="dead_letter",
                        provider_status=(
                            error.status_code
                        ),
                        response_body_sha256=None,
                        limitations=(
                            "retry_attempts_exhausted",
                        ),
                    )
                    current = replace(
                        current,
                        state="dead_letter",
                        next_attempt_at=None,
                        last_error_code=(
                            type(error).__name__
                        ),
                        receipt=receipt,
                        updated_at=utc_now(),
                    )
                    self._outbox.save(current)
                    return receipt
                delay = (
                    error.retry_after_seconds
                    if (
                        error.retry_after_seconds
                        is not None
                    )
                    else self._delay_seconds(
                        current.event,
                        attempt_number,
                    )
                )
                next_attempt = (
                    datetime.now(timezone.utc)
                    + timedelta(seconds=delay)
                ).isoformat().replace(
                    "+00:00",
                    "Z",
                )
                current = replace(
                    current,
                    state="pending",
                    next_attempt_at=next_attempt,
                    last_error_code=(
                        type(error).__name__
                    ),
                    updated_at=utc_now(),
                )
                self._outbox.save(current)
                await asyncio.sleep(delay)
        raise AssertionError(
            "delivery loop exited without a receipt"
        )
    def _delay_seconds(
        self,
        event: FeedbackEvent,
        attempt_number: int,
    ) -> float:
        exponential = min(
            self._maximum_delay,
            self._initial_delay
            * (2 ** (attempt_number - 1)),
        )
        deterministic_fraction = (
            int(event.event_id[-8:], 16)
            % 1000
        ) / 1000.0
        jitter = min(
            0.25 * exponential,
            deterministic_fraction,
        )
        return min(
            self._maximum_delay,
            exponential + jitter,
        )
def _receipt(
    *,
    event: FeedbackEvent,
    transport: str,
    attempt_count: int,
    status: str,
    provider_status: int | None,
    response_body_sha256: str | None,
    limitations: tuple[str, ...],
) -> DeliveryReceipt:
    delivered_at = (
        utc_now()
        if status in {
            "delivered",
            "duplicate",
        }
        else None
    )
    receipt_id = namespaced_identity(
        "feedback_receipt_",
        {
            "event_id": event.event_id,
            "idempotency_key": (
                event.idempotency_key
            ),
            "transport": transport,
            "status": status,
            "attempt_count": attempt_count,
            "provider_status": provider_status,
        },
    )
    return DeliveryReceipt(
        receipt_id=receipt_id,
        event_id=event.event_id,
        idempotency_key=(
            event.idempotency_key
        ),
        transport=transport,
        status=status,
        attempt_count=attempt_count,
        provider_status=provider_status,
        delivered_at=delivered_at,
        response_body_sha256=(
            response_body_sha256
        ),
        limitations=tuple(
            sorted(set(limitations))
        ),
    )
EOF
###############################################################################
# 11. Event loading
###############################################################################
cat > src/l9_debt_resolver/feedback/loader.py <<'EOF'
from __future__ import annotations
import json
from pathlib import Path
from .models import FeedbackEvent
from .privacy import validate_feedback_event
def load_feedback_event(
    path: Path,
) -> FeedbackEvent:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise ValueError(
            "feedback event must be an object"
        )
    if (
        value.get("schema_version")
        != "l9.intelligence-feedback-event/v1"
    ):
        raise ValueError(
            "unsupported feedback event version"
        )
    validate_feedback_event(value)
    return FeedbackEvent(
        event_id=value["event_id"],
        idempotency_key=(
            value["idempotency_key"]
        ),
        event_type=value["event_type"],
        repository_pseudonym=(
            value["repository_pseudonym"]
        ),
        provider=value["provider"],
        resolver_version=(
            value["resolver_version"]
        ),
        occurred_at=value["occurred_at"],
        failure=dict(value["failure"]),
        resolution=dict(value["resolution"]),
        validation=dict(value["validation"]),
        correlation=dict(value["correlation"]),
        provenance=dict(value["provenance"]),
        limitations=tuple(
            value["limitations"]
        ),
    )
EOF
###############################################################################
# 12. Runtime feedback service
###############################################################################
cat > src/l9_debt_resolver/runtime/feedback_service.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.feedback.delivery import (
    FeedbackDeliveryService,
)
from l9_debt_resolver.feedback.models import (
    DeliveryReceipt,
    FeedbackEvent,
)
class ResolverFeedbackService:
    def __init__(
        self,
        delivery: FeedbackDeliveryService,
    ) -> None:
        self._delivery = delivery
    async def publish(
        self,
        event: FeedbackEvent,
    ) -> DeliveryReceipt:
        return await self._delivery.submit(event)
    async def drain_outbox(
        self,
    ) -> tuple[DeliveryReceipt, ...]:
        return await self._delivery.drain()
EOF
###############################################################################
# 13. Capabilities
###############################################################################
cat > src/l9_debt_resolver/runtime/capabilities.py <<'EOF'
from __future__ import annotations
from typing import Any
def resolver_capabilities() -> dict[str, Any]:
    return {
        "schema_version": "l9.resolver-capabilities/v1",
        "phase": "RESOLVER-P5",
        "capabilities": {
            "contract_validation": True,
            "typed_CI_evidence": True,
            "failed_log_acquisition": True,
            "SDK_repository_snapshots": True,
            "root_cause_classification": True,
            "bounded_remediation": True,
            "SDK_validation_execution": True,
            "repair_branch_policy": True,
            "push_authorization": True,
            "CI_rerun_observation": True,
            "attempt_limits": True,
            "terminal_state_emission": True,
            "privacy_safe_feedback_events": True,
            "repository_pseudonymization": True,
            "deterministic_feedback_IDs": True,
            "feedback_idempotency": True,
            "corpus_safe_provenance": True,
            "repeated_failure_telemetry": True,
            "durable_feedback_outbox": True,
            "bounded_delivery_retries": True,
            "retry_after_support": True,
            "dead_letter_state": True,
            "delivery_receipts": True,
            "https_feedback_transport": True,
            "json_file_feedback_transport": True,
            "raw_log_feedback": False,
            "source_content_feedback": False,
            "patch_content_feedback": False,
            "developer_identity_feedback": False,
            "automatic_merge": False,
            "PR_Repair_delegation": False
        },
        "limitations": [
            "P5 emits feedback but does not mine the Intelligence corpus.",
            "P5 cannot create Intelligence findings.",
            "P5 cannot compile prevention artifacts.",
            "PR_Repair delegation begins in RESOLVER-P6.",
            "Automatic merge remains prohibited."
        ]
    }
EOF
###############################################################################
# 14. CLI extension
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("src/l9_debt_resolver/cli.py")
content = path.read_text(encoding="utf-8")
imports = """from .feedback.delivery import FeedbackDeliveryService
from .feedback.file_transport import JSONFileFeedbackTransport
from .feedback.http_transport import HTTPSFeedbackTransport
from .feedback.loader import load_feedback_event
from .feedback.outbox import FeedbackOutbox
from .runtime.feedback_service import ResolverFeedbackService
"""
anchor = "from .runtime.capabilities import resolver_capabilities\n"
if imports not in content:
    content = content.replace(
        anchor,
        anchor + imports,
    )
commands = """
    publish_feedback = commands.add_parser(
        "publish-feedback"
    )
    publish_feedback.add_argument(
        "--event",
        required=True,
        type=Path,
    )
    publish_feedback.add_argument(
        "--outbox",
        required=True,
        type=Path,
    )
    publish_feedback.add_argument(
        "--transport",
        choices=["json-file", "https"],
        required=True,
    )
    publish_feedback.add_argument(
        "--destination",
        required=True,
    )
    publish_feedback.add_argument(
        "--token-environment",
        default="L9_FEEDBACK_TOKEN",
    )
    drain_feedback = commands.add_parser(
        "drain-feedback-outbox"
    )
    drain_feedback.add_argument(
        "--outbox",
        required=True,
        type=Path,
    )
    drain_feedback.add_argument(
        "--transport",
        choices=["json-file", "https"],
        required=True,
    )
    drain_feedback.add_argument(
        "--destination",
        required=True,
    )
    drain_feedback.add_argument(
        "--token-environment",
        default="L9_FEEDBACK_TOKEN",
    )
"""
anchor = "    remediate = commands.add_parser(\n"
if 'publish-feedback' not in content:
    content = content.replace(
        anchor,
        commands + "\n" + anchor,
    )
helpers = """
def _feedback_transport(
    *,
    transport_name: str,
    destination: str,
    token_environment: str,
):
    import os
    if transport_name == "json-file":
        return JSONFileFeedbackTransport(
            directory=Path(destination)
        )
    token = os.environ.get(
        token_environment
    )
    if not token:
        raise ValueError(
            f"feedback token environment variable "
            f"{token_environment} is missing"
        )
    return HTTPSFeedbackTransport(
        endpoint=destination,
        bearer_token=token,
    )
async def publish_feedback(
    *,
    event_path: Path,
    outbox_path: Path,
    transport_name: str,
    destination: str,
    token_environment: str,
) -> dict[str, Any]:
    event = load_feedback_event(
        event_path
    )
    service = ResolverFeedbackService(
        FeedbackDeliveryService(
            outbox=FeedbackOutbox(
                directory=outbox_path
            ),
            transport=_feedback_transport(
                transport_name=transport_name,
                destination=destination,
                token_environment=token_environment,
            ),
        )
    )
    receipt = await service.publish(event)
    return receipt.as_dict()
async def drain_feedback(
    *,
    outbox_path: Path,
    transport_name: str,
    destination: str,
    token_environment: str,
) -> list[dict[str, Any]]:
    service = ResolverFeedbackService(
        FeedbackDeliveryService(
            outbox=FeedbackOutbox(
                directory=outbox_path
            ),
            transport=_feedback_transport(
                transport_name=transport_name,
                destination=destination,
                token_environment=token_environment,
            ),
        )
    )
    receipts = await service.drain_outbox()
    return [
        receipt.as_dict()
        for receipt in receipts
    ]
"""
anchor = "def main() -> int:\n"
if helpers not in content:
    content = content.replace(
        anchor,
        helpers + anchor,
    )
handlers = """
    if arguments.command == "publish-feedback":
        receipt = asyncio.run(
            publish_feedback(
                event_path=arguments.event,
                outbox_path=arguments.outbox,
                transport_name=arguments.transport,
                destination=arguments.destination,
                token_environment=(
                    arguments.token_environment
                ),
            )
        )
        emit(receipt)
        return (
            0
            if receipt["status"]
            in {"delivered", "duplicate"}
            else 2
        )
    if arguments.command == "drain-feedback-outbox":
        receipts = asyncio.run(
            drain_feedback(
                outbox_path=arguments.outbox,
                transport_name=arguments.transport,
                destination=arguments.destination,
                token_environment=(
                    arguments.token_environment
                ),
            )
        )
        emit(
            {
                "schema_version": (
                    "l9.feedback-drain-result/v1"
                ),
                "receipts": receipts,
            }
        )
        return (
            0
            if all(
                receipt["status"]
                in {"delivered", "duplicate"}
                for receipt in receipts
            )
            else 2
        )
"""
anchor = '    if arguments.command == "remediate-offline":\n'
if handlers not in content:
    content = content.replace(
        anchor,
        handlers + anchor,
    )
content = content.replace(
    '            "validation-transcript",',
    '            "validation-transcript",\n'
    '            "intelligence-feedback-event",\n'
    '            "feedback-delivery-receipt",\n'
    '            "feedback-outbox-record",',
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 15. Version and roadmap
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("pyproject.toml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    'version = "0.5.0"',
    'version = "0.6.0"',
)
path.write_text(content, encoding="utf-8")
path = Path("src/l9_debt_resolver/__init__.py")
content = path.read_text(encoding="utf-8")
content = content.replace(
    '__version__ = "0.5.0"',
    '__version__ = "0.6.0"',
)
path.write_text(content, encoding="utf-8")
path = Path(".l9/repo-spec.yaml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    "phase: RESOLVER-P4",
    "phase: RESOLVER-P5",
    1,
)
content = content.replace(
    "phase_name: remote_resolution_loop",
    "phase_name: intelligence_feedback",
    1,
)
content = content.replace(
    """  - phase: RESOLVER-P5
    name: intelligence_feedback
    priority: medium
    status: planned""",
    """  - phase: RESOLVER-P5
    name: intelligence_feedback
    priority: medium
    status: implemented""",
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 16. Tests
###############################################################################
cat > tests/feedback/test_identity.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.feedback.identity import (
    idempotency_key,
    repository_pseudonym,
)
def test_repository_pseudonym_is_deterministic() -> None:
    key = b"a" * 32
    first = repository_pseudonym(
        repository="Quantum-L9/example",
        pseudonym_key=key,
    )
    second = repository_pseudonym(
        repository="Quantum-L9/example",
        pseudonym_key=key,
    )
    assert first == second
    assert "Quantum-L9" not in first
def test_idempotency_excludes_timestamp() -> None:
    first = idempotency_key(
        {
            "failure": "failure-1",
            "terminal": "clean",
        }
    )
    second = idempotency_key(
        {
            "failure": "failure-1",
            "terminal": "clean",
        }
    )
    assert first == second
EOF
cat > tests/privacy/test_feedback_privacy.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.feedback.errors import (
    FeedbackPrivacyError,
)
from l9_debt_resolver.feedback.privacy import (
    validate_feedback_event,
)
@pytest.mark.parametrize(
    "document",
    [
        {"raw_log": "failure"},
        {"patch_body": "diff --git"},
        {"developer_email": "dev@example.com"},
        {"value": "Bearer abcdefghijklmnop"},
        {"value": "/home/alice/project/app.py"},
        {"value": "192.168.1.1"},
        {"value": "https://user:pass@example.com/api"},
    ],
)
def test_sensitive_feedback_is_rejected(
    document: dict[str, object],
) -> None:
    with pytest.raises(
        FeedbackPrivacyError
    ):
        validate_feedback_event(document)
def test_safe_aggregate_feedback_is_allowed() -> None:
    validate_feedback_event(
        {
            "event_type": "repeated_failure",
            "changed_file_count": 2,
            "failure_fingerprint": (
                "failure_" + "a" * 64
            ),
        }
    )
EOF
cat > tests/feedback/test_file_transport.py <<'EOF'
from __future__ import annotations
from pathlib import Path
import pytest
from l9_debt_resolver.feedback.file_transport import (
    JSONFileFeedbackTransport,
)
from l9_debt_resolver.feedback.models import (
    FeedbackEvent,
)
def event() -> FeedbackEvent:
    return FeedbackEvent(
        event_id="feedback_event_" + "a" * 64,
        idempotency_key=(
            "feedback_idempotency_" + "b" * 64
        ),
        event_type="resolution_succeeded",
        repository_pseudonym=(
            "repository_" + "c" * 64
        ),
        provider="github_actions",
        resolver_version="0.6.0",
        occurred_at="2026-07-19T00:00:00Z",
        failure={
            "fingerprint": "failure_" + "d" * 64,
            "category": "test_failure",
            "confidence_bucket": "high",
            "repeated": False,
            "attempt_number": 1,
            "observed_fingerprint_changed": None,
        },
        resolution={
            "terminal_state": "clean",
            "remediation_class": "bounded_source",
            "changed_file_count": 1,
            "changed_line_bucket": "1_10",
            "remote_push_performed": True,
            "rerun_observed": True,
        },
        validation={
            "result": "passed",
            "result_id_hash": "e" * 64,
            "step_count": 4,
            "duration_bucket": "10_60s",
            "graph_delta_accepted": True,
        },
        correlation={
            "capability_profile": ["python"],
            "finding_ids": [],
            "contract_ids": [],
            "language_families": ["python"],
            "entity_count": 1,
            "related_test_count": 1,
        },
        provenance={
            "snapshot_id_hash": "f" * 64,
            "evidence_id_hashes": ["1" * 64],
            "classification_id_hash": "2" * 64,
            "remediation_plan_id_hash": "3" * 64,
            "attempt_id_hash": "4" * 64,
            "rerun_id_hash": "5" * 64,
        },
        limitations=(),
    )
@pytest.mark.asyncio
async def test_file_transport_is_idempotent(
    tmp_path: Path,
) -> None:
    transport = JSONFileFeedbackTransport(
        directory=tmp_path
    )
    first = await transport.deliver(event())
    second = await transport.deliver(event())
    assert first.duplicate is False
    assert second.duplicate is True
EOF
cat > tests/resilience/test_feedback_delivery.py <<'EOF'
from __future__ import annotations
from pathlib import Path
import pytest
from l9_debt_resolver.feedback.delivery import (
    FeedbackDeliveryService,
)
from l9_debt_resolver.feedback.errors import (
    RetryableDeliveryError,
)
from l9_debt_resolver.feedback.models import (
    DeliveryResponse,
)
from l9_debt_resolver.feedback.outbox import (
    FeedbackOutbox,
)
from tests.feedback.test_file_transport import event
class FlakyTransport:
    name = "https"
    def __init__(self) -> None:
        self.calls = 0
    async def deliver(self, feedback_event):
        del feedback_event
        self.calls += 1
        if self.calls < 3:
            raise RetryableDeliveryError(
                "temporary failure",
                status_code=503,
                retry_after_seconds=0,
            )
        return DeliveryResponse(
            transport="https",
            status_code=202,
            duplicate=False,
            response_body_sha256="a" * 64,
        )
@pytest.mark.asyncio
async def test_retryable_delivery_succeeds(
    tmp_path: Path,
) -> None:
    transport = FlakyTransport()
    service = FeedbackDeliveryService(
        outbox=FeedbackOutbox(
            directory=tmp_path
        ),
        transport=transport,
        maximum_attempts=5,
        initial_delay_seconds=0,
        maximum_delay_seconds=0,
    )
    receipt = await service.submit(
        event()
    )
    assert receipt.status == "delivered"
    assert receipt.attempt_count == 3
    assert transport.calls == 3
class AlwaysFailTransport:
    name = "https"
    async def deliver(self, feedback_event):
        del feedback_event
        raise RetryableDeliveryError(
            "temporary failure",
            status_code=503,
            retry_after_seconds=0,
        )
@pytest.mark.asyncio
async def test_retry_exhaustion_dead_letters(
    tmp_path: Path,
) -> None:
    service = FeedbackDeliveryService(
        outbox=FeedbackOutbox(
            directory=tmp_path
        ),
        transport=AlwaysFailTransport(),
        maximum_attempts=2,
        initial_delay_seconds=0,
        maximum_delay_seconds=0,
    )
    receipt = await service.submit(
        event()
    )
    assert receipt.status == "dead_letter"
    assert receipt.attempt_count == 2
EOF
cat > tests/feedback/test_outbox.py <<'EOF'
from __future__ import annotations
from pathlib import Path
from l9_debt_resolver.feedback.outbox import (
    FeedbackOutbox,
)
from tests.feedback.test_file_transport import event
def test_outbox_enqueue_is_idempotent(
    tmp_path: Path,
) -> None:
    outbox = FeedbackOutbox(
        directory=tmp_path
    )
    first = outbox.enqueue(
        event(),
        now="2026-07-19T00:00:00Z",
    )
    second = outbox.enqueue(
        event(),
        now="2026-07-19T00:00:01Z",
    )
    assert first.record_id == second.record_id
    assert len(
        list(
            tmp_path.glob(
                "feedback_outbox_*.json"
            )
        )
    ) == 1
EOF
cat > tests/architecture/test_P5_boundaries.py <<'EOF'
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED = (
    "raw_log",
    "patch_body",
    "diff_body",
    "developer_email",
    "github_actor",
    "automatic_merge",
    "merge_pull_request",
    "l9_debt_intelligence.internal",
    "l9_debt_intelligence.private",
)
def test_feedback_runtime_has_no_prohibited_payload_fields() -> None:
    feedback = SOURCE / "feedback"
    exemptions = {
        "privacy.py",
    }
    for path in feedback.rglob("*.py"):
        if path.name in exemptions:
            continue
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED:
            assert term not in content, (
                f"{path} contains prohibited feedback "
                f"term {term}"
            )
def test_no_private_intelligence_imports() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        assert (
            "l9_debt_intelligence.internal"
            not in content
        )
        assert (
            "l9_debt_intelligence.private"
            not in content
        )
EOF
touch tests/feedback/__init__.py
touch tests/privacy/__init__.py
touch tests/resilience/__init__.py
###############################################################################
# 17. Documentation
###############################################################################
cat > docs/architecture/ADRs/ADR-RESOLVER-021-feedback-is-aggregate-only.md <<'EOF'
# ADR-RESOLVER-021: Intelligence feedback is aggregate-only
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
Feedback events contain classifications, fingerprints, canonical IDs, counts,
buckets, terminal states, and hashed provenance.
They do not contain raw logs, source code, patches, diffs, paths, credentials,
or developer identity.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-022-repositories-are-pseudonymized.md <<'EOF'
# ADR-RESOLVER-022: Repository identity is pseudonymized
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
The raw repository owner and name are never transmitted in feedback events.
Repository identity is represented by HMAC-SHA256 using an operator-controlled
secret key.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-023-feedback-uses-a-durable-outbox.md <<'EOF'
# ADR-RESOLVER-023: Feedback uses a durable outbox
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
Every validated feedback event is written atomically to a local owner-only
outbox before delivery.
Successful delivery records a receipt. Exhausted or permanent failures enter
dead-letter state.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-024-feedback-delivery-is-idempotent.md <<'EOF'
# ADR-RESOLVER-024: Feedback delivery is idempotent
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
Event identity and idempotency keys are deterministic for a resolution outcome.
HTTP 409 is treated as successful duplicate acknowledgement.
EOF
cat >> README.md <<'EOF'
## RESOLVER-P5: Intelligence feedback
P5 emits privacy-safe resolution outcomes to the Intelligence subsystem.
```text
resolution outcome
        ↓
aggregate event construction
        ↓
repository pseudonymization
        ↓
privacy validation
        ↓
deterministic event ID
        ↓
durable outbox
        ↓
bounded delivery retries
        ├── delivered
        ├── duplicate
        └── dead_letter

Feedback payloads include

* failure fingerprint and category;
* confidence bucket;
* terminal state;
* repeated-failure indicator;
* attempt number;
* remediation class;
* changed-file count;
* changed-line bucket;
* validation outcome;
* canonical SDK finding and contract IDs;
* capability profile;
* hashed provenance.

Feedback payloads exclude

* raw logs;
* source code;
* patches and diffs;
* file paths;
* branch names;
* commit messages;
* credentials;
* developer identity;
* raw repository names.

JSON-file delivery

l9-debt-resolver publish-feedback \
  --event feedback-event.json \
  --outbox .resolver-feedback-outbox \
  --transport json-file \
  --destination feedback-export

HTTPS delivery

export L9_FEEDBACK_TOKEN='...'
l9-debt-resolver publish-feedback \
  --event feedback-event.json \
  --outbox .resolver-feedback-outbox \
  --transport https \
  --destination https://intelligence.example/api/v1/events

Drain pending feedback

l9-debt-resolver drain-feedback-outbox \
  --outbox .resolver-feedback-outbox \
  --transport json-file \
  --destination feedback-export

EOF

python3 - <<‘PY’
from pathlib import Path

path = Path(“ROADMAP.md”)
content = path.read_text(encoding=“utf-8”)

content = content.replace(
“””## RESOLVER-P5 — Intelligence feedback

Status: Planned

* resolution events
* repeated-failure telemetry
* privacy-safe payloads
* delivery retries
* idempotency”””,
    “””## RESOLVER-P5 — Intelligence feedback

Status: Implemented

* privacy-safe resolution events
* repeated-failure telemetry
* repository pseudonymization
* deterministic event identities
* deterministic idempotency keys
* corpus-safe provenance
* durable local outbox
* bounded delivery retries
* Retry-After support
* JSON-file transport
* HTTPS transport
* delivery receipts
* dead-letter state”””,
    )

path.write_text(content, encoding=“utf-8”)
PY

###############################################################################

18. Acceptance gates

###############################################################################

cat > .l9/phase-5-acceptance-gates.yaml <<‘EOF’
schema: l9.phase-acceptance-gates/v1

repository: Quantum-L9/l9-ci-debt-resolver
phase: RESOLVER-P5

gates:

* id: p5-aggregate-only
    requirement: >
    Feedback contains aggregate classification, remediation, validation,
    correlation, and terminal-state data only.
* id: p5-no-raw-logs
    requirement: >
    Raw CI logs, stdout, stderr, and log excerpts cannot enter feedback.
* id: p5-no-source
    requirement: >
    Source content, patches, diffs, and file paths cannot enter feedback.
* id: p5-no-developer-identity
    requirement: >
    Developer names, emails, actors, IP addresses, and credentials cannot
    enter feedback.
* id: p5-pseudonymization
    requirement: >
    Raw repository identity is replaced with HMAC-SHA256 pseudonymization.
* id: p5-deterministic-ID
    requirement: >
    Equivalent outcomes produce the same event ID and idempotency key.
* id: p5-outbox-before-delivery
    requirement: >
    Events are atomically persisted before transport delivery.
* id: p5-retry-bounds
    requirement: >
    Retry attempts and delays are bounded.
* id: p5-retry-after
    requirement: >
    Bounded Retry-After values are honored.
* id: p5-duplicate-success
    requirement: >
    Duplicate acknowledgements are treated as successful idempotent delivery.
* id: p5-dead-letter
    requirement: >
    Permanent and exhausted delivery failures enter dead-letter state.
* id: p5-public-boundary
    requirement: >
    Resolver uses a public Intelligence event contract and no private
    Intelligence modules.
* id: p5-no-prevention
    requirement: >
    Resolver does not create prevention artifacts or mine the corpus.
    EOF

###############################################################################

19. CI

###############################################################################

cat > .github/workflows/phase-5-intelligence-feedback.yml <<‘EOF’
name: RESOLVER-P5 Intelligence Feedback

on:
pull_request:
push:
branches:
- main

permissions:
contents: read

jobs:
intelligence-feedback:
runs-on: ubuntu-latest
timeout-minutes: 20

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
  - name: Feedback tests
    run: pytest tests/feedback
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

20. Structural validation

###############################################################################

python3 -m compileall -q src

python3 - <<‘PY’
from future import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path.cwd()

required = [
“.l9/intelligence-feedback-contract.yaml”,
“.l9/feedback-privacy-policy.yaml”,
“.l9/phase-5-acceptance-gates.yaml”,
“schemas/resolver/intelligence-feedback-event.schema.json”,
“schemas/resolver/feedback-delivery-receipt.schema.json”,
“schemas/resolver/feedback-outbox-record.schema.json”,
“src/l9_debt_resolver/feedback/privacy.py”,
“src/l9_debt_resolver/feedback/identity.py”,
“src/l9_debt_resolver/feedback/builder.py”,
“src/l9_debt_resolver/feedback/protocol.py”,
“src/l9_debt_resolver/feedback/file_transport.py”,
“src/l9_debt_resolver/feedback/http_transport.py”,
“src/l9_debt_resolver/feedback/outbox.py”,
“src/l9_debt_resolver/feedback/delivery.py”,
“src/l9_debt_resolver/runtime/feedback_service.py”,
“tests/feedback/test_identity.py”,
“tests/feedback/test_file_transport.py”,
“tests/feedback/test_outbox.py”,
“tests/privacy/test_feedback_privacy.py”,
“tests/resilience/test_feedback_delivery.py”,
“.github/workflows/phase-5-intelligence-feedback.yml”,
]

missing = [
item
for item in required
if not (root / item).is_file()
]

if missing:
raise SystemExit(
f”RESOLVER-P5 required files missing: {missing}”
)

for path in sorted(
(root / “schemas/resolver”).glob(”*.json”)
):
schema = json.loads(
path.read_text(encoding=“utf-8”)
)
Draft202012Validator.check_schema(schema)

source = root / “src/l9_debt_resolver”

prohibited_imports = (
“l9_debt_intelligence.internal”,
“l9_debt_intelligence.private”,
)

for path in source.rglob(”*.py”):
content = path.read_text(
encoding=“utf-8”
).lower()

for term in prohibited_imports:
    if term in content:
        raise SystemExit(
            f"prohibited Intelligence dependency "
            f"{term!r} in {path}"
        )

feedback_source = source / “feedback”

prohibited_feedback_terms = (
‘“raw_log”’,
‘“patch_body”’,
‘“diff_body”’,
‘“developer_email”’,
‘“github_actor”’,
‘“repository_path”’,
‘“absolute_path”’,
)

for path in feedback_source.rglob(”*.py”):
if path.name == “privacy.py”:
continue

content = path.read_text(
    encoding="utf-8"
).lower()
for term in prohibited_feedback_terms:
    if term in content:
        raise SystemExit(
            f"prohibited feedback field "
            f"{term!r} in {path}"
        )

capabilities = (
source
/ “runtime”
/ “capabilities.py”
).read_text(encoding=“utf-8”)

required_capabilities = (
‘“privacy_safe_feedback_events”: True’,
‘“repository_pseudonymization”: True’,
‘“deterministic_feedback_IDs”: True’,
‘“feedback_idempotency”: True’,
‘“corpus_safe_provenance”: True’,
‘“repeated_failure_telemetry”: True’,
‘“durable_feedback_outbox”: True’,
‘“bounded_delivery_retries”: True’,
‘“retry_after_support”: True’,
‘“dead_letter_state”: True’,
‘“delivery_receipts”: True’,
‘“raw_log_feedback”: False’,
‘“source_content_feedback”: False’,
‘“patch_content_feedback”: False’,
‘“developer_identity_feedback”: False’,
‘“PR_Repair_delegation”: False’,
)

for capability in required_capabilities:
if capability not in capabilities:
raise SystemExit(
f”missing capability declaration: {capability}”
)

print(
json.dumps(
{
“schema_version”: “l9.phase-build-result/v1”,
“repository”: (
“Quantum-L9/l9-ci-debt-resolver”
),
“version”: “0.6.0”,
“phase”: “RESOLVER-P5”,
“status”: “built”,
“privacy_safe_feedback_events”: True,
“repository_pseudonymization”: True,
“deterministic_event_identity”: True,
“idempotent_delivery”: True,
“corpus_safe_provenance”: True,
“repeated_failure_telemetry”: True,
“durable_outbox”: True,
“bounded_delivery_retries”: True,
“retry_after_support”: True,
“dead_letter_state”: True,
“delivery_receipts”: True,
“raw_log_transmission”: False,
“source_content_transmission”: False,
“patch_content_transmission”: False,
“developer_identity_transmission”: False,
“corpus_mining”: False,
“prevention_compilation”: False,
“PR_Repair_delegation”: False
},
sort_keys=True,
separators=(”,”, “:”),
)
)
PY

printf ‘\n’
printf ‘RESOLVER-P5 build complete.\n’
printf ‘\n’
printf ‘Implemented:\n’
printf ’  - privacy-safe Intelligence feedback events\n’
printf ’  - repository HMAC pseudonymization\n’
printf ’  - deterministic event IDs\n’
printf ’  - deterministic idempotency keys\n’
printf ’  - repeated-failure telemetry\n’
printf ’  - corpus-safe hashed provenance\n’
printf ’  - durable owner-only outbox\n’
printf ’  - bounded retry with Retry-After\n’
printf ’  - deterministic retry jitter\n’
printf ’  - duplicate acknowledgement handling\n’
printf ’  - delivery receipts\n’
printf ’  - dead-letter state\n’
printf ’  - JSON-file transport\n’
printf ’  - HTTPS transport\n’
printf ’  - no raw logs, source, patches, paths, or identity\n’
printf ‘\n’
printf ‘Validate with:\n’
printf “  python -m pip install -e ‘.[dev]’\n”
printf ’  pytest\n’
printf ’  ruff check .\n’
printf ’  mypy src\n’
printf ’  l9-debt-resolver capabilities\n’
printf ‘\n’
printf ‘Next phase:\n’
printf ’  RESOLVER-P6 — optional PR_Repair delegation for unsupported or\n’
printf ’  approval-required outcomes, with typed handoff contracts,\n’
printf ’  bounded context, privacy gates, callback verification, and no\n’
printf ’  direct authority transfer over merge or protected branches.\n’

:::
P5 completes the resolver’s direct remediation loop. P6 should remain an optional delegation boundary: Resolver may request a repair proposal from `PR_Repair`, but must retain evidence authority, validation authority, push policy, attempt limits, and terminal-state ownership.