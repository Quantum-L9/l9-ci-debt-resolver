from __future__ import annotations

from datetime import UTC, datetime

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
        classification_id=("classification_" + "a" * 64),
        failure_fingerprint=("failure_" + "b" * 64),
        category="test_failure",
        confidence=0.95,
        evidence_ids=("evidence_" + "c" * 64,),
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
        evidence_ids=("evidence_" + "c" * 64,),
        justification="fix assertion",
    )
    return RemediationPlan(
        plan_id="remediation_plan_" + "1" * 64,
        classification_id=("classification_" + "a" * 64),
        failure_fingerprint=("failure_" + "b" * 64),
        repository_snapshot_id="snapshot-1",
        repository_revision="a" * 40,
        remediation_class="bounded_source",
        evidence_ids=("evidence_" + "c" * 64,),
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
            classification=classification("approval_required"),
            plan=plan(),
            bounds=RemediationBounds(),
            now=datetime.now(UTC),
        )
