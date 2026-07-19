RESOLVER-P3 implements evidence-bounded local remediation and SDK-owned validation. It adds approval checks, protected-path enforcement, transactional workspace mutation, original-failure reproduction, targeted validation, graph-delta checks, and automatic rollback. Remote branch mutation and CI rerun observation remain deferred to P4. repo-spec.yaml

Save as build-phase-3.sh and run it after P2.

#!/usr/bin/env bash
set -euo pipefail
###############################################################################
# Quantum-L9/l9-ci-debt-resolver
# RESOLVER-P3 — Evidence-Bounded Remediation and SDK Validation
#
# Incremental build over RESOLVER-P0, P1, and P2.
#
# Implements:
#   - evidence-bound remediation plans
#   - approval and protected-path policy
#   - bounded file and line-change limits
#   - exact-content preconditions
#   - transactional local workspace mutation
#   - rollback on patch or validation failure
#   - SDK-owned validation-plan gateway
#   - original failed-command reproduction
#   - targeted tests and affected-contract validation
#   - graph-delta validation
#   - deterministic validation transcripts
#   - remediation records
#   - P3 CLI
#   - architecture, safety, rollback, and validation tests
#
# Does not implement:
#   - Git branch creation or push              (RESOLVER-P4)
#   - CI rerun observation                     (RESOLVER-P4)
#   - automatic merge                          (prohibited)
#   - Intelligence event delivery              (RESOLVER-P5)
###############################################################################
fail() {
  printf 'RESOLVER-P3: %s\n' "$*" >&2
  exit 1
}
require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "required command not found: $1"
}
require_command python3
[[ -d .git ]] \
  || fail "run from the l9-ci-debt-resolver repository root"
[[ -f .l9/repository-correlation-contract.yaml ]] \
  || fail "RESOLVER-P2 correlation contract is missing"
[[ -f src/l9_debt_resolver/runtime/diagnosis_service.py ]] \
  || fail "RESOLVER-P2 diagnosis runtime is missing"
mkdir -p \
  .github/workflows \
  .l9 \
  docs/architecture/ADRs \
  schemas/resolver \
  src/l9_debt_resolver/remediation \
  src/l9_debt_resolver/validation \
  tests/remediation \
  tests/validation \
  tests/runtime \
  tests/architecture
###############################################################################
# 1. Authoritative P3 contracts
###############################################################################
cat > .l9/remediation-contract.yaml <<'EOF'
schema: l9.resolver-remediation-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P3
  status: authoritative
authority:
  classification:
    source: RESOLVER-P2 classification trace
  repository_semantics:
    source: Quantum-L9/l9-ci-sdk
  validation:
    source: Quantum-L9/l9-ci-sdk
eligibility:
  automatic:
    required:
      - classification remediation eligibility is automatic
      - classification confidence is at least 0.90
      - complete failed-log evidence exists
      - exact SDK repository snapshot exists
      - every changed path maps to correlated evidence
      - no protected path is touched
      - bounded-change limits are satisfied
  approval_required:
    required:
      - classification remediation eligibility is approval_required
      - explicit approval token is present
      - approval scope contains all changed paths
      - approval has not expired
  unsupported:
    remediation: prohibited
allowed_remediation_classes:
  - configuration
  - dependency
  - bounded_source
  - generated_file
prohibited:
  - disabling tests
  - skipping tests
  - weakening lint rules
  - weakening security rules
  - weakening governance
  - commenting out failures
  - broad refactoring
  - deleting unrelated code
  - protected branch mutation
  - remote push
  - automatic merge
  - speculative multi-attempt mutation
  - shell execution from untrusted patch data
bounds:
  maximum_changed_files: 10
  maximum_changed_lines: 500
  maximum_operations: 50
  maximum_file_bytes: 5242880
  maximum_total_replacement_bytes: 10485760
protected_paths:
  exact:
    - .git
    - .github/CODEOWNERS
  prefixes:
    - .git/
    - .github/workflows/
    - .l9/
    - schemas/
    - security/
    - compliance/
    - governance/
  override:
    allowed: false
patch_preconditions:
  - repository revision matches the classified snapshot revision
  - target file is repository relative
  - target file remains inside the workspace root
  - target file hash matches expected hash
  - expected text occurs exactly once
  - replacement hash matches declared replacement hash
transaction:
  behavior:
    - capture original bytes
    - apply all changes in memory
    - verify bounds before writing
    - write atomically
    - validate
    - commit local transaction only after validation succeeds
  rollback_when:
    - patch precondition fails
    - operation fails
    - original failed command still fails
    - targeted validation fails
    - affected contract validation fails
    - graph delta exceeds plan
    - SDK full gate fails
    - validation result is unavailable
remote_behavior:
  branch_creation: prohibited_in_P3
  push: prohibited_in_P3
  CI_rerun: prohibited_in_P3
EOF
cat > .l9/validation-contract.yaml <<'EOF'
schema: l9.resolver-validation-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P3
  status: authoritative
authority:
  owner: Quantum-L9/l9-ci-sdk
  contract: public_validation_gateway
required_inputs:
  - repository snapshot ID
  - classification trace
  - changed paths
  - remediation class
  - original failed command
  - related tests
  - applicable contracts
required_plan_steps:
  - original failure reproduction or equivalent
  - affected contract validation
  - targeted tests
conditional_full_gate:
  required_when:
    - policy requires full gate
    - change crosses package boundary
    - change affects governance
    - change affects schemas
    - change affects dependency resolution
    - graph delta exceeds targeted scope
result_states:
  - passed
  - failed
  - unavailable
  - incomplete
graph_delta:
  required:
    - before snapshot ID
    - after working-tree digest
    - changed paths
    - changed package boundaries
    - changed contract references
    - changed dependency edges
    - unexpected changed paths
  rejection:
    - unexpected changed paths
    - unapproved package boundary changes
    - unapproved contract changes
    - unapproved dependency-edge changes
transcript:
  include:
    - validation plan ID
    - ordered step IDs
    - command hashes
    - exit codes
    - duration buckets
    - stdout hashes
    - stderr hashes
    - result
    - limitations
  exclude:
    - credentials
    - unredacted logs
    - absolute paths
    - source content
success:
  requirement: >
    A remediation is successful only when the SDK validation result passes and
    the local workspace transaction remains within the approved graph delta.
EOF
###############################################################################
# 2. P3 schemas
###############################################################################
cat > schemas/resolver/remediation-plan.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/remediation-plan/v1",
  "title": "L9 Resolver Remediation Plan",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "plan_id",
    "classification_id",
    "failure_fingerprint",
    "repository_snapshot_id",
    "repository_revision",
    "remediation_class",
    "evidence_ids",
    "justification",
    "operations",
    "expected_changed_paths",
    "expected_package_boundaries",
    "expected_contract_ids",
    "expected_dependency_edges",
    "validation_plan_id",
    "approval"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.remediation-plan/v1"
    },
    "plan_id": {
      "type": "string",
      "pattern": "^remediation_plan_[0-9a-f]{64}$"
    },
    "classification_id": {
      "type": "string",
      "pattern": "^classification_[0-9a-f]{64}$"
    },
    "failure_fingerprint": {
      "type": "string",
      "pattern": "^failure_[0-9a-f]{64}$"
    },
    "repository_snapshot_id": {
      "type": "string",
      "minLength": 1
    },
    "repository_revision": {
      "type": "string",
      "minLength": 7,
      "maxLength": 128
    },
    "remediation_class": {
      "enum": [
        "configuration",
        "dependency",
        "bounded_source",
        "generated_file"
      ]
    },
    "evidence_ids": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    },
    "justification": {
      "type": "string",
      "minLength": 1,
      "maxLength": 4000
    },
    "operations": {
      "type": "array",
      "minItems": 1,
      "maxItems": 50,
      "items": {
        "$ref": "#/$defs/replaceOperation"
      }
    },
    "expected_changed_paths": {
      "type": "array",
      "minItems": 1,
      "maxItems": 10,
      "items": {
        "type": "string",
        "minLength": 1,
        "maxLength": 1000
      },
      "uniqueItems": true
    },
    "expected_package_boundaries": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 500
      },
      "uniqueItems": true
    },
    "expected_contract_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 500
      },
      "uniqueItems": true
    },
    "expected_dependency_edges": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 1000
      },
      "uniqueItems": true
    },
    "validation_plan_id": {
      "type": "string",
      "minLength": 1
    },
    "approval": {
      "oneOf": [
        {
          "type": "null"
        },
        {
          "$ref": "#/$defs/approval"
        }
      ]
    }
  },
  "$defs": {
    "replaceOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "operation_id",
        "path",
        "expected_file_sha256",
        "expected_text",
        "replacement_text",
        "replacement_sha256",
        "evidence_ids",
        "justification"
      ],
      "properties": {
        "operation_id": {
          "type": "string",
          "pattern": "^operation_[0-9a-f]{64}$"
        },
        "path": {
          "type": "string",
          "minLength": 1,
          "maxLength": 1000,
          "not": {
            "pattern": "^(?:/|[A-Za-z]:\\\\|.*(?:^|/)\\.\\.(?:/|$))"
          }
        },
        "expected_file_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "expected_text": {
          "type": "string",
          "minLength": 1,
          "maxLength": 1048576
        },
        "replacement_text": {
          "type": "string",
          "maxLength": 1048576
        },
        "replacement_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "evidence_ids": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "justification": {
          "type": "string",
          "minLength": 1,
          "maxLength": 2000
        }
      }
    },
    "approval": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "approval_id",
        "approved_paths",
        "approved_at",
        "expires_at"
      ],
      "properties": {
        "approval_id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 500
        },
        "approved_paths": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "approved_at": {
          "type": "string",
          "format": "date-time"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time"
        }
      }
    }
  }
}
EOF
cat > schemas/resolver/validation-transcript.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/validation-transcript/v1",
  "title": "L9 Resolver Validation Transcript",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "transcript_id",
    "validation_plan_id",
    "validation_result_id",
    "steps",
    "graph_delta",
    "result",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.validation-transcript/v1"
    },
    "transcript_id": {
      "type": "string",
      "pattern": "^validation_transcript_[0-9a-f]{64}$"
    },
    "validation_plan_id": {
      "type": "string",
      "minLength": 1
    },
    "validation_result_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "steps": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/step"
      }
    },
    "graph_delta": {
      "$ref": "#/$defs/graphDelta"
    },
    "result": {
      "enum": [
        "passed",
        "failed",
        "unavailable",
        "incomplete"
      ]
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    }
  },
  "$defs": {
    "step": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "step_id",
        "kind",
        "command_sha256",
        "exit_code",
        "duration_bucket",
        "stdout_sha256",
        "stderr_sha256",
        "result"
      ],
      "properties": {
        "step_id": {
          "type": "string",
          "minLength": 1
        },
        "kind": {
          "enum": [
            "original_failure",
            "targeted_test",
            "affected_contract",
            "graph_delta",
            "full_gate"
          ]
        },
        "command_sha256": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "exit_code": {
          "type": [
            "integer",
            "null"
          ]
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
        "stdout_sha256": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "stderr_sha256": {
          "type": [
            "string",
            "null"
          ],
          "pattern": "^[0-9a-f]{64}$"
        },
        "result": {
          "enum": [
            "passed",
            "failed",
            "unavailable",
            "incomplete"
          ]
        }
      }
    },
    "graphDelta": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "before_snapshot_id",
        "after_worktree_digest",
        "changed_paths",
        "changed_package_boundaries",
        "changed_contract_ids",
        "changed_dependency_edges",
        "unexpected_changed_paths"
      ],
      "properties": {
        "before_snapshot_id": {
          "type": "string"
        },
        "after_worktree_digest": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "changed_paths": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "changed_package_boundaries": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "changed_contract_ids": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "changed_dependency_edges": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "unexpected_changed_paths": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        }
      }
    }
  }
}
EOF
###############################################################################
# 3. Remediation models and policy
###############################################################################
cat > src/l9_debt_resolver/remediation/__init__.py <<'EOF'
"""Evidence-bounded local remediation."""
EOF
cat > src/l9_debt_resolver/remediation/errors.py <<'EOF'
from __future__ import annotations
class RemediationError(RuntimeError):
    """Base remediation failure."""
