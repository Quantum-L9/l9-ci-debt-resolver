The reconstructed P0 below is a complete bootstrap, not the incomplete rename instruction in the uploaded Phase 0 note. It defines the exact base interfaces later phases depend on: CIRunEvidence, FailureClassification, canonical identities, schema validation, attempt lifecycle, terminal states, corpus-safe resolution events, packaging, CLI, tests, CI, ADRs, and roadmap metadata. P1 requires the repository specification and contract models to exist, upgrades version 0.1.0 to 0.2.0, and replaces the initial CLI with its acquisition CLI. 

The evidence fields match the constructor used by P2, while the classification fields match P3’s policy and fixtures. 

Save this as build-phase-0.sh.

#!/usr/bin/env bash
set -euo pipefail
###############################################################################
# Quantum-L9/l9-ci-debt-resolver
# RESOLVER-P0 — Contract Alignment and Production Foundation
#
# This is a full repository bootstrap. It intentionally overwrites all
# non-Git content in the current repository.
#
# Implements:
#   - repository ownership and dependency boundaries
#   - canonical deterministic identity generation
#   - typed CI evidence
#   - typed CI failure classification
#   - bounded attempt lifecycle
#   - deterministic terminal-state policy
#   - corpus-safe resolution events
#   - JSON Schema validation
#   - initial CLI and capabilities
#   - architecture and behavioral tests
#   - CI validation workflow
#
# Does not implement:
#   - failed-log acquisition              (RESOLVER-P1)
#   - SDK repository correlation          (RESOLVER-P2)
#   - root-cause classification runtime   (RESOLVER-P2)
#   - bounded remediation                 (RESOLVER-P3)
#   - remote branch operations            (RESOLVER-P4)
#   - CI rerun observation                (RESOLVER-P4)
#   - Intelligence feedback delivery      (RESOLVER-P5)
#   - PR_Repair delegation                (RESOLVER-P6)
###############################################################################
fail() {
  printf 'RESOLVER-P0: %s\n' "$*" >&2
  exit 1
}
require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "required command not found: $1"
}
require_command python3
[[ -d .git ]] \
  || fail "run from the l9-ci-debt-resolver Git repository root"
###############################################################################
# 1. Clean overwrite
###############################################################################
find . -mindepth 1 -maxdepth 1 \
  ! -name '.git' \
  ! -name 'build-phase-0.sh' \
  -exec rm -rf {} +
mkdir -p \
  .github/workflows \
  .l9 \
  docs/architecture/ADRs \
  schemas/resolver \
  src/l9_debt_resolver/contracts \
  src/l9_debt_resolver/runtime \
  tests/architecture \
  tests/contracts \
  tests/runtime \
  tests/fixtures
###############################################################################
# 2. Repository specification
###############################################################################
cat > .l9/repo-spec.yaml <<'EOF'
schema: l9.repo-spec/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  repository_url: https://github.com/Quantum-L9/l9-ci-debt-resolver
  spec_path: .l9/repo-spec.yaml
  spec_version: 1.0.0
  status: authoritative
  phase: RESOLVER-P0
  phase_name: contract_alignment
  last_converged: 2026-07-19
identity:
  name: l9-ci-debt-resolver
  constellation_role: CI_failure_evidence_specialist
  architectural_plane: failure_diagnosis_and_bounded_recovery
  operating_model:
    - evidence_first
    - actual_CI_log_driven
    - deterministic
    - minimal_remediation
    - fail_closed
  mission: >
    Retrieve actual failed CI evidence, classify root causes, correlate failures
    with SDK repository knowledge, apply minimal evidence-supported remediation,
    validate through SDK-owned contracts, observe CI reruns, and emit canonical
    resolution events.
ownership:
  owns:
    - failed CI run acquisition
    - failed job retrieval
    - failed log retrieval
    - log completeness assessment
    - CI-specific evidence extensions
    - CI-specific root-cause classification
    - resolver attempt lifecycle
    - remediation lifecycle
    - minimal evidence-bounded remediation
    - approved repair-branch interaction
    - CI rerun observation
    - repeated-failure detection
    - terminal-state handling
    - corpus-safe resolver events
  does_not_own:
    - scanner-native parsing
    - canonical SDK schema ownership
    - canonical SDK finding identity
    - repository semantic implementation
    - fleet corpus storage
    - historical corpus mining
    - prevention compilation
    - editor behavior
    - broad speculative repair planning
    - policy weakening
    - automatic merge
dependency_contract:
  required:
    - Quantum-L9/l9-ci-sdk
  operational_integrations:
    - GitHub Actions API
    - Git
  must_not_depend_on:
    - Quantum-L9/l9-ci-debt-intelligence runtime internals
    - Quantum-L9/l9-ci-debt-lsp
    - Quantum-L9/PR_Repair internals
  PR_Repair_relationship:
    resolver_scope: specialized actual-CI-failure remediation
    PR_Repair_scope: broad multi-source governed proposal generation
    future_option: >
      Complex approved repairs may be delegated through a public,
      proposal-only contract.
evidence_authority:
  precedence:
    - actual_failed_log
    - failed_job_metadata
    - SDK_repository_evidence
    - historical_context
  SDK_authority_classes:
    - RUNTIME_LOG
    - CI_RESULT
    - STATIC_ANALYZER
    - COMPILER_SEMANTIC
    - USER_ASSERTION
  prohibitions:
    - Historical memory cannot override current failed logs.
    - Job names alone cannot establish root cause.
    - Missing logs cannot be treated as PASS.
    - Incomplete logs cannot authorize remediation.
    - Every remediation must reference evidence.
    - Every limitation must remain visible.
attempt_lifecycle:
  initial_state: created
  states:
    - created
    - evidence_acquired
    - classified
    - remediation_planned
    - validating
    - validated
    - pushed
    - observing
    - clean
    - insufficient_log_evidence
    - unsupported
    - validation_failed
    - repeated_failure
    - new_failure
    - attempt_limit_reached
    - remote_operation_failed
    - rerun_timeout
  terminal_states:
    - clean
    - insufficient_log_evidence
    - unsupported
    - validation_failed
    - repeated_failure
    - new_failure
    - attempt_limit_reached
    - remote_operation_failed
    - rerun_timeout
  transitions:
    created:
      - evidence_acquired
      - insufficient_log_evidence
      - remote_operation_failed
    evidence_acquired:
      - classified
      - insufficient_log_evidence
      - unsupported
      - remote_operation_failed
    classified:
      - remediation_planned
      - unsupported
      - attempt_limit_reached
    remediation_planned:
      - validating
      - validation_failed
      - unsupported
    validating:
      - validated
      - validation_failed
      - remote_operation_failed
    validated:
      - pushed
      - remote_operation_failed
    pushed:
      - observing
      - remote_operation_failed
    observing:
      - clean
      - repeated_failure
      - new_failure
      - rerun_timeout
      - remote_operation_failed
terminal_state_policy:
  clean:
    requires:
      - completed CI rerun
      - successful CI rerun conclusion
  repeated_failure:
    requires:
      - completed unsuccessful rerun
      - observed failure fingerprint equals original fingerprint
  new_failure:
    requires:
      - completed unsuccessful rerun
      - observed failure fingerprint differs from original fingerprint
  insufficient_log_evidence:
    requires:
      - failed log unavailable, incomplete, or truncated
  success_claim:
    local_validation_only: prohibited
    successful_push_only: prohibited
    successful_rerun_required: true
privacy:
  corpus_safe_events:
    include:
      - provider
      - repository pseudonym
      - failure fingerprint
      - classification category
      - terminal state
      - attempt number
      - canonical SDK identity references
      - aggregate remediation metrics
      - hashed provenance
      - limitations
    exclude:
      - raw CI logs
      - source content
      - patches
      - diffs
      - credentials
      - developer identity
      - absolute paths
      - repository-relative paths
      - branch names
      - commit messages
