from __future__ import annotations

from l9_debt_resolver.resolution.terminal import (
    determine_terminal_state,
)


def test_success_is_clean() -> None:
    assert (
        determine_terminal_state(
            rerun_conclusion="success",
            original_fingerprint=("failure_" + "a" * 64),
            observed_fingerprint=None,
        )
        == "clean"
    )


def test_same_fingerprint_is_repeated_failure() -> None:
    fingerprint = "failure_" + "a" * 64
    assert (
        determine_terminal_state(
            rerun_conclusion="failure",
            original_fingerprint=fingerprint,
            observed_fingerprint=fingerprint,
        )
        == "repeated_failure"
    )


def test_different_fingerprint_is_new_failure() -> None:
    assert (
        determine_terminal_state(
            rerun_conclusion="failure",
            original_fingerprint=("failure_" + "a" * 64),
            observed_fingerprint=("failure_" + "b" * 64),
        )
        == "new_failure"
    )
