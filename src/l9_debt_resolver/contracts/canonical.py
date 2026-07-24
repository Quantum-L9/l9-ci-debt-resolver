from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import IdentityError


def canonical_json(value: object) -> bytes:
    """Encode deterministic identity material as canonical UTF-8 JSON."""
    normalized = _normalize(value)
    try:
        return json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise IdentityError(f"value cannot be canonically encoded: {error}") from error


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def namespaced_identity(
    prefix: str,
    value: object,
) -> str:
    if not prefix:
        raise IdentityError("identity prefix cannot be empty")
    if not prefix.endswith("_"):
        raise IdentityError("identity prefix must end with an underscore")
    return prefix + sha256_bytes(canonical_json(value))


def stable_text_hash(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _normalize(value: object) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise IdentityError("canonical object keys must be strings")
            result[key] = _normalize(item)
        return result
    if isinstance(value, tuple | list):
        return [_normalize(item) for item in value]
    if isinstance(value, set | frozenset):
        normalized = [_normalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: canonical_json(item),
        )
    if isinstance(value, float):
        if not math.isfinite(value):
            raise IdentityError("non-finite numbers are prohibited")
        return value
    if value is None or isinstance(
        value,
        (str, int, bool),
    ):
        return value
    raise IdentityError(f"unsupported canonical value: {type(value).__name__}")
