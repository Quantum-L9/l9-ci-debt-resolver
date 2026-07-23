from __future__ import annotations

from typing import Protocol

from .models import PRRepairRequest


class PRRepairTransport(Protocol):
    name: str

    async def deliver(
        self,
        request: PRRepairRequest,
    ) -> str:
        """Deliver a request and return a transport receipt identity."""