phases:
  - phase: RESOLVER-P0
    name: contract_alignment
    priority: critical
    status: implemented
    deliverables:
      - repository boundary
      - typed CI evidence
      - attempt lifecycle
      - terminal states
      - corpus-safe event contract
  - phase: RESOLVER-P1
    name: failed_log_acquisition
    priority: critical
    status: planned
    deliverables:
      - failed-run retrieval
      - failed-job retrieval
      - failed-log retrieval
      - completeness assessment
      - provenance and redaction
  - phase: RESOLVER-P2
    name: repository_correlation
    priority: high
    status: planned
    deliverables:
      - SDK Knowledge API
      - stack-frame resolution
      - related tests
      - applicable contracts
      - root-cause classification
  - phase: RESOLVER-P3
    name: bounded_validation
    priority: high
    status: planned
    deliverables:
      - bounded remediation
      - SDK validation plans
      - original failure reproduction
      - graph-delta checks
      - rollback
  - phase: RESOLVER-P4
    name: remote_loop
    priority: high
    status: planned
    deliverables:
      - repair-branch safety
      - authorized push
      - rerun observation
      - repeated-failure detection
      - deterministic terminal states
  - phase: RESOLVER-P5
    name: intelligence_feedback
    priority: medium
    status: planned
    deliverables:
      - privacy-safe resolution events
      - repeated-failure telemetry
      - idempotent delivery
      - corpus-safe provenance
  - phase: RESOLVER-P6
    name: pr_repair_delegation
    priority: medium
    status: planned
    deliverables:
      - proposal-only PR_Repair handoff
      - bounded context
      - callback verification
      - retained Resolver authority
adr_seeds:
  - id: ADR-RESOLVER-001
    title: Current CI logs are the primary failure authority
    status: accepted
  - id: ADR-RESOLVER-002
    title: Repository semantics and validation remain SDK-owned
    status: accepted
  - id: ADR-RESOLVER-003
    title: Resolver repairs are minimal and evidence-bounded
    status: accepted
  - id: ADR-RESOLVER-004
    title: Repeated identical failures terminate
    status: accepted
  - id: ADR-RESOLVER-005
    title: Resolver events are correction-versioned and corpus-safe
    status: accepted
acceptance_gates:
  - id: resolver-log-first
    requirement: >
      No remediation begins before authoritative failed logs are retrieved and
      their completeness is validated.
  - id: resolver-evidence-trace
    requirement: >
      Every changed path and remediation operation traces to classified
      evidence.
  - id: resolver-bounded-change
    requirement: >
      Repair scope is no broader than demonstrated failure scope.
  - id: resolver-shared-validation
    requirement: >
      SDK validation contracts replace bespoke test selection.
  - id: resolver-rerun-proof
    requirement: >
      Clean is emitted only after a successful CI rerun.
  - id: resolver-no-merge
    requirement: >
      Automatic merge remains prohibited.
EOF
cat > .l9/resolver-foundation-contract.yaml <<'EOF'
schema: l9.resolver-foundation-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P0
  status: authoritative
contracts:
  CI_evidence:
    schema: l9://resolver/ci-run-evidence/v1
    typed_model: l9_debt_resolver.contracts.models.CIRunEvidence
  classification:
    schema: l9://resolver/ci-failure-classification/v1
    typed_model: l9_debt_resolver.contracts.models.FailureClassification
  attempt:
    schema: l9://resolver/resolver-attempt/v1
    typed_model: l9_debt_resolver.contracts.models.ResolverAttempt
  terminal_state:
    schema: l9://resolver/resolver-terminal-state/v1
    typed_model: l9_debt_resolver.contracts.models.ResolverTerminalState
  resolution_event:
    schema: l9://resolver/resolution-event/v1
    typed_model: l9_debt_resolver.contracts.models.ResolutionEvent
determinism:
  canonical_encoding:
    format: UTF-8 JSON
    keys: lexicographically_sorted
    separators: compact
    NaN: prohibited
  identity:
    algorithm: SHA-256
    input: canonical_encoding
    format: namespace_prefix_plus_lowercase_hex_digest
security:
  fail_closed: true
  arbitrary_shell_execution: prohibited
  automatic_merge: prohibited
  raw_log_corpus_transmission: prohibited
  source_content_corpus_transmission: prohibited
EOF
cat > .l9/phase-0-acceptance-gates.yaml <<'EOF'
schema: l9.phase-acceptance-gates/v1
repository: Quantum-L9/l9-ci-debt-resolver
phase: RESOLVER-P0
gates:
  - id: p0-installable
    requirement: >
      The Python package installs in editable mode with the development
      dependency group.
  - id: p0-canonical-identities
    requirement: >
      Identity generation is deterministic and insensitive to dictionary input
      order.
  - id: p0-typed-evidence
    requirement: >
      CI evidence has a strict typed representation and JSON Schema.
  - id: p0-typed-classification
    requirement: >
      Failure classification has a strict typed representation and JSON Schema.
  - id: p0-attempt-lifecycle
    requirement: >
      Attempt state transitions are explicit and illegal transitions fail.
  - id: p0-terminal-states
    requirement: >
      Terminal states are enumerated and cannot transition further.
  - id: p0-corpus-safety
    requirement: >
      Resolution events contain aggregate references and prohibit raw logs,
      source content, patches, credentials, and paths.
  - id: p0-no-private-dependencies
    requirement: >
      Resolver imports no private Intelligence, LSP, SDK, or PR_Repair modules.
  - id: p0-no-remote-behavior
    requirement: >
      P0 performs no branch mutation, push, rerun, or merge.
  - id: p0-p1-compatible
    requirement: >
      P1 can import CIRunEvidence, SchemaValidator, capability output, and the
      CLI foundation without modification.
