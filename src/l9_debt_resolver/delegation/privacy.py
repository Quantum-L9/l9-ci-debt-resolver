from __future__ import annotations

import json
import re
from typing import Any

from .errors import DelegationPrivacyError

FORBIDDEN_KEYS = {
    "raw_log",
    "source_code",
    "source_content",
    "patch",
    "diff",
    "branch",
    "commit_message",
    "credential",
    "token",
    "authorization",
    "password",
    "secret",
    "environment",
    "developer",
    "actor",
    "email",
    "absolute_path",
    "repository_path",
}
SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(
        r"\b(?:ghp|github_pat|gho|ghu|ghs|ghr)_"
        r"[A-Za-z0-9_]{20,}\b"
    ),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
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
MAX_REQUEST_BYTES = 65536
MAX_PROPOSAL_BYTES = 262144
MAX_DEPTH = 12
MAX_STRING = 1048576


def validate_request(
    document: dict[str, Any],
) -> None:
    _validate_document(
        document,
        maximum_bytes=MAX_REQUEST_BYTES,
    )


def validate_proposal(
    document: dict[str, Any],
) -> None:
    _validate_document(
        document,
        maximum_bytes=MAX_PROPOSAL_BYTES,
    )


def _validate_document(
    document: dict[str, Any],
    *,
    maximum_bytes: int,
) -> None:
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > maximum_bytes:
        raise DelegationPrivacyError("delegation document exceeds size limit")
    _walk(
        document,
        path="$",
        depth=0,
    )


def _walk(
    value: Any,
    *,
    path: str,
    depth: int,
) -> None:
    if depth > MAX_DEPTH:
        raise DelegationPrivacyError(f"delegation document exceeds depth at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).casefold()
            if normalized in FORBIDDEN_KEYS:
                raise DelegationPrivacyError(
                    f"forbidden delegation key at {path}.{key}"
                )
            _walk(
                item,
                path=f"{path}.{key}",
                depth=depth + 1,
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
            )
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise DelegationPrivacyError(f"delegation string too large at {path}")
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(value):
                raise DelegationPrivacyError(f"sensitive delegation value at {path}")
        if "\n" in value and len(value.splitlines()) > 2000:
            raise DelegationPrivacyError(f"excessive multiline content at {path}")
        return
    if value is None or isinstance(
        value,
        (bool, int, float),
    ):
        return
    raise DelegationPrivacyError(f"unsupported delegation value at {path}")
