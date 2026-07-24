from __future__ import annotations


def determine_terminal_state(
    *,
    rerun_conclusion: str | None,
    original_fingerprint: str,
    observed_fingerprint: str | None,
) -> str:
    if rerun_conclusion == "success":
        return "clean"
    if observed_fingerprint is None:
        return "remote_operation_failed"
    if observed_fingerprint == original_fingerprint:
        return "repeated_failure"
    return "new_failure"
