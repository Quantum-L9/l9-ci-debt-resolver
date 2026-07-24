from __future__ import annotations

from l9_debt_resolver.acquisition.completeness import (
    assess_log_completeness,
)


def test_complete_log_requires_terminal_marker() -> None:
    result = assess_log_completeness(
        raw=(b"tests failed\nError: Process completed with exit code 1.\n"),
        content_length=None,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "complete"


def test_empty_log_is_unavailable() -> None:
    result = assess_log_completeness(
        raw=b"",
        content_length=0,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "unavailable"


def test_explicit_marker_is_truncated() -> None:
    result = assess_log_completeness(
        raw=b"log output truncated\n",
        content_length=None,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "truncated"


def test_content_length_mismatch_is_truncated() -> None:
    result = assess_log_completeness(
        raw=b"short",
        content_length=100,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "truncated"


def test_missing_terminal_marker_is_uncertain() -> None:
    result = assess_log_completeness(
        raw=b"failure happened",
        content_length=None,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "possibly_truncated"
