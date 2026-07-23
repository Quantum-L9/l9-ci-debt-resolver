from __future__ import annotations

import pytest

from l9_debt_resolver.contracts.errors import (
    AttemptTransitionError,
)
from l9_debt_resolver.contracts.models import (
    ResolverState,
)
from l9_debt_resolver.runtime.attempts import (
    create_attempt,
)


def test_valid_attempt_lifecycle() -> None:
    attempt = create_attempt(
        failure_fingerprint=("failure_" + "a" * 64),
        attempt_number=1,
        original_run_id="100",
        created_at="2026-07-19T00:00:00Z",
    )
    acquired = attempt.transition(
        ResolverState.EVIDENCE_ACQUIRED,
        updated_at="2026-07-19T00:01:00Z",
    )
    classified = acquired.transition(
        ResolverState.CLASSIFIED,
        classification_id=("classification_" + "b" * 64),
        updated_at="2026-07-19T00:02:00Z",
    )
    assert classified.state == ResolverState.CLASSIFIED


def test_illegal_transition_is_rejected() -> None:
    attempt = create_attempt(
        failure_fingerprint=("failure_" + "a" * 64),
        attempt_number=1,
        original_run_id="100",
        created_at="2026-07-19T00:00:00Z",
    )
    with pytest.raises(AttemptTransitionError):
        attempt.transition(
            ResolverState.CLEAN,
            updated_at="2026-07-19T00:01:00Z",
        )


def test_terminal_state_cannot_transition() -> None:
    attempt = create_attempt(
        failure_fingerprint=("failure_" + "a" * 64),
        attempt_number=1,
        original_run_id="100",
        created_at="2026-07-19T00:00:00Z",
    )
    terminal = attempt.transition(
        ResolverState.INSUFFICIENT_LOG_EVIDENCE,
        updated_at="2026-07-19T00:01:00Z",
    )
    with pytest.raises(AttemptTransitionError):
        terminal.transition(
            ResolverState.EVIDENCE_ACQUIRED,
            updated_at="2026-07-19T00:02:00Z",
        )
