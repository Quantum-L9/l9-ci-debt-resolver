#!/usr/bin/env bash
set -euo pipefail
###############################################################################
# Quantum-L9/l9-ci-debt-resolver
# RESOLVER-P2 - SDK Repository Correlation and Root-Cause Classification
#
# Incremental build over RESOLVER-P0 and RESOLVER-P1.
#
# Implements:
#   - SDK repository-knowledge public adapter contract
#   - SDK-owned repository snapshot references
#   - redacted evidence bundles
#   - deterministic stack-frame extraction
#   - stack-frame-to-entity correlation
#   - related-test correlation
#   - applicable-contract correlation
#   - canonical SDK finding correlation
#   - evidence-bound CI root-cause classification
#   - confidence and remediation-eligibility policy
#   - classification trace and limitations
#   - unsupported and infrastructure failure handling
#   - JSON document SDK adapter for integration and fixtures
#   - CLI correlation/classification command
#   - architecture, privacy, determinism, and contract tests
#
# Does not implement:
#   - repository mutation or patch application       (RESOLVER-P3)
#   - SDK validation-plan execution                  (RESOLVER-P3)
#   - Git branch interaction                         (RESOLVER-P4)
#   - CI rerun observation                           (RESOLVER-P4)
#   - Intelligence event delivery                    (RESOLVER-P5)
###############################################################################
fail() {
  printf 'RESOLVER-P2: %s\n' "$*" >&2
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
  || fail "RESOLVER-P0 repository specification is missing"
[[ -f .l9/log-acquisition-contract.yaml ]] \
  || fail "RESOLVER-P1 log-acquisition contract is missing"
[[ -f src/l9_debt_resolver/acquisition/service.py ]] \
  || fail "RESOLVER-P1 runtime is missing"
mkdir -p \
  .github/workflows \
  .l9 \
  docs/architecture/ADRs \
  schemas/resolver \
  src/l9_debt_resolver/correlation \
  src/l9_debt_resolver/classification \
  src/l9_debt_resolver/sdk \
  tests/correlation \
  tests/classification \
  tests/sdk \
  tests/fixtures/sdk \
  tests/architecture
###############################################################################
# 1. Authoritative P2 contracts
###############################################################################
cat > .l9/repository-correlation-contract.yaml <<'EOF'
schema: l9.resolver-repository-correlation-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P2
  status: authoritative
authority:
  CI_failure:
    primary: actual_failed_log
    secondary: failed_job_metadata
  repository_semantics:
    authority: Quantum-L9/l9-ci-sdk
  historical_context:
    may_support: true
    may_override_current_logs: false
SDK_boundary:
  required_public_operations:
    - open_repository_snapshot
    - resolve_source_locations
    - resolve_repository_entities
    - find_related_tests
    - find_applicable_contracts
    - correlate_findings
  canonical_identities:
    owned_by_SDK:
      - repository_snapshot_id
      - evidence_id
      - finding_id
      - source_location_id
      - repository_entity_id
      - validation_plan_id
      - validation_result_id
  resolver_must_not:
    - redefine SDK schema identities
    - inspect private SDK internals
    - synthesize canonical SDK finding IDs
    - infer repository semantics from file names alone
    - treat historical findings as current CI evidence
input:
  required:
    - failed run identity
    - failed job identity
    - complete typed CI evidence
    - redacted failed log
    - repository revision
  prohibitions:
    - unredacted log persistence
    - source-content persistence
    - absolute-path persistence
    - credentials
stack_frames:
  supported_families:
    - python
    - javascript_typescript
    - java_kotlin
    - go
    - rust
    - dotnet
    - generic_compiler_location
  output:
    - normalized repository-relative path
    - line
    - column
    - symbol hint
    - language family
    - log line number
    - confidence
    - limitations
  protections:
    - absolute paths are reduced to repository-relative candidates
    - traversal segments are rejected
    - paths outside the repository are excluded
    - redaction placeholders are never interpreted as paths
correlation:
  required_outputs:
    - repository_snapshot_id
    - stack_frames
    - repository_entities
    - related_tests
    - applicable_contracts
    - correlated_findings
    - unresolved_locations
    - limitations
  determinism:
    - outputs are sorted by canonical identity
    - duplicate locations are removed
    - duplicate SDK entities are removed
    - duplicate SDK findings are removed
classification:
  categories:
    - configuration
    - dependency
    - compilation
    - test_failure
    - lint_failure
    - type_failure
    - generated_file_drift
    - security_failure
    - infrastructure
    - unsupported
  required_trace:
    - classification_id
    - failure_fingerprint
    - category
    - confidence
    - evidence_ids
    - matched_signals
    - failed_command
    - repository_snapshot_id
    - affected_entities
    - related_tests
    - applicable_contracts
    - correlated_finding_ids
    - remediation_eligibility
    - limitations
  confidence_policy:
    automatic_minimum: 0.90
    approval_required_minimum: 0.70
    below_approval_threshold: unsupported
  safety:
    infrastructure:
      remediation_eligibility: unsupported
    security_failure:
      remediation_eligibility: approval_required
    unsupported:
      remediation_eligibility: unsupported
    incomplete_evidence:
      classification: prohibited
      terminal_state: insufficient_log_evidence
    conflicting_high_confidence_categories:
      classification: unsupported
      limitation: conflicting root-cause signals
failure_behavior:
  SDK_unavailable:
    terminal_state: remote_operation_failed
  SDK_snapshot_failure:
    terminal_state: remote_operation_failed
  no_resolved_entities:
    classification_allowed: true
    limitation_required: true
  no_matching_root_cause:
    category: unsupported
    remediation_eligibility: unsupported
EOF
cat > .l9/classification-policy.yaml <<'EOF'
schema: l9.resolver-classification-policy/v1
metadata:
  phase: RESOLVER-P2
  authority: repository
confidence:
  automatic_minimum: 0.90
  approval_required_minimum: 0.70
signal_weights:
  exact_failed_command: 0.20
  explicit_tool_signature: 0.35
  explicit_failure_marker: 0.20
  resolved_repository_entity: 0.10
  applicable_contract: 0.05
  correlated_SDK_finding: 0.10
caps:
  no_explicit_tool_signature: 0.69
  no_complete_runtime_log: 0.00
  infrastructure: 0.89
  conflicting_categories: 0.49
automatic_categories:
  - configuration
  - dependency
  - compilation
  - test_failure
  - lint_failure
  - type_failure
  - generated_file_drift
approval_required_categories:
  - security_failure
unsupported_categories:
  - infrastructure
  - unsupported
prohibitions:
  - classification from job name alone
  - classification from historical memory alone
  - classification from incomplete logs
  - automatic remediation of conflicting classifications
  - automatic remediation of infrastructure failures
  - automatic remediation of security policy failures
EOF
###############################################################################
# 2. P2 schemas
###############################################################################
cat > schemas/resolver/evidence-bundle.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/evidence-bundle/v1",
  "title": "L9 Resolver Evidence Bundle",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "repository",
    "revision",
    "evidence",
    "redacted_log",
    "failed_job"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.evidence-bundle/v1"
    },
    "repository": {
      "type": "string",
      "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    },
    "revision": {
      "type": "string",
      "minLength": 7,
      "maxLength": 128
    },
    "evidence": {
      "$ref": "l9://resolver/ci-run-evidence/v1"
    },
    "redacted_log": {
      "type": "string",
      "minLength": 1,
      "maxLength": 52428800
    },
    "failed_job": {
      "$ref": "l9://resolver/failed-job/v1"
    }
  }
}
EOF
cat > schemas/resolver/stack-frame.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/stack-frame/v1",
  "title": "L9 Resolver Stack Frame",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "frame_id",
    "path",
    "line",
    "column",
    "symbol_hint",
    "language_family",
    "log_line_number",
    "confidence",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.stack-frame/v1"
    },
    "frame_id": {
      "type": "string",
      "pattern": "^frame_[0-9a-f]{64}$"
    },
    "path": {
      "type": "string",
      "minLength": 1,
      "maxLength": 1000,
      "not": {
        "pattern": "^(?:/|[A-Za-z]:\\\\|.*(?:^|/)\\.\\.(?:/|$))"
      }
    },
    "line": {
      "type": [
        "integer",
        "null"
      ],
      "minimum": 1
    },
    "column": {
      "type": [
        "integer",
        "null"
      ],
      "minimum": 1
    },
    "symbol_hint": {
      "type": [
        "string",
        "null"
      ],
      "maxLength": 1000
    },
    "language_family": {
      "enum": [
        "python",
        "javascript_typescript",
        "java_kotlin",
        "go",
        "rust",
        "dotnet",
        "generic"
      ]
    },
    "log_line_number": {
      "type": "integer",
      "minimum": 1
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
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
cat > schemas/resolver/repository-correlation.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/repository-correlation/v1",
  "title": "L9 Resolver Repository Correlation",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "correlation_id",
    "evidence_id",
    "repository_snapshot_id",
    "stack_frames",
    "repository_entities",
    "related_tests",
    "applicable_contracts",
    "correlated_findings",
    "unresolved_locations",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.repository-correlation/v1"
    },
    "correlation_id": {
      "type": "string",
      "pattern": "^correlation_[0-9a-f]{64}$"
    },
    "evidence_id": {
      "type": "string",
      "pattern": "^evidence_[0-9a-f]{64}$"
    },
    "repository_snapshot_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "stack_frames": {
      "type": "array",
      "items": {
        "$ref": "l9://resolver/stack-frame/v1"
      }
    },
    "repository_entities": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/repository-entity/v1"
      }
    },
    "related_tests": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/repository-entity/v1"
      }
    },
    "applicable_contracts": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/contract-reference/v1"
      }
    },
    "correlated_findings": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/finding/v1"
      }
    },
    "unresolved_locations": {
      "type": "array",
      "items": {
        "$ref": "l9://resolver/stack-frame/v1"
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
cat > schemas/resolver/classification-trace.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/classification-trace/v1",
  "title": "L9 Resolver Classification Trace",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "classification_id",
    "failure_fingerprint",
    "category",
    "confidence",
    "evidence_ids",
    "matched_signals",
    "failed_command",
    "repository_snapshot_id",
    "affected_entities",
    "related_tests",
    "applicable_contracts",
    "correlated_finding_ids",
    "remediation_eligibility",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.classification-trace/v1"
    },
    "classification_id": {
      "type": "string",
      "pattern": "^classification_[0-9a-f]{64}$"
    },
    "failure_fingerprint": {
      "type": "string",
      "pattern": "^failure_[0-9a-f]{64}$"
    },
    "category": {
      "enum": [
        "configuration",
        "dependency",
        "compilation",
        "test_failure",
        "lint_failure",
        "type_failure",
        "generated_file_drift",
        "security_failure",
        "infrastructure",
        "unsupported"
      ]
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "evidence_ids": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "pattern": "^evidence_[0-9a-f]{64}$"
      },
      "uniqueItems": true
    },
    "matched_signals": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "signal",
          "category",
          "weight",
          "source"
        ],
        "properties": {
          "signal": {
            "type": "string",
            "minLength": 1,
            "maxLength": 500
          },
          "category": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
          },
          "weight": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "source": {
            "enum": [
              "failed_log",
              "failed_command",
              "SDK_entity",
              "SDK_contract",
              "SDK_finding"
            ]
          }
        }
      }
    },
    "failed_command": {
      "type": [
        "string",
        "null"
      ],
      "maxLength": 2000
    },
    "repository_snapshot_id": {
      "type": "string",
      "minLength": 1
    },
    "affected_entities": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1,
        "maxLength": 500
      },
      "uniqueItems": true
    },
    "related_tests": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1,
        "maxLength": 500
      },
      "uniqueItems": true
    },
    "applicable_contracts": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1,
        "maxLength": 500
      },
      "uniqueItems": true
    },
    "correlated_finding_ids": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1,
        "maxLength": 500
      },
      "uniqueItems": true
    },
    "remediation_eligibility": {
      "enum": [
        "automatic",
        "approval_required",
        "unsupported"
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
cat > schemas/resolver/sdk-knowledge-document.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/sdk-knowledge-document/v1",
  "title": "L9 Resolver SDK Knowledge Exchange Document",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "repository",
    "revision",
    "snapshot",
    "entities",
    "tests",
    "contracts",
    "findings"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.sdk-knowledge-document/v1"
    },
    "repository": {
      "type": "string",
      "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    },
    "revision": {
      "type": "string",
      "minLength": 7,
      "maxLength": 128
    },
    "snapshot": {
      "$ref": "l9://sdk/repository-snapshot/v1"
    },
    "entities": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/repository-entity/v1"
      }
    },
    "tests": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/repository-entity/v1"
      }
    },
    "contracts": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/contract-reference/v1"
      }
    },
    "findings": {
      "type": "array",
      "items": {
        "$ref": "l9://sdk/finding/v1"
      }
    }
  }
}
EOF
###############################################################################
# 3. SDK public integration models and protocol
###############################################################################
cat > src/l9_debt_resolver/sdk/__init__.py <<'EOF'
"""Public SDK repository-knowledge integration boundary."""
EOF
cat > src/l9_debt_resolver/sdk/errors.py <<'EOF'
from __future__ import annotations
class SDKIntegrationError(RuntimeError):
    """Base SDK integration failure."""
