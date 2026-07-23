from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import DelegationReplayError


class CallbackNonceLedger:
    def __init__(
        self,
        *,
        path: Path,
    ) -> None:
        self._path = path

    def consume(
        self,
        *,
        request_id: str,
        nonce: str,
        proposal_id: str,
    ) -> None:
        document = self._load()
        consumed = document.setdefault(
            "consumed",
            {},
        )
        key = f"{request_id}:{nonce}"
        if key in consumed:
            raise DelegationReplayError("callback nonce has already been consumed")
        consumed[key] = proposal_id
        self._write(document)

    def _load(self) -> dict[str, object]:
        if not self._path.exists():
            return {
                "schema_version": ("l9.callback-nonce-ledger/v1"),
                "consumed": {},
            }
        value = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("callback nonce ledger must be an object")
        return value

    def _write(
        self,
        value: dict[str, object],
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        descriptor, temporary = tempfile.mkstemp(
            dir=self._path.parent,
            prefix=".callback-nonce.",
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
