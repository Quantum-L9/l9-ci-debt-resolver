from __future__ import annotations

from datetime import UTC, datetime

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.contracts.models import (
    ResolverAttempt,
    ResolverState,
)


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def create_attempt(
    *,
    failure_fingerprint: str,
    attempt_number: int,
    original_run_id: str,
    evidence_ids: tuple[str, ...] = (),
    created_at: str | None = None,
) -> ResolverAttempt:
    timestamp = created_at or utc_now()
    attempt_id = namespaced_identity(
        "attempt_",
        {
            "failure_fingerprint": (failure_fingerprint),
            "attempt_number": attempt_number,
            "original_run_id": original_run_id,
        },
    )
    return ResolverAttempt(
        attempt_id=attempt_id,
        failure_fingerprint=(failure_fingerprint),
        attempt_number=attempt_number,
        state=ResolverState.CREATED,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        classification_id=None,
        remediation_plan_id=None,
        validation_result_id=None,
        original_run_id=original_run_id,
        rerun_id=None,
        created_at=timestamp,
        updated_at=timestamp,
        limitations=(),
    )
