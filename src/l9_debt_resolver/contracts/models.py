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
            raise ValueError("log_size_bytes cannot be negative")
        if self.log_completeness not in {
            "complete",
            "possibly_truncated",
            "truncated",
            "unavailable",
        }:
            raise ValueError("unsupported log completeness state")
        if self.authority_class not in {
            "RUNTIME_LOG",
            "CI_RESULT",
            "STATIC_ANALYZER",
            "COMPILER_SEMANTIC",
            "USER_ASSERTION",
        }:
            raise ValueError("unsupported evidence authority class")

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
            raise ValueError("classification confidence must be between 0 and 1")
        if not self.evidence_ids:
            raise ValueError("classification requires at least one evidence ID")
        if self.remediation_eligibility not in {
            "automatic",
            "approval_required",
            "unsupported",
        }:
            raise ValueError("unsupported remediation eligibility")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ("l9.ci-failure-classification/v1"),
            "classification_id": self.classification_id,
            "failure_fingerprint": (self.failure_fingerprint),
            "category": self.category,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "failed_command": self.failed_command,
            "repository_snapshot_id": (self.repository_snapshot_id),
            "affected_entities": list(self.affected_entities),
            "remediation_eligibility": (self.remediation_eligibility),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class ResolverTerminalState:
    state: ResolverState

    def __post_init__(self) -> None:
        if self.state not in TERMINAL_STATES:
            raise TerminalStateError(f"state is not terminal: {self.state}")

    def as_dict(self) -> dict[str, str]:
        return {
            "schema_version": ("l9.resolver-terminal-state/v1"),
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
            raise ValueError("attempt_number must be positive")

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
            rerun_id=(rerun_id if rerun_id is not None else self.rerun_id),
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
            "failure_fingerprint": (self.failure_fingerprint),
            "attempt_number": self.attempt_number,
            "state": self.state.value,
            "evidence_ids": list(self.evidence_ids),
            "classification_id": self.classification_id,
            "remediation_plan_id": (self.remediation_plan_id),
            "validation_result_id": (self.validation_result_id),
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
            raise TerminalStateError("resolution event requires a terminal state")
        if self.event_version < 1:
            raise ValueError("event_version must be positive")
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive")
        if self.changed_file_count < 0:
            raise ValueError("changed_file_count cannot be negative")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.resolution-event/v1",
            "event_id": self.event_id,
            "event_version": self.event_version,
            "repository_pseudonym": (self.repository_pseudonym),
            "provider": self.provider,
            "failure_fingerprint": (self.failure_fingerprint),
            "classification_category": (self.classification_category),
            "terminal_state": self.terminal_state.value,
            "attempt_number": self.attempt_number,
            "evidence_id_hashes": list(self.evidence_id_hashes),
            "finding_ids": list(self.finding_ids),
            "contract_ids": list(self.contract_ids),
            "changed_file_count": (self.changed_file_count),
            "changed_line_bucket": (self.changed_line_bucket),
            "validation_result": (self.validation_result),
            "occurred_at": self.occurred_at,
            "limitations": list(self.limitations),
        }
