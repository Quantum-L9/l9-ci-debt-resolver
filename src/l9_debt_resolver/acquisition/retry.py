from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TypeVar

from .config import RetryPolicy
from .errors import RetryExhaustedError

T = TypeVar("T")


@dataclass(frozen=True)
class RetrySignal(Exception):
    status: int
    retry_after: str | None = None


def retry_after_seconds(
    value: str | None,
    *,
    now: datetime | None = None,
) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    try:
        return max(0.0, float(stripped))
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(stripped)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    reference = now or datetime.now(UTC)
    return max(
        0.0,
        (parsed - reference).total_seconds(),
    )


async def with_retry(
    operation: Callable[[int], Awaitable[T]],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    last_signal: RetrySignal | None = None
    for attempt in range(1, policy.maximum_attempts + 1):
        try:
            return await operation(attempt)
        except RetrySignal as signal:
            last_signal = signal
            if signal.status not in policy.retryable_statuses:
                raise
            if attempt >= policy.maximum_attempts:
                break
            server_delay = retry_after_seconds(signal.retry_after)
            exponential_delay = min(
                policy.maximum_backoff_seconds,
                policy.initial_backoff_seconds * (2 ** (attempt - 1)),
            )
            delay = (
                min(
                    server_delay,
                    policy.maximum_retry_after_seconds,
                )
                if server_delay is not None
                else exponential_delay
            )
            await sleep(delay)
    status = last_signal.status if last_signal is not None else "unknown"
    raise RetryExhaustedError(
        f"provider operation exhausted bounded retries after status {status}"
    )
