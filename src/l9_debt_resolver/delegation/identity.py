from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)


def stable_hash(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_id(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "pr_repair_request_",
        material,
    )


def request_idempotency_key(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "pr_repair_idempotency_",
        material,
    )


def callback_id(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "callback_",
        material,
    )


def new_nonce() -> str:
    return secrets.token_hex(32)


def path_token(
    *,
    repository_path: str,
    path_key: bytes,
) -> str:
    if len(path_key) < 32:
        raise ValueError("path-token key must be at least 32 bytes")
    digest = hmac.new(
        path_key,
        repository_path.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"path_{digest}"


def proposal_signature(
    *,
    unsigned_document: dict[str, Any],
    callback_key: bytes,
) -> str:
    if len(callback_key) < 32:
        raise ValueError("callback key must be at least 32 bytes")
    canonical = json.dumps(
        unsigned_document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(
        callback_key,
        canonical,
        hashlib.sha256,
    ).hexdigest()


def verify_proposal_signature(
    *,
    unsigned_document: dict[str, Any],
    signature: str,
    callback_key: bytes,
) -> bool:
    expected = proposal_signature(
        unsigned_document=unsigned_document,
        callback_key=callback_key,
    )
    return hmac.compare_digest(
        expected,
        signature,
    )
