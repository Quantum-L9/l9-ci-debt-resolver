from __future__ import annotations

import hashlib
import hmac
from typing import Any

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)


def repository_pseudonym(
    *,
    repository: str,
    pseudonym_key: bytes,
) -> str:
    if len(pseudonym_key) < 32:
        raise ValueError("feedback pseudonym key must be at least 32 bytes")
    digest = hmac.new(
        pseudonym_key,
        repository.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"repository_{digest}"


def stable_hash(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def feedback_event_id(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "feedback_event_",
        material,
    )


def idempotency_key(
    material: dict[str, Any],
) -> str:
    return namespaced_identity(
        "feedback_idempotency_",
        material,
    )
