from __future__ import annotations

from l9_debt_resolver.acquisition.completeness import (
    _TERMINAL_MARKERS,
    assess_log_completeness,
)

# The real shape of a GitHub Actions job log: a UTF-8 BOM, then every line
# prefixed with the runner's own ISO-8601 timestamp. Every fixture in this
# module used to be untimestamped synthetic text, which is why the anchored
# terminal markers passed their tests and could never match a real log.
# Lines below are the verbatim shape observed on
# Quantum-L9/l9-assurance run 33922209358, job "Validate Python assurance
# plane (3.13)".
REAL_LOG_TAIL = (
    "﻿2026-09-04T21:41:02.6079788Z Current runner version: '2.337.0'\n"
    "2026-09-04T21:41:19.9264531Z ##[group]Run repository gates\n"
    "2026-09-04T21:41:20.2147612Z ##[error]Process completed with exit code 1.\n"
    "2026-09-04T21:41:20.2292611Z Post job cleanup.\n"
).encode()


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


def test_real_timestamped_actions_log_is_complete() -> None:
    """A real GitHub Actions job log must assess ``complete``.

    Regression for the defect where every terminal marker anchored with ``^``
    while every log line carries the runner's timestamp prefix, so no real log
    could ever be complete and acquisition always terminated
    ``insufficient_log_evidence``.
    """
    result = assess_log_completeness(
        raw=REAL_LOG_TAIL,
        content_length=len(REAL_LOG_TAIL),
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "complete"
    assert "no recognized terminal log marker was detected" not in result.limitations


def test_bracketed_markers_are_not_corrupted_regexes() -> None:
    """The ``##[error]`` and ``##[section]`` markers must be real regexes.

    Two of these patterns had their bracket literals replaced with LaTeX
    math delimiters, in which ``$`` is an end-of-string anchor, so neither
    could match anything. Assert on behaviour against the real line content
    rather than on the pattern text.
    """
    for line, expected in (
        ("##[error]Process completed with exit code 1.", True),
        ("##[section]Finishing: Run repository gates", True),
    ):
        assert any(p.search(line) for p in _TERMINAL_MARKERS) is expected, line


def test_marker_quoted_mid_line_does_not_terminate() -> None:
    """The ``^`` anchor must survive de-prefixing.

    A marker quoted inside a log message is not the log's own terminus, so
    stripping the runner prefix must not degrade into an unanchored search.
    """
    raw = (
        "﻿2026-09-04T21:41:02.0000000Z the build printed ##[error]Process "
        "completed with exit code 1. while retrying\n"
    ).encode()
    result = assess_log_completeness(
        raw=raw,
        content_length=len(raw),
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "possibly_truncated"


def test_timestamped_log_without_terminal_marker_is_uncertain() -> None:
    raw = (
        "﻿2026-09-04T21:41:02.6079788Z Current runner version: '2.337.0'\n"
        "2026-09-04T21:41:19.9264531Z ##[group]Run repository gates\n"
    ).encode()
    result = assess_log_completeness(
        raw=raw,
        content_length=len(raw),
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "possibly_truncated"


def test_untimestamped_log_still_assessed() -> None:
    """De-prefixing must not break logs that carry no runner prefix."""
    result = assess_log_completeness(
        raw=b"Post job cleanup.\n",
        content_length=None,
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "complete"


def test_timestamped_explicit_truncation_marker_is_truncated() -> None:
    raw = "﻿2026-09-04T21:41:02.0000000Z log output truncated\n".encode()
    result = assess_log_completeness(
        raw=raw,
        content_length=len(raw),
        exceeded_limit=False,
        download_complete=True,
    )
    assert result.state == "truncated"
