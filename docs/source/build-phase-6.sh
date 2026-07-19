#!/usr/bin/env bash
set -euo pipefail
###############################################################################
# Quantum-L9/l9-ci-debt-resolver
# RESOLVER-P6 - Constrained PR_Repair Delegation
#
# Incremental build over RESOLVER-P0 through RESOLVER-P5.
#
# Implements:
#   - typed PR_Repair handoff requests
#   - bounded delegation context
#   - privacy-safe handoff payloads
#   - explicit delegation eligibility policy
#   - proposal-only authority boundary
#   - signed callback envelopes
#   - callback replay protection
#   - proposal schema and semantic validation
#   - evidence/fingerprint/snapshot binding
#   - protected-path and scope verification
#   - conversion into Resolver remediation plans
#   - durable delegation ledger
#   - bounded callback retries
#   - delegation terminal states
#   - file and HTTPS transports
#   - P6 CLI commands and tests
#
# PR_Repair never receives authority to:
#   - mutate the repository
#   - execute validation
#   - create or push branches
#   - trigger CI reruns
#   - merge changes
#   - override protected paths
#   - change attempt limits
#   - emit Resolver terminal states
###############################################################################
fail() {
  printf 'RESOLVER-P6: %s\n' "$*" >&2
  exit 1
}
require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "required command not found: $1"
}
require_command python3
[[ -d .git ]] \
  || fail "run from the l9-ci-debt-resolver repository root"
[[ -f .l9/intelligence-feedback-contract.yaml ]] \
  || fail "RESOLVER-P5 feedback contract is missing"
[[ -f src/l9_debt_resolver/runtime/feedback_service.py ]] \
  || fail "RESOLVER-P5 runtime is missing"
mkdir -p \
  .github/workflows \
  .l9 \
  docs/architecture/ADRs \
  schemas/resolver \
  src/l9_debt_resolver/delegation \
  tests/delegation \
  tests/privacy \
  tests/resilience \
  tests/architecture
###############################################################################
# 1. Authoritative P6 contracts
###############################################################################
cat > .l9/pr-repair-delegation-contract.yaml <<'EOF'
schema: l9.resolver-pr-repair-delegation-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P6
  status: authoritative
purpose:
  description: >
    Delegate proposal generation to PR_Repair only when the Resolver cannot
    safely produce a bounded remediation directly.
authority:
  resolver_retains:
    - CI evidence authority
    - classification authority
    - repository snapshot authority
    - validation authority
    - protected-path policy
    - workspace mutation authority
    - branch policy
    - push authorization
    - rerun observation
    - attempt limits
    - terminal-state selection
    - feedback event emission
  PR_Repair_may:
    - analyze bounded, privacy-safe context
    - return a remediation proposal
    - return an explicit unsupported response
    - return clarification requirements as structured limitations
  PR_Repair_must_not:
    - mutate repositories
    - invoke Git
    - execute arbitrary commands
    - execute validation
    - create branches
    - push commits
    - trigger CI
    - merge changes
    - override Resolver policy
    - redefine SDK identities
    - create Resolver evidence
    - create Resolver classifications
    - emit Resolver terminal states
eligibility:
  allowed_when:
    - classification remediation eligibility is approval_required
    - classification remediation eligibility is unsupported
    - direct remediation policy rejected a proposal as insufficiently bounded
    - repeated failure occurred and attempt limit has not been exceeded
    - a new failure requires proposal generation
  prohibited_when:
    - evidence is incomplete
    - repository snapshot is unavailable
    - failure fingerprint is unavailable
    - privacy-safe context cannot be constructed
    - attempt limit has been reached
    - protected-path change is required
    - security or governance policy forbids delegation
request_context:
  allowed:
    - request ID
    - repository pseudonym
    - failure fingerprint
    - classification category
    - confidence bucket
    - remediation eligibility
    - failed-command hash
    - normalized error signatures
    - SDK snapshot identity hash
    - canonical entity IDs
    - canonical finding IDs
    - canonical contract IDs
    - related test IDs
    - language families
    - capability profile
    - allowed path hashes
    - maximum file count
    - maximum changed lines
    - maximum operations
    - limitation codes
    - callback endpoint identity
    - callback nonce
  prohibited:
    - raw logs
    - source code
    - repository files
    - patches
    - diffs
    - credentials
    - access tokens
    - raw repository identity
    - branch names
    - commit messages
    - developer identity
    - absolute paths
    - environment variables
    - arbitrary CI-provider payloads
proposal:
  required:
    - proposal ID
    - request ID
    - failure fingerprint
    - snapshot identity hash
    - proposal status
    - remediation class
    - bounded operations
    - evidence rationale
    - requested validation classes
    - limitations
    - callback signature
  operation:
    form: exact_text_replacement
    path_identity: HMAC path token
    required:
      - operation ID
      - path token
      - expected file hash
      - expected text hash
      - replacement text
      - replacement hash
      - evidence identity hashes
      - justification
  prohibited:
    - shell commands
    - Git commands
    - executable scripts
    - binary patches
    - unified diff
    - repository-wide replacement
    - path traversal
    - protected-path targeting
callback:
  authentication:
    algorithm: HMAC-SHA256
    secret_source: L9_PR_REPAIR_CALLBACK_KEY
  replay_protection:
    required:
      - request ID
      - callback nonce
      - proposal ID
      - timestamp
      - signature
      - durable nonce consumption
  timestamp_tolerance_seconds: 300
conversion:
  rule: >
    A PR_Repair proposal may be converted into a Resolver remediation plan only
    after identity binding, signature validation, replay validation, privacy
    validation, path-token resolution, protected-path enforcement, operation
    bounds, and replacement-hash verification succeed.
failure_behavior:
  invalid_signature: rejected
  replay: rejected
  expired_callback: rejected
  privacy_violation: rejected
  unknown_path_token: rejected
  protected_path: rejected
  bounds_exceeded: rejected
  snapshot_mismatch: rejected
  fingerprint_mismatch: rejected
  malformed_proposal: rejected
terminal_states:
  - proposal_accepted
  - proposal_rejected
  - delegation_unsupported
  - callback_timeout
  - callback_invalid
  - delegation_delivery_failed
EOF
cat > .l9/delegation-privacy-policy.yaml <<'EOF'
schema: l9.resolver-delegation-privacy-policy/v1
metadata:
  phase: RESOLVER-P6
  enforcement: fail_closed
maximums:
  request_bytes: 65536
  proposal_bytes: 262144
  signatures: 25
  entity_ids: 100
  finding_ids: 100
  contract_ids: 100
  test_ids: 100
  operations: 50
  replacement_bytes_per_operation: 1048576
  total_replacement_bytes: 10485760
forbidden_keys:
  - raw_log
  - source_code
  - source_content
  - patch
  - diff
  - branch
  - commit_message
  - credential
  - token
  - authorization
  - password
  - secret
  - environment
  - developer
  - actor
  - email
  - absolute_path
  - repository_path
forbidden_values:
  - bearer_token
  - GitHub_token
  - AWS_access_key
  - private_key
  - email_address
  - IP_address
  - Unix_absolute_path
  - Windows_absolute_path
  - credential_bearing_URL
  - multiline_source_content