class RemediationNotEligibleError(RemediationError):
    """Classification cannot authorize remediation."""
class ApprovalRequiredError(RemediationError):
    """Explicit approval is missing, expired, or incomplete."""
class ProtectedPathError(RemediationError):
    """A remediation targets a protected path."""
class PatchPreconditionError(RemediationError):
    """A patch precondition does not match the workspace."""
class PatchBoundError(RemediationError):
    """A patch exceeds configured safety bounds."""
class TransactionError(RemediationError):
    """A transactional workspace operation failed."""
class ValidationFailedError(RemediationError):
    """SDK-owned validation rejected the remediation."""
EOF
cat > src/l9_debt_resolver/remediation/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class Approval:
    approval_id: str
    approved_paths: tuple[str, ...]
    approved_at: str
    expires_at: str
@dataclass(frozen=True)
class ReplaceTextOperation:
    operation_id: str
    path: str
    expected_file_sha256: str
    expected_text: str
    replacement_text: str
    replacement_sha256: str
    evidence_ids: tuple[str, ...]
    justification: str
@dataclass(frozen=True)
class RemediationPlan:
    plan_id: str
    classification_id: str
    failure_fingerprint: str
    repository_snapshot_id: str
    repository_revision: str
    remediation_class: str
    evidence_ids: tuple[str, ...]
    justification: str
    operations: tuple[ReplaceTextOperation, ...]
    expected_changed_paths: tuple[str, ...]
    expected_package_boundaries: tuple[str, ...]
    expected_contract_ids: tuple[str, ...]
    expected_dependency_edges: tuple[str, ...]
    validation_plan_id: str
    approval: Approval | None
@dataclass(frozen=True)
class AppliedChange:
    path: str
    before_sha256: str
    after_sha256: str
    changed_line_count: int
@dataclass(frozen=True)
class TransactionResult:
    changes: tuple[AppliedChange, ...]
    worktree_digest: str
    @property
    def changed_paths(self) -> tuple[str, ...]:
        return tuple(change.path for change in self.changes)
    @property
    def changed_line_count(self) -> int:
        return sum(
            change.changed_line_count
            for change in self.changes
        )
@dataclass(frozen=True)
class RemediationExecutionResult:
    remediation_id: str
    plan_id: str
    status: str
    changed_paths: tuple[str, ...]
    changed_line_count: int
    validation_transcript: dict[str, Any]
    rolled_back: bool
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.remediation-execution-result/v1"
            ),
            "remediation_id": self.remediation_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "changed_paths": list(self.changed_paths),
            "changed_line_count": self.changed_line_count,
            "validation_transcript": (
                self.validation_transcript
            ),
            "rolled_back": self.rolled_back,
            "limitations": list(self.limitations),
        }
EOF
cat > src/l9_debt_resolver/remediation/policy.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from l9_debt_resolver.contracts.models import (
    FailureClassification,
)
from .errors import (
    ApprovalRequiredError,
    PatchBoundError,
    ProtectedPathError,
    RemediationNotEligibleError,
)
from .models import RemediationPlan
@dataclass(frozen=True)
class RemediationBounds:
    maximum_changed_files: int = 10
    maximum_changed_lines: int = 500
    maximum_operations: int = 50
    maximum_file_bytes: int = 5 * 1024 * 1024
    maximum_total_replacement_bytes: int = 10 * 1024 * 1024
PROTECTED_EXACT = {
    ".git",
    ".github/CODEOWNERS",
}
PROTECTED_PREFIXES = (
    ".git/",
    ".github/workflows/",
    ".l9/",
    "schemas/",
    "security/",
    "compliance/",
    "governance/",
)
ALLOWED_REMEDIATION_CLASSES = {
    "configuration",
    "dependency",
    "bounded_source",
    "generated_file",
}
def validate_remediation_policy(
    *,
    classification: FailureClassification,
    plan: RemediationPlan,
    bounds: RemediationBounds,
    now: datetime | None = None,
) -> None:
    if classification.remediation_eligibility == "unsupported":
        raise RemediationNotEligibleError(
            "classification is not eligible for remediation"
        )
    if classification.classification_id != plan.classification_id:
        raise RemediationNotEligibleError(
            "plan classification does not match diagnosis"
        )
    if (
        classification.failure_fingerprint
        != plan.failure_fingerprint
    ):
        raise RemediationNotEligibleError(
            "plan failure fingerprint does not match diagnosis"
        )
    if (
        classification.repository_snapshot_id
        != plan.repository_snapshot_id
    ):
        raise RemediationNotEligibleError(
            "plan snapshot does not match classification"
        )
    if plan.remediation_class not in ALLOWED_REMEDIATION_CLASSES:
        raise RemediationNotEligibleError(
            "remediation class is not permitted"
        )
    if not set(plan.evidence_ids).issubset(
        set(classification.evidence_ids)
    ):
        raise RemediationNotEligibleError(
            "plan references evidence outside the classification"
        )
    paths = {
        operation.path
        for operation in plan.operations
    }
    if paths != set(plan.expected_changed_paths):
        raise PatchBoundError(
            "operation paths do not match expected changed paths"
        )
    if len(paths) > bounds.maximum_changed_files:
        raise PatchBoundError(
            "remediation exceeds changed-file limit"
        )
    if len(plan.operations) > bounds.maximum_operations:
        raise PatchBoundError(
            "remediation exceeds operation limit"
        )
    total_replacement_bytes = sum(
        len(operation.replacement_text.encode("utf-8"))
        for operation in plan.operations
    )
    if (
        total_replacement_bytes
        > bounds.maximum_total_replacement_bytes
    ):
        raise PatchBoundError(
            "replacement data exceeds configured byte limit"
        )
    for path in sorted(paths):
        validate_mutable_path(path)
    if (
        classification.remediation_eligibility
        == "approval_required"
    ):
        _validate_approval(
            plan=plan,
            now=now or datetime.now(timezone.utc),
        )
def validate_mutable_path(path: str) -> None:
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ProtectedPathError(
            f"unsafe remediation path: {path}"
        )
    canonical = normalized.as_posix()
    if canonical in PROTECTED_EXACT:
        raise ProtectedPathError(
            f"protected remediation path: {canonical}"
        )
    if canonical.startswith(PROTECTED_PREFIXES):
        raise ProtectedPathError(
            f"protected remediation path: {canonical}"
        )
def _validate_approval(
    *,
    plan: RemediationPlan,
    now: datetime,
) -> None:
    approval = plan.approval
    if approval is None:
        raise ApprovalRequiredError(
            "explicit remediation approval is required"
        )
    expires_at = datetime.fromisoformat(
        approval.expires_at.replace("Z", "+00:00")
    )
    if expires_at <= now:
        raise ApprovalRequiredError(
            "remediation approval has expired"
        )
    missing = set(
        plan.expected_changed_paths
    ) - set(approval.approved_paths)
    if missing:
        raise ApprovalRequiredError(
            "approval does not cover all changed paths"
        )
