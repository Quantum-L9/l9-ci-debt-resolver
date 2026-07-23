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
        SDK_plan = await self._gateway.create_validation_plan(
            repository_snapshot_id=(remediation_plan.repository_snapshot_id),
            classification_trace=classification_trace,
            remediation_plan=remediation_plan,
        )
        step_results = []
        for step in SDK_plan.steps:
            result = await self._gateway.execute_validation_step(
                workspace_root=workspace_root,
                step=step,
            )
            step_results.append(result)
            if result.result != "passed":
                break
        graph_delta = await self._gateway.calculate_graph_delta(
            repository_snapshot_id=(remediation_plan.repository_snapshot_id),
            transaction=transaction,
            remediation_plan=remediation_plan,
        )
        (
            result,
            validation_result_id,
            limitations,
        ) = await self._gateway.finalize_validation(
            validation_plan_id=(SDK_plan.validation_plan_id),
            step_results=tuple(step_results),
            graph_delta=graph_delta,
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
            "validation_plan_id": (SDK_plan.validation_plan_id),
            "validation_result_id": (validation_result_id),
            "steps": [step.as_dict() for step in step_results],
            "graph_delta": graph_delta.as_dict(),
            "result": result,
        }
        return ValidationTranscript(
            transcript_id=namespaced_identity(
                "validation_transcript_",
                transcript_material,
            ),
            validation_plan_id=(SDK_plan.validation_plan_id),
            validation_result_id=(validation_result_id),
            steps=tuple(step_results),
            graph_delta=graph_delta,
            result=result,
            limitations=all_limitations,
        )