EOF
###############################################################################
# 2. P6 schemas
###############################################################################
cat > schemas/resolver/pr-repair-request.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/pr-repair-request/v1",
  "title": "L9 Resolver PR Repair Request",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "request_id",
    "idempotency_key",
    "repository_pseudonym",
    "failure_fingerprint",
    "classification",
    "repository_context",
    "constraints",
    "callback",
    "created_at",
    "expires_at",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.pr-repair-request/v1"
    },
    "request_id": {
      "type": "string",
      "pattern": "^pr_repair_request_[0-9a-f]{64}$"
    },
    "idempotency_key": {
      "type": "string",
      "pattern": "^pr_repair_idempotency_[0-9a-f]{64}$"
    },
    "repository_pseudonym": {
      "type": "string",
      "pattern": "^repository_[0-9a-f]{64}$"
    },
    "failure_fingerprint": {
      "type": "string",
      "pattern": "^failure_[0-9a-f]{64}$"
    },
    "classification": {
      "$ref": "#/$defs/classification"
    },
    "repository_context": {
      "$ref": "#/$defs/repositoryContext"
    },
    "constraints": {
      "$ref": "#/$defs/constraints"
    },
    "callback": {
      "$ref": "#/$defs/callback"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "expires_at": {
      "type": "string",
      "format": "date-time"
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
    "classification": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "category",
        "confidence_bucket",
        "remediation_eligibility",
        "failed_command_hash",
        "normalized_error_signatures"
      ],
      "properties": {
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
        "remediation_eligibility": {
          "enum": [
            "automatic",
            "approval_required",
            "unsupported"
          ]
        },
        "failed_command_hash": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "normalized_error_signatures": {
          "type": "array",
          "maxItems": 25,
          "items": {
            "type": "string",
            "maxLength": 1000
          },
          "uniqueItems": true
        }
      }
    },
    "repositoryContext": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "snapshot_id_hash",
        "entity_ids",
        "finding_ids",
        "contract_ids",
        "related_test_ids",
        "language_families",
        "capability_profile",
        "allowed_path_tokens"
      ],
      "properties": {
        "snapshot_id_hash": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "entity_ids": {
          "type": "array",
          "maxItems": 100,
          "items": {
            "type": "string",
            "maxLength": 500
          },
          "uniqueItems": true
        },
        "finding_ids": {
          "type": "array",
          "maxItems": 100,
          "items": {
            "type": "string",
            "maxLength": 500
          },
          "uniqueItems": true
        },
        "contract_ids": {
          "type": "array",
          "maxItems": 100,
          "items": {
            "type": "string",
            "maxLength": 500
          },
          "uniqueItems": true
        },
        "related_test_ids": {
          "type": "array",
          "maxItems": 100,
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
        "capability_profile": {
          "type": "array",
          "items": {
            "type": "string",
            "maxLength": 200
          },
          "uniqueItems": true
        },
        "allowed_path_tokens": {
          "type": "array",
          "maxItems": 100,
          "items": {
            "type": "string",
            "pattern": "^path_[0-9a-f]{64}$"
          },
          "uniqueItems": true
        }
      }
    },
    "constraints": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "maximum_changed_files",
        "maximum_changed_lines",
        "maximum_operations",
        "allowed_remediation_classes",
        "protected_paths_enforced",
        "validation_required",
        "remote_authority_granted"
      ],
      "properties": {
        "maximum_changed_files": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "maximum_changed_lines": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10000
        },
        "maximum_operations": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "allowed_remediation_classes": {
          "type": "array",
          "items": {
            "enum": [
              "configuration",
              "dependency",
              "bounded_source",
              "generated_file"
            ]
          },
          "uniqueItems": true
        },
        "protected_paths_enforced": {
          "const": true
        },
        "validation_required": {
          "const": true
        },
        "remote_authority_granted": {
          "const": false
        }
      }
    },
    "callback": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "callback_id",
        "nonce",
        "signature_algorithm"
      ],
      "properties": {
        "callback_id": {
          "type": "string",
          "pattern": "^callback_[0-9a-f]{64}$"
        },
        "nonce": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "signature_algorithm": {
          "const": "HMAC-SHA256"
        }
      }
    }
  }
}
EOF
cat > schemas/resolver/pr-repair-proposal.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/pr-repair-proposal/v1",
  "title": "L9 PR Repair Proposal",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "proposal_id",
    "request_id",
    "failure_fingerprint",
    "snapshot_id_hash",
    "status",
    "remediation_class",
    "operations",
    "requested_validation_classes",
    "rationale",
    "limitations",
    "issued_at",
    "callback_nonce",
    "signature"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.pr-repair-proposal/v1"
    },
    "proposal_id": {
      "type": "string",
      "pattern": "^pr_repair_proposal_[0-9a-f]{64}$"
    },
    "request_id": {
      "type": "string",
      "pattern": "^pr_repair_request_[0-9a-f]{64}$"
    },
    "failure_fingerprint": {
      "type": "string",
      "pattern": "^failure_[0-9a-f]{64}$"
    },
    "snapshot_id_hash": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "status": {
      "enum": [
        "proposed",
        "unsupported"
      ]
    },
    "remediation_class": {
      "oneOf": [
        {
          "enum": [
            "configuration",
            "dependency",
            "bounded_source",
            "generated_file"
          ]
        },
        {
          "type": "null"
        }
      ]
    },
    "operations": {
      "type": "array",
      "maxItems": 50,
      "items": {
        "$ref": "#/$defs/operation"
      }
    },
    "requested_validation_classes": {
      "type": "array",
      "items": {
        "enum": [
          "original_failure",
          "targeted_test",
          "affected_contract",
          "graph_delta",
          "full_gate"
        ]
      },
      "uniqueItems": true
    },
    "rationale": {
      "type": "string",
      "minLength": 1,
      "maxLength": 4000
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 500
      },
      "uniqueItems": true
    },
    "issued_at": {
      "type": "string",
      "format": "date-time"
    },
    "callback_nonce": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "signature": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    }
  },
  "$defs": {
    "operation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "operation_id",
        "path_token",
        "expected_file_sha256",
        "expected_text_sha256",
        "replacement_text",
        "replacement_sha256",
        "evidence_id_hashes",
        "justification"
      ],
      "properties": {
        "operation_id": {
          "type": "string",
          "pattern": "^pr_operation_[0-9a-f]{64}$"
        },
        "path_token": {
          "type": "string",
          "pattern": "^path_[0-9a-f]{64}$"
        },
        "expected_file_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "expected_text_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "replacement_text": {
          "type": "string",
          "maxLength": 1048576
        },
        "replacement_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "evidence_id_hashes": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$"
          },
          "uniqueItems": true
        },
        "justification": {
          "type": "string",
          "minLength": 1,
          "maxLength": 2000
        }
      }
    }
  }
}
EOF
cat > schemas/resolver/delegation-record.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/delegation-record/v1",
  "title": "L9 Resolver Delegation Record",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "record_id",
    "request",
    "state",
    "delivery_attempts",
    "proposal_id",
    "terminal_state",
    "created_at",
    "updated_at",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.delegation-record/v1"
    },
    "record_id": {
      "type": "string",
      "pattern": "^delegation_record_[0-9a-f]{64}$"
    },
    "request": {
      "$ref": "l9://resolver/pr-repair-request/v1"
    },
    "state": {
      "enum": [
        "pending",
        "delivered",
        "awaiting_callback",
        "proposal_received",
        "proposal_accepted",
        "proposal_rejected",
        "unsupported",
        "dead_letter"
      ]
    },
    "delivery_attempts": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100
    },
    "proposal_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "terminal_state": {
      "type": [
        "string",
        "null"
      ]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
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
###############################################################################
# 3. Delegation models and errors
###############################################################################
cat > src/l9_debt_resolver/delegation/__init__.py <<'EOF'
"""Constrained PR_Repair proposal delegation."""
EOF
cat > src/l9_debt_resolver/delegation/errors.py <<'EOF'
from __future__ import annotations
class DelegationError(RuntimeError):
    """Base delegation failure."""
class DelegationNotEligibleError(DelegationError):
    """Failure is not eligible for PR_Repair delegation."""
class DelegationPrivacyError(DelegationError):
    """Delegation data contains prohibited information."""
class DelegationSignatureError(DelegationError):
    """Proposal signature is invalid."""
class DelegationReplayError(DelegationError):
    """Callback nonce was already consumed."""
class DelegationExpiredError(DelegationError):
    """Request or callback timestamp has expired."""
class DelegationProposalError(DelegationError):
    """Proposal violates the Resolver delegation contract."""
class DelegationDeliveryError(DelegationError):
    """Request delivery failed."""
class DelegationRetryableError(DelegationDeliveryError):
    """Request delivery may be retried."""
class DelegationPermanentError(DelegationDeliveryError):
    """Request delivery must not be retried."""
EOF
cat > src/l9_debt_resolver/delegation/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class PRRepairRequest:
    request_id: str
    idempotency_key: str
    repository_pseudonym: str
    failure_fingerprint: str
    classification: dict[str, Any]
    repository_context: dict[str, Any]
    constraints: dict[str, Any]
    callback: dict[str, Any]
    created_at: str
    expires_at: str
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.pr-repair-request/v1"
            ),
            "request_id": self.request_id,
            "idempotency_key": self.idempotency_key,
            "repository_pseudonym": (
                self.repository_pseudonym
            ),
            "failure_fingerprint": (
                self.failure_fingerprint
            ),
            "classification": self.classification,
            "repository_context": (
                self.repository_context
            ),
            "constraints": self.constraints,
            "callback": self.callback,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class PRRepairOperation:
    operation_id: str
    path_token: str
    expected_file_sha256: str
    expected_text_sha256: str
    replacement_text: str
    replacement_sha256: str
    evidence_id_hashes: tuple[str, ...]
    justification: str
