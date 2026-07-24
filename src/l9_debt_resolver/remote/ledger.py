from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import AttemptLimitReachedError


class AttemptLedger:
    def __init__(
        self,
        *,
        path: Path,
        maximum_attempts: int = 2,
    ) -> None:
        self._path = path
        self._maximum_attempts = maximum_attempts

    def next_attempt(
        self,
        failure_fingerprint: str,
    ) -> int:
        document = self._load()
        attempts = document.setdefault(
            "attempts",
            {},
        )
        current = int(
            attempts.get(
                failure_fingerprint,
                0,
            )
        )
        if current >= self._maximum_attempts:
            raise AttemptLimitReachedError(
                "failure fingerprint reached the configured attempt limit"
            )
        next_value = current + 1
        attempts[failure_fingerprint] = next_value
        self._write(document)
        return next_value

    def count(
        self,
        failure_fingerprint: str,
    ) -> int:
        document = self._load()
        return int(
            document.get(
                "attempts",
                {},
            ).get(
                failure_fingerprint,
                0,
            )
        )

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {
                "schema_version": ("l9.remote-attempt-ledger/v1"),
                "attempts": {},
            }
        value = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("attempt ledger must be an object")
        return value

    def _write(
        self,
        value: dict[str, Any],
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        descriptor, temporary = tempfile.mkstemp(
            dir=self._path.parent,
            prefix=".attempt-ledger.",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
            ) as stream:
                json.dump(
                    value,
                    stream,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                self._path,
            )
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
