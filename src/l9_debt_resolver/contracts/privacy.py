from __future__ import annotations

import json
import re
from typing import Any

from .errors import CorpusSafetyError

FORBIDDEN_KEY_FRAGMENTS = (
    "raw_log",
    "source_code",
    "source_content",
    "patch",
    "diff",
    "credential",
    "authorization",
    "password",
    "secret",
    "developer",
    "actor",
    "email",
    "absolute_path",
    "repository_path",
    "branch",
    "commit_message",
    "environment",
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(
        r"\b(?:ghp|github_pat|gho|ghu|ghs|ghr)_"
        r"[A-Za-z0-9_]{20,}\b"
    ),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"\b[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    re.compile(
        r"(?<![A-Za-z0-9_.-])/"
        r"(?:home|Users|tmp|var|workspace|github)/"
    ),
    re.compile(
        r"\b[A-Za-z]:\\"
        r"(?:Users|Temp|workspace|runner)\\"
    ),
)


def validate_corpus_safe_document(
    document: dict[str, Any],
    *,
    maximum_bytes: int = 65536,
) -> None:
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > maximum_bytes:
        raise CorpusSafetyError("corpus-safe document exceeds byte limit")
    _walk(document, path="$", depth=0)


def _walk(
    value: Any,
    *,
    path: str,
    depth: int,
) -> None:
    if depth > 10:
        raise CorpusSafetyError(f"document exceeds depth limit at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).casefold()
            if any(fragment in normalized for fragment in FORBIDDEN_KEY_FRAGMENTS):
                raise CorpusSafetyError(f"forbidden corpus key at {path}.{key}")
            _walk(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        if len(value) > 500:
            raise CorpusSafetyError(f"array exceeds limit at {path}")
        for index, item in enumerate(value):
            _walk(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        if len(value) > 4000:
            raise CorpusSafetyError(f"string exceeds limit at {path}")
        for pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                raise CorpusSafetyError(f"sensitive value at {path}")
        if "\n" in value and len(value.splitlines()) > 5:
            raise CorpusSafetyError(f"multiline content prohibited at {path}")
        return
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return
    raise CorpusSafetyError(f"unsupported value at {path}")
