from __future__ import annotations

import email.message
import io
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
    RetryPolicy,
)
from l9_debt_resolver.acquisition.errors import (
    AuthenticationError,
    AuthorizationError,
    RemoteResponseError,
    RetryExhaustedError,
)
from l9_debt_resolver.delegation.errors import (
    DelegationPermanentError,
    DelegationRetryableError,
)
from l9_debt_resolver.delegation.http_transport import (
    HTTPSPRRepairTransport,
)
from l9_debt_resolver.delegation.models import PRRepairRequest
from l9_debt_resolver.feedback.errors import (
    PermanentDeliveryError,
    RetryableDeliveryError,
)
from l9_debt_resolver.feedback.http_transport import (
    HTTPSFeedbackTransport,
)
from l9_debt_resolver.feedback.models import FeedbackEvent
from l9_debt_resolver.providers.github.transport import GitHubTransport

# ---------------------------------------------------------------------------
# Fakes mimicking http.client.HTTPResponse / urllib error objects.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._body = body
        self.headers = headers or {}

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self, amt: int | None = None) -> bytes:
        return self._body if amt is None else self._body[:amt]


def _urlopen_returning(response: _FakeResponse):
    def fake(request: Any, timeout: float | None = None) -> _FakeResponse:
        return response

    return fake


def _urlopen_raising(error: Exception):
    def fake(request: Any, timeout: float | None = None) -> _FakeResponse:
        raise error

    return fake


def _http_error(
    code: int,
    *,
    body: bytes = b"boom",
    headers: dict[str, str] | None = None,
) -> HTTPError:
    message = email.message.Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return HTTPError(
        url="https://api.github.com/x",
        code=code,
        msg="error",
        hdrs=message,  # type: ignore[arg-type]
        fp=io.BytesIO(body),
    )


# ---------------------------------------------------------------------------
# GitHubTransport
# ---------------------------------------------------------------------------


def _fast_config() -> AcquisitionConfig:
    return AcquisitionConfig(retry=RetryPolicy(maximum_attempts=1))


def _transport(config: AcquisitionConfig | None = None) -> GitHubTransport:
    return GitHubTransport(
        token="secret-token",
        config=config or AcquisitionConfig(),
        base_url="https://api.github.com",
    )


def test_transport_requires_token() -> None:
    with pytest.raises(AuthenticationError):
        GitHubTransport(token="   ", config=AcquisitionConfig())


@pytest.mark.asyncio
async def test_get_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _FakeResponse(
        status=200,
        body=b'{"id": 100, "status": "completed"}',
        headers={"Content-Type": "application/json", "ETag": "abc"},
    )
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_returning(response),
    )
    document, http_response = await _transport().get_json("/repos/x/y")
    assert document == {"id": 100, "status": "completed"}
    assert http_response.status == 200
    assert http_response.headers["etag"] == "abc"
    assert http_response.body


@pytest.mark.asyncio
async def test_get_bytes_success(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _FakeResponse(status=200, body=b"log-bytes")
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_returning(response),
    )
    result = await _transport().get_bytes("/logs")
    assert result.body == b"log-bytes"


@pytest.mark.asyncio
async def test_get_json_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _FakeResponse(status=200, body=b"not-json")
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_returning(response),
    )
    with pytest.raises(RemoteResponseError):
        await _transport().get_json("/repos/x/y")


@pytest.mark.asyncio
async def test_get_json_non_object(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _FakeResponse(status=200, body=b"[1, 2, 3]")
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_returning(response),
    )
    with pytest.raises(RemoteResponseError):
        await _transport().get_json("/repos/x/y")


@pytest.mark.asyncio
async def test_get_bytes_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_raising(_http_error(401)),
    )
    with pytest.raises(AuthenticationError):
        await _transport().get_bytes("/logs")


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [403, 404])
async def test_get_bytes_denied(
    monkeypatch: pytest.MonkeyPatch,
    code: int,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_raising(_http_error(code)),
    )
    with pytest.raises(AuthorizationError):
        await _transport().get_bytes("/logs")


@pytest.mark.asyncio
async def test_get_bytes_non_retryable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_raising(_http_error(418, body=b"teapot")),
    )
    with pytest.raises(RemoteResponseError):
        await _transport().get_bytes("/logs")


@pytest.mark.asyncio
async def test_get_bytes_retryable_status_exhausts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_raising(_http_error(429, headers={"Retry-After": "0"})),
    )
    with pytest.raises(RetryExhaustedError):
        await _transport(_fast_config()).get_bytes("/logs")


@pytest.mark.asyncio
async def test_get_bytes_url_error_exhausts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.providers.github.transport.urlopen",
        _urlopen_raising(URLError("no route")),
    )
    with pytest.raises(RetryExhaustedError):
        await _transport(_fast_config()).get_bytes("/logs")


# ---------------------------------------------------------------------------
# Feedback HTTPS transport
# ---------------------------------------------------------------------------


def _event() -> FeedbackEvent:
    return FeedbackEvent(
        event_id="feedback_event_" + "a" * 64,
        idempotency_key="feedback_idempotency_" + "b" * 64,
        event_type="resolution_succeeded",
        repository_pseudonym="repository_" + "c" * 64,
        provider="github_actions",
        resolver_version="0.6.0",
        occurred_at="2026-07-19T00:00:00Z",
        failure={"fingerprint": "failure_" + "d" * 64},
        resolution={"terminal_state": "clean"},
        validation={"result": "passed"},
        correlation={"capability_profile": ["python"]},
        provenance={"snapshot_id_hash": "f" * 64},
        limitations=(),
    )