EOF
###############################################################################
# 3. JSON Schemas
###############################################################################
cat > schemas/resolver/ci-run-evidence.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/ci-run-evidence/v1",
  "title": "L9 Resolver CI Run Evidence",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "evidence_id",
    "provider",
    "run_id",
    "job_id",
    "job_name",
    "failed_command",
    "conclusion",
    "log_sha256",
    "log_size_bytes",
    "log_completeness",
    "authority_class",
    "artifact_provenance",
    "observed_at",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.ci-run-evidence/v1"
    },
    "evidence_id": {
      "type": "string",
      "pattern": "^evidence_[0-9a-f]{64}$"
    },
    "provider": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "run_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "job_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "job_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "failed_command": {
      "type": ["string", "null"],
      "maxLength": 2000
    },
    "conclusion": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "log_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "log_size_bytes": {
      "type": "integer",
      "minimum": 0
    },
    "log_completeness": {
      "enum": [
        "complete",
        "possibly_truncated",
        "truncated",
        "unavailable"
      ]
    },
    "authority_class": {
      "enum": [
        "RUNTIME_LOG",
        "CI_RESULT",
        "STATIC_ANALYZER",
        "COMPILER_SEMANTIC",
        "USER_ASSERTION"
      ]
    },
    "artifact_provenance": {
      "type": "object"
    },
    "observed_at": {
      "type": "string",
      "format": "date-time"
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
cat > schemas/resolver/ci-failure-classification.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/ci-failure-classification/v1",
  "title": "L9 Resolver CI Failure Classification",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "classification_id",
    "failure_fingerprint",
    "category",
    "confidence",
    "evidence_ids",
    "failed_command",
    "repository_snapshot_id",
    "affected_entities",
    "remediation_eligibility",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.ci-failure-classification/v1"
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
    "failed_command": {
      "type": ["string", "null"],
      "maxLength": 2000
    },
    "repository_snapshot_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
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
cat > schemas/resolver/resolver-attempt.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/resolver-attempt/v1",
  "title": "L9 Resolver Attempt",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "attempt_id",
    "failure_fingerprint",
    "attempt_number",
    "state",
    "evidence_ids",
    "classification_id",
    "remediation_plan_id",
    "validation_result_id",
    "original_run_id",
    "rerun_id",
    "created_at",
    "updated_at",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.resolver-attempt/v1"
    },
    "attempt_id": {
      "type": "string",
      "pattern": "^attempt_[0-9a-f]{64}$"
    },
    "failure_fingerprint": {
      "type": "string",
      "pattern": "^failure_[0-9a-f]{64}$"
    },
    "attempt_number": {
      "type": "integer",
      "minimum": 1
    },
    "state": {
      "$ref": "l9://resolver/resolver-terminal-state/v1#/$defs/state"
    },
    "evidence_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    },
    "classification_id": {
      "type": ["string", "null"]
    },
    "remediation_plan_id": {
      "type": ["string", "null"]
    },
    "validation_result_id": {
      "type": ["string", "null"]
    },
    "original_run_id": {
      "type": "string",
      "minLength": 1
    },
    "rerun_id": {
      "type": ["string", "null"]
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
cat > schemas/resolver/resolver-terminal-state.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/resolver-terminal-state/v1",
  "title": "L9 Resolver State",
  "$ref": "#/$defs/state",
  "$defs": {
    "state": {
      "enum": [
        "created",
        "evidence_acquired",
        "classified",
        "remediation_planned",
        "validating",
        "validated",
        "pushed",
        "observing",
        "clean",
        "insufficient_log_evidence",
        "unsupported",
        "validation_failed",
        "repeated_failure",
        "new_failure",
        "attempt_limit_reached",
        "remote_operation_failed",
        "rerun_timeout"
      ]
    }
  }
}
EOF
cat > schemas/resolver/remediation-record.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/remediation-record/v1",
  "title": "L9 Resolver Remediation Record",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "remediation_id",
    "classification_id",
    "failure_fingerprint",
    "status",
    "changed_paths",
    "changed_line_count",
    "validation_result_id",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.remediation-record/v1"
    },
    "remediation_id": {
      "type": "string",
      "pattern": "^remediation_[0-9a-f]{64}$"
    },
    "classification_id": {
      "type": "string"
    },
    "failure_fingerprint": {
      "type": "string"
    },
    "status": {
      "enum": [
        "planned",
        "validating",
        "validated",
        "rolled_back",
        "rejected"
      ]
    },
    "changed_paths": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    },
    "changed_line_count": {
      "type": "integer",
      "minimum": 0
    },
    "validation_result_id": {
      "type": ["string", "null"]
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
cat > schemas/resolver/resolution-event.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/resolution-event/v1",
  "title": "L9 Resolver Corpus-Safe Resolution Event",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "event_id",
    "event_version",
    "repository_pseudonym",
    "provider",
    "failure_fingerprint",
    "classification_category",
    "terminal_state",
    "attempt_number",
    "evidence_id_hashes",
    "finding_ids",
    "contract_ids",
    "changed_file_count",
    "changed_line_bucket",
    "validation_result",
    "occurred_at",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.resolution-event/v1"
    },
    "event_id": {
      "type": "string",
      "pattern": "^resolution_event_[0-9a-f]{64}$"
    },
    "event_version": {
      "type": "integer",
      "minimum": 1
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
    "failure_fingerprint": {
      "type": "string",
      "pattern": "^failure_[0-9a-f]{64}$"
    },
    "classification_category": {
      "type": "string",
      "maxLength": 100
    },
    "terminal_state": {
      "$ref": "l9://resolver/resolver-terminal-state/v1#/$defs/state"
    },
    "attempt_number": {
      "type": "integer",
      "minimum": 1
    },
    "evidence_id_hashes": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[0-9a-f]{64}$"
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
    "changed_file_count": {
      "type": "integer",
      "minimum": 0
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
    "validation_result": {
      "enum": [
        "passed",
        "failed",
        "unavailable",
        "incomplete",
        "not_run"
      ]
    },
    "occurred_at": {
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
cat > schemas/resolver/resolver-capabilities.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/resolver-capabilities/v1",
  "title": "L9 Resolver Capabilities",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "phase",
    "capabilities",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.resolver-capabilities/v1"
    },
    "phase": {
      "const": "RESOLVER-P0"
    },
    "capabilities": {
      "type": "object"
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  }
}
EOF
###############################################################################
# 4. Packaging
###############################################################################
cat > pyproject.toml <<'EOF'
[build-system]
requires = ["hatchling>=1.25,<2"]
build-backend = "hatchling.build"
[project]
name = "l9-ci-debt-resolver"
version = "0.1.0"
description = "Evidence-first CI failure diagnosis and bounded recovery"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "Apache-2.0" }
authors = [
  { name = "Quantum-L9" }
]
dependencies = [
  "jsonschema>=4.23,<5",
  "pyyaml>=6.0,<7"
]
[project.optional-dependencies]
dev = [
  "mypy>=1.11,<2",
  "pytest>=8.3,<9",
  "pytest-cov>=5,<7",
  "pytest-asyncio>=0.24,<1",
  "ruff>=0.6,<1"
]
[project.scripts]
l9-debt-resolver = "l9_debt_resolver.cli:main"
[tool.hatch.build.targets.wheel]
packages = ["src/l9_debt_resolver"]
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
asyncio_mode = "strict"
[tool.ruff]
target-version = "py311"
line-length = 88
[tool.ruff.lint]
select = [
  "E",
  "F",
  "I",
  "B",
  "UP",
  "RUF"
]
[tool.mypy]
python_version = "3.11"
strict = true
packages = ["l9_debt_resolver"]
EOF
###############################################################################
# 5. Python package
###############################################################################
cat > src/l9_debt_resolver/__init__.py <<'EOF'
"""Quantum-L9 CI debt resolver."""
__version__ = "0.1.0"
EOF
cat > src/l9_debt_resolver/contracts/__init__.py <<'EOF'
"""Public Resolver contracts."""
EOF
cat > src/l9_debt_resolver/contracts/errors.py <<'EOF'
from __future__ import annotations
class ContractError(ValueError):
    """Base contract failure."""
class SchemaValidationError(ContractError):
    """A document violates its JSON Schema contract."""
class IdentityError(ContractError):
    """Canonical identity material is invalid."""
class AttemptTransitionError(ContractError):
    """A resolver attempt transition is not permitted."""
class TerminalStateError(ContractError):
    """A terminal state invariant is violated."""
class CorpusSafetyError(ContractError):
    """A resolution event contains prohibited data."""
EOF
cat > src/l9_debt_resolver/contracts/canonical.py <<'EOF'
from __future__ import annotations
import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from .errors import IdentityError
def canonical_json(value: object) -> bytes:
    """Encode deterministic identity material as canonical UTF-8 JSON."""
    normalized = _normalize(value)
    try:
        return json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise IdentityError(
            f"value cannot be canonically encoded: {error}"
        ) from error
def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
def namespaced_identity(
    prefix: str,
    value: object,
) -> str:
    if not prefix:
        raise IdentityError("identity prefix cannot be empty")
    if not prefix.endswith("_"):
        raise IdentityError(
            "identity prefix must end with an underscore"
        )
    return prefix + sha256_bytes(canonical_json(value))
def stable_text_hash(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))
def _normalize(value: object) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise IdentityError(
                    "canonical object keys must be strings"
                )
            result[key] = _normalize(item)
        return result
    if isinstance(value, tuple | list):
        return [_normalize(item) for item in value]
    if isinstance(value, set | frozenset):
        normalized = [_normalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: canonical_json(item),
        )
    if isinstance(value, float):
        if not math.isfinite(value):
            raise IdentityError(
                "non-finite numbers are prohibited"
            )
        return value
    if value is None or isinstance(
        value,
        (str, int, bool),
    ):
        return value
    raise IdentityError(
        f"unsupported canonical value: {type(value).__name__}"
    )
EOF
cat > src/l9_debt_resolver/contracts/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any
from .errors import (
    AttemptTransitionError,
    TerminalStateError,
)
class ResolverState(StrEnum):
    CREATED = "created"
    EVIDENCE_ACQUIRED = "evidence_acquired"
    CLASSIFIED = "classified"
    REMEDIATION_PLANNED = "remediation_planned"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PUSHED = "pushed"
    OBSERVING = "observing"
    CLEAN = "clean"
    INSUFFICIENT_LOG_EVIDENCE = "insufficient_log_evidence"
    UNSUPPORTED = "unsupported"
    VALIDATION_FAILED = "validation_failed"
    REPEATED_FAILURE = "repeated_failure"
    NEW_FAILURE = "new_failure"
    ATTEMPT_LIMIT_REACHED = "attempt_limit_reached"
    REMOTE_OPERATION_FAILED = "remote_operation_failed"
    RERUN_TIMEOUT = "rerun_timeout"
