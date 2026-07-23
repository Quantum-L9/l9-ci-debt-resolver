from __future__ import annotations

from datetime import UTC, datetime

from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import (
    RepositoryCorrelation,
)
from l9_debt_resolver.resolution.models import (
    ResolutionOutcome,
)

from .identity import (
    feedback_event_id,
    idempotency_key,
    repository_pseudonym,
    stable_hash,
)
from .models import FeedbackEvent
from .privacy import validate_feedback_event

TERMINAL_EVENT_TYPES = {
    "clean": "resolution_succeeded",
    "repeated_failure": "repeated_failure",
    "new_failure": "new_failure",
    "attempt_limit_reached": "attempt_limit_reached",
    "remote_operation_failed": "remote_operation_failed",
    "rerun_timeout": "rerun_timeout",
    "validation_failed": "validation_failed",
    "unsupported": "unsupported",
}


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def build_feedback_event(
    *,
    repository: str,
    pseudonym_key: bytes,
    provider: str,
    resolver_version: str,
    attempt_number: int,
    classification_trace: ClassificationTrace,
    correlation: RepositoryCorrelation,
    resolution_outcome: ResolutionOutcome,
    remediation_class: str | None,
    changed_file_count: int,
    changed_line_count: int | None,
    validation_result: str,
    validation_result_id: str | None,
    validation_step_count: int,
    validation_duration_bucket: str,
    graph_delta_accepted: bool | None,
    remediation_plan_id: str | None,
) -> FeedbackEvent:
    classification = classification_trace.classification
    event_type = TERMINAL_EVENT_TYPES.get(
        resolution_outcome.terminal_state,
        "unsupported",
    )
    repository_id = repository_pseudonym(
        repository=repository,
        pseudonym_key=pseudonym_key,
    )
    observed = resolution_outcome.observed_failure_fingerprint
    identity_material = {
        "repository_pseudonym": repository_id,
        "failure_fingerprint": (classification.failure_fingerprint),
        "attempt_number": attempt_number,
        "terminal_state": (resolution_outcome.terminal_state),
        "rerun_id_hash": stable_hash(resolution_outcome.rerun_id),
        "validation_result_id_hash": stable_hash(validation_result_id),
    }
    event_id = feedback_event_id(identity_material)
    event = FeedbackEvent(
        event_id=event_id,
        idempotency_key=idempotency_key(identity_material),
        event_type=event_type,
        repository_pseudonym=repository_id,
        provider=provider,
        resolver_version=resolver_version,
        occurred_at=utc_now(),
        failure={
            "fingerprint": (classification.failure_fingerprint),
            "category": classification.category,
            "confidence_bucket": _confidence_bucket(classification.confidence),
            "repeated": (resolution_outcome.terminal_state == "repeated_failure"),
            "attempt_number": attempt_number,
            "observed_fingerprint_changed": (
                None
                if observed is None
                else observed != classification.failure_fingerprint
            ),
        },
        resolution={
            "terminal_state": (resolution_outcome.terminal_state),
            "remediation_class": remediation_class,
            "changed_file_count": max(
                0,
                changed_file_count,
            ),
            "changed_line_bucket": (_changed_line_bucket(changed_line_count)),
            "remote_push_performed": (resolution_outcome.commit_sha is not None),
            "rerun_observed": (resolution_outcome.rerun_id is not None),
        },
        validation={
            "result": validation_result,
            "result_id_hash": stable_hash(validation_result_id),
            "step_count": max(
                0,
                validation_step_count,
            ),
            "duration_bucket": (validation_duration_bucket),
            "graph_delta_accepted": (graph_delta_accepted),
        },
        correlation={
            "capability_profile": list(sorted(set(correlation.capability_profile))),
            "finding_ids": list(
                sorted({reference.id for reference in (correlation.finding_references)})
            ),
            "contract_ids": list(
                sorted(
                    {reference.id for reference in (correlation.contract_references)}
                )
            ),
            "language_families": list(
                sorted({frame.framework for frame in (correlation.stack_frames)})
            ),
            "entity_count": len(correlation.entity_references),
            "related_test_count": len(correlation.related_test_references),
        },
        provenance={
            "snapshot_id_hash": stable_hash(correlation.repository_snapshot_id),
            "evidence_id_hashes": list(
                sorted(
                    stable_hash(value)
                    for value in (classification.evidence_ids)
                    if stable_hash(value) is not None
                )
            ),
            "classification_id_hash": (stable_hash(classification.classification_id)),
            "remediation_plan_id_hash": (stable_hash(remediation_plan_id)),
            "attempt_id_hash": stable_hash(resolution_outcome.attempt_id),
            "rerun_id_hash": stable_hash(resolution_outcome.rerun_id),
        },
        limitations=tuple(
            sorted(
                {
                    *classification.limitations,
                    *correlation.limitations,
                    *resolution_outcome.limitations,
                }
            )
        ),
    )
    document = event.as_dict()
    validate_feedback_event(document)
    return event


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


def _changed_line_bucket(
    count: int | None,
) -> str:
    if count is None:
        return "unknown"
    if count <= 0:
        return "0"
    if count <= 10:
        return "1_10"
    if count <= 50:
        return "11_50"
    if count <= 100:
        return "51_100"
    if count <= 250:
        return "101_250"
    if count <= 500:
        return "251_500"
    return "gt_500"
