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
        self._validation = ValidationService(validation_gateway)
        self._bounds = bounds or RemediationBounds()

    async def execute(
        self,
        *,
        workspace_root: Path,
        classification_trace: ClassificationTrace,
        remediation_plan: RemediationPlan,
    ) -> RemediationExecutionResult:
        classification = classification_trace.classification
        validate_remediation_policy(
            classification=classification,
            plan=remediation_plan,
            bounds=self._bounds,
        )
        transaction = WorkspaceTransaction(
            workspace_root=workspace_root,
            bounds=self._bounds,
        )
        transaction_result = transaction.apply(remediation_plan)
        try:
            transcript = await self._validation.validate(
                workspace_root=str(workspace_root.resolve()),
                classification_trace=(classification_trace),
                remediation_plan=remediation_plan,
                transaction=transaction_result,
            )
            if transcript.result != "passed":
                raise ValidationFailedError("SDK validation rejected remediation")
            if transcript.graph_delta.unexpected_changed_paths:
                raise ValidationFailedError("graph delta contains unexpected paths")
            transaction.commit()
            remediation_id = namespaced_identity(
                "remediation_",
                {
                    "plan_id": remediation_plan.plan_id,
                    "classification_id": (classification.classification_id),
                    "changed_paths": list(transaction_result.changed_paths),
                    "validation_result_id": (transcript.validation_result_id),
                },
            )
            return RemediationExecutionResult(
                remediation_id=remediation_id,
                plan_id=remediation_plan.plan_id,
                status="validated",
                changed_paths=(transaction_result.changed_paths),
                changed_line_count=(transaction_result.changed_line_count),
                validation_transcript=(transcript.as_dict()),
                rolled_back=False,
                limitations=transcript.limitations,
            )
        except Exception:
            transaction.rollback()
            raise
