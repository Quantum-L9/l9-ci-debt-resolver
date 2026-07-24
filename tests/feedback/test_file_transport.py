from __future__ import annotations

from pathlib import Path

import pytest

from l9_debt_resolver.feedback.file_transport import (
    JSONFileFeedbackTransport,
)
from l9_debt_resolver.feedback.models import (
    FeedbackEvent,
)


def event() -> FeedbackEvent:
    return FeedbackEvent(
        event_id="feedback_event_" + "a" * 64,
        idempotency_key=("feedback_idempotency_" + "b" * 64),
        event_type="resolution_succeeded",
        repository_pseudonym=("repository_" + "c" * 64),
        provider="github_actions",
        resolver_version="0.6.0",
        occurred_at="2026-07-19T00:00:00Z",
        failure={
            "fingerprint": "failure_" + "d" * 64,
            "category": "test_failure",
            "confidence_bucket": "high",
            "repeated": False,
            "attempt_number": 1,
            "observed_fingerprint_changed": None,
        },
        resolution={
            "terminal_state": "clean",
            "remediation_class": "bounded_source",
            "changed_file_count": 1,
            "changed_line_bucket": "1_10",
            "remote_push_performed": True,
            "rerun_observed": True,
        },
        validation={
            "result": "passed",
            "result_id_hash": "e" * 64,
            "step_count": 4,
            "duration_bucket": "10_60s",
            "graph_delta_accepted": True,
        },
        correlation={
            "capability_profile": ["python"],
            "finding_ids": [],
            "contract_ids": [],
            "language_families": ["python"],
            "entity_count": 1,
            "related_test_count": 1,
        },
        provenance={
            "snapshot_id_hash": "f" * 64,
            "evidence_id_hashes": ["1" * 64],
            "classification_id_hash": "2" * 64,
            "remediation_plan_id_hash": "3" * 64,
            "attempt_id_hash": "4" * 64,
            "rerun_id_hash": "5" * 64,
        },
        limitations=(),
    )


@pytest.mark.asyncio
async def test_file_transport_is_idempotent(
    tmp_path: Path,
) -> None:
    transport = JSONFileFeedbackTransport(directory=tmp_path)
    first = await transport.deliver(event())
    second = await transport.deliver(event())
    assert first.duplicate is False
    assert second.duplicate is True
