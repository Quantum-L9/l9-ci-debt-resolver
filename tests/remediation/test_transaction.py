from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from l9_debt_resolver.remediation.errors import (
    PatchPreconditionError,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    ReplaceTextOperation,
)
from l9_debt_resolver.remediation.policy import (
    RemediationBounds,
)
from l9_debt_resolver.remediation.transaction import (
    WorkspaceTransaction,
)


def plan(
    *,
    before: str,
    replacement: str,
) -> RemediationPlan:
    operation = ReplaceTextOperation(
        operation_id="operation_" + "a" * 64,
        path="src/app.py",
        expected_file_sha256=hashlib.sha256(before.encode("utf-8")).hexdigest(),
        expected_text="old",
        replacement_text=replacement,
        replacement_sha256=hashlib.sha256(replacement.encode("utf-8")).hexdigest(),
        evidence_ids=("evidence_" + "b" * 64,),
        justification="bounded change",
    )
    return RemediationPlan(
        plan_id="remediation_plan_" + "c" * 64,
        classification_id=("classification_" + "d" * 64),
        failure_fingerprint=("failure_" + "e" * 64),
        repository_snapshot_id="snapshot-1",
        repository_revision="f" * 40,
        remediation_class="bounded_source",
        evidence_ids=("evidence_" + "b" * 64,),
        justification="bounded change",
        operations=(operation,),
        expected_changed_paths=("src/app.py",),
        expected_package_boundaries=(),
        expected_contract_ids=(),
        expected_dependency_edges=(),
        validation_plan_id="validation-plan-1",
        approval=None,
    )


def test_transaction_applies_and_rolls_back(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src/app.py"
    target.parent.mkdir()
    before = "value = 'old'\n"
    target.write_text(before, encoding="utf-8")
    transaction = WorkspaceTransaction(
        workspace_root=tmp_path,
        bounds=RemediationBounds(),
    )
    transaction.apply(
        plan(
            before=before,
            replacement="new",
        )
    )
    assert "new" in target.read_text(encoding="utf-8")
    transaction.rollback()
    assert target.read_text(encoding="utf-8") == before


def test_hash_mismatch_rejects_patch(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src/app.py"
    target.parent.mkdir()
    target.write_text(
        "value = 'different'\n",
        encoding="utf-8",
    )
    transaction = WorkspaceTransaction(
        workspace_root=tmp_path,
        bounds=RemediationBounds(),
    )
    with pytest.raises(PatchPreconditionError):
        transaction.apply(
            plan(
                before="value = 'old'\n",
                replacement="new",
            )
        )