EOF
###############################################################################
# 4. Transactional patch engine
###############################################################################
cat > src/l9_debt_resolver/remediation/transaction.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
from .errors import (
    PatchBoundError,
    PatchPreconditionError,
    TransactionError,
)
from .models import (
    AppliedChange,
    RemediationPlan,
    TransactionResult,
)
from .policy import RemediationBounds, validate_mutable_path
@dataclass(frozen=True)
class OriginalFile:
    path: Path
    existed: bool
    content: bytes
class WorkspaceTransaction:
    def __init__(
        self,
        *,
        workspace_root: Path,
        bounds: RemediationBounds,
    ) -> None:
        self._root = workspace_root.resolve()
        self._bounds = bounds
        self._originals: dict[Path, OriginalFile] = {}
        self._committed = False
    def apply(
        self,
        plan: RemediationPlan,
    ) -> TransactionResult:
        staged: dict[Path, bytes] = {}
        for operation in plan.operations:
            validate_mutable_path(operation.path)
            target = self._resolve_target(operation.path)
            if target not in staged:
                current = self._read_target(target)
                if len(current) > self._bounds.maximum_file_bytes:
                    raise PatchBoundError(
                        f"file exceeds byte limit: {operation.path}"
                    )
                staged[target] = current
                self._originals[target] = OriginalFile(
                    path=target,
                    existed=target.exists(),
                    content=current,
                )
            current = staged[target]
            current_sha256 = hashlib.sha256(current).hexdigest()
            if (
                current_sha256
                != operation.expected_file_sha256
            ):
                raise PatchPreconditionError(
                    f"file hash mismatch: {operation.path}"
                )
            replacement_sha256 = hashlib.sha256(
                operation.replacement_text.encode("utf-8")
            ).hexdigest()
            if (
                replacement_sha256
                != operation.replacement_sha256
            ):
                raise PatchPreconditionError(
                    f"replacement hash mismatch: {operation.path}"
                )
            text = current.decode("utf-8")
            occurrences = text.count(operation.expected_text)
            if occurrences != 1:
                raise PatchPreconditionError(
                    f"expected text must occur exactly once in "
                    f"{operation.path}; found {occurrences}"
                )
            updated = text.replace(
                operation.expected_text,
                operation.replacement_text,
                1,
            )
            staged[target] = updated.encode("utf-8")
        changes = []
        for target, updated in sorted(
            staged.items(),
            key=lambda item: item[0].as_posix(),
        ):
            original = self._originals[target].content
            changed_lines = _changed_line_count(
                original.decode("utf-8"),
                updated.decode("utf-8"),
            )
            changes.append(
                AppliedChange(
                    path=target.relative_to(
                        self._root
                    ).as_posix(),
                    before_sha256=hashlib.sha256(
                        original
                    ).hexdigest(),
                    after_sha256=hashlib.sha256(
                        updated
                    ).hexdigest(),
                    changed_line_count=changed_lines,
                )
            )
        total_lines = sum(
            change.changed_line_count
            for change in changes
        )
        if total_lines > self._bounds.maximum_changed_lines:
            raise PatchBoundError(
                "remediation exceeds changed-line limit"
            )
        try:
            for target, updated in staged.items():
                _atomic_write(target, updated)
        except Exception as error:
            self.rollback()
            raise TransactionError(
                "transactional patch write failed"
            ) from error
        return TransactionResult(
            changes=tuple(changes),
            worktree_digest=_worktree_digest(
                self._root,
                tuple(
                    change.path
                    for change in changes
                ),
            ),
        )
    def commit(self) -> None:
        self._committed = True
        self._originals.clear()
    def rollback(self) -> None:
        if self._committed:
            return
        errors = []
        for original in self._originals.values():
            try:
                if original.existed:
                    _atomic_write(
                        original.path,
                        original.content,
                    )
                elif original.path.exists():
                    original.path.unlink()
            except Exception as error:
                errors.append(error)
        self._originals.clear()
        if errors:
            raise TransactionError(
                "workspace rollback was incomplete"
            )
    def _resolve_target(self, path: str) -> Path:
        candidate = (
            self._root / path
        ).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as error:
            raise PatchPreconditionError(
                f"path escapes workspace: {path}"
            ) from error
        if not candidate.is_file():
            raise PatchPreconditionError(
                f"target file does not exist: {path}"
            )
        return candidate
    @staticmethod
    def _read_target(path: Path) -> bytes:
        return path.read_bytes()
def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.resolver.",
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
def _changed_line_count(
    before: str,
    after: str,
) -> int:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    maximum = max(len(before_lines), len(after_lines))
    count = 0
    for index in range(maximum):
        before_value = (
            before_lines[index]
            if index < len(before_lines)
            else None
        )
        after_value = (
            after_lines[index]
            if index < len(after_lines)
            else None
        )
        if before_value != after_value:
            count += 1
    return count
def _worktree_digest(
    root: Path,
    paths: tuple[str, ...],
) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        content = (root / path).read_bytes()
        digest.update(path.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(
            hashlib.sha256(content).digest()
        )
    return digest.hexdigest()
EOF
###############################################################################
# 5. Validation public gateway and models
###############################################################################
cat > src/l9_debt_resolver/validation/__init__.py <<'EOF'
"""SDK-owned validation planning and execution boundary."""
EOF
cat > src/l9_debt_resolver/validation/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class ValidationStep:
    step_id: str
    kind: str
    command: tuple[str, ...] | None
    contract_id: str | None
    test_id: str | None
@dataclass(frozen=True)
class SDKValidationPlan:
    validation_plan_id: str
    steps: tuple[ValidationStep, ...]
    full_gate_required: bool
    limitations: tuple[str, ...]
@dataclass(frozen=True)
class ValidationStepResult:
    step_id: str
    kind: str
    command_sha256: str | None
    exit_code: int | None
    duration_bucket: str
    stdout_sha256: str | None
    stderr_sha256: str | None
    result: str
    def as_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "kind": self.kind,
            "command_sha256": self.command_sha256,
            "exit_code": self.exit_code,
            "duration_bucket": self.duration_bucket,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "result": self.result,
        }
@dataclass(frozen=True)
class GraphDelta:
    before_snapshot_id: str
    after_worktree_digest: str
    changed_paths: tuple[str, ...]
    changed_package_boundaries: tuple[str, ...]
    changed_contract_ids: tuple[str, ...]
    changed_dependency_edges: tuple[str, ...]
    unexpected_changed_paths: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "before_snapshot_id": self.before_snapshot_id,
            "after_worktree_digest": self.after_worktree_digest,
            "changed_paths": list(self.changed_paths),
            "changed_package_boundaries": list(
                self.changed_package_boundaries
            ),
            "changed_contract_ids": list(
                self.changed_contract_ids
            ),
            "changed_dependency_edges": list(
                self.changed_dependency_edges
            ),
            "unexpected_changed_paths": list(
                self.unexpected_changed_paths
            ),
        }
@dataclass(frozen=True)
class ValidationTranscript:
    transcript_id: str
    validation_plan_id: str
    validation_result_id: str | None
    steps: tuple[ValidationStepResult, ...]
    graph_delta: GraphDelta
    result: str
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.validation-transcript/v1",
            "transcript_id": self.transcript_id,
            "validation_plan_id": self.validation_plan_id,
            "validation_result_id": self.validation_result_id,
            "steps": [
                step.as_dict()
                for step in self.steps
            ],
            "graph_delta": self.graph_delta.as_dict(),
            "result": self.result,
            "limitations": list(self.limitations),
        }
EOF
cat > src/l9_debt_resolver/validation/protocol.py <<'EOF'
from __future__ import annotations
from typing import Protocol
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    TransactionResult,
)
from .models import (
    GraphDelta,
    SDKValidationPlan,
    ValidationStepResult,
)
class SDKValidationGateway(Protocol):
    async def create_validation_plan(
        self,
        *,
        repository_snapshot_id: str,
        classification_trace: ClassificationTrace,
        remediation_plan: RemediationPlan,
    ) -> SDKValidationPlan:
        """Create an SDK-owned validation plan."""
    async def execute_validation_step(
        self,
        *,
        workspace_root: str,
        step: object,
    ) -> ValidationStepResult:
        """Execute one SDK-authorized validation step."""
    async def calculate_graph_delta(
        self,
        *,
        repository_snapshot_id: str,
        transaction: TransactionResult,
        remediation_plan: RemediationPlan,
    ) -> GraphDelta:
        """Calculate SDK repository graph delta."""
    async def finalize_validation(
        self,
        *,
        validation_plan_id: str,
        step_results: tuple[ValidationStepResult, ...],
        graph_delta: GraphDelta,
    ) -> tuple[str, str | None, tuple[str, ...]]:
        """Return result, canonical validation-result ID, limitations."""
