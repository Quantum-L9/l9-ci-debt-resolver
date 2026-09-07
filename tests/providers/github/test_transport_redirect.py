from __future__ import annotations

import io
from typing import Any
from urllib.request import Request

from l9_debt_resolver.providers.github.transport import (
    _CrossHostAuthStrippingRedirectHandler,
)


def _redirect(
    *,
    from_url: str,
    to_url: str,
) -> Request | None:
    """Run the handler over one 302, returning the redirected request."""
    original = Request(
        from_url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer token-value",
            "User-Agent": "l9-debt-resolver",
        },
    )
    return _CrossHostAuthStrippingRedirectHandler().redirect_request(
        original,
        io.BytesIO(b""),
        302,
        "Found",
        {},
        to_url,
    )


def _header_names(request: Request) -> set[str]:
    return {name.lower() for name in request.headers}


def test_authorization_is_dropped_when_the_redirect_leaves_the_host() -> None:
    """GitHub redirects job logs to signed blob storage.

    Replaying ``Authorization`` onto that pre-signed request makes the storage
    backend answer 401, which the transport reported as an authentication
    failure against GitHub.
    """
    redirected = _redirect(
        from_url="https://api.github.com/repos/o/r/actions/jobs/1/logs",
        to_url="https://productionresultssa4.blob.core.windows.net/x?sig=abc",
    )
    assert redirected is not None
    assert "authorization" not in _header_names(redirected)


def test_other_headers_survive_a_cross_host_redirect() -> None:
    redirected = _redirect(
        from_url="https://api.github.com/repos/o/r/actions/jobs/1/logs",
        to_url="https://storage.example.com/log?sig=abc",
    )
    assert redirected is not None
    assert "user-agent" in _header_names(redirected)


def test_authorization_survives_a_same_host_redirect() -> None:
    """Ordinary API redirects must keep authenticating."""
    redirected = _redirect(
        from_url="https://api.github.com/repos/o/r/actions/jobs/1/logs",
        to_url="https://api.github.com/repos/o/r/actions/jobs/1/logs/final",
    )
    assert redirected is not None
    assert "authorization" in _header_names(redirected)


def test_module_opener_installs_the_handler() -> None:
    """The opener must carry the handler, or the fix is unreachable."""
    from l9_debt_resolver.providers.github import transport

    opener: Any = transport._OPENER
    assert any(
        isinstance(handler, _CrossHostAuthStrippingRedirectHandler)
        for handler in opener.handlers
    )
