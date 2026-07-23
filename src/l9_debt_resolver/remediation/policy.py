from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath

from l9_debt_resolver.contracts.models import (
    FailureClassification,
)

from .errors import (
    ApprovalRequiredError,
    PatchBoundError,
    ProtectedPathError,
    RemediationNotEligibleError,
)
from .models import RemediationPlan


@dataclass(frozen=True)
class RemediationBounds:
    maximum_changed_files: int = 10
    maximum_changed_lines: int = 500
    maximum_operations: int = 50
    maximum_file_bytes: int = 5 * 1024 * 1024
    maximum_total_replacement_bytes: int = 10 * 1024 * 1024


PROTECTED_EXACT = {
    ".git",
    ".github/CODEOWNERS",
}
PROTECTED_PREFIXES = (
    ".git/",
    ".github/workflows/",
    ".l9/",
    "schemas/",
    "security/",
    "compliance/",
    "governance/",
)
ALLOWED_REMEDIATION_CLASSES = {
    "configuration",
    "dependency",
    "bounded_source",
    "generated_file",
}


def validate_remediation_policy(
    *,
    classification: FailureClassification,
    plan: RemediationPlan,
    bounds: RemediationBounds,
    now: datetime | None = None,
) -> None:
    if classification.remediation_eligibility == "unsupported":
        raise RemediationNotEligibleError(
            "classification is not eligible for remediation"
        )
    if classification.classification_id != plan.classification_id:
        raise RemediationNotEligibleError(
            "plan classification does not match diagnosis"
        )
    if classification.failure_fingerprint != plan.failure_fingerprint:
        raise RemediationNotEligibleError(
            "plan failure fingerprint does not match diagnosis"
        )
    if classification.repository_snapshot_id != plan.repository_snapshot_id:
        raise RemediationNotEligibleError("plan snapshot does not match classification")
    if plan.remediation_class not in ALLOWED_REMEDIATION_CLASSES:
        raise RemediationNotEligibleError("remediation class is not permitted")
    if not set(plan.evidence_ids).issubset(set(classification.evidence_ids)):
        raise RemediationNotEligibleError(
            "plan references evidence outside the classification"
        )
    paths = {operation.path for operation in plan.operations}
    if paths != set(plan.expected_changed_paths):
        raise PatchBoundError("operation paths do not match expected changed paths")
    if len(paths) > bounds.maximum_changed_files:
        raise PatchBoundError("remediation exceeds changed-file limit")
    if len(plan.operations) > bounds.maximum_operations:
        raise PatchBoundError("remediation exceeds operation limit")
    total_replacement_bytes = sum(
        len(operation.replacement_text.encode("utf-8")) for operation in plan.operations
    )
    if total_replacement_bytes > bounds.maximum_total_replacement_bytes:
        raise PatchBoundError("replacement data exceeds configured byte limit")
    for path in sorted(paths):
        validate_mutable_path(path)
    if classification.remediation_eligibility == "approval_required":
        _validate_approval(
            plan=plan,
            now=now or datetime.now(UTC),
        )


def validate_mutable_path(path: str) -> None:
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ProtectedPathError(f"unsafe remediation path: {path}")
    canonical = normalized.as_posix()
    if canonical in PROTECTED_EXACT:
        raise ProtectedPathError(f"protected remediation path: {canonical}")
    if canonical.startswith(PROTECTED_PREFIXES):
        raise ProtectedPathError(f"protected remediation path: {canonical}")


def _validate_approval(
    *,
    plan: RemediationPlan,
    now: datetime,
) -> None:
    approval = plan.approval
    if approval is None:
        raise ApprovalRequiredError("explicit remediation approval is required")
    expires_at = datetime.fromisoformat(approval.expires_at.replace("Z", "+00:00"))
    if expires_at <= now:
        raise ApprovalRequiredError("remediation approval has expired")
    missing = set(plan.expected_changed_paths) - set(approval.approved_paths)
    if missing:
        raise ApprovalRequiredError("approval does not cover all changed paths")
