from __future__ import annotations

import hashlib

import pytest

from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
    FailureClassification,
)


def test_CI_evidence_round_trip_shape() -> None:
    evidence = CIRunEvidence(
        evidence_id="evidence_" + "a" * 64,
        provider="github_actions",
        run_id="100",
        job_id="200",
        job_name="tests",
        failed_command="pytest",
        conclusion="failure",
        log_sha256=hashlib.sha256(b"log").hexdigest(),
        log_size_bytes=3,
        log_completeness="complete",
        authority_class="RUNTIME_LOG",
        artifact_provenance={"source": "github_actions_job_log"},
        observed_at="2026-07-19T00:00:00Z",
        limitations=(),
    )
    document = evidence.as_dict()
    assert document["job_name"] == "tests"
    assert document["log_completeness"] == "complete"
    assert document["limitations"] == []


def test_invalid_log_completeness_is_rejected() -> None:
    with pytest.raises(ValueError):
        CIRunEvidence(
            evidence_id="evidence_" + "a" * 64,
            provider="github_actions",
            run_id="100",
            job_id="200",
            job_name="tests",
            failed_command=None,
            conclusion="failure",
            log_sha256="b" * 64,
            log_size_bytes=0,
            log_completeness="unknown",
            authority_class="RUNTIME_LOG",
            artifact_provenance={},
            observed_at="2026-07-19T00:00:00Z",
            limitations=(),
        )


def test_classification_requires_evidence() -> None:
    with pytest.raises(ValueError):
        FailureClassification(
            classification_id=("classification_" + "a" * 64),
            failure_fingerprint=("failure_" + "b" * 64),
            category="test_failure",
            confidence=0.95,
            evidence_ids=(),
            failed_command="pytest",
            repository_snapshot_id="snapshot-1",
            affected_entities=(),
            remediation_eligibility="automatic",
            limitations=(),
        )
