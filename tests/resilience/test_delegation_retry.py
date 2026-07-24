from __future__ import annotations

from pathlib import Path

import pytest

from l9_debt_resolver.delegation.errors import (
    DelegationRetryableError,
)
from l9_debt_resolver.delegation.ledger import (
    DelegationLedger,
)
from l9_debt_resolver.delegation.service import (
    PRRepairDelegationService,
)
from tests.delegation.test_file_transport import request


class FlakyTransport:
    name = "https"

    def __init__(self) -> None:
        self.calls = 0

    async def deliver(self, request_value):
        del request_value
        self.calls += 1
        if self.calls < 3:
            raise DelegationRetryableError("temporary")
        return "receipt"


@pytest.mark.asyncio
async def test_retryable_delivery_succeeds(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def no_sleep(_):
        return None

    monkeypatch.setattr(
        "l9_debt_resolver.delegation.service.asyncio.sleep",
        no_sleep,
    )
    transport = FlakyTransport()
    service = PRRepairDelegationService(
        ledger=DelegationLedger(directory=tmp_path),
        transport=transport,
        maximum_attempts=5,
    )
    record = await service.submit(request())
    assert record.state == "awaiting_callback"
    assert record.delivery_attempts == 3
