from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .models import (
    DeliveryResponse,
    FeedbackEvent,
)


class JSONFileFeedbackTransport:
    name = "json_file"

    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory

    async def deliver(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        return await asyncio.to_thread(
            self._deliver_sync,
            event,
        )

    def _deliver_sync(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = self._directory / f"{event.event_id}.json"
        encoded = (
            json.dumps(
                event.as_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if destination.exists():
            existing = destination.read_bytes()
            if existing == encoded:
                return DeliveryResponse(
                    transport=self.name,
                    status_code=409,
                    duplicate=True,
                    response_body_sha256=(hashlib.sha256(existing).hexdigest()),
                )
            raise RuntimeError("event identity collision in file transport")
        descriptor, temporary = tempfile.mkstemp(
            dir=self._directory,
            prefix=".feedback-event.",
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
        return DeliveryResponse(
            transport=self.name,
            status_code=201,
            duplicate=False,
            response_body_sha256=(hashlib.sha256(encoded).hexdigest()),
        )
