from __future__ import annotations

from l9_debt_resolver.feedback.delivery import (
    FeedbackDeliveryService,
)
from l9_debt_resolver.feedback.models import (
    DeliveryReceipt,
    FeedbackEvent,
)


class ResolverFeedbackService:
    def __init__(
        self,
        delivery: FeedbackDeliveryService,
    ) -> None:
        self._delivery = delivery

    async def publish(
        self,
        event: FeedbackEvent,
    ) -> DeliveryReceipt:
        return await self._delivery.submit(event)

    async def drain_outbox(
        self,
    ) -> tuple[DeliveryReceipt, ...]:
        return await self._delivery.drain()
