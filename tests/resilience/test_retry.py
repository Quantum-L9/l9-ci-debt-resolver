from __future__ import annotations

import pytest

from l9_debt_resolver.acquisition.config import (
    RetryPolicy,
)
from l9_debt_resolver.acquisition.errors import (
    RetryExhaustedError,
)
from l9_debt_resolver.acquisition.retry import (
    RetrySignal,
    with_retry,
)


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failure() -> None:
    attempts = 0
    sleeps: list[float] = []

    async def operation(attempt: int) -> str:
        nonlocal attempts
        attempts = attempt
        if attempt < 3:
            raise RetrySignal(status=503)
        return "ok"

    async def sleep(value: float) -> None:
        sleeps.append(value)

    result = await with_retry(
        operation,
        policy=RetryPolicy(
            maximum_attempts=4,
            initial_backoff_seconds=0.1,
            maximum_backoff_seconds=1,
        ),
        sleep=sleep,
    )
    assert result == "ok"
    assert attempts == 3
    assert sleeps == [0.1, 0.2]


@pytest.mark.asyncio
async def test_retry_is_bounded() -> None:
    async def operation(attempt: int) -> str:
        del attempt
        raise RetrySignal(status=503)

    async def sleep(value: float) -> None:
        del value

    with pytest.raises(RetryExhaustedError):
        await with_retry(
            operation,
            policy=RetryPolicy(
                maximum_attempts=2,
                initial_backoff_seconds=0,
                maximum_backoff_seconds=0,
            ),
            sleep=sleep,
        )
