from __future__ import annotations

from pathlib import Path

import pytest

from l9_debt_resolver.feedback.delivery import (
    FeedbackDeliveryService,
)
from l9_debt_resolver.feedback.errors import (
    RetryableDeliveryError,
)
from l9_debt_resolver.feedback.models import (
    DeliveryResponse,
)
from l9_debt_resolver.feedback.outbox import (
    FeedbackOutbox,
)
from tests.feedback.test_file_transport import event


class FlakyTransport:
    name = "https"

    def __init__(self) -> None:
        self.calls = 0

    async def deliver(self, feedback_event):
        del feedback_event
        self.calls += 1
        if self.calls < 3:
            raise RetryableDeliveryError(
                "temporary failure",
                status_code=503,
                retry_after_seconds=0,
            )
        return DeliveryResponse(
            transport="https",
            status_code=202,
            duplicate=False,
            response_body_sha256="a" * 64,
        )


@pytest.mark.asyncio
async def test_retryable_delivery_succeeds(
    tmp_path: Path,
) -> None:
    transport = FlakyTransport()
    service = FeedbackDeliveryService(
        outbox=FeedbackOutbox(directory=tmp_path),
        transport=transport,
        maximum_attempts=5,
        initial_delay_seconds=0,
        maximum_delay_seconds=0,
    )
    receipt = await service.submit(event())
    assert receipt.status == "delivered"
    assert receipt.attempt_count == 3
    assert transport.calls == 3


class AlwaysFailTransport:
    name = "https"

    async def deliver(self, feedback_event):
        del feedback_event
        raise RetryableDeliveryError(
            "temporary failure",
            status_code=503,
            retry_after_seconds=0,
        )


@pytest.mark.asyncio
async def test_retry_exhaustion_dead_letters(
    tmp_path: Path,
) -> None:
    service = FeedbackDeliveryService(
        outbox=FeedbackOutbox(directory=tmp_path),
        transport=AlwaysFailTransport(),
        maximum_attempts=2,
        initial_delay_seconds=0,
        maximum_delay_seconds=0,
    )
    receipt = await service.submit(event())
    assert receipt.status == "dead_letter"
    assert receipt.attempt_count == 2
