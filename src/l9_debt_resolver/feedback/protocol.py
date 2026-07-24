from __future__ import annotations

from typing import Protocol

from .models import (
    DeliveryResponse,
    FeedbackEvent,
)


class FeedbackTransport(Protocol):
    name: str

    async def deliver(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        """Deliver one privacy-validated feedback event."""