TERMINAL_STATES = frozenset(
    {
        ResolverState.CLEAN,
        ResolverState.INSUFFICIENT_LOG_EVIDENCE,
        ResolverState.UNSUPPORTED,
        ResolverState.VALIDATION_FAILED,
        ResolverState.REPEATED_FAILURE,
        ResolverState.NEW_FAILURE,
        ResolverState.ATTEMPT_LIMIT_REACHED,
        ResolverState.REMOTE_OPERATION_FAILED,
        ResolverState.RERUN_TIMEOUT,
    }
)
ALLOWED_TRANSITIONS: dict[
    ResolverState,
    frozenset[ResolverState],
] = {
    ResolverState.CREATED: frozenset(
        {
            ResolverState.EVIDENCE_ACQUIRED,
            ResolverState.INSUFFICIENT_LOG_EVIDENCE,
            ResolverState.REMOTE_OPERATION_FAILED,
        }
    ),
    ResolverState.EVIDENCE_ACQUIRED: frozenset(
        {
            ResolverState.CLASSIFIED,
            ResolverState.INSUFFICIENT_LOG_EVIDENCE,
            ResolverState.UNSUPPORTED,
            ResolverState.REMOTE_OPERATION_FAILED,
        }
    ),
    ResolverState.CLASSIFIED: frozenset(
        {
            ResolverState.REMEDIATION_PLANNED,
            ResolverState.UNSUPPORTED,
            ResolverState.ATTEMPT_LIMIT_REACHED,
        }
    ),
    ResolverState.REMEDIATION_PLANNED: frozenset(
        {
            ResolverState.VALIDATING,
            ResolverState.VALIDATION_FAILED,
            ResolverState.UNSUPPORTED,
        }
    ),
    ResolverState.VALIDATING: frozenset(
        {
            ResolverState.VALIDATED,
            ResolverState.VALIDATION_FAILED,
            ResolverState.REMOTE_OPERATION_FAILED,
        }
    ),
    ResolverState.VALIDATED: frozenset(
        {
            ResolverState.PUSHED,
            ResolverState.REMOTE_OPERATION_FAILED,
        }
    ),
    ResolverState.PUSHED: frozenset(
        {
            ResolverState.OBSERVING,
            ResolverState.REMOTE_OPERATION_FAILED,
        }
    ),
    ResolverState.OBSERVING: frozenset(
        {
            ResolverState.CLEAN,
            ResolverState.REPEATED_FAILURE,
            ResolverState.NEW_FAILURE,
            ResolverState.RERUN_TIMEOUT,
            ResolverState.REMOTE_OPERATION_FAILED,
        }
    ),
}
@dataclass(frozen=True)
class CIRunEvidence:
    evidence_id: str
    provider: str
    run_id: str
    job_id: str
    job_name: str
    failed_command: str | None
    conclusion: str
    log_sha256: str
    log_size_bytes: int
    log_completeness: str
    authority_class: str
    artifact_provenance: dict[str, Any]
    observed_at: str
    limitations: tuple[str, ...]
    def __post_init__(self) -> None:
        if self.log_size_bytes < 0:
            raise ValueError(
                "log_size_bytes cannot be negative"
            )
        if self.log_completeness not in {
            "complete",
            "possibly_truncated",
            "truncated",
            "unavailable",
        }:
            raise ValueError(
                "unsupported log completeness state"
            )
        if self.authority_class not in {
            "RUNTIME_LOG",
            "CI_RESULT",
            "STATIC_ANALYZER",
            "COMPILER_SEMANTIC",
            "USER_ASSERTION",
        }:
            raise ValueError(
                "unsupported evidence authority class"
            )
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.ci-run-evidence/v1",
            "evidence_id": self.evidence_id,
            "provider": self.provider,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "job_name": self.job_name,
            "failed_command": self.failed_command,
            "conclusion": self.conclusion,
            "log_sha256": self.log_sha256,
            "log_size_bytes": self.log_size_bytes,
            "log_completeness": self.log_completeness,
            "authority_class": self.authority_class,
            "artifact_provenance": self.artifact_provenance,
            "observed_at": self.observed_at,
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class FailureClassification:
    classification_id: str
    failure_fingerprint: str
    category: str
    confidence: float
    evidence_ids: tuple[str, ...]
    failed_command: str | None
    repository_snapshot_id: str
    affected_entities: tuple[str, ...]
    remediation_eligibility: str
    limitations: tuple[str, ...]
    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError(
                "classification confidence must be between 0 and 1"
            )
        if not self.evidence_ids:
            raise ValueError(
                "classification requires at least one evidence ID"
            )
        if self.remediation_eligibility not in {
            "automatic",
            "approval_required",
            "unsupported",
        }:
            raise ValueError(
                "unsupported remediation eligibility"
            )
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "l9.ci-failure-classification/v1"
            ),
            "classification_id": self.classification_id,
            "failure_fingerprint": (
                self.failure_fingerprint
            ),
            "category": self.category,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "failed_command": self.failed_command,
            "repository_snapshot_id": (
                self.repository_snapshot_id
            ),
            "affected_entities": list(
                self.affected_entities
            ),
            "remediation_eligibility": (
                self.remediation_eligibility
            ),
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class ResolverTerminalState:
    state: ResolverState
    def __post_init__(self) -> None:
        if self.state not in TERMINAL_STATES:
            raise TerminalStateError(
                f"state is not terminal: {self.state}"
            )
    def as_dict(self) -> dict[str, str]:
        return {
            "schema_version": (
                "l9.resolver-terminal-state/v1"
            ),
            "state": self.state.value,
        }
@dataclass(frozen=True)
class ResolverAttempt:
    attempt_id: str
    failure_fingerprint: str
    attempt_number: int
    state: ResolverState
    evidence_ids: tuple[str, ...]
    classification_id: str | None
    remediation_plan_id: str | None
    validation_result_id: str | None
    original_run_id: str
    rerun_id: str | None
    created_at: str
    updated_at: str
    limitations: tuple[str, ...]
    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError(
                "attempt_number must be positive"
            )
    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES
    def transition(
        self,
        target: ResolverState,
        *,
        updated_at: str,
        classification_id: str | None = None,
        remediation_plan_id: str | None = None,
        validation_result_id: str | None = None,
        rerun_id: str | None = None,
        limitations: tuple[str, ...] = (),
    ) -> ResolverAttempt:
        if self.terminal:
            raise AttemptTransitionError(
                f"terminal state cannot transition: {self.state}"
            )
        permitted = ALLOWED_TRANSITIONS.get(
            self.state,
            frozenset(),
        )
        if target not in permitted:
            raise AttemptTransitionError(
                f"illegal transition: {self.state} -> {target}"
            )
        return replace(
            self,
            state=target,
            classification_id=(
                classification_id
                if classification_id is not None
                else self.classification_id
            ),
            remediation_plan_id=(
                remediation_plan_id
                if remediation_plan_id is not None
                else self.remediation_plan_id
            ),
            validation_result_id=(
                validation_result_id
                if validation_result_id is not None
                else self.validation_result_id
            ),
            rerun_id=(
                rerun_id
                if rerun_id is not None
                else self.rerun_id
            ),
            updated_at=updated_at,
            limitations=tuple(
                sorted(
                    {
                        *self.limitations,
                        *limitations,
                    }
                )
            ),
        )
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.resolver-attempt/v1",
            "attempt_id": self.attempt_id,
            "failure_fingerprint": (
                self.failure_fingerprint
            ),
            "attempt_number": self.attempt_number,
            "state": self.state.value,
            "evidence_ids": list(self.evidence_ids),
            "classification_id": self.classification_id,
            "remediation_plan_id": (
                self.remediation_plan_id
            ),
            "validation_result_id": (
                self.validation_result_id
            ),
            "original_run_id": self.original_run_id,
            "rerun_id": self.rerun_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class ResolutionEvent:
    event_id: str
    event_version: int
    repository_pseudonym: str
    provider: str
    failure_fingerprint: str
    classification_category: str
    terminal_state: ResolverState
    attempt_number: int
    evidence_id_hashes: tuple[str, ...]
    finding_ids: tuple[str, ...]
    contract_ids: tuple[str, ...]
    changed_file_count: int
    changed_line_bucket: str
    validation_result: str
    occurred_at: str
    limitations: tuple[str, ...]
    def __post_init__(self) -> None:
        if self.terminal_state not in TERMINAL_STATES:
            raise TerminalStateError(
                "resolution event requires a terminal state"
            )
        if self.event_version < 1:
            raise ValueError(
                "event_version must be positive"
            )
        if self.attempt_number < 1:
            raise ValueError(
                "attempt_number must be positive"
            )
        if self.changed_file_count < 0:
            raise ValueError(
                "changed_file_count cannot be negative"
            )
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.resolution-event/v1",
            "event_id": self.event_id,
            "event_version": self.event_version,
            "repository_pseudonym": (
                self.repository_pseudonym
            ),
            "provider": self.provider,
            "failure_fingerprint": (
                self.failure_fingerprint
            ),
            "classification_category": (
                self.classification_category
            ),
            "terminal_state": self.terminal_state.value,
            "attempt_number": self.attempt_number,
            "evidence_id_hashes": list(
                self.evidence_id_hashes
            ),
            "finding_ids": list(self.finding_ids),
            "contract_ids": list(self.contract_ids),
            "changed_file_count": (
                self.changed_file_count
            ),
            "changed_line_bucket": (
                self.changed_line_bucket
            ),
            "validation_result": (
                self.validation_result
            ),
            "occurred_at": self.occurred_at,
            "limitations": list(self.limitations),
        }
