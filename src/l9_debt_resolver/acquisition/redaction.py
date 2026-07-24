from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    classes: tuple[str, ...]


_PATTERN_DEFINITIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "PRIVATE_KEY",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
            r".*?"
            r"-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    (
        "GITHUB_TOKEN",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}"
            r"|github_pat_[A-Za-z0-9_]{20,})\b"
        ),
    ),
    (
        "AWS_ACCESS_KEY",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "BEARER_TOKEN",
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    ),
    (
        "ASSIGNMENT_SECRET",
        re.compile(
            r"(?i)\b("
            r"token|secret|password|passwd|api[_-]?key"
            r"|access[_-]?key|client[_-]?secret"
            r")\s*[:=]\s*"
            r"(?!\[REDACTED:)([\"']?)[^\s,\"']{8,}\2"
        ),
    ),
    (
        "EMAIL",
        re.compile(
            r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
            r"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?)+\b"
        ),
    ),
    (
        "WINDOWS_PATH",
        re.compile(
            r"(?<![A-Za-z0-9_.-])"
            r"[A-Za-z]:\\(?:[^\\\r\n\t ]+\\)*"
            r"[^\\\r\n\t ]*"
        ),
    ),
    (
        "UNIX_PATH",
        re.compile(
            r"(?<![A-Za-z0-9_.-])"
            r"/(?:home|Users|private|tmp|var|opt|workspace"
            r"|github/workspace)"
            r"(?:/[^\s:'\"<>|]+)+"
        ),
    ),
)


class LogRedactor:
    def __init__(
        self,
        repository_root: str | None = None,
    ) -> None:
        self._repository_root = (
            repository_root.rstrip("/\\") if repository_root else None
        )

    def redact(self, text: str) -> RedactionResult:
        value = text
        classes: set[str] = set()
        if self._repository_root:
            replacement = "[REDACTED:REPOSITORY_ROOT]"
            if self._repository_root in value:
                value = value.replace(
                    self._repository_root,
                    replacement,
                )
                classes.add("REPOSITORY_ROOT")
        for redaction_class, pattern in _PATTERN_DEFINITIONS:
            value, count = pattern.subn(
                f"[REDACTED:{redaction_class}]",
                value,
            )
            if count:
                classes.add(redaction_class)
        return RedactionResult(
            text=value,
            classes=tuple(sorted(classes)),
        )
