from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FeedbackEvent:
    event_id: str
    idempotency_key: str
    event_type: str
    repository_pseudonym: str
    provider: str
    resolver_version: str
    occurred_at: str
    failure: dict[str, Any]
    resolution: dict[str, Any]
    validation: dict[str, Any]
    correlation: dict[str, Any]
    provenance: dict[str, Any]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ("l9.intelligence-feedback-event/v1"),
            "event_id": self.event_id,
            "idempotency_key": self.idempotency_key,
            "event_type": self.event_type,
            "repository_pseudonym": (self.repository_pseudonym),
            "provider": self.provider,
            "resolver_version": self.resolver_version,
            "occurred_at": self.occurred_at,
            "failure": self.failure,
            "resolution": self.resolution,
            "validation": self.validation,
            "correlation": self.correlation,
            "provenance": self.provenance,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class DeliveryResponse:
    transport: str
    status_code: int | None
    duplicate: bool
    response_body_sha256: str | None


@dataclass(frozen=True)
class DeliveryReceipt:
    receipt_id: str
    event_id: str
    idempotency_key: str
    transport: str
    status: str
    attempt_count: int
    provider_status: int | None
    delivered_at: str | None
    response_body_sha256: str | None
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ("l9.feedback-delivery-receipt/v1"),
            "receipt_id": self.receipt_id,
            "event_id": self.event_id,
            "idempotency_key": self.idempotency_key,
            "transport": self.transport,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "provider_status": self.provider_status,
            "delivered_at": self.delivered_at,
            "response_body_sha256": (self.response_body_sha256),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class OutboxRecord:
    record_id: str
    state: str
    event: FeedbackEvent
    attempt_count: int
    next_attempt_at: str | None
    last_error_code: str | None
    receipt: DeliveryReceipt | None
    created_at: str
    updated_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ("l9.feedback-outbox-record/v1"),
            "record_id": self.record_id,
            "state": self.state,
            "event": self.event.as_dict(),
            "attempt_count": self.attempt_count,
            "next_attempt_at": self.next_attempt_at,
            "last_error_code": self.last_error_code,
            "receipt": (self.receipt.as_dict() if self.receipt else None),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