EOF
cat > src/l9_debt_resolver/contracts/schema.py <<'EOF'
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import (
    Draft202012Validator,
    FormatChecker,
)
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from .errors import SchemaValidationError
class SchemaRegistry:
    def __init__(
        self,
        schema_root: Path,
    ) -> None:
        self._schema_root = schema_root
        self._documents = self._load_documents()
        self._registry = self._build_registry()
    @property
    def registry(self) -> Registry:
        return self._registry
    def document(
        self,
        path: Path,
    ) -> dict[str, Any]:
        resolved = path.resolve()
        try:
            return self._documents[resolved]
        except KeyError as error:
            raise SchemaValidationError(
                f"schema is outside registry: {path}"
            ) from error
    def _load_documents(
        self,
    ) -> dict[Path, dict[str, Any]]:
        documents: dict[Path, dict[str, Any]] = {}
        for path in sorted(
            self._schema_root.glob("*.json")
        ):
            value = json.loads(
                path.read_text(encoding="utf-8")
            )
            if not isinstance(value, dict):
                raise SchemaValidationError(
                    f"schema must be an object: {path}"
                )
            Draft202012Validator.check_schema(value)
            documents[path.resolve()] = value
        return documents
    def _build_registry(self) -> Registry:
        registry = Registry()
        for document in self._documents.values():
            identifier = document.get("$id")
            if not isinstance(identifier, str):
                continue
            resource = Resource.from_contents(
                document
            )
            registry = registry.with_resource(
                identifier,
                resource,
            )
        return registry
class SchemaValidator:
    def __init__(
        self,
        schema_path: Path,
    ) -> None:
        schema_path = schema_path.resolve()
        registry = SchemaRegistry(
            schema_path.parent
        )
        schema = registry.document(schema_path)
        self._validator = Draft202012Validator(
            schema,
            registry=registry.registry,
            format_checker=FormatChecker(),
        )
    def validate(
        self,
        document: object,
    ) -> None:
        errors = sorted(
            self._validator.iter_errors(document),
            key=lambda error: (
                tuple(str(item) for item in error.path),
                error.message,
            ),
        )
        if not errors:
            return
        raise SchemaValidationError(
            "; ".join(
                _format_error(error)
                for error in errors
            )
        )
def _format_error(
    error: ValidationError,
) -> str:
    location = "$"
    for item in error.absolute_path:
        if isinstance(item, int):
            location += f"[{item}]"
        else:
            location += f".{item}"
    return f"{location}: {error.message}"
EOF
cat > src/l9_debt_resolver/contracts/privacy.py <<'EOF'
from __future__ import annotations
import json
import re
from typing import Any
from .errors import CorpusSafetyError
FORBIDDEN_KEY_FRAGMENTS = (
    "raw_log",
    "source_code",
    "source_content",
    "patch",
    "diff",
    "credential",
    "authorization",
    "password",
    "secret",
    "developer",
    "actor",
    "email",
    "absolute_path",
    "repository_path",
    "branch",
    "commit_message",
    "environment",
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(
        r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"
    ),
    re.compile(
        r"\b(?:ghp|github_pat|gho|ghu|ghs|ghr)_"
        r"[A-Za-z0-9_]{20,}\b"
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
def validate_corpus_safe_document(
    document: dict[str, Any],
    *,
    maximum_bytes: int = 65536,
) -> None:
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > maximum_bytes:
        raise CorpusSafetyError(
            "corpus-safe document exceeds byte limit"
        )
    _walk(document, path="$", depth=0)
def _walk(
    value: Any,
    *,
    path: str,
    depth: int,
) -> None:
    if depth > 10:
        raise CorpusSafetyError(
            f"document exceeds depth limit at {path}"
        )
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).casefold()
            if any(
                fragment in normalized
                for fragment in FORBIDDEN_KEY_FRAGMENTS
            ):
                raise CorpusSafetyError(
                    f"forbidden corpus key at {path}.{key}"
                )
            _walk(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        if len(value) > 500:
            raise CorpusSafetyError(
                f"array exceeds limit at {path}"
            )
        for index, item in enumerate(value):
            _walk(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        if len(value) > 4000:
            raise CorpusSafetyError(
                f"string exceeds limit at {path}"
            )
        for pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                raise CorpusSafetyError(
                    f"sensitive value at {path}"
                )
        if "\n" in value and len(
            value.splitlines()
        ) > 5:
            raise CorpusSafetyError(
                f"multiline content prohibited at {path}"
            )
        return
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return
    raise CorpusSafetyError(
        f"unsupported value at {path}"
    )
EOF
###############################################################################
# 6. Runtime
###############################################################################
cat > src/l9_debt_resolver/runtime/__init__.py <<'EOF'
"""Resolver runtime foundation."""
EOF
cat > src/l9_debt_resolver/runtime/capabilities.py <<'EOF'
from __future__ import annotations
from typing import Any
def resolver_capabilities() -> dict[str, Any]:
    return {
        "schema_version": "l9.resolver-capabilities/v1",
        "phase": "RESOLVER-P0",
        "capabilities": {
            "contract_validation": True,
            "typed_CI_evidence": True,
            "typed_failure_classification": True,
            "deterministic_identities": True,
            "cross_schema_resolution": True,
            "attempt_lifecycle": True,
            "terminal_states": True,
            "corpus_safe_events": True,
            "corpus_privacy_validation": True,
            "failed_run_acquisition": False,
            "failed_job_acquisition": False,
            "failed_log_acquisition": False,
            "SDK_repository_correlation": False,
            "root_cause_classification": False,
            "bounded_remediation": False,
            "SDK_validation_execution": False,
            "branch_mutation": False,
            "remote_push": False,
            "CI_rerun_observation": False,
            "Intelligence_feedback_delivery": False,
            "PR_Repair_delegation": False,
            "automatic_merge": False
        },
        "limitations": [
            "P0 establishes contracts and lifecycle foundations only.",
            "Failed-log acquisition begins in RESOLVER-P1.",
            "SDK correlation and diagnosis begin in RESOLVER-P2.",
            "Bounded remediation begins in RESOLVER-P3.",
            "Remote branch operations and rerun observation begin in RESOLVER-P4.",
            "Intelligence feedback begins in RESOLVER-P5.",
            "PR_Repair proposal delegation begins in RESOLVER-P6.",
            "Automatic merge is prohibited."
        ]
    }
EOF
cat > src/l9_debt_resolver/runtime/attempts.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.contracts.models import (
    ResolverAttempt,
    ResolverState,
)
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
def create_attempt(
    *,
    failure_fingerprint: str,
    attempt_number: int,
    original_run_id: str,
    evidence_ids: tuple[str, ...] = (),
    created_at: str | None = None,
) -> ResolverAttempt:
    timestamp = created_at or utc_now()
    attempt_id = namespaced_identity(
        "attempt_",
        {
            "failure_fingerprint": (
                failure_fingerprint
            ),
            "attempt_number": attempt_number,
            "original_run_id": original_run_id,
        },
    )
    return ResolverAttempt(
        attempt_id=attempt_id,
        failure_fingerprint=(
            failure_fingerprint
        ),
        attempt_number=attempt_number,
        state=ResolverState.CREATED,
        evidence_ids=tuple(
            sorted(set(evidence_ids))
        ),
        classification_id=None,
        remediation_plan_id=None,
        validation_result_id=None,
        original_run_id=original_run_id,
        rerun_id=None,
        created_at=timestamp,
        updated_at=timestamp,
        limitations=(),
    )
EOF
###############################################################################
# 7. CLI
###############################################################################
cat > src/l9_debt_resolver/cli.py <<'EOF'
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Sequence
from .contracts.schema import SchemaValidator
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
            "resolver-capabilities",
        ],
    )
    validate.add_argument(
        "document",
        type=Path,
    )
    return parser
def main(
    argv: Sequence[str] | None = None,
) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "capabilities":
        emit(resolver_capabilities())
        return 0
    if arguments.command == "validate":
        document = json.loads(
            arguments.document.read_text(
                encoding="utf-8"
            )
        )
        schema_path = (
            schema_root()
            / f"{arguments.schema}.schema.json"
        )
        SchemaValidator(
            schema_path
        ).validate(document)
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
    raise AssertionError("unreachable")
if __name__ == "__main__":
    raise SystemExit(main())
EOF
###############################################################################
# 8. Tests
###############################################################################
cat > tests/contracts/test_canonical.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.contracts.canonical import (
    canonical_json,
    namespaced_identity,
)
from l9_debt_resolver.contracts.errors import (
    IdentityError,
)
def test_mapping_order_does_not_change_identity() -> None:
    first = namespaced_identity(
        "example_",
        {
            "a": 1,
            "b": 2,
        },
    )
    second = namespaced_identity(
        "example_",
        {
            "b": 2,
            "a": 1,
        },
    )
    assert first == second
def test_identity_has_expected_shape() -> None:
    value = namespaced_identity(
        "evidence_",
        {"value": 1},
    )
    assert value.startswith("evidence_")
    assert len(value) == len("evidence_") + 64
def test_non_finite_numbers_are_rejected() -> None:
    with pytest.raises(IdentityError):
        canonical_json(
            {
                "value": float("nan"),
            }
        )
EOF
cat > tests/contracts/test_models.py <<'EOF'
from __future__ import annotations
import hashlib
import pytest
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
    FailureClassification,
)
def test_CI_evidence_round_trip_shape() -> None:
    evidence = CIRunEvidence(
        evidence_id="evidence_" + "a" * 64,
        provider="github_actions",
        run_id="100",
        job_id="200",
        job_name="tests",
        failed_command="pytest",
        conclusion="failure",
        log_sha256=hashlib.sha256(
            b"log"
        ).hexdigest(),
        log_size_bytes=3,
        log_completeness="complete",
        authority_class="RUNTIME_LOG",
        artifact_provenance={
            "source": "github_actions_job_log"
        },
        observed_at="2026-07-19T00:00:00Z",
        limitations=(),
    )
    document = evidence.as_dict()
    assert document["job_name"] == "tests"
    assert document["log_completeness"] == "complete"
    assert document["limitations"] == []
