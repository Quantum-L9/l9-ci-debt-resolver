from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CompletenessAssessment:
    state: str
    limitations: tuple[str, ...]


_EXPLICIT_TRUNCATION_MARKERS = (
    re.compile(r"(?i)\blog output truncated\b"),
    re.compile(r"(?i)\btruncated to last \d+ lines\b"),
    re.compile(r"(?i)\bmaximum log length exceeded\b"),
    re.compile(r"(?i)\blog exceeded .* limit\b"),
    re.compile(r"(?i)\btoo much output\b"),
    re.compile(r"(?i)\boutput has been truncated\b"),
)
_TERMINAL_MARKERS = (
    re.compile(r"(?im)^##\[error\]"),
    re.compile(r"(?im)^Error: Process completed with exit code"),
    re.compile(r"(?im)^Process completed with exit code"),
    re.compile(r"(?im)^##\[section\]Finishing:"),
    re.compile(r"(?im)^Post job cleanup\."),
)
# Every line of a GitHub Actions job log is prefixed with the runner's own
# ISO-8601 timestamp and a single space:
#
#     2026-09-04T21:41:20.2147612Z ##[error]Process completed with exit code 1.
#
# The terminal markers above are anchored with ``^`` because a marker quoted
# inside a log message must not count as the log's own terminus. That anchor is
# correct and must stay -- but it can only ever match once the runner prefix is
# removed, so the prefix is stripped before assessment rather than the anchor
# being dropped. Without this, no GitHub Actions log can ever be assessed
# ``complete``, every acquisition reports ``possibly_truncated``, and the
# service terminates ``insufficient_log_evidence`` against the only provider it
# implements.
#
# The optional \ufeff covers the UTF-8 BOM the provider puts at the head of the
# first line; without it the first line alone keeps its prefix.
_RUNNER_TIMESTAMP = re.compile(
    r"(?m)^\ufeff?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z ",
)


def _strip_runner_timestamps(text: str) -> str:
    """Remove the runner's per-line timestamp prefix, leaving line content."""
    return _RUNNER_TIMESTAMP.sub("", text)


def assess_log_completeness(
    *,
    raw: bytes,
    content_length: int | None,
    exceeded_limit: bool,
    download_complete: bool,
) -> CompletenessAssessment:
    limitations: list[str] = []
    if not raw:
        return CompletenessAssessment(
            state="unavailable",
            limitations=("provider returned an empty log",),
        )
    text = raw.decode("utf-8", errors="replace")
    if exceeded_limit:
        limitations.append("log exceeded the configured per-job byte limit")
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if not download_complete:
        limitations.append("provider response did not complete successfully")
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if content_length is not None and content_length > len(raw):
        limitations.append("HTTP content length exceeds downloaded bytes")
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    # Marker matching runs against the de-prefixed text so the anchors in
    # _TERMINAL_MARKERS mean "at the start of a log line's content", which is
    # what they were written to mean. The undecodable-bytes check below stays on
    # the decoded text, because that is a question about the decode, not the
    # line shape.
    content = _strip_runner_timestamps(text)
    if any(pattern.search(content) for pattern in _EXPLICIT_TRUNCATION_MARKERS):
        limitations.append("an explicit truncation marker was detected")
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if "\ufffd" in text:
        limitations.append("log contained undecodable byte sequences")
    terminal_marker_present = any(
        pattern.search(content) for pattern in _TERMINAL_MARKERS
    )
    if not terminal_marker_present:
        limitations.append("no recognized terminal log marker was detected")
        return CompletenessAssessment(
            state="possibly_truncated",
            limitations=tuple(limitations),
        )
    return CompletenessAssessment(
        state="complete",
        limitations=tuple(limitations),
    )