@dataclass(frozen=True)
class PRRepairProposal:
    proposal_id: str
    request_id: str
    failure_fingerprint: str
    snapshot_id_hash: str
    status: str
    remediation_class: str | None
    operations: tuple[PRRepairOperation, ...]
    requested_validation_classes: tuple[str, ...]
    rationale: str
    limitations: tuple[str, ...]
    issued_at: str
    callback_nonce: str
    signature: str
    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.pr-repair-proposal/v1"
            ),
            "proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "failure_fingerprint": (
                self.failure_fingerprint
            ),
            "snapshot_id_hash": (
                self.snapshot_id_hash
            ),
            "status": self.status,
            "remediation_class": (
                self.remediation_class
            ),
            "operations": [
                {
                    "operation_id": item.operation_id,
                    "path_token": item.path_token,
                    "expected_file_sha256": (
                        item.expected_file_sha256
                    ),
                    "expected_text_sha256": (
                        item.expected_text_sha256
                    ),
                    "replacement_text": (
                        item.replacement_text
                    ),
                    "replacement_sha256": (
                        item.replacement_sha256
                    ),
                    "evidence_id_hashes": list(
                        item.evidence_id_hashes
                    ),
                    "justification": (
                        item.justification
                    ),
                }
                for item in self.operations
            ],
            "requested_validation_classes": list(
                self.requested_validation_classes
            ),
            "rationale": self.rationale,
            "limitations": list(self.limitations),
            "issued_at": self.issued_at,
            "callback_nonce": self.callback_nonce,
        }
    def as_dict(self) -> dict[str, Any]:
        return {
            **self.unsigned_dict(),
            "signature": self.signature,
        }
@dataclass(frozen=True)
class DelegationRecord:
    record_id: str
    request: PRRepairRequest
    state: str
    delivery_attempts: int
    proposal_id: str | None
    terminal_state: str | None
    created_at: str
    updated_at: str
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.delegation-record/v1"
            ),
            "record_id": self.record_id,
            "request": self.request.as_dict(),
            "state": self.state,
            "delivery_attempts": (
                self.delivery_attempts
            ),
            "proposal_id": self.proposal_id,
            "terminal_state": self.terminal_state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "limitations": list(self.limitations),
        }
EOF
###############################################################################
# 4. Delegation privacy validator
###############################################################################
cat > src/l9_debt_resolver/delegation/privacy.py <<'EOF'
from __future__ import annotations
import json
import re
from typing import Any
from .errors import DelegationPrivacyError
FORBIDDEN_KEYS = {
    "raw_log",
    "source_code",
    "source_content",
    "patch",
    "diff",
    "branch",
    "commit_message",
    "credential",
    "token",
    "authorization",
    "password",
    "secret",
    "environment",
    "developer",
    "actor",
    "email",
    "absolute_path",
    "repository_path",
}
SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"
    ),
    re.compile(
        r"\b(?:ghp|github_pat|gho|ghu|ghs|ghr)_"
        r"[A-Za-z0-9_]{20,}\b"
    ),
    re.compile(
        r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    ),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    ),
    re.compile(
        r"\b[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    re.compile(
        r"(?<![A-Za-z0-9_.-])/"
        r"(?:home|Users|tmp|var|workspace|github)/"
    ),
    re.compile(
        r"\b[A-Za-z]:\\"
        r"(?:Users|Temp|workspace|runner)\\"
    ),
)
MAX_REQUEST_BYTES = 65536
MAX_PROPOSAL_BYTES = 262144
MAX_DEPTH = 12
MAX_STRING = 1048576
def validate_request(
    document: dict[str, Any],
) -> None:
    _validate_document(
        document,
        maximum_bytes=MAX_REQUEST_BYTES,
    )
def validate_proposal(
    document: dict[str, Any],
) -> None:
    _validate_document(
        document,
        maximum_bytes=MAX_PROPOSAL_BYTES,
    )
def _validate_document(
    document: dict[str, Any],
    *,
    maximum_bytes: int,
) -> None:
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > maximum_bytes:
        raise DelegationPrivacyError(
            "delegation document exceeds size limit"
        )
    _walk(
        document,
        path="$",
        depth=0,
    )