def test_invalid_log_completeness_is_rejected() -> None:
    with pytest.raises(ValueError):
        CIRunEvidence(
            evidence_id="evidence_" + "a" * 64,
            provider="github_actions",
            run_id="100",
            job_id="200",
            job_name="tests",
            failed_command=None,
            conclusion="failure",
            log_sha256="b" * 64,
            log_size_bytes=0,
            log_completeness="unknown",
            authority_class="RUNTIME_LOG",
            artifact_provenance={},
            observed_at="2026-07-19T00:00:00Z",
            limitations=(),
        )
def test_classification_requires_evidence() -> None:
    with pytest.raises(ValueError):
        FailureClassification(
            classification_id=(
                "classification_" + "a" * 64
            ),
            failure_fingerprint=(
                "failure_" + "b" * 64
            ),
            category="test_failure",
            confidence=0.95,
            evidence_ids=(),
            failed_command="pytest",
            repository_snapshot_id="snapshot-1",
            affected_entities=(),
            remediation_eligibility="automatic",
            limitations=(),
        )
EOF
cat > tests/contracts/test_schema.py <<'EOF'
from __future__ import annotations
import hashlib
from pathlib import Path
import pytest
from l9_debt_resolver.contracts.errors import (
    SchemaValidationError,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)
from l9_debt_resolver.contracts.schema import (
    SchemaValidator,
)
ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas" / "resolver"
def test_evidence_schema_accepts_typed_document() -> None:
    evidence = CIRunEvidence(
        evidence_id="evidence_" + "a" * 64,
        provider="github_actions",
        run_id="100",
        job_id="200",
        job_name="tests",
        failed_command="pytest",
        conclusion="failure",
        log_sha256=hashlib.sha256(
            b"log"
        ).hexdigest(),
        log_size_bytes=3,
        log_completeness="complete",
        authority_class="RUNTIME_LOG",
        artifact_provenance={},
        observed_at="2026-07-19T00:00:00Z",
        limitations=(),
    )
    SchemaValidator(
        SCHEMAS / "ci-run-evidence.schema.json"
    ).validate(evidence.as_dict())
def test_unknown_property_is_rejected() -> None:
    validator = SchemaValidator(
        SCHEMAS / "ci-run-evidence.schema.json"
    )
    with pytest.raises(
        SchemaValidationError
    ):
        validator.validate(
            {
                "schema_version": (
                    "l9.ci-run-evidence/v1"
                ),
                "unexpected": True,
            }
        )
def test_cross_schema_reference_resolves() -> None:
    validator = SchemaValidator(
        SCHEMAS / "resolver-attempt.schema.json"
    )
    validator.validate(
        {
            "schema_version": (
                "l9.resolver-attempt/v1"
            ),
            "attempt_id": (
                "attempt_" + "a" * 64
            ),
            "failure_fingerprint": (
                "failure_" + "b" * 64
            ),
            "attempt_number": 1,
            "state": "created",
            "evidence_ids": [],
            "classification_id": None,
            "remediation_plan_id": None,
            "validation_result_id": None,
            "original_run_id": "100",
            "rerun_id": None,
            "created_at": "2026-07-19T00:00:00Z",
            "updated_at": "2026-07-19T00:00:00Z",
            "limitations": [],
        }
    )
EOF
cat > tests/contracts/test_privacy.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.contracts.errors import (
    CorpusSafetyError,
)
from l9_debt_resolver.contracts.privacy import (
    validate_corpus_safe_document,
)
@pytest.mark.parametrize(
    "document",
    [
        {"raw_log": "failure"},
        {"source_content": "print('x')"},
        {"patch": "diff --git"},
        {"developer_email": "dev@example.com"},
        {"value": "Bearer abcdefghijklmnop"},
        {"value": "/home/alice/project/app.py"},
    ],
)
def test_sensitive_corpus_data_is_rejected(
    document: dict[str, object],
) -> None:
    with pytest.raises(CorpusSafetyError):
        validate_corpus_safe_document(document)
def test_aggregate_event_data_is_allowed() -> None:
    validate_corpus_safe_document(
        {
            "failure_fingerprint": (
                "failure_" + "a" * 64
            ),
            "terminal_state": "repeated_failure",
            "changed_file_count": 2,
            "finding_ids": ["finding:1"],
        }
    )
EOF
cat > tests/runtime/test_attempt_lifecycle.py <<'EOF'
from __future__ import annotations
import pytest
from l9_debt_resolver.contracts.errors import (
    AttemptTransitionError,
)
from l9_debt_resolver.contracts.models import (
    ResolverState,
)
from l9_debt_resolver.runtime.attempts import (
    create_attempt,
)
def test_valid_attempt_lifecycle() -> None:
    attempt = create_attempt(
        failure_fingerprint=(
            "failure_" + "a" * 64
        ),
        attempt_number=1,
        original_run_id="100",
        created_at="2026-07-19T00:00:00Z",
    )
    acquired = attempt.transition(
        ResolverState.EVIDENCE_ACQUIRED,
        updated_at="2026-07-19T00:01:00Z",
    )
    classified = acquired.transition(
        ResolverState.CLASSIFIED,
        classification_id=(
            "classification_" + "b" * 64
        ),
        updated_at="2026-07-19T00:02:00Z",
    )
    assert classified.state == ResolverState.CLASSIFIED