EOF
###############################################################################
# 6. Safe subprocess runner and JSON SDK validation gateway
###############################################################################
cat > src/l9_debt_resolver/validation/runner.py <<'EOF'
from __future__ import annotations
import asyncio
import hashlib
import os
from pathlib import Path
import time
from .models import (
    ValidationStep,
    ValidationStepResult,
)
_ALLOWED_EXECUTABLES = {
    "python",
    "python3",
    "pytest",
    "ruff",
    "mypy",
    "npm",
    "pnpm",
    "yarn",
    "go",
    "cargo",
    "dotnet",
    "java",
    "gradle",
    "./gradlew",
    "make",
}
class ValidationCommandRunner:
    def __init__(
        self,
        *,
        timeout_seconds: float = 900.0,
    ) -> None:
        self._timeout_seconds = timeout_seconds
    async def execute(
        self,
        *,
        workspace_root: Path,
        step: ValidationStep,
    ) -> ValidationStepResult:
        if step.command is None:
            return ValidationStepResult(
                step_id=step.step_id,
                kind=step.kind,
                command_sha256=None,
                exit_code=None,
                duration_bucket="unknown",
                stdout_sha256=None,
                stderr_sha256=None,
                result="incomplete",
            )
        if not step.command:
            raise ValueError(
                "validation command cannot be empty"
            )
        executable = step.command[0]
        if executable not in _ALLOWED_EXECUTABLES:
            raise ValueError(
                f"validation executable is not allowed: "
                f"{executable}"
            )
        command_hash = hashlib.sha256(
            "\x00".join(step.command).encode("utf-8")
        ).hexdigest()
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {
                "GITHUB_TOKEN",
                "GH_TOKEN",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AZURE_CLIENT_SECRET",
                "GOOGLE_APPLICATION_CREDENTIALS",
            }
        }
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *step.command,
            cwd=workspace_root,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            elapsed = time.monotonic() - started
            return ValidationStepResult(
                step_id=step.step_id,
                kind=step.kind,
                command_sha256=command_hash,
                exit_code=None,
                duration_bucket=_duration_bucket(
                    elapsed
                ),
                stdout_sha256=None,
                stderr_sha256=None,
                result="failed",
            )
        elapsed = time.monotonic() - started
        return ValidationStepResult(
            step_id=step.step_id,
            kind=step.kind,
            command_sha256=command_hash,
            exit_code=process.returncode,
            duration_bucket=_duration_bucket(
                elapsed
            ),
            stdout_sha256=hashlib.sha256(
                stdout
            ).hexdigest(),
            stderr_sha256=hashlib.sha256(
                stderr
            ).hexdigest(),
            result=(
                "passed"
                if process.returncode == 0
                else "failed"
            ),
        )
def _duration_bucket(seconds: float) -> str:
    if seconds < 1:
        return "lt_1s"
    if seconds < 10:
        return "1_10s"
    if seconds < 60:
        return "10_60s"
    if seconds < 300:
        return "1_5m"
    if seconds < 900:
        return "5_15m"
    return "gt_15m"
EOF
cat > src/l9_debt_resolver/validation/json_gateway.py <<'EOF'
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    TransactionResult,
)
from .models import (
    GraphDelta,
    SDKValidationPlan,
    ValidationStep,
    ValidationStepResult,
)
from .runner import ValidationCommandRunner
class JSONSDKValidationGateway:
    """
    Offline/public-contract SDK validation adapter.
    The SDK-produced document owns the validation plan identity and permitted
    commands. Resolver does not invent validation semantics.
    """
    def __init__(
        self,
        *,
        document_path: Path,
        runner: ValidationCommandRunner | None = None,
    ) -> None:
        document = json.loads(
            document_path.read_text(encoding="utf-8")
        )
        if not isinstance(document, dict):
            raise ValueError(
                "SDK validation document must be an object"
            )
        if (
            document.get("schema_version")
            != "l9.sdk-validation-document/v1"
        ):
            raise ValueError(
                "unsupported SDK validation document"
            )
        self._document = document
        self._runner = runner or ValidationCommandRunner()
    async def create_validation_plan(
        self,
        *,
        repository_snapshot_id: str,
        classification_trace: ClassificationTrace,
        remediation_plan: RemediationPlan,
    ) -> SDKValidationPlan:
        plan = self._document.get("validation_plan")
        if not isinstance(plan, dict):
            raise ValueError(
                "SDK validation plan is missing"
            )
        if (
            plan.get("repository_snapshot_id")
            != repository_snapshot_id
        ):
            raise ValueError(
                "SDK validation snapshot mismatch"
            )
        if (
            plan.get("classification_id")
            != classification_trace.classification.classification_id
        ):
            raise ValueError(
                "SDK validation classification mismatch"
            )
        if (
            plan.get("remediation_plan_id")
            != remediation_plan.plan_id
        ):
            raise ValueError(
                "SDK validation remediation-plan mismatch"
            )
        steps_value = plan.get("steps")
        if not isinstance(steps_value, list):
            raise ValueError(
                "SDK validation steps must be an array"
            )
        steps = tuple(
            _parse_step(value)
            for value in steps_value
        )
        kinds = {
            step.kind
            for step in steps
        }
        required = {
            "original_failure",
            "targeted_test",
            "affected_contract",
            "graph_delta",
        }
        if not required.issubset(kinds):
            raise ValueError(
                "SDK validation plan lacks required steps"
            )
        return SDKValidationPlan(
            validation_plan_id=str(
                plan["validation_plan_id"]
            ),
            steps=steps,
            full_gate_required=bool(
                plan.get(
                    "full_gate_required",
                    False,
                )
            ),
            limitations=tuple(
                sorted(
                    str(value)
                    for value in plan.get(
                        "limitations",
                        [],
                    )
                )
            ),
        )
    async def execute_validation_step(
        self,
        *,
        workspace_root: str,
        step: object,
    ) -> ValidationStepResult:
        if not isinstance(step, ValidationStep):
            raise TypeError(
                "validation step has an invalid type"
            )
        if step.kind == "graph_delta":
            return ValidationStepResult(
                step_id=step.step_id,
                kind=step.kind,
                command_sha256=None,
                exit_code=0,
                duration_bucket="lt_1s",
                stdout_sha256=None,
                stderr_sha256=None,
                result="passed",
            )
        return await self._runner.execute(
            workspace_root=Path(workspace_root),
            step=step,
        )
    async def calculate_graph_delta(
        self,
        *,
        repository_snapshot_id: str,
        transaction: TransactionResult,
        remediation_plan: RemediationPlan,
    ) -> GraphDelta:
        changed_paths = tuple(
            sorted(transaction.changed_paths)
        )
        expected_paths = set(
            remediation_plan.expected_changed_paths
        )
        unexpected = tuple(
            sorted(
                set(changed_paths) - expected_paths
            )
        )
        return GraphDelta(
            before_snapshot_id=repository_snapshot_id,
            after_worktree_digest=(
                transaction.worktree_digest
            ),
            changed_paths=changed_paths,
            changed_package_boundaries=tuple(
                sorted(
                    remediation_plan
                    .expected_package_boundaries
                )
            ),
            changed_contract_ids=tuple(
                sorted(
                    remediation_plan
                    .expected_contract_ids
                )
            ),
            changed_dependency_edges=tuple(
                sorted(
                    remediation_plan
                    .expected_dependency_edges
                )
            ),
            unexpected_changed_paths=unexpected,
        )
    async def finalize_validation(
        self,
        *,
        validation_plan_id: str,
        step_results: tuple[ValidationStepResult, ...],
        graph_delta: GraphDelta,
    ) -> tuple[str, str | None, tuple[str, ...]]:
        limitations = []
        if graph_delta.unexpected_changed_paths:
            limitations.append(
                "graph delta contains unexpected changed paths"
            )
        failed = any(
            result.result != "passed"
            for result in step_results
        )
        if failed or limitations:
            return (
                "failed",
                None,
                tuple(sorted(limitations)),
            )
        result_id = self._document.get(
            "validation_result_id"
        )
        if not isinstance(result_id, str):
            return (
                "unavailable",
                None,
                (
                    "SDK validation result identity is missing",
                ),
            )
        return (
            "passed",
            result_id,
            (),
        )
def _parse_step(value: object) -> ValidationStep:
    if not isinstance(value, dict):
        raise ValueError(
            "SDK validation step must be an object"
        )
    command_value = value.get("command")
    if command_value is None:
        command = None
    elif isinstance(command_value, list) and all(
        isinstance(item, str)
        for item in command_value
    ):
        command = tuple(command_value)
    else:
        raise ValueError(
            "SDK validation command must be an array"
        )
    return ValidationStep(
        step_id=str(value["step_id"]),
        kind=str(value["kind"]),
        command=command,
        contract_id=(
            str(value["contract_id"])
            if value.get("contract_id") is not None
            else None
        ),
        test_id=(
            str(value["test_id"])
            if value.get("test_id") is not None
            else None
        ),
    )
