from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

from .errors import (
    DelegationPermanentError,
    DelegationRetryableError,
)
from .ledger import DelegationLedger
from .models import (
    DelegationRecord,
    PRRepairRequest,
)
from .protocol import PRRepairTransport


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


class PRRepairDelegationService:
    def __init__(
        self,
        *,
        ledger: DelegationLedger,
        transport: PRRepairTransport,
        maximum_attempts: int = 5,
    ) -> None:
        self._ledger = ledger
        self._transport = transport
        self._maximum_attempts = maximum_attempts

    async def submit(
        self,
        request: PRRepairRequest,
    ) -> DelegationRecord:
        record = self._ledger.create(request)
        if record.state in {
            "delivered",
            "awaiting_callback",
            "proposal_received",
            "proposal_accepted",
            "unsupported",
        }:
            return record
        current = record
        while current.delivery_attempts < self._maximum_attempts:
            attempt = current.delivery_attempts + 1
            try:
                await self._transport.deliver(request)
                current = replace(
                    current,
                    state="awaiting_callback",
                    delivery_attempts=attempt,
                    updated_at=utc_now(),
                )
                self._ledger.save(current)
                return current
            except DelegationPermanentError as error:
                current = replace(
                    current,
                    state="dead_letter",
                    delivery_attempts=attempt,
                    terminal_state=("delegation_delivery_failed"),
                    updated_at=utc_now(),
                    limitations=tuple(
                        sorted(
                            {
                                *current.limitations,
                                type(error).__name__,
                            }
                        )
                    ),
                )
                self._ledger.save(current)
                return current
            except DelegationRetryableError as error:
                if attempt >= self._maximum_attempts:
                    current = replace(
                        current,
                        state="dead_letter",
                        delivery_attempts=attempt,
                        terminal_state=("delegation_delivery_failed"),
                        updated_at=utc_now(),
                        limitations=tuple(
                            sorted(
                                {
                                    *current.limitations,
                                    "delivery_retries_exhausted",
                                    type(error).__name__,
                                }
                            )
                        ),
                    )
                    self._ledger.save(current)
                    return current
                current = replace(
                    current,
                    state="pending",
                    delivery_attempts=attempt,
                    updated_at=utc_now(),
                )
                self._ledger.save(current)
                await asyncio.sleep(
                    min(
                        30,
                        2 ** (attempt - 1),
                    )
                )
        return current
