from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    Approval,
    RemediationPlan,
    ReplaceTextOperation,
)


def load_remediation_plan(
    path: Path,
) -> RemediationPlan:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("remediation plan must be an object")
    if document.get("schema_version") != "l9.remediation-plan/v1":
        raise ValueError("unsupported remediation plan version")
    operations = tuple(
        _operation(value)
        for value in _list(
            document,
            "operations",
        )
    )
    approval_value = document.get("approval")
    approval = _approval(approval_value) if approval_value is not None else None
    return RemediationPlan(
        plan_id=_string(document, "plan_id"),
        classification_id=_string(
            document,
            "classification_id",
        ),
        failure_fingerprint=_string(
            document,
            "failure_fingerprint",
        ),
        repository_snapshot_id=_string(
            document,
            "repository_snapshot_id",
        ),
        repository_revision=_string(
            document,
            "repository_revision",
        ),
        remediation_class=_string(
            document,
            "remediation_class",
        ),
        evidence_ids=tuple(
            sorted(
                _string_list(
                    document,
                    "evidence_ids",
                )
            )
        ),
        justification=_string(
            document,
            "justification",
        ),
        operations=operations,
        expected_changed_paths=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_changed_paths",
                )
            )
        ),
        expected_package_boundaries=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_package_boundaries",
                )
            )
        ),
        expected_contract_ids=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_contract_ids",
                )
            )
        ),
        expected_dependency_edges=tuple(
            sorted(
                _string_list(
                    document,
                    "expected_dependency_edges",
                )
            )
        ),
        validation_plan_id=_string(
            document,
            "validation_plan_id",
        ),
        approval=approval,
    )


def _operation(
    value: object,
) -> ReplaceTextOperation:
    document = _object(value)
    return ReplaceTextOperation(
        operation_id=_string(
            document,
            "operation_id",
        ),
        path=_string(document, "path"),
        expected_file_sha256=_string(
            document,
            "expected_file_sha256",
        ),
        expected_text=_string(
            document,
            "expected_text",
        ),
        replacement_text=_string(
            document,
            "replacement_text",
        ),
        replacement_sha256=_string(
            document,
            "replacement_sha256",
        ),
        evidence_ids=tuple(
            sorted(
                _string_list(
                    document,
                    "evidence_ids",
                )
            )
        ),
        justification=_string(
            document,
            "justification",
        ),
    )


def _approval(
    value: object,
) -> Approval:
    document = _object(value)
    return Approval(
        approval_id=_string(
            document,
            "approval_id",
        ),
        approved_paths=tuple(
            sorted(
                _string_list(
                    document,
                    "approved_paths",
                )
            )
        ),
        approved_at=_string(
            document,
            "approved_at",
        ),
        expires_at=_string(
            document,
            "expires_at",
        ),
    )


def _object(
    value: object,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def _list(
    document: dict[str, Any],
    key: str,
) -> list[object]:
    value = document.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array")
    return value


def _string(
    document: dict[str, Any],
    key: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _string_list(
    document: dict[str, Any],
    key: str,
) -> list[str]:
    return [str(value) for value in _list(document, key)]