class SDKUnavailableError(SDKIntegrationError):
    """The public SDK knowledge service is unavailable."""
class SDKContractError(SDKIntegrationError):
    """SDK knowledge does not satisfy the public exchange contract."""
class SnapshotMismatchError(SDKIntegrationError):
    """SDK knowledge belongs to another repository revision."""
EOF
cat > src/l9_debt_resolver/sdk/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class SDKSnapshot:
    snapshot_id: str
    repository: str
    revision: str
    capability_profile: tuple[str, ...]
    limitations: tuple[str, ...]
@dataclass(frozen=True)
class SDKRepositoryEntity:
    entity_id: str
    kind: str
    path: str | None
    start_line: int | None
    end_line: int | None
    symbol: str | None
    language: str | None
    metadata: dict[str, Any]
@dataclass(frozen=True)
class SDKContractReference:
    contract_id: str
    kind: str
    subject_entity_ids: tuple[str, ...]
    metadata: dict[str, Any]
@dataclass(frozen=True)
class SDKFindingReference:
    finding_id: str
    rule_id: str
    severity: str
    entity_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    metadata: dict[str, Any]
EOF
cat > src/l9_debt_resolver/sdk/protocol.py <<'EOF'
from __future__ import annotations
from typing import Protocol
from l9_debt_resolver.correlation.models import (
    StackFrame,
)
from .models import (
    SDKContractReference,
    SDKFindingReference,
    SDKRepositoryEntity,
    SDKSnapshot,
)
class SDKKnowledgeProvider(Protocol):
    async def open_repository_snapshot(
        self,
        *,
        repository: str,
        revision: str,
    ) -> SDKSnapshot:
        """Open a canonical SDK-owned repository snapshot."""
    async def resolve_repository_entities(
        self,
        *,
        snapshot_id: str,
        locations: tuple[StackFrame, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        """Resolve log locations to canonical SDK entities."""
    async def find_related_tests(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        """Return canonical SDK test entities related to entities."""
    async def find_applicable_contracts(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKContractReference, ...]:
        """Return SDK-owned contracts applicable to entities."""
    async def correlate_findings(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
    ) -> tuple[SDKFindingReference, ...]:
        """Return canonical SDK findings associated with the failure."""
EOF
###############################################################################
# 4. Correlation models and stack-frame extraction
###############################################################################
cat > src/l9_debt_resolver/correlation/__init__.py <<'EOF'
"""Evidence-to-repository correlation."""
EOF
cat > src/l9_debt_resolver/correlation/errors.py <<'EOF'
from __future__ import annotations
class CorrelationError(RuntimeError):
    """Base repository-correlation failure."""
class IncompleteEvidenceError(CorrelationError):
    """Correlation requires complete primary failed-log evidence."""
class UnsafePathError(CorrelationError):
    """A log path cannot be safely interpreted as repository-relative."""
EOF
cat > src/l9_debt_resolver/correlation/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from l9_debt_resolver.sdk.models import (
    SDKContractReference,
    SDKFindingReference,
    SDKRepositoryEntity,
)
@dataclass(frozen=True)
class EvidenceBundle:
    repository: str
    revision: str
    evidence: Any
    redacted_log: str
    failed_job: Any
@dataclass(frozen=True)
class StackFrame:
    frame_id: str
    path: str
    line: int | None
    column: int | None
    symbol_hint: str | None
    language_family: str
    log_line_number: int
    confidence: float
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.stack-frame/v1",
            "frame_id": self.frame_id,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "symbol_hint": self.symbol_hint,
            "language_family": self.language_family,
            "log_line_number": self.log_line_number,
            "confidence": self.confidence,
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class RepositoryCorrelation:
    correlation_id: str
    evidence_id: str
    repository_snapshot_id: str
    stack_frames: tuple[StackFrame, ...]
    repository_entities: tuple[SDKRepositoryEntity, ...]
    related_tests: tuple[SDKRepositoryEntity, ...]
    applicable_contracts: tuple[SDKContractReference, ...]
    correlated_findings: tuple[SDKFindingReference, ...]
    unresolved_locations: tuple[StackFrame, ...]
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.repository-correlation/v1",
            "correlation_id": self.correlation_id,
            "evidence_id": self.evidence_id,
            "repository_snapshot_id": self.repository_snapshot_id,
            "stack_frames": [
                frame.as_dict()
                for frame in self.stack_frames
            ],
            "repository_entities": [
                {
                    "entity_id": entity.entity_id,
                    "kind": entity.kind,
                    "path": entity.path,
                    "start_line": entity.start_line,
                    "end_line": entity.end_line,
                    "symbol": entity.symbol,
                    "language": entity.language,
                    "metadata": entity.metadata,
                }
                for entity in self.repository_entities
            ],
            "related_tests": [
                {
                    "entity_id": entity.entity_id,
                    "kind": entity.kind,
                    "path": entity.path,
                    "start_line": entity.start_line,
                    "end_line": entity.end_line,
                    "symbol": entity.symbol,
                    "language": entity.language,
                    "metadata": entity.metadata,
                }
                for entity in self.related_tests
            ],
            "applicable_contracts": [
                {
                    "contract_id": contract.contract_id,
                    "kind": contract.kind,
                    "subject_entity_ids": list(
                        contract.subject_entity_ids
                    ),
                    "metadata": contract.metadata,
                }
                for contract in self.applicable_contracts
            ],
            "correlated_findings": [
                {
                    "finding_id": finding.finding_id,
                    "rule_id": finding.rule_id,
                    "severity": finding.severity,
                    "entity_ids": list(finding.entity_ids),
                    "evidence_ids": list(finding.evidence_ids),
                    "metadata": finding.metadata,
                }
                for finding in self.correlated_findings
            ],
            "unresolved_locations": [
                frame.as_dict()
                for frame in self.unresolved_locations
            ],
            "limitations": list(self.limitations),
        }
EOF
cat > src/l9_debt_resolver/correlation/paths.py <<'EOF'
from __future__ import annotations
from pathlib import PurePosixPath
import re
from .errors import UnsafePathError
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
def normalize_log_path(value: str) -> str:
    path = value.strip().strip("'\"()[]{}")
    path = path.replace("\\", "/")
    if (
        not path
        or "[REDACTED:" in path
        or "\x00" in path
    ):
        raise UnsafePathError("path is unavailable or redacted")
    if _WINDOWS_DRIVE.match(path):
        parts = path.split("/")
        path = _select_repository_suffix(parts)
    elif path.startswith("/"):
        parts = path.split("/")
        path = _select_repository_suffix(parts)
    while path.startswith("./"):
        path = path[2:]
    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise UnsafePathError(
            "absolute path could not be reduced safely"
        )
    if ".." in pure.parts:
        raise UnsafePathError(
            "repository traversal path is prohibited"
        )
    normalized = pure.as_posix()
    if not normalized or normalized == ".":
        raise UnsafePathError("empty normalized path")
    return normalized
def _select_repository_suffix(parts: list[str]) -> str:
    cleaned = [part for part in parts if part]
    anchors = (
        "src",
        "tests",
        "test",
        "lib",
        "app",
        "packages",
        "services",
        "cmd",
        "internal",
        "pkg",
        "crates",
    )
    for index, part in enumerate(cleaned):
        if part in anchors and index < len(cleaned) - 1:
            return "/".join(cleaned[index:])
    if len(cleaned) >= 2:
        return "/".join(cleaned[-2:])
    raise UnsafePathError(
        "absolute path lacks a safe repository suffix"
    )
EOF
cat > src/l9_debt_resolver/correlation/stack_frames.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
import re
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from .models import StackFrame
from .paths import normalize_log_path
from .errors import UnsafePathError
@dataclass(frozen=True)
class FramePattern:
    language_family: str
    confidence: float
    pattern: re.Pattern[str]
_PATTERNS = (
    FramePattern(
        language_family="python",
        confidence=0.98,
        pattern=re.compile(
            r'File ["\'](?P<path>[^"\']+)["\'], '
            r"line (?P<line>\d+)"
            r"(?:, in (?P<symbol>[^\r\n]+))?"
        ),
    ),
    FramePattern(
        language_family="javascript_typescript",
        confidence=0.96,
        pattern=re.compile(
            r"(?:at\s+(?:(?P<symbol>[^\s(]+)\s+\()?)"
            r"(?P<path>[^()\s]+?\.(?:js|jsx|ts|tsx|mjs|cjs))"
            r":(?P<line>\d+):(?P<column>\d+)\)?"
        ),
    ),
    FramePattern(
        language_family="java_kotlin",
        confidence=0.94,
        pattern=re.compile(
            r"at\s+(?P<symbol>[\w.$<>]+)"
            r"\((?P<path>[^():]+\.(?:java|kt))"
            r":(?P<line>\d+)\)"
        ),
    ),
    FramePattern(
        language_family="rust",
        confidence=0.93,
        pattern=re.compile(
            r"-->\s+(?P<path>[^:\r\n]+\.rs)"
            r":(?P<line>\d+):(?P<column>\d+)"
        ),
    ),
    FramePattern(
        language_family="go",
        confidence=0.92,
        pattern=re.compile(
            r"(?P<path>[^\s:]+\.go)"
            r":(?P<line>\d+)"
            r"(?::(?P<column>\d+))?"
        ),
    ),
    FramePattern(
        language_family="dotnet",
        confidence=0.92,
        pattern=re.compile(
            r"in\s+(?P<path>[^:\r\n]+\.(?:cs|fs|vb))"
            r":line\s+(?P<line>\d+)"
        ),
    ),
    FramePattern(
        language_family="generic",
        confidence=0.82,
        pattern=re.compile(
            r"(?P<path>[A-Za-z0-9_./\\-]+"
            r"\.(?:py|js|jsx|ts|tsx|java|kt|go|rs|cs|fs|vb"
            r"|c|cc|cpp|h|hpp|rb|php|swift|scala|sh|yaml|yml"
            r"|json|toml|xml))"
            r":(?P<line>\d+)"
            r"(?::(?P<column>\d+))?"
        ),
    ),
)
def extract_stack_frames(
    redacted_log: str,
) -> tuple[StackFrame, ...]:
    frames: dict[
        tuple[str, int | None, int | None, str | None],
        StackFrame,
    ] = {}
    for log_line_number, log_line in enumerate(
        redacted_log.splitlines(),
        start=1,
    ):
        for frame_pattern in _PATTERNS:
            for match in frame_pattern.pattern.finditer(log_line):
                raw_path = match.group("path")
                try:
                    path = normalize_log_path(raw_path)
                except UnsafePathError:
                    continue
                line = _positive_integer(
                    match.groupdict().get("line")
                )
                column = _positive_integer(
                    match.groupdict().get("column")
                )
                symbol = _clean_symbol(
                    match.groupdict().get("symbol")
                )
                key = (
                    path,
                    line,
                    column,
                    symbol,
                )
                candidate = StackFrame(
                    frame_id=namespaced_identity(
                        "frame_",
                        {
                            "path": path,
                            "line": line,
                            "column": column,
                            "symbol": symbol,
                            "log_line_number": log_line_number,
                        },
                    ),
                    path=path,
                    line=line,
                    column=column,
                    symbol_hint=symbol,
                    language_family=(
                        frame_pattern.language_family
                    ),
                    log_line_number=log_line_number,
                    confidence=frame_pattern.confidence,
                    limitations=(),
                )
                current = frames.get(key)
                if (
                    current is None
                    or candidate.confidence > current.confidence
                ):
                    frames[key] = candidate
    return tuple(
        sorted(
            frames.values(),
            key=lambda frame: (
                frame.path,
                frame.line or 0,
                frame.column or 0,
                frame.symbol_hint or "",
                frame.frame_id,
            ),
        )
    )
def _positive_integer(
    value: str | None,
) -> int | None:
    if value is None:
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None
def _clean_symbol(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped[:1000] if stripped else None
EOF
###############################################################################
# 5. SDK document adapter
###############################################################################
cat > src/l9_debt_resolver/sdk/document_adapter.py <<'EOF'
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from l9_debt_resolver.correlation.models import StackFrame
from .errors import (
    SDKContractError,
    SnapshotMismatchError,
)
from .models import (
    SDKContractReference,
    SDKFindingReference,
    SDKRepositoryEntity,
    SDKSnapshot,
)
class DocumentSDKKnowledgeProvider:
    """
    Public exchange-document adapter.
    This adapter is intentionally not an SDK schema implementation. It consumes
    canonical identities and records exported by the public SDK boundary.
    """
    def __init__(self, document: dict[str, Any]) -> None:
        self._document = document
        if (
            document.get("schema_version")
            != "l9.sdk-knowledge-document/v1"
        ):
            raise SDKContractError(
                "unsupported SDK knowledge document"
            )
        self._snapshot = _snapshot(document.get("snapshot"))
        self._entities = tuple(
            _entity(value)
            for value in _list(document, "entities")
        )
        self._tests = tuple(
            _entity(value)
            for value in _list(document, "tests")
        )
        self._contracts = tuple(
            _contract(value)
            for value in _list(document, "contracts")
        )
        self._findings = tuple(
            _finding(value)
            for value in _list(document, "findings")
        )
    @classmethod
    def from_path(
        cls,
        path: Path,
    ) -> "DocumentSDKKnowledgeProvider":
        document = json.loads(
            path.read_text(encoding="utf-8")
        )
        if not isinstance(document, dict):
            raise SDKContractError(
                "SDK knowledge document must be an object"
            )
        return cls(document)
    async def open_repository_snapshot(
        self,
        *,
        repository: str,
        revision: str,
    ) -> SDKSnapshot:
        if (
            self._snapshot.repository != repository
            or self._snapshot.revision != revision
        ):
            raise SnapshotMismatchError(
                "SDK snapshot does not match repository revision"
            )
        return self._snapshot
    async def resolve_repository_entities(
        self,
        *,
        snapshot_id: str,
        locations: tuple[StackFrame, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        self._require_snapshot(snapshot_id)
        matched: dict[str, SDKRepositoryEntity] = {}
        for frame in locations:
            for entity in self._entities:
                if entity.path != frame.path:
                    continue
                if (
                    frame.line is not None
                    and entity.start_line is not None
                    and entity.end_line is not None
                    and not (
                        entity.start_line
                        <= frame.line
                        <= entity.end_line
                    )
                ):
                    continue
                matched[entity.entity_id] = entity
        return _sorted_entities(matched.values())
    async def find_related_tests(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        self._require_snapshot(snapshot_id)
        subjects = set(entity_ids)
        matched = []
        for test in self._tests:
            related = test.metadata.get(
                "related_entity_ids",
                [],
            )
            if (
                isinstance(related, list)
                and subjects.intersection(
                    str(value)
                    for value in related
                )
            ):
                matched.append(test)
        return _sorted_entities(matched)
    async def find_applicable_contracts(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKContractReference, ...]:
        self._require_snapshot(snapshot_id)
        subjects = set(entity_ids)
        return tuple(
            sorted(
                (
                    contract
                    for contract in self._contracts
                    if subjects.intersection(
                        contract.subject_entity_ids
                    )
                ),
                key=lambda contract: contract.contract_id,
            )
        )
    async def correlate_findings(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
    ) -> tuple[SDKFindingReference, ...]:
        self._require_snapshot(snapshot_id)
        entities = set(entity_ids)
        evidence = set(evidence_ids)
        return tuple(
            sorted(
                (
                    finding
                    for finding in self._findings
                    if (
                        entities.intersection(
                            finding.entity_ids
                        )
                        or evidence.intersection(
                            finding.evidence_ids
                        )
                    )
                ),
                key=lambda finding: finding.finding_id,
            )
        )
    def _require_snapshot(
        self,
        snapshot_id: str,
    ) -> None:
        if snapshot_id != self._snapshot.snapshot_id:
            raise SnapshotMismatchError(
                "unknown SDK snapshot identity"
            )
def _snapshot(value: object) -> SDKSnapshot:
    document = _object(value, "snapshot")
    return SDKSnapshot(
        snapshot_id=_required_string(
            document,
            "snapshot_id",
        ),
        repository=_required_string(
            document,
            "repository",
        ),
        revision=_required_string(
            document,
            "revision",
        ),
        capability_profile=tuple(
            sorted(
                _string_list(
                    document.get("capability_profile", [])
                )
            )
        ),
        limitations=tuple(
            sorted(
                _string_list(
                    document.get("limitations", [])
                )
            )
        ),
    )
def _entity(value: object) -> SDKRepositoryEntity:
    document = _object(value, "entity")
    return SDKRepositoryEntity(
        entity_id=_required_string(
            document,
            "entity_id",
        ),
        kind=_required_string(
            document,
            "kind",
        ),
        path=_optional_string(
            document.get("path")
        ),
        start_line=_optional_integer(
            document.get("start_line")
        ),
        end_line=_optional_integer(
            document.get("end_line")
        ),
        symbol=_optional_string(
            document.get("symbol")
        ),
        language=_optional_string(
            document.get("language")
        ),
        metadata=_metadata(document),
    )
def _contract(value: object) -> SDKContractReference:
    document = _object(value, "contract")
    return SDKContractReference(
        contract_id=_required_string(
            document,
            "contract_id",
        ),
        kind=_required_string(
            document,
            "kind",
        ),
        subject_entity_ids=tuple(
            sorted(
                _string_list(
                    document.get(
                        "subject_entity_ids",
                        [],
                    )
                )
            )
        ),
        metadata=_metadata(document),
    )
def _finding(value: object) -> SDKFindingReference:
    document = _object(value, "finding")
    return SDKFindingReference(
        finding_id=_required_string(
            document,
            "finding_id",
        ),
        rule_id=_required_string(
            document,
            "rule_id",
        ),
        severity=_required_string(
            document,
            "severity",
        ),
        entity_ids=tuple(
            sorted(
                _string_list(
                    document.get("entity_ids", [])
                )
            )
        ),
        evidence_ids=tuple(
            sorted(
                _string_list(
                    document.get("evidence_ids", [])
                )
            )
        ),
        metadata=_metadata(document),
    )
def _list(
    document: dict[str, Any],
    key: str,
) -> list[object]:
    value = document.get(key)
    if not isinstance(value, list):
        raise SDKContractError(
            f"SDK knowledge field {key} must be a list"
        )
    return value
def _object(
    value: object,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SDKContractError(
            f"SDK {label} must be an object"
        )
    return value
def _required_string(
    document: dict[str, Any],
    key: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise SDKContractError(
            f"SDK field {key} must be a non-empty string"
        )
    return value
def _optional_string(
    value: object,
) -> str | None:
    return value if isinstance(value, str) else None
def _optional_integer(
    value: object,
) -> int | None:
    return value if isinstance(value, int) else None
def _string_list(
    value: object,
) -> list[str]:
    if not isinstance(value, list):
        raise SDKContractError(
            "SDK list field has an invalid type"
        )
    return [
        item
        for item in value
        if isinstance(item, str)
    ]
def _metadata(
    document: dict[str, Any],
) -> dict[str, Any]:
    value = document.get("metadata", {})
    if not isinstance(value, dict):
        raise SDKContractError(
            "SDK metadata must be an object"
        )
    return dict(value)
def _sorted_entities(
    entities: object,
) -> tuple[SDKRepositoryEntity, ...]:
    unique = {
        entity.entity_id: entity
        for entity in entities
    }
    return tuple(
        sorted(
            unique.values(),
            key=lambda entity: entity.entity_id,
        )
    )
EOF
###############################################################################
# 6. Correlation service
###############################################################################
cat > src/l9_debt_resolver/correlation/service.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.sdk.protocol import (
    SDKKnowledgeProvider,
)
from .errors import IncompleteEvidenceError
from .models import (
    EvidenceBundle,
    RepositoryCorrelation,
)
from .stack_frames import extract_stack_frames
class RepositoryCorrelationService:
    def __init__(
        self,
        SDK: SDKKnowledgeProvider,
    ) -> None:
        self._SDK = SDK
    async def correlate(
        self,
        bundle: EvidenceBundle,
    ) -> RepositoryCorrelation:
        if bundle.evidence.log_completeness != "complete":
            raise IncompleteEvidenceError(
                "repository correlation requires a complete "
                "failed runtime log"
            )
        snapshot = await self._SDK.open_repository_snapshot(
            repository=bundle.repository,
            revision=bundle.revision,
        )
        frames = extract_stack_frames(
            bundle.redacted_log
        )
        entities = (
            await self._SDK.resolve_repository_entities(
                snapshot_id=snapshot.snapshot_id,
                locations=frames,
            )
        )
        entity_ids = tuple(
            sorted(
                {
                    entity.entity_id
                    for entity in entities
                }
            )
        )
        related_tests = (
            await self._SDK.find_related_tests(
                snapshot_id=snapshot.snapshot_id,
                entity_ids=entity_ids,
            )
        )
        contracts = (
            await self._SDK.find_applicable_contracts(
                snapshot_id=snapshot.snapshot_id,
                entity_ids=entity_ids,
            )
        )
        findings = await self._SDK.correlate_findings(
            snapshot_id=snapshot.snapshot_id,
            entity_ids=entity_ids,
            evidence_ids=(
                bundle.evidence.evidence_id,
            ),
        )
        resolved_paths = {
            entity.path
            for entity in entities
            if entity.path is not None
        }
        unresolved = tuple(
            frame
            for frame in frames
            if frame.path not in resolved_paths
        )
        limitations = set(snapshot.limitations)
        if not frames:
            limitations.add(
                "no repository source locations were extracted "
                "from the failed log"
            )
        if frames and not entities:
            limitations.add(
                "SDK resolved no repository entities for "
                "extracted source locations"
            )
        if unresolved:
            limitations.add(
                "one or more log locations were unresolved"
            )
        correlation_material = {
            "evidence_id": bundle.evidence.evidence_id,
            "snapshot_id": snapshot.snapshot_id,
            "frame_ids": [
                frame.frame_id
                for frame in frames
            ],
            "entity_ids": list(entity_ids),
            "test_ids": [
                test.entity_id
                for test in related_tests
            ],
            "contract_ids": [
                contract.contract_id
                for contract in contracts
            ],
            "finding_ids": [
                finding.finding_id
                for finding in findings
            ],
        }
        return RepositoryCorrelation(
            correlation_id=namespaced_identity(
                "correlation_",
                correlation_material,
            ),
            evidence_id=bundle.evidence.evidence_id,
            repository_snapshot_id=snapshot.snapshot_id,
            stack_frames=frames,
            repository_entities=tuple(
                sorted(
                    entities,
                    key=lambda entity: entity.entity_id,
                )
            ),
            related_tests=tuple(
                sorted(
                    related_tests,
                    key=lambda entity: entity.entity_id,
                )
            ),
            applicable_contracts=tuple(
                sorted(
                    contracts,
                    key=lambda contract: contract.contract_id,
                )
            ),
            correlated_findings=tuple(
                sorted(
                    findings,
                    key=lambda finding: finding.finding_id,
                )
            ),
            unresolved_locations=tuple(
                sorted(
                    unresolved,
                    key=lambda frame: frame.frame_id,
                )
            ),
            limitations=tuple(sorted(limitations)),
        )
EOF
###############################################################################
# 7. Classification engine
###############################################################################
cat > src/l9_debt_resolver/classification/__init__.py <<'EOF'
"""Evidence-bound CI failure classification."""
EOF
cat > src/l9_debt_resolver/classification/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class ClassificationSignal:
    signal: str
    category: str
    weight: float
    source: str
    def as_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "category": self.category,
            "weight": self.weight,
            "source": self.source,
        }
@dataclass(frozen=True)
class ClassificationTrace:
    classification_id: str
    failure_fingerprint: str
    category: str
    confidence: float
    evidence_ids: tuple[str, ...]
    matched_signals: tuple[ClassificationSignal, ...]
    failed_command: str | None
    repository_snapshot_id: str
    affected_entities: tuple[str, ...]
    related_tests: tuple[str, ...]
    applicable_contracts: tuple[str, ...]
    correlated_finding_ids: tuple[str, ...]
    remediation_eligibility: str
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.classification-trace/v1",
            "classification_id": self.classification_id,
            "failure_fingerprint": self.failure_fingerprint,
            "category": self.category,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "matched_signals": [
                signal.as_dict()
                for signal in self.matched_signals
            ],
            "failed_command": self.failed_command,
            "repository_snapshot_id": (
                self.repository_snapshot_id
            ),
            "affected_entities": list(
                self.affected_entities
            ),
            "related_tests": list(self.related_tests),
            "applicable_contracts": list(
                self.applicable_contracts
            ),
            "correlated_finding_ids": list(
                self.correlated_finding_ids
            ),
            "remediation_eligibility": (
                self.remediation_eligibility
            ),
            "limitations": list(self.limitations),
        }
EOF
cat > src/l9_debt_resolver/classification/rules.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
import re
@dataclass(frozen=True)
class ClassificationRule:
    name: str
    category: str
    weight: float
    pattern: re.Pattern[str]
RULES = (
    ClassificationRule(
        "pytest_failure",
        "test_failure",
        0.45,
        re.compile(
            r"(?im)(?:=+\s+FAILURES\s+=+|"
            r"\bFAILED\s+.+::.+|"
            r"\b\d+\s+failed(?:,\s+\d+\s+passed)?)"
        ),
    ),
    ClassificationRule(
        "jest_failure",
        "test_failure",
        0.45,
        re.compile(
            r"(?im)(?:Test Suites:\s+\d+\s+failed|"
            r"Tests:\s+\d+\s+failed)"
        ),
    ),
    ClassificationRule(
        "generic_assertion_failure",
        "test_failure",
        0.30,
        re.compile(
            r"(?im)(?:AssertionError|assertion failed|"
            r"expected .+ (?:to equal|but was))"
        ),
    ),
    ClassificationRule(
        "python_syntax_error",
        "compilation",
        0.45,
        re.compile(
            r"(?im)(?:SyntaxError:|IndentationError:|"
            r"TabError:)"
        ),
    ),
    ClassificationRule(
        "compiler_error",
        "compilation",
        0.45,
        re.compile(
            r"(?im)(?:\berror\s+[A-Z]?\d{3,5}\b|"
            r"\bfatal error:|"
            r"\bcompilation failed\b|"
            r"\bcould not compile\b)"
        ),
    ),
    ClassificationRule(
        "typescript_compile",
        "type_failure",
        0.45,
        re.compile(r"(?im)\berror TS\d{4}:")
    ),
    ClassificationRule(
        "mypy_failure",
        "type_failure",
        0.45,
        re.compile(
            r"(?im)(?:\berror:\s+.+\s+\[[a-z0-9-]+\]|"
            r"Found \d+ errors? in \d+ files?)"
        ),
    ),
    ClassificationRule(
        "pyright_failure",
        "type_failure",
        0.45,
        re.compile(
            r"(?im)\b\d+\s+errors?,\s+\d+\s+warnings?"
        ),
    ),
    ClassificationRule(
        "ruff_failure",
        "lint_failure",
        0.45,
        re.compile(
            r"(?im)(?:Found \d+ errors?\.?$|"
            r"\b[A-Z]{1,4}\d{3,4}\b.+)"
        ),
    ),
    ClassificationRule(
        "eslint_failure",
        "lint_failure",
        0.45,
        re.compile(
            r"(?im)(?:\b\d+\s+problems?\s+"
            r"\(\d+\s+errors?|"
            r"\beslint\b.+\berror\b)"
        ),
    ),
    ClassificationRule(
        "dependency_not_found",
        "dependency",
        0.45,
        re.compile(
            r"(?im)(?:ModuleNotFoundError:|"
            r"Cannot find module|"
            r"package .+ is not in GOROOT|"
            r"could not find .+ in registry|"
            r"failed to resolve dependency)"
        ),
    ),
    ClassificationRule(
        "dependency_version_conflict",
        "dependency",
        0.45,
        re.compile(
            r"(?im)(?:ResolutionImpossible|"
            r"version solving failed|"
            r"dependency conflict|"
            r"conflicting dependencies)"
        ),
    ),
    ClassificationRule(
        "configuration_parse",
        "configuration",
        0.45,
        re.compile(
            r"(?im)(?:invalid configuration|"
            r"configuration error|"
            r"failed to parse .+\.(?:ya?ml|toml|json)|"
            r"unknown configuration key)"
        ),
    ),
    ClassificationRule(
        "generated_drift",
        "generated_file_drift",
        0.45,
        re.compile(
            r"(?im)(?:generated files? (?:are )?out of date|"
            r"run .+generate|"
            r"code generation produced changes|"
            r"generated output differs)"
        ),
    ),
    ClassificationRule(
        "security_scanner",
        "security_failure",
        0.45,
        re.compile(
            r"(?im)(?:critical vulnerability|"
            r"high severity vulnerability|"
            r"security scan failed|"
            r"secret detected|"
            r"policy violation)"
        ),
    ),
    ClassificationRule(
        "runner_infrastructure",
        "infrastructure",
        0.45,
        re.compile(
            r"(?im)(?:The hosted runner lost communication|"
            r"No space left on device|"
            r"runner was terminated|"
            r"service unavailable|"
            r"connection reset by peer|"
            r"network is unreachable|"
            r"rate limit exceeded)"
        ),
    ),
)
COMMAND_RULES = (
    (
        re.compile(r"(?i)\bpytest\b"),
        "test_failure",
    ),
    (
        re.compile(r"(?i)\b(?:jest|vitest|mocha)\b"),
        "test_failure",
    ),
    (
        re.compile(r"(?i)\b(?:ruff|flake8|pylint|eslint)\b"),
        "lint_failure",
    ),
    (
        re.compile(r"(?i)\b(?:mypy|pyright|tsc)\b"),
        "type_failure",
    ),
    (
        re.compile(r"(?i)\b(?:cargo build|go build|javac|gradle compile)\b"),
        "compilation",
    ),
    (
        re.compile(r"(?i)\b(?:pip install|npm install|npm ci|"
                   r"pnpm install|yarn install|cargo fetch)\b"),
        "dependency",
    ),
)
EOF
cat > src/l9_debt_resolver/classification/engine.py <<'EOF'
from __future__ import annotations
from collections import defaultdict
import re
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.correlation.models import (
    EvidenceBundle,
    RepositoryCorrelation,
)
from .models import (
    ClassificationSignal,
    ClassificationTrace,
)
from .rules import COMMAND_RULES, RULES
class RootCauseClassifier:
    AUTOMATIC_MINIMUM = 0.90
    APPROVAL_MINIMUM = 0.70
    async def classify(
        self,
        *,
        bundle: EvidenceBundle,
        correlation: RepositoryCorrelation,
    ) -> ClassificationTrace:
        if bundle.evidence.log_completeness != "complete":
            raise ValueError(
                "classification requires complete runtime-log evidence"
            )
        signals = self._collect_signals(
            bundle=bundle,
            correlation=correlation,
        )
        category_scores: dict[str, float] = defaultdict(float)
        for signal in signals:
            category_scores[signal.category] += signal.weight
        limitations = set(correlation.limitations)
        if not category_scores:
            category = "unsupported"
            confidence = 0.0
            limitations.add(
                "no supported root-cause signal was detected"
            )
        else:
            ranked = sorted(
                category_scores.items(),
                key=lambda value: (
                    -value[1],
                    value[0],
                ),
            )
            category, raw_score = ranked[0]
            confidence = min(0.99, raw_score)
            if (
                len(ranked) > 1
                and ranked[1][1] >= 0.70
                and abs(raw_score - ranked[1][1]) < 0.15
            ):
                category = "unsupported"
                confidence = min(confidence, 0.49)
                limitations.add(
                    "conflicting high-confidence root-cause signals"
                )
        explicit_log_signal = any(
            signal.source == "failed_log"
            and signal.weight >= 0.35
            for signal in signals
        )
        if not explicit_log_signal and category != "unsupported":
            confidence = min(confidence, 0.69)
            limitations.add(
                "classification lacks an explicit failed-log "
                "tool signature"
            )
        if category == "infrastructure":
            confidence = min(confidence, 0.89)
            eligibility = "unsupported"
        elif category == "security_failure":
            eligibility = "approval_required"
        elif category == "unsupported":
            eligibility = "unsupported"
        elif confidence >= self.AUTOMATIC_MINIMUM:
            eligibility = "automatic"
        elif confidence >= self.APPROVAL_MINIMUM:
            eligibility = "approval_required"
        else:
            eligibility = "unsupported"
        affected_entities = tuple(
            entity.entity_id
            for entity in correlation.repository_entities
        )
        related_tests = tuple(
            entity.entity_id
            for entity in correlation.related_tests
        )
        applicable_contracts = tuple(
            contract.contract_id
            for contract in correlation.applicable_contracts
        )
        finding_ids = tuple(
            finding.finding_id
            for finding in correlation.correlated_findings
        )
        fingerprint_material = {
            "category": category,
            "failed_command": _normalize_command(
                bundle.evidence.failed_command
            ),
            "log_hash": bundle.evidence.log_sha256,
            "entity_ids": list(affected_entities),
            "contract_ids": list(applicable_contracts),
            "finding_ids": list(finding_ids),
        }
        failure_fingerprint = namespaced_identity(
            "failure_",
            fingerprint_material,
        )
        classification_material = {
            "failure_fingerprint": failure_fingerprint,
            "snapshot_id": (
                correlation.repository_snapshot_id
            ),
            "signals": [
                signal.as_dict()
                for signal in signals
            ],
            "confidence": round(confidence, 4),
            "eligibility": eligibility,
        }
        return ClassificationTrace(
            classification_id=namespaced_identity(
                "classification_",
                classification_material,
            ),
            failure_fingerprint=failure_fingerprint,
            category=category,
            confidence=round(confidence, 4),
            evidence_ids=(
                bundle.evidence.evidence_id,
            ),
            matched_signals=signals,
            failed_command=bundle.evidence.failed_command,
            repository_snapshot_id=(
                correlation.repository_snapshot_id
            ),
            affected_entities=affected_entities,
            related_tests=related_tests,
            applicable_contracts=applicable_contracts,
            correlated_finding_ids=finding_ids,
            remediation_eligibility=eligibility,
            limitations=tuple(sorted(limitations)),
        )
    def _collect_signals(
        self,
        *,
        bundle: EvidenceBundle,
        correlation: RepositoryCorrelation,
    ) -> tuple[ClassificationSignal, ...]:
        signals: list[ClassificationSignal] = []
        for rule in RULES:
            if rule.pattern.search(bundle.redacted_log):
                signals.append(
                    ClassificationSignal(
                        signal=rule.name,
                        category=rule.category,
                        weight=rule.weight,
                        source="failed_log",
                    )
                )
        command = bundle.evidence.failed_command or ""
        for pattern, category in COMMAND_RULES:
            if pattern.search(command):
                signals.append(
                    ClassificationSignal(
                        signal="failed_command_tool",
                        category=category,
                        weight=0.20,
                        source="failed_command",
                    )
                )
        if correlation.repository_entities:
            entity_categories = _metadata_categories(
                entity.metadata
                for entity in correlation.repository_entities
            )
            for category in entity_categories:
                signals.append(
                    ClassificationSignal(
                        signal="SDK_entity_category",
                        category=category,
                        weight=0.10,
                        source="SDK_entity",
                    )
                )
        contract_categories = _metadata_categories(
            contract.metadata
            for contract in correlation.applicable_contracts
        )
        for category in contract_categories:
            signals.append(
                ClassificationSignal(
                    signal="SDK_contract_category",
                    category=category,
                    weight=0.05,
                    source="SDK_contract",
                )
            )
        finding_categories = _metadata_categories(
            finding.metadata
            for finding in correlation.correlated_findings
        )
        for category in finding_categories:
            signals.append(
                ClassificationSignal(
                    signal="SDK_finding_category",
                    category=category,
                    weight=0.10,
                    source="SDK_finding",
                )
            )
        return tuple(
            sorted(
                signals,
                key=lambda signal: (
                    signal.category,
                    signal.source,
                    signal.signal,
                    signal.weight,
                ),
            )
        )
_ALLOWED_CATEGORIES = {
    "configuration",
    "dependency",
    "compilation",
    "test_failure",
    "lint_failure",
    "type_failure",
    "generated_file_drift",
    "security_failure",
    "infrastructure",
    "unsupported",
}
def _metadata_categories(
    metadata_values: object,
) -> tuple[str, ...]:
    categories: set[str] = set()
    for metadata in metadata_values:
        value = metadata.get("CI_failure_category")
        if (
            isinstance(value, str)
            and value in _ALLOWED_CATEGORIES
        ):
            categories.add(value)
    return tuple(sorted(categories))
def _normalize_command(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value.strip())[:2000]
EOF
###############################################################################
# 8. P2 orchestration service
###############################################################################
cat > src/l9_debt_resolver/runtime/correlation_service.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from l9_debt_resolver.classification.engine import (
    RootCauseClassifier,
)
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import (
    EvidenceBundle,
    RepositoryCorrelation,
)
from l9_debt_resolver.correlation.service import (
    RepositoryCorrelationService,
)
from l9_debt_resolver.sdk.protocol import (
    SDKKnowledgeProvider,
)
@dataclass(frozen=True)
class CorrelationAndClassificationResult:
    correlation: RepositoryCorrelation
    classification: ClassificationTrace
    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": (
                "l9.correlation-classification-result/v1"
            ),
            "correlation": self.correlation.as_dict(),
            "classification": self.classification.as_dict(),
        }
class ResolverCorrelationRuntime:
    def __init__(
        self,
        *,
        SDK: SDKKnowledgeProvider,
    ) -> None:
        self._correlation = RepositoryCorrelationService(
            SDK
        )
        self._classifier = RootCauseClassifier()
    async def execute(
        self,
        bundle: EvidenceBundle,
    ) -> CorrelationAndClassificationResult:
        correlation = await self._correlation.correlate(
            bundle
        )
        classification = await self._classifier.classify(
            bundle=bundle,
            correlation=correlation,
        )
        return CorrelationAndClassificationResult(
            correlation=correlation,
            classification=classification,
        )
EOF
###############################################################################
# 9. Bundle loading
###############################################################################
cat > src/l9_debt_resolver/correlation/loader.py <<'EOF'
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from l9_debt_resolver.acquisition.models import (
    FailedJob,
    FailedStep,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)
from .models import EvidenceBundle
def load_evidence_bundle(
    path: Path,
) -> EvidenceBundle:
    document = json.loads(
        path.read_text(encoding="utf-8")
    )
    if not isinstance(document, dict):
        raise ValueError(
            "evidence bundle must be a JSON object"
        )
    if (
        document.get("schema_version")
        != "l9.evidence-bundle/v1"
    ):
        raise ValueError(
            "unsupported evidence bundle version"
        )
    return EvidenceBundle(
        repository=_string(document, "repository"),
        revision=_string(document, "revision"),
        evidence=_evidence(_object(document, "evidence")),
        redacted_log=_string(
            document,
            "redacted_log",
        ),
        failed_job=_failed_job(
            _object(document, "failed_job")
        ),
    )
def _evidence(
    document: dict[str, Any],
) -> CIRunEvidence:
    provenance = _object(
        document,
        "artifact_provenance",
    )
    return CIRunEvidence(
        evidence_id=_string(document, "evidence_id"),
        provider=_string(document, "provider"),
        run_id=_string(document, "run_id"),
        job_id=_string(document, "job_id"),
        job_name=_string(document, "job_name"),
        failed_command=_optional_string(
            document.get("failed_command")
        ),
        conclusion=_string(document, "conclusion"),
        log_sha256=_string(document, "log_sha256"),
        log_size_bytes=_integer(
            document,
            "log_size_bytes",
        ),
        log_completeness=_string(
            document,
            "log_completeness",
        ),
        authority_class=_string(
            document,
            "authority_class",
        ),
        artifact_provenance=provenance,
        observed_at=_string(document, "observed_at"),
        limitations=tuple(
            _string_list(
                document.get("limitations", [])
            )
        ),
    )
def _failed_job(
    document: dict[str, Any],
) -> FailedJob:
    steps = []
    for value in _list(document, "failed_steps"):
        step = _object_value(value, "failed step")
        steps.append(
            FailedStep(
                number=_integer(step, "number"),
                name=_string(step, "name"),
                conclusion=_string(
                    step,
                    "conclusion",
                ),
            )
        )
    return FailedJob(
        provider=_string(document, "provider"),
        run_id=_string(document, "run_id"),
        job_id=_string(document, "job_id"),
        name=_string(document, "name"),
        status=_string(document, "status"),
        conclusion=_string(document, "conclusion"),
        started_at=_optional_string(
            document.get("started_at")
        ),
        completed_at=_optional_string(
            document.get("completed_at")
        ),
        runner_name=_optional_string(
            document.get("runner_name")
        ),
        labels=tuple(
            sorted(
                _string_list(
                    document.get("labels", [])
                )
            )
        ),
        failed_steps=tuple(steps),
    )
def _string(
    document: dict[str, Any],
    key: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value
def _integer(
    document: dict[str, Any],
    key: str,
) -> int:
    value = document.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value
def _optional_string(
    value: object,
) -> str | None:
    return value if isinstance(value, str) else None
def _object(
    document: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    return _object_value(document.get(key), key)
def _object_value(
    value: object,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value
def _list(
    document: dict[str, Any],
    key: str,
) -> list[object]:
    value = document.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value
def _string_list(
    value: object,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("value must be a list")
    return [
        item
        for item in value
        if isinstance(item, str)
    ]
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
        "phase": "RESOLVER-P2",
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
            "SDK_repository_snapshots": True,
            "stack_frame_extraction": True,
            "SDK_entity_correlation": True,
            "related_test_correlation": True,
            "applicable_contract_correlation": True,
            "canonical_finding_correlation": True,
            "root_cause_classification": True,
            "classification_confidence": True,
            "classification_trace": True,
            "bounded_remediation": False,
            "SDK_validation_execution": False,
            "branch_mutation": False,
            "CI_rerun_observation": False
        },
        "limitations": [
            "P2 classifies failures but does not mutate repositories.",
            "Bounded remediation and SDK validation begin in RESOLVER-P3.",
            "Remote branch interaction begins in RESOLVER-P4.",
            "CI rerun observation begins in RESOLVER-P4."
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
imports = """from .correlation.loader import load_evidence_bundle
from .runtime.correlation_service import ResolverCorrelationRuntime
from .sdk.document_adapter import DocumentSDKKnowledgeProvider
"""
anchor = "from .contracts.schema import SchemaValidator\n"
if imports not in content:
    content = content.replace(
        anchor,
        anchor + imports,
    )
command_block = """
    correlate = commands.add_parser(
        "correlate-classify"
    )
    correlate.add_argument(
        "--evidence-bundle",
        required=True,
        type=Path,
    )
    correlate.add_argument(
        "--SDK-knowledge",
        required=True,
        type=Path,
    )
"""
anchor = "    acquire = commands.add_parser(\n"
if 'correlate-classify' not in content:
    content = content.replace(
        anchor,
        command_block + "\n" + anchor,
    )
handler = """
    if arguments.command == "correlate-classify":
        bundle = load_evidence_bundle(
            arguments.evidence_bundle
        )
        SDK = DocumentSDKKnowledgeProvider.from_path(
            arguments.SDK_knowledge
        )
        runtime = ResolverCorrelationRuntime(
            SDK=SDK
        )
        result = asyncio.run(
            runtime.execute(bundle)
        )
        emit(result.as_dict())
        return (
            0
            if result.classification.category
            != "unsupported"
            else 2
        )
"""
anchor = '    if arguments.command == "acquire-github-run":\n'
if handler not in content:
    content = content.replace(
        anchor,
        handler + anchor,
    )
content = content.replace(
    '            "acquisition-report",',
    '            "acquisition-report",\n'
    '            "evidence-bundle",\n'
    '            "stack-frame",\n'
    '            "repository-correlation",\n'
    '            "classification-trace",\n'
    '            "sdk-knowledge-document",',
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
    'version = "0.2.0"',
    'version = "0.3.0"',
)
path.write_text(content, encoding="utf-8")
path = Path("src/l9_debt_resolver/__init__.py")
content = path.read_text(encoding="utf-8")
content = content.replace(
    '__version__ = "0.2.0"',
    '__version__ = "0.3.0"',
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 13. Tests
###############################################################################
cat > tests/correlation/test_paths.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.correlation.errors import (
    UnsafePathError,
)
from l9_debt_resolver.correlation.paths import (
    normalize_log_path,
)
def test_repository_relative_path_is_preserved() -> None:
    assert (
        normalize_log_path("src/example/service.py")
        == "src/example/service.py"
    )
def test_absolute_path_is_reduced() -> None:
    assert (
        normalize_log_path(
            "/home/runner/work/repo/repo/src/example.py"
        )
        == "src/example.py"
    )
def test_windows_path_is_reduced() -> None:
    assert (
        normalize_log_path(
            r"C:\work\repo\tests\test_example.py"
        )
        == "tests/test_example.py"
    )
@pytest.mark.parametrize(
    "value",
    [
        "../secret.py",
        "src/../../secret.py",
        "[REDACTED:UNIX_PATH]",
        "",
    ],
)
def test_unsafe_paths_are_rejected(value: str) -> None:
    with pytest.raises(UnsafePathError):
        normalize_log_path(value)
EOF
cat > tests/correlation/test_stack_frames.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.correlation.stack_frames import (
    extract_stack_frames,
)
def test_python_frame() -> None:
    frames = extract_stack_frames(
        'File "/home/runner/work/repo/repo/src/app.py", '
        'line 42, in execute'
    )
    assert len(frames) == 1
    assert frames[0].path == "src/app.py"
    assert frames[0].line == 42
    assert frames[0].symbol_hint == "execute"
    assert frames[0].language_family == "python"
def test_typescript_frame() -> None:
    frames = extract_stack_frames(
        "at execute (/workspace/project/src/app.ts:10:8)"
    )
    assert len(frames) == 1
    assert frames[0].path == "src/app.ts"
    assert frames[0].line == 10
    assert frames[0].column == 8
def test_frames_are_deterministic() -> None:
    log = (
        "src/b.py:20:1 error\n"
        "src/a.py:10:2 error\n"
        "src/b.py:20:1 error\n"
    )
    first = extract_stack_frames(log)
    second = extract_stack_frames(log)
    assert first == second
    assert [frame.path for frame in first] == [
        "src/a.py",
        "src/b.py",
    ]
EOF
cat > tests/sdk/test_document_adapter.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.correlation.models import (
    StackFrame,
)
from l9_debt_resolver.sdk.document_adapter import (
    DocumentSDKKnowledgeProvider,
)
from l9_debt_resolver.sdk.errors import (
    SnapshotMismatchError,
)
def document() -> dict[str, object]:
    return {
        "schema_version": "l9.sdk-knowledge-document/v1",
        "repository": "Quantum-L9/example",
        "revision": "abcdef1234567",
        "snapshot": {
            "snapshot_id": "snapshot-1",
            "repository": "Quantum-L9/example",
            "revision": "abcdef1234567",
            "capability_profile": ["python"],
            "limitations": [],
        },
        "entities": [
            {
                "entity_id": "entity-1",
                "kind": "function",
                "path": "src/app.py",
                "start_line": 1,
                "end_line": 100,
                "symbol": "execute",
                "language": "python",
                "metadata": {
                    "CI_failure_category": "test_failure"
                },
            }
        ],
        "tests": [
            {
                "entity_id": "test-1",
                "kind": "test",
                "path": "tests/test_app.py",
                "start_line": 1,
                "end_line": 50,
                "symbol": "test_execute",
                "language": "python",
                "metadata": {
                    "related_entity_ids": ["entity-1"]
                },
            }
        ],
        "contracts": [
            {
                "contract_id": "contract-1",
                "kind": "behavior",
                "subject_entity_ids": ["entity-1"],
                "metadata": {
                    "CI_failure_category": "test_failure"
                },
            }
        ],
        "findings": [
            {
                "finding_id": "finding-1",
                "rule_id": "rule-1",
                "severity": "error",
                "entity_ids": ["entity-1"],
                "evidence_ids": [],
                "metadata": {
                    "CI_failure_category": "test_failure"
                },
            }
        ],
    }
@pytest.mark.asyncio
async def test_snapshot_and_entity_correlation() -> None:
    adapter = DocumentSDKKnowledgeProvider(
        document()
    )
    snapshot = await adapter.open_repository_snapshot(
        repository="Quantum-L9/example",
        revision="abcdef1234567",
    )
    entities = await adapter.resolve_repository_entities(
        snapshot_id=snapshot.snapshot_id,
        locations=(
            StackFrame(
                frame_id="frame-" + "a" * 64,
                path="src/app.py",
                line=42,
                column=None,
                symbol_hint="execute",
                language_family="python",
                log_line_number=1,
                confidence=0.98,
                limitations=(),
            ),
        ),
    )
    assert snapshot.snapshot_id == "snapshot-1"
    assert [entity.entity_id for entity in entities] == [
        "entity-1"
    ]
@pytest.mark.asyncio
async def test_snapshot_mismatch_fails() -> None:
    adapter = DocumentSDKKnowledgeProvider(
        document()
    )
    with pytest.raises(SnapshotMismatchError):
        await adapter.open_repository_snapshot(
            repository="Quantum-L9/example",
            revision="different",
        )
EOF
cat > tests/correlation/test_service.py <<'EOF'
from __future__ import annotations
import hashlib
import pytest
from l9_debt_resolver.acquisition.models import (
    FailedJob,
    FailedStep,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)
from l9_debt_resolver.correlation.models import (
    EvidenceBundle,
)
from l9_debt_resolver.correlation.service import (
    RepositoryCorrelationService,
)
from l9_debt_resolver.sdk.document_adapter import (
    DocumentSDKKnowledgeProvider,
)
def bundle(completeness: str = "complete") -> EvidenceBundle:
    raw_hash = hashlib.sha256(b"log").hexdigest()
    evidence = CIRunEvidence(
        evidence_id="evidence_" + "a" * 64,
        provider="github_actions",
        run_id="100",
        job_id="200",
        job_name="tests",
        failed_command="pytest",
        conclusion="failure",
        log_sha256=raw_hash,
        log_size_bytes=3,
        log_completeness=completeness,
        authority_class="RUNTIME_LOG",
        artifact_provenance={
            "source": "github_actions_job_log",
            "retrieval_id": "retrieval_" + "b" * 64,
            "retrieved_at": "2026-07-18T00:00:00Z",
        },
        observed_at="2026-07-18T00:00:00Z",
        limitations=(),
    )
    job = FailedJob(
        provider="github_actions",
        run_id="100",
        job_id="200",
        name="tests",
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
    )
    return EvidenceBundle(
        repository="Quantum-L9/example",
        revision="abcdef1234567",
        evidence=evidence,
        redacted_log=(
            'File "/home/runner/work/repo/repo/src/app.py", '
            "line 42, in execute\n"
            "AssertionError\n"
            "Error: Process completed with exit code 1.\n"
        ),
        failed_job=job,
    )
def SDK_document() -> dict[str, object]:
    return {
        "schema_version": "l9.sdk-knowledge-document/v1",
        "repository": "Quantum-L9/example",
        "revision": "abcdef1234567",
        "snapshot": {
            "snapshot_id": "snapshot-1",
            "repository": "Quantum-L9/example",
            "revision": "abcdef1234567",
            "capability_profile": ["python"],
            "limitations": [],
        },
        "entities": [
            {
                "entity_id": "entity-1",
                "kind": "function",
                "path": "src/app.py",
                "start_line": 1,
                "end_line": 100,
                "symbol": "execute",
                "language": "python",
                "metadata": {
                    "CI_failure_category": "test_failure"
                },
            }
        ],
        "tests": [],
        "contracts": [],
        "findings": [],
    }
@pytest.mark.asyncio
async def test_repository_correlation() -> None:
    service = RepositoryCorrelationService(
        DocumentSDKKnowledgeProvider(
            SDK_document()
        )
    )
    result = await service.correlate(bundle())
    assert result.repository_snapshot_id == "snapshot-1"
    assert [
        entity.entity_id
        for entity in result.repository_entities
    ] == ["entity-1"]
EOF
cat > tests/classification/test_engine.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.classification.engine import (
    RootCauseClassifier,
)
from l9_debt_resolver.correlation.models import (
    RepositoryCorrelation,
)
from tests.correlation.test_service import bundle
def correlation() -> RepositoryCorrelation:
    return RepositoryCorrelation(
        correlation_id="correlation_" + "c" * 64,
        evidence_id="evidence_" + "a" * 64,
        repository_snapshot_id="snapshot-1",
        stack_frames=(),
        repository_entities=(),
        related_tests=(),
        applicable_contracts=(),
        correlated_findings=(),
        unresolved_locations=(),
        limitations=(),
    )
@pytest.mark.asyncio
async def test_test_failure_classification() -> None:
    value = bundle()
    result = await RootCauseClassifier().classify(
        bundle=value,
        correlation=correlation(),
    )
    assert result.category == "test_failure"
    assert result.failure_fingerprint.startswith(
        "failure_"
    )
    assert result.evidence_ids == (
        value.evidence.evidence_id,
    )
@pytest.mark.asyncio
async def test_infrastructure_is_not_automatic() -> None:
    value = bundle()
    value = type(value)(
        repository=value.repository,
        revision=value.revision,
        evidence=value.evidence,
        redacted_log=(
            "The hosted runner lost communication\n"
            "Error: Process completed with exit code 1.\n"
        ),
        failed_job=value.failed_job,
    )
    result = await RootCauseClassifier().classify(
        bundle=value,
        correlation=correlation(),
    )
    assert result.category == "infrastructure"
    assert result.remediation_eligibility == "unsupported"
@pytest.mark.asyncio
async def test_unknown_failure_is_unsupported() -> None:
    value = bundle()
    value = type(value)(
        repository=value.repository,
        revision=value.revision,
        evidence=value.evidence,
        redacted_log=(
            "unknown failure\n"
            "Error: Process completed with exit code 1.\n"
        ),
        failed_job=value.failed_job,
    )
    result = await RootCauseClassifier().classify(
        bundle=value,
        correlation=correlation(),
    )
    assert result.category == "unsupported"
    assert result.remediation_eligibility == "unsupported"
EOF
cat > tests/classification/test_determinism.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.classification.engine import (
    RootCauseClassifier,
)
from tests.classification.test_engine import correlation
from tests.correlation.test_service import bundle
@pytest.mark.asyncio
async def test_classification_identity_is_deterministic() -> None:
    classifier = RootCauseClassifier()
    value = bundle()
    correlated = correlation()
    first = await classifier.classify(
        bundle=value,
        correlation=correlated,
    )
    second = await classifier.classify(
        bundle=value,
        correlation=correlated,
    )
    assert first == second
    assert (
        first.classification_id
        == second.classification_id
    )
    assert (
        first.failure_fingerprint
        == second.failure_fingerprint
    )
EOF
cat > tests/architecture/test_P2_boundary.py <<'EOF'
from __future__ import annotations
import ast
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED_IMPORT_PREFIXES = (
    "l9_debt_intelligence",
    "l9_debt_lsp",
    "pr_repair",
)
PROHIBITED_MUTATION_TERMS = (
    "git push",
    "git commit",
    "checkout -b",
    "merge_pull_request",
    "automatic_merge",
    "apply_patch",
    "write_source_file",
    "disable_tests",
    "skip_tests",
    "weaken_security",
    "weaken_lint",
)
def imports(path: Path) -> set[str]:
    tree = ast.parse(
        path.read_text(encoding="utf-8")
    )
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(
                alias.name
                for alias in node.names
            )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
        ):
            result.add(node.module)
    return result
def test_forbidden_repository_dependencies() -> None:
    for path in SOURCE.rglob("*.py"):
        for module in imports(path):
            assert not module.startswith(
                PROHIBITED_IMPORT_PREFIXES
            ), f"{path} imports prohibited module {module}"
def test_P2_contains_no_repository_mutation() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED_MUTATION_TERMS:
            assert term not in content, (
                f"{path} contains P2-prohibited mutation "
                f"term {term}"
            )
EOF
cat > tests/architecture/test_SDK_identity_boundary.py <<'EOF'
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SDK_PACKAGE = (
    ROOT
    / "src"
    / "l9_debt_resolver"
    / "sdk"
)
def test_resolver_does_not_generate_SDK_IDs() -> None:
    prohibited_prefixes = (
        'namespaced_identity("snapshot_',
        'namespaced_identity("finding_',
        'namespaced_identity("entity_',
        'namespaced_identity("source_location_',
        'namespaced_identity("validation_plan_',
        'namespaced_identity("validation_result_',
    )
    for path in SDK_PACKAGE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        )
        for prefix in prohibited_prefixes:
            assert prefix not in content, (
                f"{path} generates SDK-owned identity "
                f"{prefix}"
            )
EOF
###############################################################################
# 14. README and roadmap
###############################################################################
cat >> README.md <<'EOF'
## RESOLVER-P2: repository correlation and classification
P2 correlates complete failed-log evidence with an SDK-owned repository
snapshot.
```text
complete failed log
       ↓
safe stack-frame extraction
       ↓
SDK repository snapshot
       ↓
canonical repository entities
       ├── related tests
       ├── applicable contracts
       └── canonical findings
       ↓
CI root-cause signals
       ↓
classification trace
       ↓
automatic | approval_required | unsupported

SDK authority boundary

The resolver does not manufacture SDK snapshot, entity, contract, finding,
validation-plan, or validation-result identities.

The included document adapter consumes a public SDK exchange document. It
exists for integration tests, offline execution, and compatibility while the
SDK transport is deployed.

Correlate and classify

l9-debt-resolver correlate-classify \
  --evidence-bundle evidence-bundle.json \
  --SDK-knowledge sdk-knowledge.json

The command exits with:

* 0 when a supported category is classified;
* 2 when the result is unsupported;
* another nonzero code for invalid evidence or SDK failures.

Classification safety

Automatic eligibility requires:

* complete failed-log evidence;
* an explicit failed-log tool or failure signature;
* confidence of at least 0.90;
* no conflicting high-confidence category;
* a category permitted for automatic remediation.

Infrastructure failures remain unsupported. Security failures require
approval.
EOF

python3 - <<'PY'
from pathlib import Path

path = Path("ROADMAP.md")
content = path.read_text(encoding="utf-8")

content = content.replace(
"""## RESOLVER-P2 - Repository correlation

Status: Planned

* public SDK Knowledge API
* repository snapshots
* stack-frame correlation
* test correlation
* contract correlation
* finding correlation
* root-cause classification""",
    """## RESOLVER-P2 - Repository correlation

Status: Implemented

* public SDK Knowledge API boundary
* SDK-owned repository snapshots
* deterministic stack-frame extraction
* repository-entity correlation
* related-test correlation
* applicable-contract correlation
* canonical finding correlation
* evidence-bound root-cause classification
* classification confidence
* remediation eligibility
* deterministic classification trace""",
    )

path.write_text(content, encoding="utf-8")
PY

###############################################################################

# 15. ADRs

###############################################################################

cat > docs/architecture/ADRs/ADR-RESOLVER-009-SDK-knowledge-authority.md <<'EOF'

ADR-RESOLVER-009: SDK owns repository knowledge

* Status: Accepted
* Phase: RESOLVER-P2

Decision

Repository snapshots, repository entities, contracts, findings, validation
plans, and validation results remain SDK-owned.

The resolver consumes these through a public adapter and does not create local
canonical equivalents.
EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-010-log-locations-are-hints.md <<'EOF'

ADR-RESOLVER-010: Failed-log source locations are correlation hints

* Status: Accepted
* Phase: RESOLVER-P2

Decision

Paths, lines, columns, symbols, and stack frames extracted from CI logs are
resolver-owned hints.

They become repository-semantic evidence only after SDK correlation.

Absolute paths are reduced to safe repository-relative candidates. Traversal
paths and redaction placeholders are rejected.
EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-011-classification-requires-current-evidence.md <<'EOF'

ADR-RESOLVER-011: Root-cause classification requires current CI evidence

* Status: Accepted
* Phase: RESOLVER-P2

Decision

A category cannot be selected from job names, historical context, SDK findings,
or repository metadata alone.

A supported classification requires a current complete failed log and an
explicit failed-log signal.
EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-012-confidence-controls-eligibility.md <<'EOF'

ADR-RESOLVER-012: Classification confidence controls eligibility

* Status: Accepted
* Phase: RESOLVER-P2

Decision

Automatic remediation eligibility requires confidence of at least 0.90.

Results from 0.70 through 0.8999 require approval. Lower-confidence,
infrastructure, conflicting, or unknown results are unsupported.

Security failures always require approval.
EOF

###############################################################################

# 16. Spec and schema registry updates

###############################################################################

python3 - <<'PY'
import json
from pathlib import Path

path = Path(".l9/repo-spec.yaml")
content = path.read_text(encoding="utf-8")

content = content.replace(
"phase: RESOLVER-P1",
"phase: RESOLVER-P2",
1,
)

content = content.replace(
"phase_name: log_acquisition",
"phase_name: repository_correlation",
1,
)

content = content.replace(
"""  - phase: RESOLVER-P2
name: repository_correlation
priority: high
status: planned""",
"""  - phase: RESOLVER-P2
name: repository_correlation
priority: high
status: implemented""",
)

path.write_text(content, encoding="utf-8")

registry_path = Path(".l9/sdk-schema-registry.json")
registry = json.loads(
registry_path.read_text(encoding="utf-8")
)

references = registry.setdefault("references", {})

references.update(
{
"repository-entity": {
"uri": "l9://sdk/repository-entity/v1",
"owner": "Quantum-L9/l9-ci-sdk"
},
"contract-reference": {
"uri": "l9://sdk/contract-reference/v1",
"owner": "Quantum-L9/l9-ci-sdk"
}
}
)

registry_path.write_text(
json.dumps(
registry,
ensure_ascii=False,
sort_keys=True,
indent=2,
)
+ "\n",
encoding="utf-8",
)
PY

###############################################################################

# 17. CI

###############################################################################

cat > .github/workflows/phase-2-repository-correlation.yml <<'EOF'
name: RESOLVER-P2 Repository Correlation

on:
pull_request:
push:
branches:
- main

permissions:
contents: read

jobs:
repository-correlation:
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
  - name: Correlation tests
    run: pytest tests/correlation
  - name: Classification tests
    run: pytest tests/classification
  - name: SDK adapter tests
    run: pytest tests/sdk
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

# 18. Acceptance gates

###############################################################################

cat > .l9/phase-2-acceptance-gates.yaml <<'EOF'
schema: l9.phase-acceptance-gates/v1

repository: Quantum-L9/l9-ci-debt-resolver
phase: RESOLVER-P2

gates:

  - id: p2-complete-evidence
    requirement: >
    Repository correlation and classification reject incomplete failed logs.
  - id: p2-SDK-snapshot
    requirement: >
    Repository knowledge is obtained from an SDK-owned snapshot matching the
    exact repository revision.
  - id: p2-no-SDK-identity-generation
    requirement: >
    Resolver code does not generate canonical SDK snapshot, entity, contract,
    finding, validation-plan, or validation-result identities.
  - id: p2-safe-paths
    requirement: >
    Stack-frame paths are repository-relative, traversal-free, and exclude
    redaction placeholders.
  - id: p2-deterministic-correlation
    requirement: >
    Frames, entities, tests, contracts, findings, and unresolved locations
    have deterministic ordering and deduplication.
  - id: p2-related-tests
    requirement: >
    Related tests are requested through the public SDK knowledge boundary.
  - id: p2-applicable-contracts
    requirement: >
    Applicable contracts are requested through the public SDK boundary.
  - id: p2-canonical-findings
    requirement: >
    Correlated findings retain canonical SDK identities.
  - id: p2-log-first-classification
    requirement: >
    Job names, historical memory, SDK metadata, and findings cannot classify
    a root cause without current complete failed-log signals.
  - id: p2-confidence
    requirement: >
    Automatic eligibility requires confidence of at least 0.90.
  - id: p2-conflict
    requirement: >
    Conflicting high-confidence categories become unsupported.
  - id: p2-infrastructure
    requirement: >
    Infrastructure failures are never automatically remediated.
  - id: p2-no-mutation
    requirement: >
    RESOLVER-P2 contains no repository mutation or remote branch behavior.
EOF
###############################################################################

# 19. Package-test import support

###############################################################################

touch tests/__init__.py
touch tests/correlation/__init__.py
touch tests/classification/__init__.py

###############################################################################


printf "phase generation complete\n"
