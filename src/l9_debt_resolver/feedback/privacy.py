from __future__ import annotations

import ipaddress
import json
import re
from typing import Any
from urllib.parse import urlsplit

from .errors import FeedbackPrivacyError

FORBIDDEN_KEY_FRAGMENTS = (
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "cookie",
    "source",
    "patch",
    "diff",
    "log",
    "stdout",
    "stderr",
    "branch",
    "commit_message",
    "actor",
    "developer",
    "email",
    "absolute_path",
    "repository_path",
    "environment",
)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
GITHUB_TOKEN = re.compile(r"\b(?:ghp|github_pat|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")
AWS_KEY = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
UNIX_PATH = re.compile(
    r"(?<![A-Za-z0-9_.-])/(?:home|Users|var|tmp|opt|workspace|github)/"
)
WINDOWS_PATH = re.compile(r"\b[A-Za-z]:\\(?:Users|Temp|workspace|runner)\\")
MAX_EVENT_BYTES = 65536
MAX_STRING_LENGTH = 2000
MAX_ARRAY_ITEMS = 500
MAX_DEPTH = 10


def validate_feedback_event(
    event: dict[str, Any],
) -> None:
    encoded = json.dumps(
        event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > MAX_EVENT_BYTES:
        raise FeedbackPrivacyError("feedback event exceeds maximum size")
    _validate_value(
        event,
        path="$",
        depth=0,
    )


def _validate_value(
    value: Any,
    *,
    path: str,
    depth: int,
) -> None:
    if depth > MAX_DEPTH:
        raise FeedbackPrivacyError(f"feedback event exceeds maximum depth at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).casefold()
            if any(fragment in normalized_key for fragment in FORBIDDEN_KEY_FRAGMENTS):
                raise FeedbackPrivacyError(f"forbidden feedback key at {path}.{key}")
            _validate_value(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_ITEMS:
            raise FeedbackPrivacyError(f"feedback array exceeds maximum size at {path}")
        for index, item in enumerate(value):
            _validate_value(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        _validate_string(value, path=path)
        return
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return
    raise FeedbackPrivacyError(f"unsupported feedback value at {path}")


def _validate_string(
    value: str,
    *,
    path: str,
) -> None:
    if len(value) > MAX_STRING_LENGTH:
        raise FeedbackPrivacyError(f"feedback string exceeds maximum size at {path}")
    patterns = (
        EMAIL,
        BEARER,
        GITHUB_TOKEN,
        AWS_KEY,
        PRIVATE_KEY,
        UNIX_PATH,
        WINDOWS_PATH,
    )
    for pattern in patterns:
        if pattern.search(value):
            raise FeedbackPrivacyError(f"sensitive feedback value detected at {path}")
    if "\n" in value and len(value.splitlines()) > 5:
        raise FeedbackPrivacyError(f"multiline content is prohibited at {path}")
    if _contains_ip_address(value):
        raise FeedbackPrivacyError(f"IP address detected at {path}")
    if _contains_credential_url(value):
        raise FeedbackPrivacyError(f"credential-bearing URL detected at {path}")


def _contains_ip_address(value: str) -> bool:
    candidates = re.findall(
        r"(?<![A-Za-z0-9:])"
        r"(?:\d{1,3}\.){3}\d{1,3}"
        r"(?![A-Za-z0-9:])",
        value,
    )
    for candidate in candidates:
        try:
            ipaddress.ip_address(candidate)
            return True
        except ValueError:
            continue
    return False


def _contains_credential_url(value: str) -> bool:
    for candidate in re.findall(
        r"https?://[^\s]+",
        value,
    ):
        parsed = urlsplit(candidate)
        if parsed.username or parsed.password:
            return True
    return False
