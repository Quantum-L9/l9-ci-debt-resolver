"""A classified-but-unrepaired failure must be expressible as a feedback event.

`build_feedback_event` needed a `ResolutionOutcome`, and the only thing that
built one was `remote_resolution_service`, on the remote-rerun path. So the
resolver's most common state -- it acquired a failed run, classified it, and did
not attempt a repair -- had no route to `l9.intelligence-feedback-event/v1` at
all. The projection existed; nothing could supply it an outcome.

These tests pin the two ways of getting that outcome wrong: claiming a remote
operation that never happened, and reporting an unattempted repair as a clean
no-op.
"""

from __future__ import annotations

from l9_debt_resolver.classification.models import (
    ClassificationSignal,
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import RepositoryCorrelation
from l9_debt_resolver.feedback.builder import build_feedback_event
from l9_debt_resolver.feedback.observation import (
    OBSERVED_ONLY_LIMITATION,
    observed_failure_outcome,
)
from l9_debt_resolver.feedback.privacy import validate_feedback_event

REPOSITORY = "Quantum-L9/l9-assurance"
RUN_ID = "33896871554"
KEY = b"k" * 32


def _classification() -> ClassificationTrace:
    return ClassificationTrace(
        classification_id="classification_" + "a" * 64,
        failure_fingerprint="failure_" + "b" * 64,
        category="lint_failure",
        confidence=0.45,
        evidence_ids=("evidence_" + "c" * 64,),
        matched_signals=(
            ClassificationSignal(
                signal="ruff_failure",
                category="lint_failure",
                weight=0.45,
                source="failed_log",
            ),
        ),
        failed_command="Run repository gates",
        repository_snapshot_id="snapshot_" + "d" * 32,
        affected_entities=(),
        related_tests=(),
        applicable_contracts=(),
        correlated_finding_ids=(),
        remediation_eligibility="unsupported",
        limitations=(),
    )


def _correlation() -> RepositoryCorrelation:
    return RepositoryCorrelation(
        correlation_id="correlation_" + "e" * 64,
        evidence_id="evidence_" + "c" * 64,
        repository_snapshot_id="snapshot_" + "d" * 32,
        capability_profile=(),
        stack_frames=(),
        repository_entities=(),
        related_tests=(),
        applicable_contracts=(),
        correlated_findings=(),
        unresolved_locations=(),
        limitations=(),
    )


def _outcome():
    return observed_failure_outcome(
        classification=_classification(),
        repository=REPOSITORY,
        run_id=RUN_ID,
        branch="main",
    )


class TestOutcome:
    def test_the_terminal_state_is_new_failure(self) -> None:
        """Not `remote_operation_failed`.

        `determine_terminal_state` reads a missing observed fingerprint as a
        failed remote operation. No remote operation was attempted here, so
        that verdict would be a false claim about something that never ran.
        """
        assert _outcome().terminal_state == "new_failure"

    def test_the_observed_fingerprint_is_the_one_that_was_observed(self) -> None:
        """`None` would mean a rerun produced nothing to compare.

        The fingerprint really was observed -- in the acquired log this
        classification came from -- so recording it as absent would understate
        what is known.
        """
        outcome = _outcome()
        assert outcome.observed_failure_fingerprint == (
            outcome.original_failure_fingerprint
        )

    def test_nothing_remote_is_claimed(self) -> None:
        outcome = _outcome()
        assert outcome.rerun_id is None
        assert outcome.commit_sha is None

    def test_the_outcome_says_no_resolution_was_attempted(self) -> None:
        assert OBSERVED_ONLY_LIMITATION in _outcome().limitations

    def test_the_outcome_is_deterministic(self) -> None:
        assert _outcome().outcome_id == _outcome().outcome_id


class TestEventProjection:
    def _event(self) -> dict[str, object]:
        return build_feedback_event(
            repository=REPOSITORY,
            pseudonym_key=KEY,
            provider="github_actions",
            resolver_version="0.7.0",
            attempt_number=1,
            classification_trace=_classification(),
            correlation=_correlation(),
            resolution_outcome=_outcome(),
            remediation_class=None,
            changed_file_count=0,
            changed_line_count=0,
            validation_result="not_run",
            validation_result_id=None,
            validation_step_count=0,
            validation_duration_bucket="unknown",
            graph_delta_accepted=None,
            remediation_plan_id=None,
        ).as_dict()

    def test_the_event_type_is_new_failure(self) -> None:
        assert self._event()["event_type"] == "new_failure"

    def test_an_unattempted_repair_is_not_reported_as_a_clean_no_op(self) -> None:
        """The distinction that matters to a learning consumer.

        `validation.result` must say `not_run`, not `passed`. A zero
        changed-file count paired with a passing validation would read as
        "repaired successfully by changing nothing", which would teach the
        corpus that this failure class resolves itself.
        """
        event = self._event()
        resolution = event["resolution"]
        validation = event["validation"]
        assert isinstance(resolution, dict) and isinstance(validation, dict)
        assert validation["result"] == "not_run"
        assert resolution["remediation_class"] is None
        assert resolution["remote_push_performed"] is False
        assert resolution["rerun_observed"] is False

    def test_the_observed_only_limitation_reaches_the_event(self) -> None:
        limitations = self._event()["limitations"]
        assert isinstance(limitations, list)
        assert OBSERVED_ONLY_LIMITATION in limitations

    def test_the_event_carries_no_raw_repository_name(self) -> None:
        import json

        assert "l9-assurance" not in json.dumps(self._event())

    def test_the_event_passes_the_privacy_validator(self) -> None:
        validate_feedback_event(self._event())

    def test_the_event_is_idempotent_for_the_same_observation(self) -> None:
        first, second = self._event(), self._event()
        assert first["idempotency_key"] == second["idempotency_key"]
        assert first["event_id"] == second["event_id"]