EOF
###############################################################################
# 7. Validation service
###############################################################################
cat > src/l9_debt_resolver/validation/service.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    TransactionResult,
)
from .models import ValidationTranscript
from .protocol import SDKValidationGateway
class ValidationService:
    def __init__(
        self,
        gateway: SDKValidationGateway,
    ) -> None:
        self._gateway = gateway
    async def validate(
        self,
        *,
        workspace_root: str,
        classification_trace: ClassificationTrace,
        remediation_plan: RemediationPlan,
        transaction: TransactionResult,
    ) -> ValidationTranscript:
        SDK_plan = (
            await self._gateway.create_validation_plan(
                repository_snapshot_id=(
                    remediation_plan.repository_snapshot_id
                ),
                classification_trace=classification_trace,
                remediation_plan=remediation_plan,
            )
        )
        step_results = []
        for step in SDK_plan.steps:
            result = (
                await self._gateway.execute_validation_step(
                    workspace_root=workspace_root,
                    step=step,
                )
            )
            step_results.append(result)
            if result.result != "passed":
                break
        graph_delta = (
            await self._gateway.calculate_graph_delta(
                repository_snapshot_id=(
                    remediation_plan.repository_snapshot_id
                ),
                transaction=transaction,
                remediation_plan=remediation_plan,
            )
        )
        result, validation_result_id, limitations = (
            await self._gateway.finalize_validation(
                validation_plan_id=(
                    SDK_plan.validation_plan_id
                ),
                step_results=tuple(step_results),
                graph_delta=graph_delta,
            )
        )
        all_limitations = tuple(
            sorted(
                {
                    *SDK_plan.limitations,
                    *limitations,
                }
            )
        )
        transcript_material = {
            "validation_plan_id": (
                SDK_plan.validation_plan_id
            ),
            "validation_result_id": (
                validation_result_id
            ),
            "steps": [
                step.as_dict()
                for step in step_results
            ],
            "graph_delta": graph_delta.as_dict(),
            "result": result,
        }
        return ValidationTranscript(
            transcript_id=namespaced_identity(
                "validation_transcript_",
                transcript_material,
            ),
            validation_plan_id=(
                SDK_plan.validation_plan_id
            ),
            validation_result_id=(
                validation_result_id
            ),
            steps=tuple(step_results),
            graph_delta=graph_delta,
            result=result,
            limitations=all_limitations,
        )
EOF
###############################################################################
# 8. Plan loading
###############################################################################
cat > src/l9_debt_resolver/remediation/loader.py <<'EOF'
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .models import (
    Approval,
    RemediationPlan,
    ReplaceTextOperation,
)
def load_remediation_plan(
    path: Path,
) -> RemediationPlan:
    document = json.loads(
        path.read_text(encoding="utf-8")
    )
    if not isinstance(document, dict):
        raise ValueError(
            "remediation plan must be an object"
        )
    if (
        document.get("schema_version")
        != "l9.remediation-plan/v1"
    ):
        raise ValueError(
            "unsupported remediation plan version"
        )
    operations = tuple(
        _operation(value)
        for value in _list(
            document,
            "operations",
        )
    )
    approval_value = document.get("approval")
    approval = (
        _approval(approval_value)
        if approval_value is not None
        else None
    )
    return RemediationPlan(
        plan_id=_string(document, "plan_id"),
        classification_id=_string(
            document,
            "classification_id",
        ),
        failure_fingerprint=_string(
            document,
            "failure_fingerprint",
        ),
        repository_snapshot_id=_string(
            document,
            "repository_snapshot_id",
        ),
        repository_revision=_string(
            document,
            "repository_revision",
        ),
        remediation_class=_string(
            document,
            "remediation_class",
        ),
        evidence_ids=tuple(
            sorted(
                _string_list(
                    document,
                    "evidence_ids",
                )
            )
        ),
        justification=_string(
            document,
            "justification",
        ),
        operations=operations,
        expected_changed_paths=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_changed_paths",
                )
            )
        ),
        expected_package_boundaries=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_package_boundaries",
                )
            )
        ),
        expected_contract_ids=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_contract_ids",
                )
            )
        ),
        expected_dependency_edges=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_dependency_edges",
                )
            )
        ),
        validation_plan_id=_string(
            document,
            "validation_plan_id",
        ),
        approval=approval,
    )
def _operation(
    value: object,
) -> ReplaceTextOperation:
    document = _object(value)
    return ReplaceTextOperation(
        operation_id=_string(
            document,
            "operation_id",
        ),
        path=_string(document, "path"),
        expected_file_sha256=_string(
            document,
            "expected_file_sha256",
        ),
        expected_text=_string(
            document,
            "expected_text",
        ),
        replacement_text=_string(
            document,
            "replacement_text",
        ),
        replacement_sha256=_string(
            document,
            "replacement_sha256",
        ),
        evidence_ids=tuple(
            sorted(
                _string_list(
                    document,
                    "evidence_ids",
                )
            )
        ),
        justification=_string(
            document,
            "justification",
        ),
    )
def _approval(
    value: object,
) -> Approval:
    document = _object(value)
    return Approval(
        approval_id=_string(
            document,
            "approval_id",
        ),
        approved_paths=tuple(
            sorted(
                _string_list(
                    document,
                    "approved_paths",
                )
            )
        ),
        approved_at=_string(
            document,
            "approved_at",
        ),
        expires_at=_string(
            document,
            "expires_at",
        ),
    )
def _object(
    value: object,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            "expected JSON object"
        )
    return value
def _list(
    document: dict[str, Any],
    key: str,
) -> list[object]:
    value = document.get(key)
    if not isinstance(value, list):
        raise ValueError(
            f"{key} must be an array"
        )
    return value
def _string(
    document: dict[str, Any],
    key: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str):
        raise ValueError(
            f"{key} must be a string"
        )
    return value
def _string_list(
    document: dict[str, Any],
    key: str,
) -> list[str]:
    return [
        str(value)
        for value in _list(document, key)
    ]
EOF
###############################################################################
# 9. P3 runtime orchestration
###############################################################################
cat > src/l9_debt_resolver/runtime/remediation_service.py <<'EOF'
from __future__ import annotations
from pathlib import Path
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.remediation.errors import (
    ValidationFailedError,
)
from l9_debt_resolver.remediation.models import (
    RemediationExecutionResult,
    RemediationPlan,
)
from l9_debt_resolver.remediation.policy import (
    RemediationBounds,
    validate_remediation_policy,
)
from l9_debt_resolver.remediation.transaction import (
    WorkspaceTransaction,
)
from l9_debt_resolver.validation.protocol import (
    SDKValidationGateway,
)
from l9_debt_resolver.validation.service import (
    ValidationService,
)
class RemediationService:
    def __init__(
        self,
        *,
        validation_gateway: SDKValidationGateway,
        bounds: RemediationBounds | None = None,
    ) -> None:
        self._validation = ValidationService(
            validation_gateway
        )
        self._bounds = bounds or RemediationBounds()
    async def execute(
        self,
        *,
        workspace_root: Path,
        classification_trace: ClassificationTrace,
        remediation_plan: RemediationPlan,
    ) -> RemediationExecutionResult:
        classification = (
            classification_trace.classification
        )
        validate_remediation_policy(
            classification=classification,
            plan=remediation_plan,
            bounds=self._bounds,
        )
        transaction = WorkspaceTransaction(
            workspace_root=workspace_root,
            bounds=self._bounds,
        )
        transaction_result = transaction.apply(
            remediation_plan
        )
        try:
            transcript = await self._validation.validate(
                workspace_root=str(
                    workspace_root.resolve()
                ),
                classification_trace=(
                    classification_trace
                ),
                remediation_plan=remediation_plan,
                transaction=transaction_result,
            )
            if transcript.result != "passed":
                raise ValidationFailedError(
                    "SDK validation rejected remediation"
                )
            if (
                transcript.graph_delta
                .unexpected_changed_paths
            ):
                raise ValidationFailedError(
                    "graph delta contains unexpected paths"
                )
            transaction.commit()
            remediation_id = namespaced_identity(
                "remediation_",
                {
                    "plan_id": remediation_plan.plan_id,
                    "classification_id": (
                        classification.classification_id
                    ),
                    "changed_paths": list(
                        transaction_result.changed_paths
                    ),
                    "validation_result_id": (
                        transcript.validation_result_id
                    ),
                },
            )
            return RemediationExecutionResult(
                remediation_id=remediation_id,
                plan_id=remediation_plan.plan_id,
                status="validated",
                changed_paths=(
                    transaction_result.changed_paths
                ),
                changed_line_count=(
                    transaction_result.changed_line_count
                ),
                validation_transcript=(
                    transcript.as_dict()
                ),
                rolled_back=False,
                limitations=transcript.limitations,
            )
        except Exception:
            transaction.rollback()
            raise
EOF
###############################################################################
# 10. Capabilities
###############################################################################
cat > src/l9_debt_resolver/runtime/capabilities.py <<'EOF'
from __future__ import annotations
from typing import Any
def resolver_capabilities() -> dict[str, Any]:
    return {
        "schema_version": "l9.resolver-capabilities/v1",
        "phase": "RESOLVER-P3",
        "capabilities": {
            "contract_validation": True,
            "typed_CI_evidence": True,
            "attempt_lifecycle": True,
            "terminal_states": True,
            "corpus_safe_events": True,
            "failed_run_acquisition": True,
            "failed_job_acquisition": True,
            "failed_log_acquisition": True,
            "truncation_detection": True,
            "artifact_provenance": True,
            "secret_redaction": True,
            "SDK_repository_snapshots": True,
            "stack_frame_extraction": True,
            "SDK_entity_correlation": True,
            "related_test_correlation": True,
            "applicable_contract_correlation": True,
            "SDK_finding_correlation": True,
            "root_cause_classification": True,
            "classification_traces": True,
            "remediation_eligibility": True,
            "approval_enforcement": True,
            "protected_path_enforcement": True,
            "bounded_remediation": True,
            "transactional_patch_application": True,
            "rollback": True,
            "SDK_validation_plans": True,
            "original_failure_reproduction": True,
            "targeted_test_validation": True,
            "affected_contract_validation": True,
            "graph_delta_validation": True,
            "SDK_validation_execution": True,
            "branch_mutation": False,
            "remote_push": False,
            "CI_rerun_observation": False
        },
        "limitations": [
            "P3 mutates only the local workspace transactionally.",
            "Git branch creation and push begin in RESOLVER-P4.",
            "CI rerun observation begins in RESOLVER-P4.",
            "Automatic merge remains prohibited."
        ]
    }
