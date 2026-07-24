from __future__ import annotations

import asyncio
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import (
    PermanentDeliveryError,
    RetryableDeliveryError,
)
from .models import (
    DeliveryResponse,
    FeedbackEvent,
)

SUCCESS = {
    200,
    201,
    202,
    204,
    409,
}
RETRYABLE = {
    408,
    425,
    429,
    500,
    502,
    503,
    504,
}


class HTTPSFeedbackTransport:
    name = "https"

    def __init__(
        self,
        *,
        endpoint: str,
        bearer_token: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("feedback endpoint must use HTTPS")
        if not bearer_token:
            raise ValueError("feedback bearer token is required")
        self._endpoint = endpoint
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds

    async def deliver(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        return await asyncio.to_thread(
            self._deliver_sync,
            event,
        )

    def _deliver_sync(
        self,
        event: FeedbackEvent,
    ) -> DeliveryResponse:
        body = json.dumps(
            event.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            method="POST",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": (f"Bearer {self._bearer_token}"),
                "Idempotency-Key": (event.idempotency_key),
                "User-Agent": ("l9-ci-debt-resolver-feedback/1"),
            },
        )
        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                response_body = response.read(1024 * 1024)
                if response.status not in SUCCESS:
                    raise PermanentDeliveryError(
                        f"feedback endpoint returned HTTP {response.status}"
                    )
                return DeliveryResponse(
                    transport=self.name,
                    status_code=response.status,
                    duplicate=(response.status == 409),
                    response_body_sha256=(hashlib.sha256(response_body).hexdigest()),
                )
        except HTTPError as error:
            response_body = error.read(1024 * 1024)
            if error.code in SUCCESS:
                return DeliveryResponse(
                    transport=self.name,
                    status_code=error.code,
                    duplicate=(error.code == 409),
                    response_body_sha256=(hashlib.sha256(response_body).hexdigest()),
                )
            if error.code in RETRYABLE:
                raise RetryableDeliveryError(
                    "retryable feedback HTTP response",
                    status_code=error.code,
                    retry_after_seconds=(
                        _retry_after_seconds(error.headers.get("Retry-After"))
                    ),
                ) from error
            raise PermanentDeliveryError(
                f"non-retryable feedback HTTP response {error.code}"
            ) from error
        except URLError as error:
            raise RetryableDeliveryError("feedback endpoint is unavailable") from error


def _retry_after_seconds(
    value: str | None,
) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return min(parsed, 30.0)
