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
            "changed_package_boundaries": list(self.changed_package_boundaries),
            "changed_contract_ids": list(self.changed_contract_ids),
            "changed_dependency_edges": list(self.changed_dependency_edges),
            "unexpected_changed_paths": list(self.unexpected_changed_paths),
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
            "steps": [step.as_dict() for step in self.steps],
            "graph_delta": self.graph_delta.as_dict(),
            "result": self.result,
            "limitations": list(self.limitations),
        }
