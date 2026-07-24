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
    re.compile(r"(?im)^##$begin:math:display$error$end:math:display$"),
    re.compile(r"(?im)^Error: Process completed with exit code"),
    re.compile(r"(?im)^Process completed with exit code"),
    re.compile(r"(?im)^##$begin:math:display$section$end:math:display$Finishing:"),
    re.compile(r"(?im)^Post job cleanup\."),
)


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
    if any(pattern.search(text) for pattern in _EXPLICIT_TRUNCATION_MARKERS):
        limitations.append("an explicit truncation marker was detected")
        return CompletenessAssessment(
            state="truncated",
            limitations=tuple(limitations),
        )
    if "\ufffd" in text:
        limitations.append("log contained undecodable byte sequences")
    terminal_marker_present = any(pattern.search(text) for pattern in _TERMINAL_MARKERS)
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
