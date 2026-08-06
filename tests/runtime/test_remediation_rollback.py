from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from l9_debt_resolver.classification.models import (
    ClassificationSignal,
    ClassificationTrace,
)
from l9_debt_resolver.remediation.errors import (
    ValidationFailedError,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    ReplaceTextOperation,
)
from l9_debt_resolver.runtime.remediation_service import (
    RemediationService,
)
from l9_debt_resolver.validation.json_gateway import (
    JSONSDKValidationGateway,
)


def trace() -> ClassificationTrace:
    return ClassificationTrace(
        classification_id=("classification_" + "a" * 64),
        failure_fingerprint=("failure_" + "b" * 64),
        category="test_failure",
        confidence=0.95,
        evidence_ids=("evidence_" + "c" * 64,),
        matched_signals=(
            ClassificationSignal(
                signal="1 failed",
                category="test_failure",
                weight=0.95,
                source="failed_log",
            ),
        ),
        failed_command="pytest",
        repository_snapshot_id="snapshot-1",
        affected_entities=("entity-1",),
        related_tests=("test-1",),
        applicable_contracts=("contract-1",),
        correlated_finding_ids=(),
        remediation_eligibility="automatic",
        limitations=(),
    )


def plan(before: str) -> RemediationPlan:
    operation = ReplaceTextOperation(
        operation_id="operation_" + "f" * 64,
        path="src/app.py",
        expected_file_sha256=hashlib.sha256(before.encode("utf-8")).hexdigest(),
        expected_text="old",
        replacement_text="new",
        replacement_sha256=hashlib.sha256(b"new").hexdigest(),
        evidence_ids=("evidence_" + "c" * 64,),
        justification="fix test",
    )
    return RemediationPlan(
        plan_id="remediation_plan_" + "1" * 64,
        classification_id=("classification_" + "a" * 64),
        failure_fingerprint=("failure_" + "b" * 64),
        repository_snapshot_id="snapshot-1",
        repository_revision="2" * 40,
        remediation_class="bounded_source",
        evidence_ids=("evidence_" + "c" * 64,),
        justification="fix test",
        operations=(operation,),
        expected_changed_paths=("src/app.py",),
        expected_package_boundaries=(),
        expected_contract_ids=("contract-1",),
        expected_dependency_edges=(),
        validation_plan_id="validation-plan-1",
        approval=None,
    )


@pytest.mark.asyncio
async def test_validation_failure_rolls_back(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src/app.py"
    target.parent.mkdir()
    before = "value = 'old'\n"
    target.write_text(before, encoding="utf-8")
    SDK_document = {
        "schema_version": "l9.sdk-validation-document/v1",
        "validation_plan": {
            "validation_plan_id": "validation-plan-1",
            "repository_snapshot_id": "snapshot-1",
            "classification_id": ("classification_" + "a" * 64),
            "remediation_plan_id": ("remediation_plan_" + "1" * 64),
            "full_gate_required": False,
            "limitations": [],
            "steps": [
                {
                    "step_id": "original",
                    "kind": "original_failure",
                    "command": ["python3", "-c", "raise SystemExit(1)"],
                },
                {
                    "step_id": "test",
                    "kind": "targeted_test",
                    "command": ["python3", "-c", "raise SystemExit(0)"],
                },
                {
                    "step_id": "contract",
                    "kind": "affected_contract",
                    "command": ["python3", "-c", "raise SystemExit(0)"],
                },
                {"step_id": "graph", "kind": "graph_delta", "command": None},
            ],
        },
        "validation_result_id": "validation-result-1",
    }
    SDK_path = tmp_path / "sdk-validation.json"
    SDK_path.write_text(
        json.dumps(SDK_document),
        encoding="utf-8",
    )
    gateway = JSONSDKValidationGateway(document_path=SDK_path)
    with pytest.raises(ValidationFailedError):
        await RemediationService(validation_gateway=gateway).execute(
            workspace_root=tmp_path,
            classification_trace=trace(),
            remediation_plan=plan(before),
        )
    assert target.read_text(encoding="utf-8") == before
