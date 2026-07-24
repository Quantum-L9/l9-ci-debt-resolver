from __future__ import annotations

import pytest

from l9_debt_resolver.classification.engine import (
    RootCauseClassifier,
)
from l9_debt_resolver.correlation.models import (
    RepositoryCorrelation,
)
from tests.correlation.test_service import bundle


def correlation() -> RepositoryCorrelation:
    return RepositoryCorrelation(
        correlation_id="correlation_" + "c" * 64,
        evidence_id="evidence_" + "a" * 64,
        repository_snapshot_id="snapshot-1",
        stack_frames=(),
        repository_entities=(),
        related_tests=(),
        applicable_contracts=(),
        correlated_findings=(),
        unresolved_locations=(),
        limitations=(),
    )


@pytest.mark.asyncio
async def test_test_failure_classification() -> None:
    value = bundle()
    result = await RootCauseClassifier().classify(
        bundle=value,
        correlation=correlation(),
    )
    assert result.category == "test_failure"
    assert result.failure_fingerprint.startswith("failure_")
    assert result.evidence_ids == (value.evidence.evidence_id,)


@pytest.mark.asyncio
async def test_infrastructure_is_not_automatic() -> None:
    value = bundle()
    value = type(value)(
        repository=value.repository,
        revision=value.revision,
        evidence=value.evidence,
        redacted_log=(
            "The hosted runner lost communication\n"
            "Error: Process completed with exit code 1.\n"
        ),
        failed_job=value.failed_job,
    )
    result = await RootCauseClassifier().classify(
        bundle=value,
        correlation=correlation(),
    )
    assert result.category == "infrastructure"
    assert result.remediation_eligibility == "unsupported"


@pytest.mark.asyncio
async def test_unknown_failure_is_unsupported() -> None:
    value = bundle()
    value = type(value)(
        repository=value.repository,
        revision=value.revision,
        evidence=value.evidence,
        redacted_log=("unknown failure\nError: Process completed with exit code 1.\n"),
        failed_job=value.failed_job,
    )
    result = await RootCauseClassifier().classify(
        bundle=value,
        correlation=correlation(),
    )
    assert result.category == "unsupported"
    assert result.remediation_eligibility == "unsupported"
