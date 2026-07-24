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
        return sum(change.changed_line_count for change in self.changes)


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
            "schema_version": ("l9.remediation-execution-result/v1"),
            "remediation_id": self.remediation_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "changed_paths": list(self.changed_paths),
            "changed_line_count": self.changed_line_count,
            "validation_transcript": (self.validation_transcript),
            "rolled_back": self.rolled_back,
            "limitations": list(self.limitations),
        }