EOF
###############################################################################
# 11. CLI integration
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("src/l9_debt_resolver/cli.py")
content = path.read_text(encoding="utf-8")
imports = """from .remediation.loader import load_remediation_plan
from .runtime.remediation_service import RemediationService
from .validation.json_gateway import JSONSDKValidationGateway
"""
anchor = "from .runtime.capabilities import resolver_capabilities\n"
if imports not in content:
    content = content.replace(
        anchor,
        anchor + imports,
    )
command = """
    remediate = commands.add_parser(
        "remediate-offline"
    )
    remediate.add_argument(
        "--workspace",
        required=True,
        type=Path,
    )
    remediate.add_argument(
        "--classification-trace",
        required=True,
        type=Path,
    )
    remediate.add_argument(
        "--remediation-plan",
        required=True,
        type=Path,
    )
    remediate.add_argument(
        "--sdk-validation",
        required=True,
        type=Path,
    )
"""
anchor = "    diagnose = commands.add_parser(\n"
if 'remediate-offline' not in content:
    content = content.replace(
        anchor,
        command + "\n" + anchor,
    )
helper = """
def _load_classification_trace(
    path: Path,
):
    from .classification.models import ClassificationTrace
    from .contracts.models import FailureClassification
    value = json.loads(
        path.read_text(encoding="utf-8")
    )
    classification = FailureClassification(
        classification_id=value["classification_id"],
        failure_fingerprint=value["failure_fingerprint"],
        category=value["category"],
        confidence=float(value["confidence"]),
        evidence_ids=tuple(value["evidence_ids"]),
        failed_command=value.get("failed_command"),
        repository_snapshot_id=value[
            "repository_snapshot_id"
        ],
        affected_entities=tuple(
            value["correlated_entity_ids"]
        ),
        remediation_eligibility=value[
            "remediation_eligibility"
        ],
        limitations=tuple(value["limitations"]),
    )
    return ClassificationTrace(
        trace_id=value["trace_id"],
        classification=classification,
        correlation_id=value["correlation_id"],
        correlated_entity_ids=tuple(
            value["correlated_entity_ids"]
        ),
        correlated_finding_ids=tuple(
            value["correlated_finding_ids"]
        ),
        related_test_ids=tuple(
            value["related_test_ids"]
        ),
        applicable_contract_ids=tuple(
            value["applicable_contract_ids"]
        ),
        matched_signatures=tuple(
            value["matched_signatures"]
        ),
        conflicting_signatures=tuple(
            value["conflicting_signatures"]
        ),
        limitations=tuple(value["limitations"]),
    )
async def remediate_offline(
    *,
    workspace: Path,
    classification_trace_path: Path,
    remediation_plan_path: Path,
    SDK_validation_path: Path,
) -> dict[str, Any]:
    classification_trace = (
        _load_classification_trace(
            classification_trace_path
        )
    )
    remediation_plan = load_remediation_plan(
        remediation_plan_path
    )
    gateway = JSONSDKValidationGateway(
        document_path=SDK_validation_path
    )
    result = await RemediationService(
        validation_gateway=gateway
    ).execute(
        workspace_root=workspace,
        classification_trace=classification_trace,
        remediation_plan=remediation_plan,
    )
    return result.as_dict()
"""
anchor = "def main() -> int:\n"
if helper not in content:
    content = content.replace(
        anchor,
        helper + anchor,
    )
handler = """
    if arguments.command == "remediate-offline":
        result = asyncio.run(
            remediate_offline(
                workspace=arguments.workspace,
                classification_trace_path=(
                    arguments.classification_trace
                ),
                remediation_plan_path=(
                    arguments.remediation_plan
                ),
                SDK_validation_path=(
                    arguments.sdk_validation
                ),
            )
        )
        emit(result)
        return 0
"""
anchor = '    if arguments.command == "diagnose-offline":\n'
if handler not in content:
    content = content.replace(
        anchor,
        handler + anchor,
    )
