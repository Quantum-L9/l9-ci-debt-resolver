from __future__ import annotations

import asyncio
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import (
    DelegationPermanentError,
    DelegationRetryableError,
)
from .models import PRRepairRequest

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


class HTTPSPRRepairTransport:
    name = "https"

    def __init__(
        self,
        *,
        endpoint: str,
        bearer_token: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("PR_Repair endpoint must use HTTPS")
        if not bearer_token:
            raise ValueError("PR_Repair bearer token is required")
        self._endpoint = endpoint
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds

    async def deliver(
        self,
        request_value: PRRepairRequest,
    ) -> str:
        return await asyncio.to_thread(
            self._deliver_sync,
            request_value,
        )

    def _deliver_sync(
        self,
        request_value: PRRepairRequest,
    ) -> str:
        body = json.dumps(
            request_value.as_dict(),
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
                "Idempotency-Key": (request_value.idempotency_key),
                "User-Agent": ("l9-ci-debt-resolver-pr-repair/1"),
            },
        )
        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                response_body = response.read(1024 * 1024)
                if response.status not in SUCCESS:
                    raise DelegationPermanentError("unexpected PR_Repair response")
                return hashlib.sha256(response_body).hexdigest()
        except HTTPError as error:
            if error.code in SUCCESS:
                return hashlib.sha256(error.read(1024 * 1024)).hexdigest()
            if error.code in RETRYABLE:
                raise DelegationRetryableError(
                    "retryable PR_Repair response"
                ) from error
            raise DelegationPermanentError(
                f"non-retryable PR_Repair response {error.code}"
            ) from error
        except URLError as error:
            raise DelegationRetryableError("PR_Repair endpoint unavailable") from error
