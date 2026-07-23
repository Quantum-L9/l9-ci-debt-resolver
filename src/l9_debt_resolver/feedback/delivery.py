from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)

from .errors import (
    PermanentDeliveryError,
    RetryableDeliveryError,
)
from .models import (
    DeliveryReceipt,
    FeedbackEvent,
    OutboxRecord,
)
from .outbox import FeedbackOutbox
from .privacy import validate_feedback_event
from .protocol import FeedbackTransport


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


class FeedbackDeliveryService:
    def __init__(
        self,
        *,
        outbox: FeedbackOutbox,
        transport: FeedbackTransport,
        maximum_attempts: int = 5,
        initial_delay_seconds: float = 1.0,
        maximum_delay_seconds: float = 30.0,
    ) -> None:
        self._outbox = outbox
        self._transport = transport
        self._maximum_attempts = maximum_attempts
        self._initial_delay = initial_delay_seconds
        self._maximum_delay = maximum_delay_seconds

    async def submit(
        self,
        event: FeedbackEvent,
    ) -> DeliveryReceipt:
        validate_feedback_event(event.as_dict())
        record = self._outbox.enqueue(
            event,
            now=utc_now(),
        )
        if record.state == "delivered" and record.receipt is not None:
            return record.receipt
        return await self._deliver_record(record)

    async def drain(
        self,
    ) -> tuple[DeliveryReceipt, ...]:
        receipts = []
        for record in self._outbox.pending():
            receipts.append(await self._deliver_record(record))
        return tuple(receipts)

    async def _deliver_record(
        self,
        record: OutboxRecord,
    ) -> DeliveryReceipt:
        current = record
        while current.attempt_count < self._maximum_attempts:
            attempt_number = current.attempt_count + 1
            current = replace(
                current,
                state="delivering",
                attempt_count=attempt_number,
                updated_at=utc_now(),
            )
            self._outbox.save(current)
            try:
                response = await self._transport.deliver(current.event)
                receipt = _receipt(
                    event=current.event,
                    transport=response.transport,
                    attempt_count=attempt_number,
                    status=("duplicate" if response.duplicate else "delivered"),
                    provider_status=(response.status_code),
                    response_body_sha256=(response.response_body_sha256),
                    limitations=(),
                )
                current = replace(
                    current,
                    state="delivered",
                    next_attempt_at=None,
                    last_error_code=None,
                    receipt=receipt,
                    updated_at=utc_now(),
                )
                self._outbox.save(current)
                return receipt
            except PermanentDeliveryError as error:
                receipt = _receipt(
                    event=current.event,
                    transport=(self._transport.name),
                    attempt_count=attempt_number,
                    status="dead_letter",
                    provider_status=None,
                    response_body_sha256=None,
                    limitations=(type(error).__name__,),
                )
                current = replace(
                    current,
                    state="dead_letter",
                    next_attempt_at=None,
                    last_error_code=(type(error).__name__),
                    receipt=receipt,
                    updated_at=utc_now(),
                )
                self._outbox.save(current)
                return receipt
            except RetryableDeliveryError as error:
                if attempt_number >= self._maximum_attempts:
                    receipt = _receipt(
                        event=current.event,
                        transport=(self._transport.name),
                        attempt_count=attempt_number,
                        status="dead_letter",
                        provider_status=(error.status_code),
                        response_body_sha256=None,
                        limitations=("retry_attempts_exhausted",),
                    )
                    current = replace(
                        current,
                        state="dead_letter",
                        next_attempt_at=None,
                        last_error_code=(type(error).__name__),
                        receipt=receipt,
                        updated_at=utc_now(),
                    )
                    self._outbox.save(current)
                    return receipt
                delay = (
                    error.retry_after_seconds
                    if (error.retry_after_seconds is not None)
                    else self._delay_seconds(
                        current.event,
                        attempt_number,
                    )
                )
                next_attempt = (
                    (datetime.now(UTC) + timedelta(seconds=delay))
                    .isoformat()
                    .replace(
                        "+00:00",
                        "Z",
                    )
                )
                current = replace(
                    current,
                    state="pending",
                    next_attempt_at=next_attempt,
                    last_error_code=(type(error).__name__),
                    updated_at=utc_now(),
                )
                self._outbox.save(current)
                await asyncio.sleep(delay)
        raise AssertionError("delivery loop exited without a receipt")

    def _delay_seconds(
        self,
        event: FeedbackEvent,
        attempt_number: int,
    ) -> float:
        exponential = min(
            self._maximum_delay,
            self._initial_delay * (2 ** (attempt_number - 1)),
        )
        deterministic_fraction = (int(event.event_id[-8:], 16) % 1000) / 1000.0
        jitter = min(
            0.25 * exponential,
            deterministic_fraction,
        )
        return min(
            self._maximum_delay,
            exponential + jitter,
        )


def _receipt(
    *,
    event: FeedbackEvent,
    transport: str,
    attempt_count: int,
    status: str,
    provider_status: int | None,
    response_body_sha256: str | None,
    limitations: tuple[str, ...],
) -> DeliveryReceipt:
    delivered_at = (
        utc_now()
        if status
        in {
            "delivered",
            "duplicate",
        }
        else None
    )
    receipt_id = namespaced_identity(
        "feedback_receipt_",
        {
            "event_id": event.event_id,
            "idempotency_key": (event.idempotency_key),
            "transport": transport,
            "status": status,
            "attempt_count": attempt_count,
            "provider_status": provider_status,
        },
    )
    return DeliveryReceipt(
        receipt_id=receipt_id,
        event_id=event.event_id,
        idempotency_key=(event.idempotency_key),
        transport=transport,
        status=status,
        attempt_count=attempt_count,
        provider_status=provider_status,
        delivered_at=delivered_at,
        response_body_sha256=(response_body_sha256),
        limitations=tuple(sorted(set(limitations))),
    )