def test_illegal_transition_is_rejected() -> None:
    attempt = create_attempt(
        failure_fingerprint=(
            "failure_" + "a" * 64
        ),
        attempt_number=1,
        original_run_id="100",
        created_at="2026-07-19T00:00:00Z",
    )
    with pytest.raises(
        AttemptTransitionError
    ):
        attempt.transition(
            ResolverState.CLEAN,
            updated_at="2026-07-19T00:01:00Z",
        )
def test_terminal_state_cannot_transition() -> None:
    attempt = create_attempt(
        failure_fingerprint=(
            "failure_" + "a" * 64
        ),
        attempt_number=1,
        original_run_id="100",
        created_at="2026-07-19T00:00:00Z",
    )
    terminal = attempt.transition(
        ResolverState.INSUFFICIENT_LOG_EVIDENCE,
        updated_at="2026-07-19T00:01:00Z",
    )
    with pytest.raises(
        AttemptTransitionError
    ):
        terminal.transition(
            ResolverState.EVIDENCE_ACQUIRED,
            updated_at="2026-07-19T00:02:00Z",
        )
EOF
cat > tests/runtime/test_capabilities.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.runtime.capabilities import (
    resolver_capabilities,
)
def test_P0_capability_boundary() -> None:
    result = resolver_capabilities()
    capabilities = result["capabilities"]
    assert result["phase"] == "RESOLVER-P0"
    assert capabilities["contract_validation"] is True
    assert capabilities["typed_CI_evidence"] is True
    assert capabilities["attempt_lifecycle"] is True
    assert capabilities["terminal_states"] is True
    assert capabilities["corpus_safe_events"] is True
    assert capabilities["failed_log_acquisition"] is False
    assert capabilities["SDK_repository_correlation"] is False
    assert capabilities["bounded_remediation"] is False
    assert capabilities["CI_rerun_observation"] is False
    assert capabilities["automatic_merge"] is False
EOF
cat > tests/architecture/test_boundaries.py <<'EOF'
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED_IMPORTS = (
    "l9_debt_intelligence",
    "l9_debt_lsp",
    "pr_repair.internal",
    "pr_repair.private",
    "l9_ci.internal",
    "l9_ci.private",
)
PROHIBITED_REMOTE_BEHAVIOR = (
    "git push",
    "git checkout",
    "git switch",
    "gh run rerun",
    "merge_pull_request",
    "gh pr merge",
    "automatic_merge",
    "create_subprocess_shell",
    "shell=true",
)
def test_no_private_constellation_dependencies() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED_IMPORTS:
            assert term not in content, (
                f"{path} contains prohibited dependency {term}"
            )
def test_P0_has_no_remote_mutation_behavior() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED_REMOTE_BEHAVIOR:
            assert term not in content, (
                f"{path} contains prohibited P0 behavior {term}"
            )
