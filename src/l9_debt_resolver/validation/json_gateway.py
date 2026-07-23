from __future__ import annotations

import json
from pathlib import Path

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
        document = json.loads(document_path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("SDK validation document must be an object")
        if document.get("schema_version") != "l9.sdk-validation-document/v1":
            raise ValueError("unsupported SDK validation document")
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
            raise ValueError("SDK validation plan is missing")
        if plan.get("repository_snapshot_id") != repository_snapshot_id:
            raise ValueError("SDK validation snapshot mismatch")
        if (
            plan.get("classification_id")
            != classification_trace.classification.classification_id
        ):
            raise ValueError("SDK validation classification mismatch")
        if plan.get("remediation_plan_id") != remediation_plan.plan_id:
            raise ValueError("SDK validation remediation-plan mismatch")
        steps_value = plan.get("steps")
        if not isinstance(steps_value, list):
            raise ValueError("SDK validation steps must be an array")
        steps = tuple(_parse_step(value) for value in steps_value)
        kinds = {step.kind for step in steps}
        required = {
            "original_failure",
            "targeted_test",
            "affected_contract",
            "graph_delta",
        }
        if not required.issubset(kinds):
            raise ValueError("SDK validation plan lacks required steps")
        return SDKValidationPlan(
            validation_plan_id=str(plan["validation_plan_id"]),
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
            raise TypeError("validation step has an invalid type")
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
        changed_paths = tuple(sorted(transaction.changed_paths))
        expected_paths = set(remediation_plan.expected_changed_paths)
        unexpected = tuple(sorted(set(changed_paths) - expected_paths))
        return GraphDelta(
            before_snapshot_id=repository_snapshot_id,
            after_worktree_digest=(transaction.worktree_digest),
            changed_paths=changed_paths,
            changed_package_boundaries=tuple(
                sorted(remediation_plan.expected_package_boundaries)
            ),
            changed_contract_ids=tuple(sorted(remediation_plan.expected_contract_ids)),
            changed_dependency_edges=tuple(
                sorted(remediation_plan.expected_dependency_edges)
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
            limitations.append("graph delta contains unexpected changed paths")
        failed = any(result.result != "passed" for result in step_results)
        if failed or limitations:
            return (
                "failed",
                None,
                tuple(sorted(limitations)),
            )
        result_id = self._document.get("validation_result_id")
        if not isinstance(result_id, str):
            return (
                "unavailable",
                None,
                ("SDK validation result identity is missing",),
            )
        return (
            "passed",
            result_id,
            (),
        )


def _parse_step(value: object) -> ValidationStep:
    if not isinstance(value, dict):
        raise ValueError("SDK validation step must be an object")
    command_value = value.get("command")
    if command_value is None:
        command = None
    elif isinstance(command_value, list) and all(
        isinstance(item, str) for item in command_value
    ):
        command = tuple(command_value)
    else:
        raise ValueError("SDK validation command must be an array")
    return ValidationStep(
        step_id=str(value["step_id"]),
        kind=str(value["kind"]),
        command=command,
        contract_id=(
            str(value["contract_id"]) if value.get("contract_id") is not None else None
        ),
        test_id=(str(value["test_id"]) if value.get("test_id") is not None else None),
    )