def _feedback_transport() -> HTTPSFeedbackTransport:
    return HTTPSFeedbackTransport(
        endpoint="https://feedback.example/api",
        bearer_token="token",
    )


def test_feedback_endpoint_must_be_https() -> None:
    with pytest.raises(ValueError):
        HTTPSFeedbackTransport(endpoint="http://x", bearer_token="t")


def test_feedback_token_required() -> None:
    with pytest.raises(ValueError):
        HTTPSFeedbackTransport(endpoint="https://x", bearer_token="")


@pytest.mark.asyncio
async def test_feedback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.feedback.http_transport.urlopen",
        _urlopen_returning(_FakeResponse(status=200, body=b"{}")),
    )
    result = await _feedback_transport().deliver(_event())
    assert result.status_code == 200
    assert result.duplicate is False
    assert result.response_body_sha256


@pytest.mark.asyncio
async def test_feedback_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.feedback.http_transport.urlopen",
        _urlopen_returning(_FakeResponse(status=409, body=b"{}")),
    )
    result = await _feedback_transport().deliver(_event())
    assert result.duplicate is True


@pytest.mark.asyncio
async def test_feedback_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.feedback.http_transport.urlopen",
        _urlopen_returning(_FakeResponse(status=418, body=b"{}")),
    )
    with pytest.raises(PermanentDeliveryError):
        await _feedback_transport().deliver(_event())


@pytest.mark.asyncio
async def test_feedback_http_error_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.feedback.http_transport.urlopen",
        _urlopen_raising(_http_error(409)),
    )
    result = await _feedback_transport().deliver(_event())
    assert result.status_code == 409
    assert result.duplicate is True


@pytest.mark.asyncio
async def test_feedback_http_error_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.feedback.http_transport.urlopen",
        _urlopen_raising(_http_error(429, headers={"Retry-After": "5"})),
    )
    with pytest.raises(RetryableDeliveryError) as info:
        await _feedback_transport().deliver(_event())
    assert info.value.status_code == 429
    assert info.value.retry_after_seconds == 5.0


@pytest.mark.asyncio
async def test_feedback_http_error_permanent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.feedback.http_transport.urlopen",
        _urlopen_raising(_http_error(400)),
    )
    with pytest.raises(PermanentDeliveryError):
        await _feedback_transport().deliver(_event())


@pytest.mark.asyncio
async def test_feedback_url_error_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.feedback.http_transport.urlopen",
        _urlopen_raising(URLError("down")),
    )
    with pytest.raises(RetryableDeliveryError):
        await _feedback_transport().deliver(_event())


# ---------------------------------------------------------------------------
# Delegation HTTPS transport
# ---------------------------------------------------------------------------


def _request() -> PRRepairRequest:
    return PRRepairRequest(
        request_id="pr_repair_request_" + "a" * 64,
        idempotency_key="pr_repair_idempotency_" + "b" * 64,
        repository_pseudonym="repository_" + "c" * 64,
        failure_fingerprint="failure_" + "d" * 64,
        classification={"category": "test_failure"},
        repository_context={"snapshot_id_hash": "f" * 64},
        constraints={"maximum_changed_files": 10},
        callback={"callback_id": "callback_" + "2" * 64},
        created_at="2026-07-19T00:00:00Z",
        expires_at="2026-07-19T00:15:00Z",
        limitations=(),
    )


def _delegation_transport() -> HTTPSPRRepairTransport:
    return HTTPSPRRepairTransport(
        endpoint="https://repair.example/api",
        bearer_token="token",
    )


def test_delegation_endpoint_must_be_https() -> None:
    with pytest.raises(ValueError):
        HTTPSPRRepairTransport(endpoint="http://x", bearer_token="t")


def test_delegation_token_required() -> None:
    with pytest.raises(ValueError):
        HTTPSPRRepairTransport(endpoint="https://x", bearer_token="")


@pytest.mark.asyncio
async def test_delegation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.delegation.http_transport.urlopen",
        _urlopen_returning(_FakeResponse(status=202, body=b"{}")),
    )
    digest = await _delegation_transport().deliver(_request())
    assert len(digest) == 64


@pytest.mark.asyncio
async def test_delegation_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.delegation.http_transport.urlopen",
        _urlopen_returning(_FakeResponse(status=418, body=b"{}")),
    )
    with pytest.raises(DelegationPermanentError):
        await _delegation_transport().deliver(_request())


@pytest.mark.asyncio
async def test_delegation_http_error_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.delegation.http_transport.urlopen",
        _urlopen_raising(_http_error(409, body=b"dup")),
    )
    digest = await _delegation_transport().deliver(_request())
    assert len(digest) == 64


@pytest.mark.asyncio
async def test_delegation_http_error_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.delegation.http_transport.urlopen",
        _urlopen_raising(_http_error(503)),
    )
    with pytest.raises(DelegationRetryableError):
        await _delegation_transport().deliver(_request())


@pytest.mark.asyncio
async def test_delegation_http_error_permanent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.delegation.http_transport.urlopen",
        _urlopen_raising(_http_error(400)),
    )
    with pytest.raises(DelegationPermanentError):
        await _delegation_transport().deliver(_request())


@pytest.mark.asyncio
async def test_delegation_url_error_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "l9_debt_resolver.delegation.http_transport.urlopen",
        _urlopen_raising(URLError("down")),
    )
    with pytest.raises(DelegationRetryableError):
        await _delegation_transport().deliver(_request())