def _walk(
    value: Any,
    *,
    path: str,
    depth: int,
) -> None:
    if depth > MAX_DEPTH:
        raise DelegationPrivacyError(
            f"delegation document exceeds depth at {path}"
        )
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).casefold()
            if normalized in FORBIDDEN_KEYS:
                raise DelegationPrivacyError(
                    f"forbidden delegation key at "
                    f"{path}.{key}"
                )
            _walk(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise DelegationPrivacyError(
                f"delegation string too large at {path}"
            )
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(value):
                raise DelegationPrivacyError(
                    f"sensitive delegation value at {path}"
                )
        if (
            "\n" in value
            and len(value.splitlines()) > 2000
        ):
            raise DelegationPrivacyError(
                f"excessive multiline content at {path}"
            )
        return
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return
    raise DelegationPrivacyError(
        f"unsupported delegation value at {path}"
    )
EOF
###############################################################################
# 5. Identity, path tokens, and callback signatures
###############################################################################
cat > src/l9_debt_resolver/delegation/identity.py <<'EOF'
from __future__ import annotations
import hashlib
import hmac
import json
import secrets
from typing import Any
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
def stable_hash(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()
def request_id(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "pr_repair_request_",
        material,
    )
def request_idempotency_key(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "pr_repair_idempotency_",
        material,
    )
def callback_id(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "callback_",
        material,
    )
def new_nonce() -> str:
    return secrets.token_hex(32)
def path_token(
    *,
    repository_path: str,
    path_key: bytes,
) -> str:
    if len(path_key) < 32:
        raise ValueError(
            "path-token key must be at least 32 bytes"
        )
    digest = hmac.new(
        path_key,
        repository_path.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"path_{digest}"
def proposal_signature(
    *,
    unsigned_document: dict[str, Any],
    callback_key: bytes,
) -> str:
    if len(callback_key) < 32:
        raise ValueError(
            "callback key must be at least 32 bytes"
        )
    canonical = json.dumps(
        unsigned_document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(
        callback_key,
        canonical,
        hashlib.sha256,
    ).hexdigest()
def verify_proposal_signature(
    *,
    unsigned_document: dict[str, Any],
    signature: str,
    callback_key: bytes,
) -> bool:
    expected = proposal_signature(
        unsigned_document=unsigned_document,
        callback_key=callback_key,
    )
    return hmac.compare_digest(
        expected,
        signature,
    )
EOF
###############################################################################
# 6. Delegation request builder
###############################################################################
cat > src/l9_debt_resolver/delegation/builder.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import (
    RepositoryCorrelation,
)
from l9_debt_resolver.feedback.identity import (
    repository_pseudonym,
)
from .errors import DelegationNotEligibleError
from .identity import (
    callback_id,
    new_nonce,
    path_token,
    request_id,
    request_idempotency_key,
    stable_hash,
)
from .models import PRRepairRequest
from .privacy import validate_request
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
def build_pr_repair_request(
    *,
    repository: str,
    repository_pseudonym_key: bytes,
    path_token_key: bytes,
    allowed_paths: tuple[str, ...],
    classification_trace: ClassificationTrace,
    correlation: RepositoryCorrelation,
    normalized_error_signatures: tuple[str, ...],
    maximum_changed_files: int = 10,
    maximum_changed_lines: int = 500,
    maximum_operations: int = 50,
    expires_in_seconds: int = 900,
) -> tuple[
    PRRepairRequest,
    dict[str, str],
]:
    classification = (
        classification_trace.classification
    )
    if (
        classification.remediation_eligibility
        not in {
            "approval_required",
            "unsupported",
        }
    ):
        raise DelegationNotEligibleError(
            "automatic classifications should use "
            "Resolver direct remediation"
        )
    if not classification.evidence_ids:
        raise DelegationNotEligibleError(
            "delegation requires evidence identities"
        )
    if not correlation.repository_snapshot_id:
        raise DelegationNotEligibleError(
            "delegation requires SDK snapshot identity"
        )
    token_map = {
        path_token(
            repository_path=path,
            path_key=path_token_key,
        ): path
        for path in sorted(set(allowed_paths))
    }
    created = utc_now()
    expires = created + timedelta(
        seconds=expires_in_seconds
    )
    nonce = new_nonce()
    repository_id = repository_pseudonym(
        repository=repository,
        pseudonym_key=(
            repository_pseudonym_key
        ),
    )
    identity_material = {
        "repository_pseudonym": repository_id,
        "failure_fingerprint": (
            classification.failure_fingerprint
        ),
        "snapshot_id_hash": stable_hash(
            correlation.repository_snapshot_id
        ),
        "classification_id_hash": stable_hash(
            classification.classification_id
        ),
        "allowed_path_tokens": sorted(
            token_map
        ),
    }
    request_identifier = request_id(
        identity_material
    )
    callback_identifier = callback_id(
        {
            "request_id": request_identifier,
            "nonce": nonce,
        }
    )
    request = PRRepairRequest(
        request_id=request_identifier,
        idempotency_key=(
            request_idempotency_key(
                identity_material
            )
        ),
        repository_pseudonym=repository_id,
        failure_fingerprint=(
            classification.failure_fingerprint
        ),
        classification={
            "category": classification.category,
            "confidence_bucket": (
                _confidence_bucket(
                    classification.confidence
                )
            ),
            "remediation_eligibility": (
                classification
                .remediation_eligibility
            ),
            "failed_command_hash": (
                stable_hash(
                    classification.failed_command
                )
            ),
            "normalized_error_signatures": list(
                sorted(
                    set(
                        normalized_error_signatures
                    )
                )[:25]
            ),
        },
        repository_context={
            "snapshot_id_hash": stable_hash(
                correlation
                .repository_snapshot_id
            ),
            "entity_ids": [
                reference.id
                for reference in (
                    correlation.entity_references
                )
            ][:100],
            "finding_ids": [
                reference.id
                for reference in (
                    correlation.finding_references
                )
            ][:100],
            "contract_ids": [
                reference.id
                for reference in (
                    correlation.contract_references
                )
            ][:100],
            "related_test_ids": [
                reference.id
                for reference in (
                    correlation
                    .related_test_references
                )
            ][:100],
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
            "capability_profile": list(
                correlation.capability_profile
            ),
            "allowed_path_tokens": list(
                sorted(token_map)
            ),
        },
        constraints={
            "maximum_changed_files": (
                maximum_changed_files
            ),
            "maximum_changed_lines": (
                maximum_changed_lines
            ),
            "maximum_operations": (
                maximum_operations
            ),
            "allowed_remediation_classes": [
                "configuration",
                "dependency",
                "bounded_source",
                "generated_file",
            ],
            "protected_paths_enforced": True,
            "validation_required": True,
            "remote_authority_granted": False,
        },
        callback={
            "callback_id": callback_identifier,
            "nonce": nonce,
            "signature_algorithm": (
                "HMAC-SHA256"
            ),
        },
        created_at=created.isoformat().replace(
            "+00:00",
            "Z",
        ),
        expires_at=expires.isoformat().replace(
            "+00:00",
            "Z",
        ),
        limitations=tuple(
            sorted(
                {
                    *classification.limitations,
                    *correlation.limitations,
                }
            )
        ),
    )
    validate_request(
        request.as_dict()
    )
    return request, token_map
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
EOF
###############################################################################
# 7. Proposal loader and validator
###############################################################################
cat > src/l9_debt_resolver/delegation/proposal.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from l9_debt_resolver.remediation.policy import (
    validate_mutable_path,
)
from .errors import (
    DelegationExpiredError,
    DelegationProposalError,
    DelegationSignatureError,
)
from .identity import (
    stable_hash,
    verify_proposal_signature,
)
from .models import (
    PRRepairOperation,
    PRRepairProposal,
    PRRepairRequest,
)
from .privacy import validate_proposal
def load_proposal(
    path: Path,
) -> PRRepairProposal:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise DelegationProposalError(
            "proposal must be an object"
        )
    operations = tuple(
        _parse_operation(item)
        for item in value.get(
            "operations",
            [],
        )
    )
    proposal = PRRepairProposal(
        proposal_id=str(
            value["proposal_id"]
        ),
        request_id=str(
            value["request_id"]
        ),
        failure_fingerprint=str(
            value["failure_fingerprint"]
        ),
        snapshot_id_hash=str(
            value["snapshot_id_hash"]
        ),
        status=str(value["status"]),
        remediation_class=(
            str(value["remediation_class"])
            if value.get(
                "remediation_class"
            )
            is not None
            else None
        ),
        operations=operations,
        requested_validation_classes=tuple(
            sorted(
                str(item)
                for item in value.get(
                    "requested_validation_classes",
                    [],
                )
            )
        ),
        rationale=str(value["rationale"]),
        limitations=tuple(
            sorted(
                str(item)
                for item in value.get(
                    "limitations",
                    [],
                )
            )
        ),
        issued_at=str(value["issued_at"]),
        callback_nonce=str(
            value["callback_nonce"]
        ),
        signature=str(value["signature"]),
    )
    validate_proposal(
        proposal.as_dict()
    )
    return proposal
def validate_proposal_contract(
    *,
    request: PRRepairRequest,
    proposal: PRRepairProposal,
    callback_key: bytes,
    repository_snapshot_id: str,
) -> None:
    if proposal.request_id != request.request_id:
        raise DelegationProposalError(
            "proposal request identity mismatch"
        )
    if (
        proposal.failure_fingerprint
        != request.failure_fingerprint
    ):
        raise DelegationProposalError(
            "proposal failure fingerprint mismatch"
        )
    if (
        proposal.snapshot_id_hash
        != stable_hash(repository_snapshot_id)
    ):
        raise DelegationProposalError(
            "proposal snapshot identity mismatch"
        )
    if (
        proposal.callback_nonce
        != request.callback["nonce"]
    ):
        raise DelegationProposalError(
            "proposal callback nonce mismatch"
        )
    issued_at = datetime.fromisoformat(
        proposal.issued_at.replace(
            "Z",
            "+00:00",
        )
    )
    now = datetime.now(timezone.utc)
    if abs(
        (now - issued_at).total_seconds()
    ) > 300:
        raise DelegationExpiredError(
            "proposal callback timestamp is outside "
            "the permitted tolerance"
        )
    if not verify_proposal_signature(
        unsigned_document=(
            proposal.unsigned_dict()
        ),
        signature=proposal.signature,
        callback_key=callback_key,
    ):
        raise DelegationSignatureError(
            "proposal callback signature is invalid"
        )
    if proposal.status == "unsupported":
        if proposal.operations:
            raise DelegationProposalError(
                "unsupported proposal cannot contain operations"
            )
        return
    if proposal.status != "proposed":
        raise DelegationProposalError(
            "unknown proposal status"
        )
    if not proposal.remediation_class:
        raise DelegationProposalError(
            "proposed remediation requires a class"
        )
    allowed_classes = set(
        request.constraints[
            "allowed_remediation_classes"
        ]
    )
    if (
        proposal.remediation_class
        not in allowed_classes
    ):
        raise DelegationProposalError(
            "proposal remediation class is not allowed"
        )
    maximum_operations = int(
        request.constraints[
            "maximum_operations"
        ]
    )
    if len(proposal.operations) > maximum_operations:
        raise DelegationProposalError(
            "proposal exceeds operation limit"
        )
    allowed_tokens = set(
        request.repository_context[
            "allowed_path_tokens"
        ]
    )
    total_replacement_bytes = 0
    for operation in proposal.operations:
        if operation.path_token not in allowed_tokens:
            raise DelegationProposalError(
                "proposal references unknown path token"
            )
        replacement_bytes = (
            operation.replacement_text.encode(
                "utf-8"
            )
        )
        total_replacement_bytes += len(
            replacement_bytes
        )
        if len(replacement_bytes) > 1048576:
            raise DelegationProposalError(
                "replacement exceeds per-operation limit"
            )
        actual_replacement_hash = (
            hashlib.sha256(
                replacement_bytes
            ).hexdigest()
        )
        if (
            actual_replacement_hash
            != operation.replacement_sha256
        ):
            raise DelegationProposalError(
                "replacement hash mismatch"
            )
    if total_replacement_bytes > 10485760:
        raise DelegationProposalError(
            "proposal exceeds total replacement limit"
        )
    required_validation = {
        "original_failure",
        "targeted_test",
        "affected_contract",
        "graph_delta",
    }
    if not required_validation.issubset(
        set(
            proposal
            .requested_validation_classes
        )
    ):
        raise DelegationProposalError(
            "proposal lacks required validation classes"
        )
def _parse_operation(
    value: object,
) -> PRRepairOperation:
    if not isinstance(value, dict):
        raise DelegationProposalError(
            "proposal operation must be an object"
        )
    return PRRepairOperation(
        operation_id=str(
            value["operation_id"]
        ),
        path_token=str(
            value["path_token"]
        ),
        expected_file_sha256=str(
            value["expected_file_sha256"]
        ),
        expected_text_sha256=str(
            value["expected_text_sha256"]
        ),
        replacement_text=str(
            value["replacement_text"]
        ),
        replacement_sha256=str(
            value["replacement_sha256"]
        ),
        evidence_id_hashes=tuple(
            sorted(
                str(item)
                for item in value[
                    "evidence_id_hashes"
                ]
            )
        ),
        justification=str(
            value["justification"]
        ),
    )
EOF
###############################################################################
# 8. Nonce ledger
###############################################################################
cat > src/l9_debt_resolver/delegation/nonce_ledger.py <<'EOF'
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from .errors import DelegationReplayError
class CallbackNonceLedger:
    def __init__(
        self,
        *,
        path: Path,
    ) -> None:
        self._path = path
    def consume(
        self,
        *,
        request_id: str,
        nonce: str,
        proposal_id: str,
    ) -> None:
        document = self._load()
        consumed = document.setdefault(
            "consumed",
            {},
        )
        key = f"{request_id}:{nonce}"
        if key in consumed:
            raise DelegationReplayError(
                "callback nonce has already been consumed"
            )
        consumed[key] = proposal_id
        self._write(document)
    def _load(self) -> dict[str, object]:
        if not self._path.exists():
            return {
                "schema_version": (
                    "l9.callback-nonce-ledger/v1"
                ),
                "consumed": {},
            }
        value = json.loads(
            self._path.read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(value, dict):
            raise ValueError(
                "callback nonce ledger must be an object"
            )
        return value
    def _write(
        self,
        value: dict[str, object],
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        descriptor, temporary = tempfile.mkstemp(
            dir=self._path.parent,
            prefix=".callback-nonce.",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
            ) as stream:
                json.dump(
                    value,
                    stream,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                self._path,
            )
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
EOF
###############################################################################
# 9. Convert accepted proposal into Resolver remediation plan
###############################################################################
cat > src/l9_debt_resolver/delegation/converter.py <<'EOF'
from __future__ import annotations
import hashlib
from pathlib import Path
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    ReplaceTextOperation,
)
from l9_debt_resolver.remediation.policy import (
    validate_mutable_path,
)
from .errors import DelegationProposalError
from .identity import stable_hash
from .models import (
    PRRepairProposal,
    PRRepairRequest,
)
def convert_proposal_to_remediation_plan(
    *,
    workspace_root: Path,
    request: PRRepairRequest,
    proposal: PRRepairProposal,
    path_token_map: dict[str, str],
    classification_trace: ClassificationTrace,
    repository_snapshot_id: str,
    repository_revision: str,
    validation_plan_id: str,
) -> RemediationPlan:
    if proposal.status != "proposed":
        raise DelegationProposalError(
            "unsupported response cannot be converted"
        )
    classification = (
        classification_trace.classification
    )
    evidence_hash_to_id = {
        stable_hash(evidence_id): evidence_id
        for evidence_id in (
            classification.evidence_ids
        )
    }
    operations = []
    for item in proposal.operations:
        path = path_token_map.get(
            item.path_token
        )
        if path is None:
            raise DelegationProposalError(
                "path token cannot be resolved"
            )
        validate_mutable_path(path)
        target = (
            workspace_root.resolve() / path
        ).resolve()
        try:
            target.relative_to(
                workspace_root.resolve()
            )
        except ValueError as error:
            raise DelegationProposalError(
                "resolved path escapes workspace"
            ) from error
        if not target.is_file():
            raise DelegationProposalError(
                f"proposal target does not exist: {path}"
            )
        file_bytes = target.read_bytes()
        file_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()
        if file_hash != item.expected_file_sha256:
            raise DelegationProposalError(
                f"proposal file hash mismatch: {path}"
            )
        text = file_bytes.decode("utf-8")
        matching_fragments = [
            candidate
            for candidate in _candidate_fragments(
                text
            )
            if hashlib.sha256(
                candidate.encode("utf-8")
            ).hexdigest()
            == item.expected_text_sha256
        ]
        if len(matching_fragments) != 1:
            raise DelegationProposalError(
                "expected-text hash must identify exactly "
                f"one bounded fragment in {path}"
            )
        evidence_ids = tuple(
            sorted(
                evidence_hash_to_id[value]
                for value in (
                    item.evidence_id_hashes
                )
                if value in evidence_hash_to_id
            )
        )
        if not evidence_ids:
            raise DelegationProposalError(
                "proposal operation lacks known evidence identity"
            )
        expected_text = matching_fragments[0]
        operation = ReplaceTextOperation(
            operation_id=namespaced_identity(
                "operation_",
                {
                    "proposal_operation_id": (
                        item.operation_id
                    ),
                    "path": path,
                    "expected_file_sha256": (
                        item.expected_file_sha256
                    ),
                    "expected_text_sha256": (
                        item.expected_text_sha256
                    ),
                    "replacement_sha256": (
                        item.replacement_sha256
                    ),
                },
            ),
            path=path,
            expected_file_sha256=(
                item.expected_file_sha256
            ),
            expected_text=expected_text,
            replacement_text=(
                item.replacement_text
            ),
            replacement_sha256=(
                item.replacement_sha256
            ),
            evidence_ids=evidence_ids,
            justification=item.justification,
        )
        operations.append(operation)
    expected_paths = tuple(
        sorted(
            {
                operation.path
                for operation in operations
            }
        )
    )
    maximum_files = int(
        request.constraints[
            "maximum_changed_files"
        ]
    )
    if len(expected_paths) > maximum_files:
        raise DelegationProposalError(
            "proposal exceeds changed-file limit"
        )
    plan_material = {
        "proposal_id": proposal.proposal_id,
        "classification_id": (
            classification.classification_id
        ),
        "failure_fingerprint": (
            classification.failure_fingerprint
        ),
        "repository_snapshot_id": (
            repository_snapshot_id
        ),
        "operations": [
            operation.operation_id
            for operation in operations
        ],
    }
    return RemediationPlan(
        plan_id=namespaced_identity(
            "remediation_plan_",
            plan_material,
        ),
        classification_id=(
            classification.classification_id
        ),
        failure_fingerprint=(
            classification.failure_fingerprint
        ),
        repository_snapshot_id=(
            repository_snapshot_id
        ),
        repository_revision=(
            repository_revision
        ),
        remediation_class=(
            proposal.remediation_class
            or "bounded_source"
        ),
        evidence_ids=tuple(
            sorted(
                classification.evidence_ids
            )
        ),
        justification=proposal.rationale,
        operations=tuple(operations),
        expected_changed_paths=expected_paths,
        expected_package_boundaries=(),
        expected_contract_ids=tuple(
            sorted(
                classification_trace
                .applicable_contract_ids
            )
        ),
        expected_dependency_edges=(),
        validation_plan_id=validation_plan_id,
        approval=None,
    )
def _candidate_fragments(
    text: str,
) -> tuple[str, ...]:
    lines = text.splitlines(
        keepends=True
    )
    candidates = set(lines)
    maximum_window = min(
        20,
        len(lines),
    )
    for window in range(
        2,
        maximum_window + 1,
    ):
        for start in range(
            0,
            len(lines) - window + 1,
        ):
            candidates.add(
                "".join(
                    lines[
                        start : start + window
                    ]
                )
            )
    return tuple(candidates)
EOF
###############################################################################
# 10. Delegation ledger
###############################################################################
cat > src/l9_debt_resolver/delegation/ledger.py <<'EOF'
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from .models import (
    DelegationRecord,
    PRRepairRequest,
)
class DelegationLedger:
    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory
    def create(
        self,
        request: PRRepairRequest,
    ) -> DelegationRecord:
        record = DelegationRecord(
            record_id=namespaced_identity(
                "delegation_record_",
                {
                    "request_id": (
                        request.request_id
                    ),
                    "idempotency_key": (
                        request.idempotency_key
                    ),
                },
            ),
            request=request,
            state="pending",
            delivery_attempts=0,
            proposal_id=None,
            terminal_state=None,
            created_at=request.created_at,
            updated_at=request.created_at,
            limitations=request.limitations,
        )
        existing = self.get(
            record.record_id
        )
        if existing is not None:
            return existing
        self.save(record)
        return record
    def save(
        self,
        record: DelegationRecord,
    ) -> None:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = (
            self._directory
            / f"{record.record_id}.json"
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
            prefix=".delegation-record.",
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
    def get(
        self,
        record_id: str,
    ) -> DelegationRecord | None:
        path = (
            self._directory
            / f"{record_id}.json"
        )
        if not path.exists():
            return None
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
        return _parse_record(value)
def _parse_record(
    value: object,
) -> DelegationRecord:
    if not isinstance(value, dict):
        raise ValueError(
            "delegation record must be an object"
        )
    request_value = value["request"]
    request = PRRepairRequest(
        request_id=request_value["request_id"],
        idempotency_key=(
            request_value["idempotency_key"]
        ),
        repository_pseudonym=(
            request_value[
                "repository_pseudonym"
            ]
        ),
        failure_fingerprint=(
            request_value[
                "failure_fingerprint"
            ]
        ),
        classification=dict(
            request_value["classification"]
        ),
        repository_context=dict(
            request_value[
                "repository_context"
            ]
        ),
        constraints=dict(
            request_value["constraints"]
        ),
        callback=dict(
            request_value["callback"]
        ),
        created_at=request_value[
            "created_at"
        ],
        expires_at=request_value[
            "expires_at"
        ],
        limitations=tuple(
            request_value["limitations"]
        ),
    )
    return DelegationRecord(
        record_id=value["record_id"],
        request=request,
        state=value["state"],
        delivery_attempts=int(
            value["delivery_attempts"]
        ),
        proposal_id=value.get(
            "proposal_id"
        ),
        terminal_state=value.get(
            "terminal_state"
        ),
        created_at=value["created_at"],
        updated_at=value["updated_at"],
        limitations=tuple(
            value["limitations"]
        ),
    )
EOF
###############################################################################
# 11. Delegation transports
###############################################################################
cat > src/l9_debt_resolver/delegation/protocol.py <<'EOF'
from __future__ import annotations
from typing import Protocol
from .models import PRRepairRequest
class PRRepairTransport(Protocol):
    name: str
    async def deliver(
        self,
        request: PRRepairRequest,
    ) -> str:
        """Deliver a request and return a transport receipt identity."""
EOF
cat > src/l9_debt_resolver/delegation/file_transport.py <<'EOF'
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile
from .models import PRRepairRequest
class JSONFilePRRepairTransport:
    name = "json_file"
    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory
    async def deliver(
        self,
        request: PRRepairRequest,
    ) -> str:
        return await asyncio.to_thread(
            self._deliver_sync,
            request,
        )
    def _deliver_sync(
        self,
        request: PRRepairRequest,
    ) -> str:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = (
            self._directory
            / f"{request.request_id}.json"
        )
        encoded = (
            json.dumps(
                request.as_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if destination.exists():
            existing = destination.read_bytes()
            if existing != encoded:
                raise RuntimeError(
                    "delegation request identity collision"
                )
            return hashlib.sha256(
                existing
            ).hexdigest()
        descriptor, temporary = tempfile.mkstemp(
            dir=self._directory,
            prefix=".pr-repair-request.",
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
        return hashlib.sha256(
            encoded
        ).hexdigest()
EOF
cat > src/l9_debt_resolver/delegation/http_transport.py <<'EOF'
from __future__ import annotations
import asyncio
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from .errors import (
    DelegationPermanentError,
    DelegationRetryableError,
)
from .models import PRRepairRequest
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
class HTTPSPRRepairTransport:
    name = "https"
    def __init__(
        self,
        *,
        endpoint: str,
        bearer_token: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not endpoint.startswith(
            "https://"
        ):
            raise ValueError(
                "PR_Repair endpoint must use HTTPS"
            )
        if not bearer_token:
            raise ValueError(
                "PR_Repair bearer token is required"
            )
        self._endpoint = endpoint
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
    async def deliver(
        self,
        request_value: PRRepairRequest,
    ) -> str:
        return await asyncio.to_thread(
            self._deliver_sync,
            request_value,
        )
    def _deliver_sync(
        self,
        request_value: PRRepairRequest,
    ) -> str:
        body = json.dumps(
            request_value.as_dict(),
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
                    request_value.idempotency_key
                ),
                "User-Agent": (
                    "l9-ci-debt-resolver-pr-repair/1"
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
                    raise DelegationPermanentError(
                        "unexpected PR_Repair response"
                    )
                return hashlib.sha256(
                    response_body
                ).hexdigest()
        except HTTPError as error:
            if error.code in SUCCESS:
                return hashlib.sha256(
                    error.read(
                        1024 * 1024
                    )
                ).hexdigest()
            if error.code in RETRYABLE:
                raise DelegationRetryableError(
                    "retryable PR_Repair response"
                ) from error
            raise DelegationPermanentError(
                "non-retryable PR_Repair response "
                f"{error.code}"
            ) from error
        except URLError as error:
            raise DelegationRetryableError(
                "PR_Repair endpoint unavailable"
            ) from error
EOF
###############################################################################
# 12. Delegation service
###############################################################################
cat > src/l9_debt_resolver/delegation/service.py <<'EOF'
from __future__ import annotations
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from .errors import (
    DelegationPermanentError,
    DelegationRetryableError,
)
from .ledger import DelegationLedger
from .models import (
    DelegationRecord,
    PRRepairRequest,
)
from .protocol import PRRepairTransport
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
class PRRepairDelegationService:
    def __init__(
        self,
        *,
        ledger: DelegationLedger,
        transport: PRRepairTransport,
        maximum_attempts: int = 5,
    ) -> None:
        self._ledger = ledger
        self._transport = transport
        self._maximum_attempts = (
            maximum_attempts
        )
    async def submit(
        self,
        request: PRRepairRequest,
    ) -> DelegationRecord:
        record = self._ledger.create(
            request
        )
        if record.state in {
            "delivered",
            "awaiting_callback",
            "proposal_received",
            "proposal_accepted",
            "unsupported",
        }:
            return record
        current = record
        while (
            current.delivery_attempts
            < self._maximum_attempts
        ):
            attempt = (
                current.delivery_attempts + 1
            )
            try:
                await self._transport.deliver(
                    request
                )
                current = replace(
                    current,
                    state="awaiting_callback",
                    delivery_attempts=attempt,
                    updated_at=utc_now(),
                )
                self._ledger.save(current)
                return current
            except DelegationPermanentError as error:
                current = replace(
                    current,
                    state="dead_letter",
                    delivery_attempts=attempt,
                    terminal_state=(
                        "delegation_delivery_failed"
                    ),
                    updated_at=utc_now(),
                    limitations=tuple(
                        sorted(
                            {
                                *current.limitations,
                                type(error).__name__,
                            }
                        )
                    ),
                )
                self._ledger.save(current)
                return current
            except DelegationRetryableError as error:
                if attempt >= self._maximum_attempts:
                    current = replace(
                        current,
                        state="dead_letter",
                        delivery_attempts=attempt,
                        terminal_state=(
                            "delegation_delivery_failed"
                        ),
                        updated_at=utc_now(),
                        limitations=tuple(
                            sorted(
                                {
                                    *current.limitations,
                                    "delivery_retries_exhausted",
                                    type(error).__name__,
                                }
                            )
                        ),
                    )
                    self._ledger.save(current)
                    return current
                current = replace(
                    current,
                    state="pending",
                    delivery_attempts=attempt,
                    updated_at=utc_now(),
                )
                self._ledger.save(current)
                await asyncio.sleep(
                    min(
                        30,
                        2 ** (attempt - 1),
                    )
                )
        return current
EOF
###############################################################################
# 13. Callback processing runtime
###############################################################################
cat > src/l9_debt_resolver/runtime/delegation_service.py <<'EOF'
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
)
from l9_debt_resolver.delegation.converter import (
    convert_proposal_to_remediation_plan,
)
from l9_debt_resolver.delegation.ledger import (
    DelegationLedger,
)
from l9_debt_resolver.delegation.models import (
    DelegationRecord,
    PRRepairProposal,
)
from l9_debt_resolver.delegation.nonce_ledger import (
    CallbackNonceLedger,
)
from l9_debt_resolver.delegation.proposal import (
    validate_proposal_contract,
)
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
class DelegationCallbackService:
    def __init__(
        self,
        *,
        ledger: DelegationLedger,
        nonce_ledger: CallbackNonceLedger,
    ) -> None:
        self._ledger = ledger
        self._nonce_ledger = nonce_ledger
    def accept_proposal(
        self,
        *,
        record: DelegationRecord,
        proposal: PRRepairProposal,
        callback_key: bytes,
        workspace_root: Path,
        path_token_map: dict[str, str],
        classification_trace: ClassificationTrace,
        repository_snapshot_id: str,
        repository_revision: str,
        validation_plan_id: str,
    ) -> tuple[
        DelegationRecord,
        RemediationPlan | None,
    ]:
        validate_proposal_contract(
            request=record.request,
            proposal=proposal,
            callback_key=callback_key,
            repository_snapshot_id=(
                repository_snapshot_id
            ),
        )
        self._nonce_ledger.consume(
            request_id=proposal.request_id,
            nonce=proposal.callback_nonce,
            proposal_id=proposal.proposal_id,
        )
        if proposal.status == "unsupported":
            updated = replace(
                record,
                state="unsupported",
                proposal_id=proposal.proposal_id,
                terminal_state=(
                    "delegation_unsupported"
                ),
                updated_at=utc_now(),
                limitations=tuple(
                    sorted(
                        {
                            *record.limitations,
                            *proposal.limitations,
                        }
                    )
                ),
            )
            self._ledger.save(updated)
            return updated, None
        remediation_plan = (
            convert_proposal_to_remediation_plan(
                workspace_root=workspace_root,
                request=record.request,
                proposal=proposal,
                path_token_map=path_token_map,
                classification_trace=(
                    classification_trace
                ),
                repository_snapshot_id=(
                    repository_snapshot_id
                ),
                repository_revision=(
                    repository_revision
                ),
                validation_plan_id=(
                    validation_plan_id
                ),
            )
        )
        updated = replace(
            record,
            state="proposal_accepted",
            proposal_id=proposal.proposal_id,
            terminal_state="proposal_accepted",
            updated_at=utc_now(),
            limitations=tuple(
                sorted(
                    {
                        *record.limitations,
                        *proposal.limitations,
                    }
                )
            ),
        )
        self._ledger.save(updated)
        return updated, remediation_plan
EOF
###############################################################################
# 14. Capabilities
###############################################################################
cat > src/l9_debt_resolver/runtime/capabilities.py <<'EOF'
from __future__ import annotations
from typing import Any
def resolver_capabilities() -> dict[str, Any]:
    return {
        "schema_version": "l9.resolver-capabilities/v1",
        "phase": "RESOLVER-P6",
        "capabilities": {
            "contract_validation": True,
            "typed_CI_evidence": True,
            "failed_log_acquisition": True,
            "SDK_repository_snapshots": True,
            "root_cause_classification": True,
            "bounded_remediation": True,
            "SDK_validation_execution": True,
            "repair_branch_policy": True,
            "CI_rerun_observation": True,
            "terminal_state_emission": True,
            "privacy_safe_feedback_events": True,
            "PR_Repair_delegation": True,
            "typed_delegation_requests": True,
            "bounded_delegation_context": True,
            "repository_pseudonymization": True,
            "path_tokenization": True,
            "signed_proposal_callbacks": True,
            "callback_replay_protection": True,
            "proposal_identity_binding": True,
            "proposal_privacy_validation": True,
            "proposal_scope_validation": True,
            "proposal_to_remediation_conversion": True,
            "durable_delegation_ledger": True,
            "bounded_delegation_retries": True,
            "json_file_PR_Repair_transport": True,
            "https_PR_Repair_transport": True,
            "PR_Repair_repository_mutation": False,
            "PR_Repair_validation_authority": False,
            "PR_Repair_push_authority": False,
            "PR_Repair_merge_authority": False,
            "PR_Repair_terminal_state_authority": False,
            "automatic_merge": False
        },
        "limitations": [
            "PR_Repair may generate proposals only.",
            "Resolver retains all mutation and validation authority.",
            "Resolver retains branch, push, rerun, attempt, and terminal-state authority.",
            "Raw logs, source content, paths, patches, credentials, and identity are excluded from delegation.",
            "Automatic merge remains prohibited."
        ]
    }
EOF
###############################################################################
# 15. Version and roadmap
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("pyproject.toml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    'version = "0.6.0"',
    'version = "0.7.0"',
)
path.write_text(content, encoding="utf-8")
path = Path("src/l9_debt_resolver/__init__.py")
content = path.read_text(encoding="utf-8")
content = content.replace(
    '__version__ = "0.6.0"',
    '__version__ = "0.7.0"',
)
path.write_text(content, encoding="utf-8")
path = Path(".l9/repo-spec.yaml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    "phase: RESOLVER-P5",
    "phase: RESOLVER-P6",
    1,
)
content = content.replace(
    "phase_name: intelligence_feedback",
    "phase_name: pr_repair_delegation",
    1,
)
content = content.replace(
    """  - phase: RESOLVER-P6
    name: pr_repair_delegation
    priority: medium
    status: planned""",
    """  - phase: RESOLVER-P6
    name: pr_repair_delegation
    priority: medium
    status: implemented""",
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 16. Tests
###############################################################################
cat > tests/delegation/test_identity.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.delegation.identity import (
    path_token,
    proposal_signature,
    verify_proposal_signature,
)
def test_path_tokens_are_deterministic() -> None:
    key = b"a" * 32
    first = path_token(
        repository_path="src/app.py",
        path_key=key,
    )
    second = path_token(
        repository_path="src/app.py",
        path_key=key,
    )
    assert first == second
    assert "src/app.py" not in first
def test_proposal_signature_verifies() -> None:
    key = b"b" * 32
    document = {
        "proposal_id": "proposal-1",
        "request_id": "request-1",
    }
    signature = proposal_signature(
        unsigned_document=document,
        callback_key=key,
    )
    assert verify_proposal_signature(
        unsigned_document=document,
        signature=signature,
        callback_key=key,
    )
EOF
cat > tests/privacy/test_delegation_privacy.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.delegation.errors import (
    DelegationPrivacyError,
)
from l9_debt_resolver.delegation.privacy import (
    validate_request,
)
@pytest.mark.parametrize(
    "document",
    [
        {"raw_log": "failure"},
        {"source_code": "print('x')"},
        {"repository_path": "src/app.py"},
        {"developer": "alice"},
        {"value": "ghp_abcdefghijklmnopqrstuvwxyz"},
        {"value": "/home/alice/project"},
        {"value": "alice@example.com"},
    ],
)
def test_sensitive_request_is_rejected(
    document: dict[str, object],
) -> None:
    with pytest.raises(
        DelegationPrivacyError
    ):
        validate_request(document)
def test_bounded_aggregate_request_is_allowed() -> None:
    validate_request(
        {
            "failure_fingerprint": (
                "failure_" + "a" * 64
            ),
            "entity_ids": ["entity:1"],
            "allowed_path_tokens": [
                "path_" + "b" * 64
            ],
        }
    )
EOF
cat > tests/delegation/test_nonce_ledger.py <<'EOF'
from __future__ import annotations
from pathlib import Path
import pytest
from l9_debt_resolver.delegation.errors import (
    DelegationReplayError,
)
from l9_debt_resolver.delegation.nonce_ledger import (
    CallbackNonceLedger,
)
def test_nonce_is_single_use(
    tmp_path: Path,
) -> None:
    ledger = CallbackNonceLedger(
        path=tmp_path / "nonces.json"
    )
    ledger.consume(
        request_id="request-1",
        nonce="a" * 64,
        proposal_id="proposal-1",
    )
    with pytest.raises(
        DelegationReplayError
    ):
        ledger.consume(
            request_id="request-1",
            nonce="a" * 64,
            proposal_id="proposal-2",
        )
EOF
cat > tests/delegation/test_file_transport.py <<'EOF'
from __future__ import annotations
from pathlib import Path
import pytest
from l9_debt_resolver.delegation.file_transport import (
    JSONFilePRRepairTransport,
)
from l9_debt_resolver.delegation.models import (
    PRRepairRequest,
)
def request() -> PRRepairRequest:
    return PRRepairRequest(
        request_id=(
            "pr_repair_request_" + "a" * 64
        ),
        idempotency_key=(
            "pr_repair_idempotency_" + "b" * 64
        ),
        repository_pseudonym=(
            "repository_" + "c" * 64
        ),
        failure_fingerprint=(
            "failure_" + "d" * 64
        ),
        classification={
            "category": "test_failure",
            "confidence_bucket": "medium",
            "remediation_eligibility": (
                "approval_required"
            ),
            "failed_command_hash": "e" * 64,
            "normalized_error_signatures": [
                "assertion failed"
            ],
        },
        repository_context={
            "snapshot_id_hash": "f" * 64,
            "entity_ids": ["entity:1"],
            "finding_ids": [],
            "contract_ids": [],
            "related_test_ids": ["test:1"],
            "language_families": ["python"],
            "capability_profile": ["python"],
            "allowed_path_tokens": [
                "path_" + "1" * 64
            ],
        },
        constraints={
            "maximum_changed_files": 10,
            "maximum_changed_lines": 500,
            "maximum_operations": 50,
            "allowed_remediation_classes": [
                "bounded_source"
            ],
            "protected_paths_enforced": True,
            "validation_required": True,
            "remote_authority_granted": False,
        },
        callback={
            "callback_id": (
                "callback_" + "2" * 64
            ),
            "nonce": "3" * 64,
            "signature_algorithm": (
                "HMAC-SHA256"
            ),
        },
        created_at="2026-07-19T00:00:00Z",
        expires_at="2026-07-19T00:15:00Z",
        limitations=(),
    )
@pytest.mark.asyncio
async def test_file_transport_is_idempotent(
    tmp_path: Path,
) -> None:
    transport = JSONFilePRRepairTransport(
        directory=tmp_path
    )
    first = await transport.deliver(
        request()
    )
    second = await transport.deliver(
        request()
    )
    assert first == second
    assert len(list(tmp_path.glob("*.json"))) == 1
EOF
cat > tests/delegation/test_proposal_signature.py <<'EOF'
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
import pytest
from l9_debt_resolver.delegation.errors import (
    DelegationSignatureError,
)
from l9_debt_resolver.delegation.identity import (
    proposal_signature,
)
from l9_debt_resolver.delegation.models import (
    PRRepairProposal,
)
from l9_debt_resolver.delegation.proposal import (
    validate_proposal_contract,
)
from tests.delegation.test_file_transport import request
def proposal(
    callback_key: bytes,
) -> PRRepairProposal:
    item = PRRepairProposal(
        proposal_id=(
            "pr_repair_proposal_" + "a" * 64
        ),
        request_id=request().request_id,
        failure_fingerprint=(
            request().failure_fingerprint
        ),
        snapshot_id_hash="f" * 64,
        status="unsupported",
        remediation_class=None,
        operations=(),
        requested_validation_classes=(),
        rationale="unable to propose safely",
        limitations=("insufficient_context",),
        issued_at=(
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        callback_nonce=(
            request().callback["nonce"]
        ),
        signature="",
    )
    return replace(
        item,
        signature=proposal_signature(
            unsigned_document=(
                item.unsigned_dict()
            ),
            callback_key=callback_key,
        ),
    )
def test_valid_signature_is_accepted() -> None:
    key = b"a" * 32
    validate_proposal_contract(
        request=request(),
        proposal=proposal(key),
        callback_key=key,
        repository_snapshot_id="snapshot",
    )
def test_invalid_signature_is_rejected() -> None:
    key = b"a" * 32
    item = replace(
        proposal(key),
        signature="0" * 64,
    )
    with pytest.raises(
        DelegationSignatureError
    ):
        validate_proposal_contract(
            request=request(),
            proposal=item,
            callback_key=key,
            repository_snapshot_id="snapshot",
        )
EOF
cat > tests/resilience/test_delegation_retry.py <<'EOF'
from __future__ import annotations
from pathlib import Path
import pytest
from l9_debt_resolver.delegation.errors import (
    DelegationRetryableError,
)
from l9_debt_resolver.delegation.ledger import (
    DelegationLedger,
)
from l9_debt_resolver.delegation.service import (
    PRRepairDelegationService,
)
from tests.delegation.test_file_transport import request
class FlakyTransport:
    name = "https"
    def __init__(self) -> None:
        self.calls = 0
    async def deliver(self, request_value):
        del request_value
        self.calls += 1
        if self.calls < 3:
            raise DelegationRetryableError(
                "temporary"
            )
        return "receipt"
@pytest.mark.asyncio
async def test_retryable_delivery_succeeds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def no_sleep(_):
        return None
    monkeypatch.setattr(
        "l9_debt_resolver.delegation.service.asyncio.sleep",
        no_sleep,
    )
    transport = FlakyTransport()
    service = PRRepairDelegationService(
        ledger=DelegationLedger(
            directory=tmp_path
        ),
        transport=transport,
        maximum_attempts=5,
    )
    record = await service.submit(
        request()
    )
    assert record.state == "awaiting_callback"
    assert record.delivery_attempts == 3
EOF
cat > tests/architecture/test_P6_boundaries.py <<'EOF'
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED = (
    "pr_repair.push",
    "pr_repair.merge",
    "pr_repair.commit",
    "pr_repair.execute",
    "automatic_merge",
    "merge_pull_request",
    "create_subprocess_shell",
    "shell=true",
)
PROHIBITED_PRIVATE_IMPORTS = (
    "pr_repair.internal",
    "pr_repair.private",
)
def test_PR_Repair_has_no_remote_authority() -> None:
    delegation = SOURCE / "delegation"
    for path in delegation.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED:
            assert term not in content, (
                f"{path} contains prohibited delegation "
                f"authority {term}"
            )
def test_no_private_PR_Repair_imports() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED_PRIVATE_IMPORTS:
            assert term not in content, (
                f"{path} imports private PR_Repair "
                f"module {term}"
            )
def test_delegation_transport_has_no_shell() -> None:
    for path in (
        SOURCE / "delegation"
    ).rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        )
        assert "subprocess" not in content
        assert "os.system" not in content
EOF
touch tests/delegation/__init__.py
###############################################################################
# 17. Documentation
###############################################################################
cat > docs/architecture/ADRs/ADR-RESOLVER-025-pr-repair-is-proposal-only.md <<'EOF'
# ADR-RESOLVER-025: PR_Repair is proposal-only
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
PR_Repair may return bounded remediation proposals.
It receives no repository mutation, validation, branch, push, rerun, merge,
attempt-limit, or terminal-state authority.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-026-paths-are-tokenized.md <<'EOF'
# ADR-RESOLVER-026: Delegated paths are tokenized
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
Repository paths are represented by HMAC-SHA256 path tokens in delegation
requests and callbacks.
Only the Resolver retains the token-to-path map.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-027-callbacks-are-signed-and-single-use.md <<'EOF'
# ADR-RESOLVER-027: PR_Repair callbacks are signed and single-use
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
Every proposal callback requires an HMAC-SHA256 signature, bounded timestamp,
request identity, proposal identity, and single-use nonce.
Replayed callbacks are rejected.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-028-proposals-reenter-P3.md <<'EOF'
# ADR-RESOLVER-028: Accepted proposals re-enter P3
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
An accepted PR_Repair proposal is converted into a normal Resolver remediation
plan.
It must pass the existing P3 protected-path, bounds, transaction, SDK
validation, graph-delta, and rollback controls before any remote operation.
EOF
cat >> README.md <<'EOF'
## RESOLVER-P6: constrained PR_Repair delegation
P6 delegates proposal generation only.
```text
unsupported or approval-required classification
        ↓
privacy-safe bounded request
        ↓
repository and path pseudonymization
        ↓
PR_Repair proposal generation
        ↓
signed callback
        ↓
replay, identity, scope, and bounds validation
        ↓
Resolver remediation plan
        ↓
normal P3 validation and rollback
        ↓
normal P4 branch, push, rerun, and terminal states

PR_Repair receives

* failure fingerprint;
* classification category and confidence bucket;
* normalized failure signatures;
* canonical SDK entity, finding, contract, and test IDs;
* capability profile;
* path tokens;
* remediation bounds;
* callback nonce.

PR_Repair does not receive

* raw logs;
* source files;
* repository paths;
* patches or diffs;
* credentials;
* repository owner or name;
* branch or commit data;
* developer identity.

Authority remains with Resolver

PR_Repair cannot mutate a repository, execute validation, push a branch,
trigger CI, merge changes, alter attempt limits, or emit terminal states.

Accepted proposals re-enter the normal RESOLVER-P3 pipeline.
EOF

python3 - <<'PY'
from pathlib import Path

path = Path("ROADMAP.md")
content = path.read_text(encoding="utf-8")

content = content.replace(
"""## RESOLVER-P6 - PR_Repair delegation

Status: Planned

* typed handoff
* bounded context
* privacy gates
* callback verification
* proposal conversion
* retained resolver authority""",
    """## RESOLVER-P6 - PR_Repair delegation

Status: Implemented

* typed PR_Repair handoff requests
* bounded privacy-safe context
* repository pseudonymization
* path tokenization
* deterministic request identities
* idempotent delivery
* file and HTTPS transports
* bounded delivery retries
* signed callbacks
* callback timestamp validation
* replay protection
* fingerprint and snapshot binding
* protected-path and scope enforcement
* proposal-to-remediation conversion
* retained Resolver validation authority
* retained Resolver remote authority
* retained Resolver terminal-state authority""",
    )

path.write_text(content, encoding="utf-8")
PY

###############################################################################

# 18. Acceptance gates

###############################################################################

cat > .l9/phase-6-acceptance-gates.yaml <<'EOF'
schema: l9.phase-acceptance-gates/v1

repository: Quantum-L9/l9-ci-debt-resolver
phase: RESOLVER-P6

gates:

  - id: p6-proposal-only
    requirement: >
    PR_Repair receives proposal-generation authority only.
  - id: p6-bounded-context
    requirement: >
    Requests contain only bounded aggregate evidence and canonical identities.
  - id: p6-no-raw-logs
    requirement: >
    Raw logs and log excerpts cannot enter delegation payloads.
  - id: p6-no-source
    requirement: >
    Source files, source content, patches, and diffs cannot enter requests.
  - id: p6-repository-pseudonym
    requirement: >
    Raw repository identity is replaced with an HMAC pseudonym.
  - id: p6-path-token
    requirement: >
    Repository paths are represented only by HMAC path tokens.
  - id: p6-signed-callback
    requirement: >
    Every proposal callback passes HMAC-SHA256 verification.
  - id: p6-replay-protection
    requirement: >
    Callback nonces are durable and single-use.
  - id: p6-identity-binding
    requirement: >
    Proposal request ID, fingerprint, snapshot, and nonce match the request.
  - id: p6-scope
    requirement: >
    Proposal operations reference only Resolver-issued path tokens.
  - id: p6-protected-paths
    requirement: >
    Token resolution re-applies normal protected-path policy.
  - id: p6-bounds
    requirement: >
    File, line, operation, and replacement-byte limits remain enforced.
  - id: p6-reentry
    requirement: >
    Accepted proposals become ordinary Resolver remediation plans and pass P3.
  - id: p6-no-remote-authority
    requirement: >
    PR_Repair cannot commit, push, rerun, merge, or emit terminal states.
  - id: p6-no-private-imports
    requirement: >
    Resolver does not import private PR_Repair implementation modules.
EOF
###############################################################################

# 19. CI

###############################################################################

cat > .github/workflows/phase-6-pr-repair-delegation.yml <<'EOF'
name: RESOLVER-P6 PR Repair Delegation

on:
pull_request:
push:
branches:
- main

permissions:
contents: read

jobs:
pr-repair-delegation:
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
  - name: Delegation tests
    run: pytest tests/delegation
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


printf "phase generation complete\n"