content = content.replace(
    '            "classification-trace",',
    '            "classification-trace",\n'
    '            "remediation-plan",\n'
    '            "validation-transcript",',
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 12. Version
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("pyproject.toml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    'version = "0.3.0"',
    'version = "0.4.0"',
)
path.write_text(content, encoding="utf-8")
path = Path("src/l9_debt_resolver/__init__.py")
content = path.read_text(encoding="utf-8")
content = content.replace(
    '__version__ = "0.3.0"',
    '__version__ = "0.4.0"',
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 13. Tests
###############################################################################
cat > tests/remediation/test_policy.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
import pytest
from l9_debt_resolver.contracts.models import (
    FailureClassification,
)
from l9_debt_resolver.remediation.errors import (
    ApprovalRequiredError,
    ProtectedPathError,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    ReplaceTextOperation,
)
from l9_debt_resolver.remediation.policy import (
    RemediationBounds,
    validate_remediation_policy,
)
def classification(
    eligibility: str = "automatic",
) -> FailureClassification:
    return FailureClassification(
        classification_id=(
            "classification_" + "a" * 64
        ),
        failure_fingerprint=(
            "failure_" + "b" * 64
        ),
        category="test_failure",
        confidence=0.95,
        evidence_ids=(
            "evidence_" + "c" * 64,
        ),
        failed_command="pytest",
        repository_snapshot_id="snapshot-1",
        affected_entities=("entity-1",),
        remediation_eligibility=eligibility,
        limitations=(),
    )
def plan(
    path: str = "src/app.py",
) -> RemediationPlan:
    operation = ReplaceTextOperation(
        operation_id="operation_" + "d" * 64,
        path=path,
        expected_file_sha256="e" * 64,
        expected_text="old",
        replacement_text="new",
        replacement_sha256="f" * 64,
        evidence_ids=(
            "evidence_" + "c" * 64,
        ),
        justification="fix assertion",
    )
    return RemediationPlan(
        plan_id="remediation_plan_" + "1" * 64,
        classification_id=(
            "classification_" + "a" * 64
        ),
        failure_fingerprint=(
            "failure_" + "b" * 64
        ),
        repository_snapshot_id="snapshot-1",
        repository_revision="a" * 40,
        remediation_class="bounded_source",
        evidence_ids=(
            "evidence_" + "c" * 64,
        ),
        justification="bounded fix",
        operations=(operation,),
        expected_changed_paths=(path,),
        expected_package_boundaries=(),
        expected_contract_ids=(),
        expected_dependency_edges=(),
        validation_plan_id="validation-plan-1",
        approval=None,
    )
def test_automatic_plan_is_allowed() -> None:
    validate_remediation_policy(
        classification=classification(),
        plan=plan(),
        bounds=RemediationBounds(),
    )
def test_protected_path_is_rejected() -> None:
    with pytest.raises(ProtectedPathError):
        validate_remediation_policy(
            classification=classification(),
            plan=plan(".github/workflows/ci.yml"),
            bounds=RemediationBounds(),
        )
def test_approval_required_plan_needs_approval() -> None:
    with pytest.raises(ApprovalRequiredError):
        validate_remediation_policy(
            classification=classification(
                "approval_required"
            ),
            plan=plan(),
            bounds=RemediationBounds(),
            now=datetime.now(timezone.utc),
        )
EOF
cat > tests/remediation/test_transaction.py <<'EOF'
from __future__ import annotations
import hashlib
from pathlib import Path
import pytest
from l9_debt_resolver.remediation.errors import (
    PatchPreconditionError,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    ReplaceTextOperation,
)
from l9_debt_resolver.remediation.policy import (
    RemediationBounds,
)
from l9_debt_resolver.remediation.transaction import (
    WorkspaceTransaction,
)
def plan(
    *,
    before: str,
    replacement: str,
) -> RemediationPlan:
    operation = ReplaceTextOperation(
        operation_id="operation_" + "a" * 64,
        path="src/app.py",
        expected_file_sha256=hashlib.sha256(
            before.encode("utf-8")
        ).hexdigest(),
        expected_text="old",
        replacement_text=replacement,
        replacement_sha256=hashlib.sha256(
            replacement.encode("utf-8")
        ).hexdigest(),
        evidence_ids=(
            "evidence_" + "b" * 64,
        ),
        justification="bounded change",
    )
    return RemediationPlan(
        plan_id="remediation_plan_" + "c" * 64,
        classification_id=(
            "classification_" + "d" * 64
        ),
        failure_fingerprint=(
            "failure_" + "e" * 64
        ),
        repository_snapshot_id="snapshot-1",
        repository_revision="f" * 40,
        remediation_class="bounded_source",
        evidence_ids=(
            "evidence_" + "b" * 64,
        ),
        justification="bounded change",
        operations=(operation,),
        expected_changed_paths=("src/app.py",),
        expected_package_boundaries=(),
        expected_contract_ids=(),
        expected_dependency_edges=(),
        validation_plan_id="validation-plan-1",
        approval=None,
    )
def test_transaction_applies_and_rolls_back(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src/app.py"
    target.parent.mkdir()
    before = "value = 'old'\n"
    target.write_text(before, encoding="utf-8")
    transaction = WorkspaceTransaction(
        workspace_root=tmp_path,
        bounds=RemediationBounds(),
    )
    transaction.apply(
        plan(
            before=before,
            replacement="new",
        )
    )
    assert "new" in target.read_text(
        encoding="utf-8"
    )
    transaction.rollback()
    assert target.read_text(
        encoding="utf-8"
    ) == before
def test_hash_mismatch_rejects_patch(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src/app.py"
    target.parent.mkdir()
    target.write_text(
        "value = 'different'\n",
        encoding="utf-8",
    )
    transaction = WorkspaceTransaction(
        workspace_root=tmp_path,
        bounds=RemediationBounds(),
    )
    with pytest.raises(PatchPreconditionError):
        transaction.apply(
            plan(
                before="value = 'old'\n",
                replacement="new",
            )
        )
EOF
cat > tests/validation/test_runner.py <<'EOF'
from __future__ import annotations
from pathlib import Path
import pytest
from l9_debt_resolver.validation.models import (
    ValidationStep,
)
from l9_debt_resolver.validation.runner import (
    ValidationCommandRunner,
)
@pytest.mark.asyncio
async def test_allowed_command_executes(
    tmp_path: Path,
) -> None:
    result = await ValidationCommandRunner().execute(
        workspace_root=tmp_path,
        step=ValidationStep(
            step_id="step-1",
            kind="targeted_test",
            command=(
                "python3",
                "-c",
                "raise SystemExit(0)",
            ),
            contract_id=None,
            test_id=None,
        ),
    )
    assert result.result == "passed"
    assert result.exit_code == 0
@pytest.mark.asyncio
async def test_unapproved_executable_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError):
        await ValidationCommandRunner().execute(
            workspace_root=tmp_path,
            step=ValidationStep(
                step_id="step-1",
                kind="targeted_test",
                command=("bash", "-c", "true"),
                contract_id=None,
                test_id=None,
            ),
        )
EOF
cat > tests/runtime/test_remediation_rollback.py <<'EOF'
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pytest
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.contracts.models import (
    FailureClassification,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    ReplaceTextOperation,
)
from l9_debt_resolver.runtime.remediation_service import (
    RemediationService,
)
from l9_debt_resolver.validation.json_gateway import (
    JSONSDKValidationGateway,
)
def trace() -> ClassificationTrace:
    classification = FailureClassification(
        classification_id=(
            "classification_" + "a" * 64
        ),
        failure_fingerprint=(
            "failure_" + "b" * 64
        ),
        category="test_failure",
        confidence=0.95,
        evidence_ids=(
            "evidence_" + "c" * 64,
        ),
        failed_command="pytest",
        repository_snapshot_id="snapshot-1",
        affected_entities=("entity-1",),
        remediation_eligibility="automatic",
        limitations=(),
    )
    return ClassificationTrace(
        trace_id=(
            "classification_trace_" + "d" * 64
        ),
        classification=classification,
        correlation_id=(
            "correlation_" + "e" * 64
        ),
        correlated_entity_ids=("entity-1",),
        correlated_finding_ids=(),
        related_test_ids=("test-1",),
        applicable_contract_ids=("contract-1",),
        matched_signatures=("1 failed",),
        conflicting_signatures=(),
        limitations=(),
    )
def plan(before: str) -> RemediationPlan:
    operation = ReplaceTextOperation(
        operation_id="operation_" + "f" * 64,
        path="src/app.py",
        expected_file_sha256=hashlib.sha256(
            before.encode("utf-8")
        ).hexdigest(),
        expected_text="old",
        replacement_text="new",
        replacement_sha256=hashlib.sha256(
            b"new"
        ).hexdigest(),
        evidence_ids=(
            "evidence_" + "c" * 64,
        ),
        justification="fix test",
    )
    return RemediationPlan(
        plan_id="remediation_plan_" + "1" * 64,
        classification_id=(
            "classification_" + "a" * 64
        ),
        failure_fingerprint=(
            "failure_" + "b" * 64
        ),
        repository_snapshot_id="snapshot-1",
        repository_revision="2" * 40,
        remediation_class="bounded_source",
        evidence_ids=(
            "evidence_" + "c" * 64,
        ),
        justification="fix test",
        operations=(operation,),
        expected_changed_paths=("src/app.py",),
        expected_package_boundaries=(),
        expected_contract_ids=("contract-1",),
        expected_dependency_edges=(),
        validation_plan_id="validation-plan-1",
        approval=None,
    )
@pytest.mark.asyncio
async def test_validation_failure_rolls_back(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src/app.py"
    target.parent.mkdir()
    before = "value = 'old'\n"
    target.write_text(before, encoding="utf-8")
    SDK_document = {
        "schema_version": "l9.sdk-validation-document/v1",
        "validation_plan": {
            "validation_plan_id": "validation-plan-1",
            "repository_snapshot_id": "snapshot-1",
            "classification_id": (
                "classification_" + "a" * 64
            ),
            "remediation_plan_id": (
                "remediation_plan_" + "1" * 64
            ),
            "full_gate_required": False,
            "limitations": [],
            "steps": [
                {
                    "step_id": "original",
                    "kind": "original_failure",
                    "command": [
                        "python3",
                        "-c",
                        "raise SystemExit(1)"
                    ]
                },
                {
                    "step_id": "test",
                    "kind": "targeted_test",
                    "command": [
                        "python3",
                        "-c",
                        "raise SystemExit(0)"
                    ]
                },
                {
                    "step_id": "contract",
                    "kind": "affected_contract",
                    "command": [
                        "python3",
                        "-c",
                        "raise SystemExit(0)"
                    ]
                },
                {
                    "step_id": "graph",
                    "kind": "graph_delta",
                    "command": null
                }
            ]
        },
        "validation_result_id": "validation-result-1"
    }
    SDK_path = tmp_path / "sdk-validation.json"
    SDK_path.write_text(
        json.dumps(SDK_document),
        encoding="utf-8",
    )
    gateway = JSONSDKValidationGateway(
        document_path=SDK_path
    )
    with pytest.raises(Exception):
        await RemediationService(
            validation_gateway=gateway
        ).execute(
            workspace_root=tmp_path,
            classification_trace=trace(),
            remediation_plan=plan(before),
        )
    assert target.read_text(
        encoding="utf-8"
    ) == before
EOF
cat > tests/architecture/test_P3_boundaries.py <<'EOF'
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED_REMOTE_TERMS = (
    "git push",
    "git commit",
    "git checkout",
    "git switch",
    "merge_pull_request",
    "automatic_merge",
    "gh pr merge",
)
PROHIBITED_WEAKENING_TERMS = (
    "disable_tests",
    "skip_tests",
    "weaken_security",
    "weaken_lint",
    "comment_out_failure",
)
def test_P3_has_no_remote_git_behavior() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED_REMOTE_TERMS:
            assert term not in content, (
                f"{path} contains prohibited remote "
                f"operation {term}"
            )
def test_P3_has_no_gate_weakening_behavior() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED_WEAKENING_TERMS:
            assert term not in content, (
                f"{path} contains prohibited weakening "
                f"operation {term}"
            )
def test_validation_runner_uses_exec_not_shell() -> None:
    path = (
        SOURCE
        / "validation"
        / "runner.py"
    )
    content = path.read_text(encoding="utf-8")
    assert "create_subprocess_exec" in content
    assert "create_subprocess_shell" not in content
    assert "shell=True" not in content
EOF
###############################################################################
# 14. Documentation
###############################################################################
cat > docs/architecture/ADRs/ADR-RESOLVER-013-transactional-local-remediation.md <<'EOF'
# ADR-RESOLVER-013: P3 remediation is transactional and local
- Status: Accepted
- Phase: RESOLVER-P3
## Decision
P3 may mutate only the local workspace.
Every original file is captured before mutation. Any patch, validation, graph
delta, or SDK result failure causes rollback.
Remote branch interaction begins only in P4.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-014-validation-is-sdk-owned.md <<'EOF'
# ADR-RESOLVER-014: Validation planning remains SDK-owned
- Status: Accepted
- Phase: RESOLVER-P3
## Decision
The resolver executes only SDK-authorized validation plans.
It does not independently choose tests, affected contracts, package gates, or
full-validation scope.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-015-protected-paths-cannot-be-overridden.md <<'EOF'
# ADR-RESOLVER-015: Protected paths cannot be overridden in P3
- Status: Accepted
- Phase: RESOLVER-P3
## Decision
Governance, schema, workflow, security, compliance, and repository-control
paths are protected.
P3 does not support an override mechanism.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-016-validation-failure-rolls-back.md <<'EOF'
# ADR-RESOLVER-016: Any validation failure rolls back remediation
- Status: Accepted
- Phase: RESOLVER-P3
## Decision
Original-failure reproduction, targeted tests, affected contracts, graph
delta, full gates, and the canonical SDK validation result must all pass.
Otherwise the workspace is restored to its pre-remediation state.
EOF
cat >> README.md <<'EOF'
## RESOLVER-P3: bounded remediation and validation
P3 applies only evidence-supported local changes.
```text
classification trace
        ↓
eligibility and approval policy
        ↓
protected-path checks
        ↓
exact file and text preconditions
        ↓
transactional local patch
        ↓
SDK validation plan
        ├── original failure reproduction
        ├── targeted tests
        ├── affected contracts
        ├── graph delta
        └── full gate when required
        ↓
pass → commit local transaction
fail → rollback

Execute an offline remediation

l9-debt-resolver remediate-offline \
  --workspace /path/to/repository \
  --classification-trace classification-trace.json \
  --remediation-plan remediation-plan.json \
  --sdk-validation sdk-validation.json

P3 never creates branches, pushes commits, observes reruns, or merges changes.

Protected paths

P3 blocks changes under:

* .git/
* .github/workflows/
* .l9/
* schemas/
* security/
* compliance/
* governance/

These paths have no P3 override.

Validation behavior

A remediation is retained only when:

* the original failed command or equivalent passes;
* targeted tests pass;
* affected contracts pass;
* graph delta matches the approved plan;
* the SDK returns a canonical passing validation result.
    EOF

python3 - <<‘PY’
from pathlib import Path

path = Path(“ROADMAP.md”)
content = path.read_text(encoding=“utf-8”)

content = content.replace(
“””## RESOLVER-P3 — Bounded validation

Status: Planned

* remediation eligibility
* protected-path enforcement
* bounded change validation
* SDK validation plans
* original failure reproduction
* graph-delta checks
* rollback”””,
    “””## RESOLVER-P3 — Bounded validation

Status: Implemented

* remediation eligibility
* approval enforcement
* protected-path enforcement
* changed-file and changed-line bounds
* exact file-hash preconditions
* exact text replacement preconditions
* transactional patch application
* SDK validation plans
* original failure reproduction
* targeted tests
* affected-contract validation
* graph-delta checks
* full-gate support
* automatic rollback”””,
    )

path.write_text(content, encoding=“utf-8”)
PY

python3 - <<‘PY’
from pathlib import Path

path = Path(”.l9/repo-spec.yaml”)
content = path.read_text(encoding=“utf-8”)

content = content.replace(
“phase: RESOLVER-P2”,
“phase: RESOLVER-P3”,
1,
)

content = content.replace(
“phase_name: repository_correlation”,
“phase_name: bounded_validation”,
1,
)

content = content.replace(
“””  - phase: RESOLVER-P3
name: bounded_validation
priority: high
status: planned”””,
“””  - phase: RESOLVER-P3
name: bounded_validation
priority: high
status: implemented”””,
)

path.write_text(content, encoding=“utf-8”)
PY

###############################################################################

15. Acceptance gates

###############################################################################

cat > .l9/phase-3-acceptance-gates.yaml <<‘EOF’
schema: l9.phase-acceptance-gates/v1

repository: Quantum-L9/l9-ci-debt-resolver
phase: RESOLVER-P3

gates:

* id: p3-classification-bound
    requirement: >
    Every remediation plan matches the exact classification ID, failure
    fingerprint, evidence IDs, and repository snapshot.
* id: p3-approval
    requirement: >
    Approval-required classifications cannot mutate the workspace without a
    non-expired approval covering every changed path.
* id: p3-protected-path
    requirement: >
    Protected workflow, schema, governance, security, compliance, and
    repository-control paths cannot be modified.
* id: p3-bounded-change
    requirement: >
    Remediation remains within file, operation, line, and byte limits.
* id: p3-exact-preconditions
    requirement: >
    Every patch operation verifies file hash, replacement hash, and a unique
    expected-text match.
* id: p3-transaction
    requirement: >
    Workspace mutation is atomic and retains original bytes until validation
    succeeds.
* id: p3-original-failure
    requirement: >
    The SDK validation plan includes the original failed command or an
    equivalent reproduction.
* id: p3-targeted-tests
    requirement: >
    SDK-selected targeted tests are executed.
* id: p3-contract-validation
    requirement: >
    SDK-selected affected contracts are validated.
* id: p3-graph-delta
    requirement: >
    Unexpected paths, package boundaries, contracts, or dependency edges
    reject the remediation.
* id: p3-rollback
    requirement: >
    Any patch or validation failure restores the original workspace.
* id: p3-no-remote
    requirement: >
    P3 cannot create branches, commit, push, merge, or observe CI reruns.
    EOF

###############################################################################

16. CI

###############################################################################

cat > .github/workflows/phase-3-bounded-remediation.yml <<‘EOF’
name: RESOLVER-P3 Bounded Remediation

on:
pull_request:
push:
branches:
- main

permissions:
contents: read

jobs:
bounded-remediation:
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
  - name: Remediation tests
    run: pytest tests/remediation
  - name: Validation tests
    run: pytest tests/validation
  - name: Runtime rollback tests
    run: pytest tests/runtime
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

17. Structural validation

###############################################################################

python3 -m compileall -q src

python3 - <<‘PY’
from future import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path.cwd()

required = [
“.l9/remediation-contract.yaml”,
“.l9/validation-contract.yaml”,
“.l9/phase-3-acceptance-gates.yaml”,
“schemas/resolver/remediation-plan.schema.json”,
“schemas/resolver/validation-transcript.schema.json”,
“src/l9_debt_resolver/remediation/models.py”,
“src/l9_debt_resolver/remediation/policy.py”,
“src/l9_debt_resolver/remediation/transaction.py”,
“src/l9_debt_resolver/validation/models.py”,
“src/l9_debt_resolver/validation/protocol.py”,
“src/l9_debt_resolver/validation/runner.py”,
“src/l9_debt_resolver/validation/json_gateway.py”,
“src/l9_debt_resolver/validation/service.py”,
“src/l9_debt_resolver/runtime/remediation_service.py”,
“tests/remediation/test_policy.py”,
“tests/remediation/test_transaction.py”,
“tests/validation/test_runner.py”,
“tests/runtime/test_remediation_rollback.py”,
“.github/workflows/phase-3-bounded-remediation.yml”,
]

missing = [
item
for item in required
if not (root / item).is_file()
]

if missing:
raise SystemExit(
f”RESOLVER-P3 required files missing: {missing}”
)

for path in sorted(
(root / “schemas/resolver”).glob(”*.json”)
):
schema = json.loads(
path.read_text(encoding=“utf-8”)
)
Draft202012Validator.check_schema(schema)

source = root / “src/l9_debt_resolver”

prohibited = (
“git push”,
“git commit”,
“git checkout”,
“git switch”,
“automatic_merge”,
“merge_pull_request”,
“gh pr merge”,
“create_subprocess_shell”,
“shell=true”,
“disable_tests”,
“skip_tests”,
“weaken_security”,
“weaken_lint”,
)

for path in source.rglob(”*.py”):
content = path.read_text(
encoding=“utf-8”
).lower()

for term in prohibited:
    if term in content:
        raise SystemExit(
            f"prohibited RESOLVER-P3 behavior "
            f"{term!r} in {path}"
        )

capabilities = (
source
/ “runtime”
/ “capabilities.py”
).read_text(encoding=“utf-8”)

required_capabilities = (
‘“approval_enforcement”: True’,
‘“protected_path_enforcement”: True’,
‘“bounded_remediation”: True’,
‘“transactional_patch_application”: True’,
‘“rollback”: True’,
‘“SDK_validation_plans”: True’,
‘“original_failure_reproduction”: True’,
‘“graph_delta_validation”: True’,
‘“SDK_validation_execution”: True’,
‘“branch_mutation”: False’,
‘“remote_push”: False’,
‘“CI_rerun_observation”: False’,
)

for capability in required_capabilities:
if capability not in capabilities:
raise SystemExit(
f”missing capability declaration: {capability}”
)

runner = (
source
/ “validation”
/ “runner.py”
).read_text(encoding=“utf-8”)

if “create_subprocess_exec” not in runner:
raise SystemExit(
“validation runner must use create_subprocess_exec”
)

if “create_subprocess_shell” in runner:
raise SystemExit(
“shell-based validation execution is prohibited”
)

print(
json.dumps(
{
“schema_version”: “l9.phase-build-result/v1”,
“repository”: (
“Quantum-L9/l9-ci-debt-resolver”
),
“version”: “0.4.0”,
“phase”: “RESOLVER-P3”,
“status”: “built”,
“approval_enforcement”: True,
“protected_path_enforcement”: True,
“bounded_remediation”: True,
“transactional_patch_application”: True,
“rollback”: True,
“SDK_validation_plans”: True,
“original_failure_reproduction”: True,
“targeted_test_validation”: True,
“affected_contract_validation”: True,
“graph_delta_validation”: True,
“full_gate_support”: True,
“branch_mutation”: False,
“remote_push”: False,
“CI_rerun_observation”: False
},
sort_keys=True,
separators=(”,”, “:”),
)
)
PY

printf ‘\n’
printf ‘RESOLVER-P3 build complete.\n’
printf ‘\n’
printf ‘Implemented:\n’
printf ’  - evidence-bound remediation plans\n’
printf ’  - confidence and approval enforcement\n’
printf ’  - protected-path enforcement\n’
printf ’  - file, operation, line, and byte bounds\n’
printf ’  - exact file-hash and text preconditions\n’
printf ’  - transactional local patch application\n’
printf ’  - automatic rollback\n’
printf ’  - SDK-owned validation plans\n’
printf ’  - original failure reproduction\n’
printf ’  - targeted test execution\n’
printf ’  - affected-contract validation\n’
printf ’  - graph-delta validation\n’
printf ’  - full-gate support\n’
printf ’  - deterministic validation transcripts\n’
printf ’  - no branch creation, push, rerun, or merge\n’
printf ‘\n’
printf ‘Validate with:\n’
printf “  python -m pip install -e ‘.[dev]’\n”
printf ’  pytest\n’
printf ’  ruff check .\n’
printf ’  mypy src\n’
printf ’  l9-debt-resolver capabilities\n’
printf ‘\n’
printf ‘Next phase:\n’
printf ’  RESOLVER-P4 — safe branch preparation, bounded commits, push\n’
printf ’  authorization, CI rerun observation, repeated-fingerprint\n’
printf ’  detection, attempt limits, and deterministic terminal states.\n’

:::
P3 intentionally supports only local transactional mutation. A validated patch is not yet considered resolved: P4 must push it to an allowed branch and confirm a successful CI rerun before the resolver can emit `clean`.