from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)

from .models import (
    DeliveryReceipt,
    FeedbackEvent,
    OutboxRecord,
)


class FeedbackOutbox:
    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory

    def enqueue(
        self,
        event: FeedbackEvent,
        *,
        now: str,
    ) -> OutboxRecord:
        record = OutboxRecord(
            record_id=namespaced_identity(
                "feedback_outbox_",
                {
                    "event_id": event.event_id,
                    "idempotency_key": (event.idempotency_key),
                },
            ),
            state="pending",
            event=event,
            attempt_count=0,
            next_attempt_at=now,
            last_error_code=None,
            receipt=None,
            created_at=now,
            updated_at=now,
        )
        existing = self.get(record.record_id)
        if existing is not None:
            if existing.event.event_id != event.event_id:
                raise ValueError("outbox identity collision")
            return existing
        self._write(record)
        return record

    def get(
        self,
        record_id: str,
    ) -> OutboxRecord | None:
        path = self._path(record_id)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return _parse_record(value)

    def save(
        self,
        record: OutboxRecord,
    ) -> None:
        self._write(record)

    def pending(
        self,
    ) -> tuple[OutboxRecord, ...]:
        if not self._directory.exists():
            return ()
        records = []
        for path in sorted(self._directory.glob("feedback_outbox_*.json")):
            record = _parse_record(json.loads(path.read_text(encoding="utf-8")))
            if record.state in {
                "pending",
                "delivering",
            }:
                records.append(record)
        return tuple(records)

    def _path(
        self,
        record_id: str,
    ) -> Path:
        return self._directory / f"{record_id}.json"

    def _write(
        self,
        record: OutboxRecord,
    ) -> None:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = self._path(record.record_id)
        encoded = (
            json.dumps(
                record.as_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(
            dir=self._directory,
            prefix=".feedback-outbox.",
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


def _parse_record(
    value: Any,
) -> OutboxRecord:
    if not isinstance(value, dict):
        raise ValueError("outbox record must be an object")
    event_value = value["event"]
    event = FeedbackEvent(
        event_id=event_value["event_id"],
        idempotency_key=(event_value["idempotency_key"]),
        event_type=event_value["event_type"],
        repository_pseudonym=(event_value["repository_pseudonym"]),
        provider=event_value["provider"],
        resolver_version=(event_value["resolver_version"]),
        occurred_at=event_value["occurred_at"],
        failure=dict(event_value["failure"]),
        resolution=dict(event_value["resolution"]),
        validation=dict(event_value["validation"]),
        correlation=dict(event_value["correlation"]),
        provenance=dict(event_value["provenance"]),
        limitations=tuple(event_value["limitations"]),
    )
    receipt_value = value.get("receipt")
    receipt = (
        DeliveryReceipt(
            receipt_id=receipt_value["receipt_id"],
            event_id=receipt_value["event_id"],
            idempotency_key=(receipt_value["idempotency_key"]),
            transport=receipt_value["transport"],
            status=receipt_value["status"],
            attempt_count=int(receipt_value["attempt_count"]),
            provider_status=(
                int(receipt_value["provider_status"])
                if receipt_value.get("provider_status") is not None
                else None
            ),
            delivered_at=receipt_value.get("delivered_at"),
            response_body_sha256=(receipt_value.get("response_body_sha256")),
            limitations=tuple(receipt_value["limitations"]),
        )
        if isinstance(receipt_value, dict)
        else None
    )
    return OutboxRecord(
        record_id=value["record_id"],
        state=value["state"],
        event=event,
        attempt_count=int(value["attempt_count"]),
        next_attempt_at=value.get("next_attempt_at"),
        last_error_code=value.get("last_error_code"),
        receipt=receipt,
        created_at=value["created_at"],
        updated_at=value["updated_at"],
    )