EOF
###############################################################################
# 9. Documentation
###############################################################################
cat > README.md <<'EOF'
# Quantum-L9 CI Debt Resolver
`l9-ci-debt-resolver` is the evidence-first failure-diagnosis and bounded
recovery component of the Quantum-L9 CI constellation.
## Authority model
```text
actual failed CI log
        ↓
failed job metadata
        ↓
SDK repository evidence
        ↓
historical context

Historical context may support diagnosis. It cannot override current failed
logs.

RESOLVER-P0

P0 establishes:

* repository ownership boundaries;
* deterministic canonical identities;
* typed CI evidence;
* typed failure classifications;
* resolver attempt lifecycle;
* deterministic terminal states;
* corpus-safe resolution-event contracts;
* schema validation;
* package, CLI, tests, and CI foundations.

P0 does not acquire logs, inspect repositories, remediate code, mutate Git,
observe reruns, deliver Intelligence feedback, or delegate to PR_Repair.

Validation

python -m pip install -e '.[dev]'
pytest
ruff check .
mypy src
l9-debt-resolver capabilities

Contract validation

l9-debt-resolver validate \
  ci-run-evidence \
  evidence.json

Success invariant

Local diagnosis, local validation, commit creation, and push do not prove a
failure is resolved.

Only a successful CI rerun may produce clean.

Prohibited behavior

The Resolver does not:

* infer root cause from historical memory alone;
* classify from job names alone;
* weaken tests or policy gates;
* broaden patch scope without evidence;
* duplicate SDK semantic identities;
* retry identical strategies indefinitely;
* push protected branches;
* force-push;
* merge automatically.
    EOF

cat > ROADMAP.md <<‘EOF’

Resolver Roadmap

RESOLVER-P0 — Contract alignment

Status: Implemented

* repository ownership boundary
* dependency boundary
* canonical identity encoding
* typed CI evidence
* typed failure classification
* attempt lifecycle
* terminal states
* corpus-safe events
* schema validation
* package and CLI foundation

RESOLVER-P1 — Failed-log acquisition

Status: Planned

* failed-run acquisition
* failed-job acquisition
* authoritative failed-log acquisition
* bounded pagination
* bounded retry
* truncation detection
* provenance
* secret and path redaction

RESOLVER-P2 — Repository correlation

Status: Planned

* SDK repository snapshots
* stack-frame extraction
* SDK entity correlation
* related tests
* applicable contracts
* canonical finding correlation
* root-cause classification

RESOLVER-P3 — Bounded validation

Status: Planned

* remediation eligibility
* approval enforcement
* protected-path enforcement
* bounded transactional changes
* SDK validation plans
* original failure reproduction
* targeted tests
* graph-delta validation
* rollback

RESOLVER-P4 — Remote resolution loop

Status: Planned

* exact revision enforcement
* expected worktree enforcement
* deterministic repair branches
* deterministic commits
* explicit push authorization
* non-force push
* rerun dispatch
* bounded rerun observation
* repeated-failure detection
* terminal states

RESOLVER-P5 — Intelligence feedback

Status: Planned

* privacy-safe resolution events
* repository pseudonymization
* repeated-failure telemetry
* deterministic event identities
* durable outbox
* bounded retries
* dead-letter state
* corpus-safe provenance

RESOLVER-P6 — PR_Repair delegation

Status: Planned

* proposal-only delegation
* bounded privacy-safe context
* repository and path pseudonymization
* signed callbacks
* replay protection
* proposal scope validation
* proposal-to-remediation conversion
* retained Resolver authority
    EOF

cat > AGENTS.md <<‘EOF’

Resolver Agent Contract

Must

* retrieve actual failed logs before diagnosis;
* verify log completeness;
* preserve evidence provenance;
* cite evidence for every remediation;
* use SDK-owned repository semantics;
* use SDK-owned validation plans;
* preserve deterministic identities;
* enforce finite attempts;
* preserve terminal-state determinism;
* redact corpus-facing events;
* fail closed when evidence is incomplete.

Must not

* infer cause from historical memory alone;
* classify from job names alone;
* treat missing logs as success;
* duplicate SDK schemas or canonical identities;
* weaken CI gates;
* disable tests;
* expand remediation beyond evidence;
* execute untrusted shell commands;
* retry identical failures indefinitely;
* claim clean before a successful rerun;
* force-push;
* push protected branches;
* merge automatically.
    EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-001-current-logs-are-authoritative.md <<‘EOF’

ADR-RESOLVER-001: Current failed CI logs are authoritative

* Status: Accepted
* Phase: RESOLVER-P0

Decision

Actual logs from the current failed CI execution are the primary root-cause
authority.

Job names and historical records may support diagnosis, but cannot replace or
override current failed-log evidence.
EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-002-sdk-owns-repository-semantics.md <<‘EOF’

ADR-RESOLVER-002: SDK owns repository semantics and validation

* Status: Accepted
* Phase: RESOLVER-P0

Decision

The Resolver consumes repository snapshots, entities, findings, contracts,
tests, validation plans, and validation results through public SDK contracts.

It does not recreate SDK semantic models or canonical identities.
EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-003-remediation-is-evidence-bounded.md <<‘EOF’

ADR-RESOLVER-003: Remediation is minimal and evidence-bounded

* Status: Accepted
* Phase: RESOLVER-P0

Decision

Every remediation operation must trace to current CI evidence and correlated
repository semantics.

The Resolver may not broaden scope merely because a wider refactor appears
desirable.
EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-004-repeated-failures-terminate.md <<‘EOF’

ADR-RESOLVER-004: Repeated identical failures terminate

* Status: Accepted
* Phase: RESOLVER-P0

Decision

When a rerun produces the same failure fingerprint, the current strategy
terminates as repeated_failure.

The Resolver does not conduct unbounded speculative retries.
EOF

cat > docs/architecture/ADRs/ADR-RESOLVER-005-events-are-corpus-safe.md <<‘EOF’

ADR-RESOLVER-005: Resolver events are correction-versioned and corpus-safe

* Status: Accepted
* Phase: RESOLVER-P0

Decision

Corpus-facing events contain aggregate classification, resolution, validation,
and hashed provenance data.

They exclude raw logs, source content, patches, paths, credentials, and
developer identity.
EOF

###############################################################################

10. CI workflow

###############################################################################

cat > .github/workflows/phase-0-foundation.yml <<‘EOF’
name: RESOLVER-P0 Foundation

on:
pull_request:
push:
branches:
- main

permissions:
contents: read

jobs:
foundation:
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
      from l9_debt_resolver.contracts.schema import SchemaRegistry
      root = Path("schemas/resolver")
      registry = SchemaRegistry(root)
      for path in sorted(root.glob("*.json")):
          value = json.loads(
              path.read_text(encoding="utf-8")
          )
          Draft202012Validator.check_schema(value)
          registry.document(path.resolve())
          print(path)
      PY
  - name: Tests
    run: |
      pytest \
        --cov=l9_debt_resolver \
        --cov-report=term-missing \
        --cov-fail-under=90
  - name: Ruff
    run: ruff check .
  - name: Mypy
    run: mypy src
  - name: Capabilities
    run: l9-debt-resolver capabilities

EOF

###############################################################################

11. Structural validation

###############################################################################

python3 -m compileall -q src

python3 - <<‘PY’
from future import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path.cwd()

required = [
“.l9/repo-spec.yaml”,
“.l9/resolver-foundation-contract.yaml”,
“.l9/phase-0-acceptance-gates.yaml”,
“pyproject.toml”,
“README.md”,
“ROADMAP.md”,
“AGENTS.md”,
“schemas/resolver/ci-run-evidence.schema.json”,
“schemas/resolver/ci-failure-classification.schema.json”,
“schemas/resolver/resolver-attempt.schema.json”,
“schemas/resolver/resolver-terminal-state.schema.json”,
“schemas/resolver/remediation-record.schema.json”,
“schemas/resolver/resolution-event.schema.json”,
“schemas/resolver/resolver-capabilities.schema.json”,
“src/l9_debt_resolver/init.py”,
“src/l9_debt_resolver/cli.py”,
“src/l9_debt_resolver/contracts/canonical.py”,
“src/l9_debt_resolver/contracts/models.py”,
“src/l9_debt_resolver/contracts/schema.py”,
“src/l9_debt_resolver/contracts/privacy.py”,
“src/l9_debt_resolver/runtime/attempts.py”,
“src/l9_debt_resolver/runtime/capabilities.py”,
“tests/contracts/test_canonical.py”,
“tests/contracts/test_models.py”,
“tests/contracts/test_schema.py”,
“tests/contracts/test_privacy.py”,
“tests/runtime/test_attempt_lifecycle.py”,
“tests/runtime/test_capabilities.py”,
“tests/architecture/test_boundaries.py”,
“.github/workflows/phase-0-foundation.yml”,
]

missing = [
item
for item in required
if not (root / item).is_file()
]

if missing:
raise SystemExit(
f”RESOLVER-P0 required files missing: {missing}”
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
“l9_debt_intelligence”,
“l9_debt_lsp”,
“pr_repair.internal”,
“pr_repair.private”,
“l9_ci.internal”,
“l9_ci.private”,
“git push”,
“git checkout”,
“git switch”,
“gh run rerun”,
“gh pr merge”,
“merge_pull_request”,
“create_subprocess_shell”,
“shell=true”,
)

for path in source.rglob(”*.py”):
content = path.read_text(
encoding=“utf-8”
).lower()

for term in prohibited:
    if term in content:
        raise SystemExit(
            f"prohibited P0 behavior {term!r} in {path}"
        )

capabilities = (
source
/ “runtime”
/ “capabilities.py”
).read_text(encoding=“utf-8”)

required_capabilities = (
‘“contract_validation”: True’,
‘“typed_CI_evidence”: True’,
‘“attempt_lifecycle”: True’,
‘“terminal_states”: True’,
‘“corpus_safe_events”: True’,
‘“failed_log_acquisition”: False’,
‘“SDK_repository_correlation”: False’,
‘“bounded_remediation”: False’,
‘“CI_rerun_observation”: False’,
‘“automatic_merge”: False’,
)

for capability in required_capabilities:
if capability not in capabilities:
raise SystemExit(
f”missing capability declaration: {capability}”
)

pyproject = (
root / “pyproject.toml”
).read_text(encoding=“utf-8”)

if ‘version = “0.1.0”’ not in pyproject:
raise SystemExit(
“P0 version must be 0.1.0 for the P1 migration”
)

init = (
source / “init.py”
).read_text(encoding=“utf-8”)

if ‘version = “0.1.0”’ not in init:
raise SystemExit(
“P0 package version must be 0.1.0”
)

repo_spec = (
root / “.l9/repo-spec.yaml”
).read_text(encoding=“utf-8”)

if “phase: RESOLVER-P0” not in repo_spec:
raise SystemExit(
“repo specification does not identify RESOLVER-P0”
)

print(
json.dumps(
{
“schema_version”: “l9.phase-build-result/v1”,
“repository”: (
“Quantum-L9/l9-ci-debt-resolver”
),
“version”: “0.1.0”,
“phase”: “RESOLVER-P0”,
“status”: “built”,
“contract_validation”: True,
“typed_CI_evidence”: True,
“typed_failure_classification”: True,
“deterministic_identities”: True,
“cross_schema_resolution”: True,
“attempt_lifecycle”: True,
“terminal_states”: True,
“corpus_safe_events”: True,
“failed_log_acquisition”: False,
“SDK_repository_correlation”: False,
“root_cause_classification”: False,
“bounded_remediation”: False,
“branch_mutation”: False,
“CI_rerun_observation”: False,
“automatic_merge”: False
},
sort_keys=True,
separators=(”,”, “:”),
)
)
PY

printf ‘\n’
printf ‘RESOLVER-P0 reconstruction complete.\n’
printf ‘\n’
printf ‘Implemented:\n’
printf ’  - authoritative repository specification\n’
printf ’  - ownership and dependency boundaries\n’
printf ’  - deterministic canonical identity encoding\n’
printf ’  - typed CI run evidence\n’
printf ’  - typed failure classification\n’
printf ’  - attempt lifecycle and transition enforcement\n’
printf ’  - deterministic terminal states\n’
printf ’  - corpus-safe resolution-event contract\n’
printf ’  - JSON Schema registry with cross-reference resolution\n’
printf ’  - installable Python package and CLI\n’
printf ’  - behavioral and architecture tests\n’
printf ’  - P1-compatible version and public interfaces\n’
printf ‘\n’
printf ‘Validate with:\n’
printf “  python -m pip install -e ‘.[dev]’\n”
printf ’  pytest\n’
printf ’  ruff check .\n’
printf ’  mypy src\n’
printf ’  l9-debt-resolver capabilities\n’
printf ‘\n’
printf ‘Then apply:\n’
printf ’  build-phase-1.sh\n’
printf ’  build-phase-2.sh\n’
printf ’  build-phase-3.sh\n’
printf ’  build-phase-4.sh\n’
printf ’  build-phase-5.sh\n’
printf ’  build-phase-6.sh\n’

:::
This version corrects the missing foundation and includes `pytest-asyncio`, which P1’s tests require.  It also preserves the exact roadmap labels and initial `0.1.0` version that the later scripts attempt to replace.