from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)

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


class _CrossHostAuthStrippingRedirectHandler(HTTPRedirectHandler):
    """Drop ``Authorization`` when a redirect leaves the original host.

    GitHub answers ``/repos/{owner}/{repo}/actions/jobs/{id}/logs`` with a 302 to
    a *signed* blob-storage URL. urllib's default handler replays every header on
    the redirected request, so the pre-signed request also carries
    ``Authorization: Bearer ...``. The storage backend rejects that combination
    with 401, which this transport then reported as ``AuthenticationError`` -- a
    credential failure that was never a credential problem.

    curl and requests both drop credentials on a cross-host redirect for the same
    reason. Same-host redirects keep the header so ordinary API redirects are
    unaffected, and forwarding a bearer token to a third-party host would leak it
    regardless.
    """

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        if urlparse(req.full_url).hostname != urlparse(newurl).hostname:
            for header in list(redirected.headers):
                if header.lower() == "authorization":
                    del redirected.headers[header]
        return redirected


_OPENER = build_opener(_CrossHostAuthStrippingRedirectHandler())


def urlopen(
    request: Request,
    *,
    timeout: float,
) -> Any:
    """Open ``request`` with cross-host ``Authorization`` stripping applied.

    Deliberately shadows ``urllib.request.urlopen``: the stdlib function uses the
    global opener, which cannot carry this module's redirect policy. Keeping the
    name means the module's existing patch point stays exactly where it was.
    """
    return _OPENER.open(request, timeout=timeout)


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
