from __future__ import annotations

from datetime import UTC, datetime, timedelta

from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import (
    RepositoryCorrelation,
)
from l9_debt_resolver.feedback.identity import (
    repository_pseudonym,
)

from .errors import DelegationNotEligibleError
from .identity import (
    callback_id,
    new_nonce,
    path_token,
    request_id,
    request_idempotency_key,
    stable_hash,
)
from .models import PRRepairRequest
from .privacy import validate_request


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_pr_repair_request(
    *,
    repository: str,
    repository_pseudonym_key: bytes,
    path_token_key: bytes,
    allowed_paths: tuple[str, ...],
    classification_trace: ClassificationTrace,
    correlation: RepositoryCorrelation,
    normalized_error_signatures: tuple[str, ...],
    maximum_changed_files: int = 10,
    maximum_changed_lines: int = 500,
    maximum_operations: int = 50,
    expires_in_seconds: int = 900,
) -> tuple[
    PRRepairRequest,
    dict[str, str],
]:
    classification = classification_trace.classification
    if classification.remediation_eligibility not in {
        "approval_required",
        "unsupported",
    }:
        raise DelegationNotEligibleError(
            "automatic classifications should use Resolver direct remediation"
        )
    if not classification.evidence_ids:
        raise DelegationNotEligibleError("delegation requires evidence identities")
    if not correlation.repository_snapshot_id:
        raise DelegationNotEligibleError("delegation requires SDK snapshot identity")
    token_map = {
        path_token(
            repository_path=path,
            path_key=path_token_key,
        ): path
        for path in sorted(set(allowed_paths))
    }
    created = utc_now()
    expires = created + timedelta(seconds=expires_in_seconds)
    nonce = new_nonce()
    repository_id = repository_pseudonym(
        repository=repository,
        pseudonym_key=(repository_pseudonym_key),
    )
    identity_material = {
        "repository_pseudonym": repository_id,
        "failure_fingerprint": (classification.failure_fingerprint),
        "snapshot_id_hash": stable_hash(correlation.repository_snapshot_id),
        "classification_id_hash": stable_hash(classification.classification_id),
        "allowed_path_tokens": sorted(token_map),
    }
    request_identifier = request_id(identity_material)
    callback_identifier = callback_id(
        {
            "request_id": request_identifier,
            "nonce": nonce,
        }
    )
    request = PRRepairRequest(
        request_id=request_identifier,
        idempotency_key=(request_idempotency_key(identity_material)),
        repository_pseudonym=repository_id,
        failure_fingerprint=(classification.failure_fingerprint),
        classification={
            "category": classification.category,
            "confidence_bucket": (_confidence_bucket(classification.confidence)),
            "remediation_eligibility": (classification.remediation_eligibility),
            "failed_command_hash": (stable_hash(classification.failed_command)),
            "normalized_error_signatures": list(
                sorted(set(normalized_error_signatures))[:25]
            ),
        },
        repository_context={
            "snapshot_id_hash": stable_hash(correlation.repository_snapshot_id),
            "entity_ids": [
                reference.id for reference in (correlation.entity_references)
            ][:100],
            "finding_ids": [
                reference.id for reference in (correlation.finding_references)
            ][:100],
            "contract_ids": [
                reference.id for reference in (correlation.contract_references)
            ][:100],
            "related_test_ids": [
                reference.id for reference in (correlation.related_test_references)
            ][:100],
            "language_families": list(
                sorted({frame.framework for frame in (correlation.stack_frames)})
            ),
            "capability_profile": list(correlation.capability_profile),
            "allowed_path_tokens": list(sorted(token_map)),
        },
        constraints={
            "maximum_changed_files": (maximum_changed_files),
            "maximum_changed_lines": (maximum_changed_lines),
            "maximum_operations": (maximum_operations),
            "allowed_remediation_classes": [
                "configuration",
                "dependency",
                "bounded_source",
                "generated_file",
            ],
            "protected_paths_enforced": True,
            "validation_required": True,
            "remote_authority_granted": False,
        },
        callback={
            "callback_id": callback_identifier,
            "nonce": nonce,
            "signature_algorithm": ("HMAC-SHA256"),
        },
        created_at=created.isoformat().replace(
            "+00:00",
            "Z",
        ),
        expires_at=expires.isoformat().replace(
            "+00:00",
            "Z",
        ),
        limitations=tuple(
            sorted(
                {
                    *classification.limitations,
                    *correlation.limitations,
                }
            )
        ),
    )
    validate_request(request.as_dict())
    return request, token_map


def _confidence_bucket(
    confidence: float,
) -> str:
    if confidence >= 0.95:
        return "very_high"
    if confidence >= 0.90:
        return "high"
    if confidence >= 0.70:
        return "medium"
    return "low"
