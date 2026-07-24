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
