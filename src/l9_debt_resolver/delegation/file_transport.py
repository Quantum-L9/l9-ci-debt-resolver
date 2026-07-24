from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .models import PRRepairRequest


class JSONFilePRRepairTransport:
    name = "json_file"

    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory

    async def deliver(
        self,
        request: PRRepairRequest,
    ) -> str:
        return await asyncio.to_thread(
            self._deliver_sync,
            request,
        )

    def _deliver_sync(
        self,
        request: PRRepairRequest,
    ) -> str:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = self._directory / f"{request.request_id}.json"
        encoded = (
            json.dumps(
                request.as_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if destination.exists():
            existing = destination.read_bytes()
            if existing != encoded:
                raise RuntimeError("delegation request identity collision")
            return hashlib.sha256(existing).hexdigest()
        descriptor, temporary = tempfile.mkstemp(
            dir=self._directory,
            prefix=".pr-repair-request.",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(
                descriptor,
                "wb",
            ) as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                destination,
            )
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return hashlib.sha256(encoded).hexdigest()
