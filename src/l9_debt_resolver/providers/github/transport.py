from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
)
from l9_debt_resolver.acquisition.errors import (
    AuthenticationError,
    AuthorizationError,
    RemoteResponseError,
)
from l9_debt_resolver.acquisition.retry import (
    RetrySignal,
    with_retry,
)


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class GitHubTransport:
    def __init__(
        self,
        *,
        token: str,
        config: AcquisitionConfig,
        base_url: str = "https://api.github.com",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not token.strip():
            raise AuthenticationError("GitHub token is required")
        self._token = token
        self._config = config
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def get_json(
        self,
        path: str,
    ) -> tuple[dict[str, Any], HTTPResponse]:
        response = await self.get_bytes(
            path,
            accept="application/vnd.github+json",
        )
        try:
            document = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RemoteResponseError("GitHub returned invalid JSON") from error
        if not isinstance(document, dict):
            raise RemoteResponseError("GitHub JSON response must be an object")
        return document, response

    async def get_bytes(
        self,
        path: str,
        *,
        accept: str = "application/vnd.github+json",
    ) -> HTTPResponse:
        async def operation(attempt: int) -> HTTPResponse:
            del attempt
            return await asyncio.to_thread(
                self._request,
                path,
                accept,
            )

        try:
            return await with_retry(
                operation,
                policy=self._config.retry,
            )
        except RetrySignal as signal:
            raise RemoteResponseError(
                f"GitHub returned HTTP {signal.status}"
            ) from signal

    def _request(
        self,
        path: str,
        accept: str,
    ) -> HTTPResponse:
        request = Request(
            self._base_url + path,
            method="GET",
            headers={
                "Accept": accept,
                "Authorization": f"Bearer {self._token}",
                "User-Agent": self._config.user_agent,
                "X-GitHub-Api-Version": (self._config.api_version),
            },
        )
        try:
            with urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                return HTTPResponse(
                    status=int(response.status),
                    headers={
                        key.casefold(): value for key, value in response.headers.items()
                    },
                    body=response.read(),
                )
        except HTTPError as error:
            status = int(error.code)
            if status == 401:
                raise AuthenticationError("GitHub authentication failed") from error
            if status in {403, 404}:
                raise AuthorizationError(
                    "GitHub denied access or the resource does not exist"
                ) from error
            retry_after = error.headers.get("Retry-After")
            if status in self._config.retry.retryable_statuses:
                raise RetrySignal(
                    status=status,
                    retry_after=retry_after,
                ) from error
            body = error.read(4096).decode(
                "utf-8",
                errors="replace",
            )
            raise RemoteResponseError(
                f"GitHub returned HTTP {status}: {body}"
            ) from error
        except URLError as error:
            raise RetrySignal(status=503) from error
