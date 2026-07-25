from __future__ import annotations

from typing import Any
from urllib.error import HTTPError

import pytest

from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
    AcquisitionLimits,
)
from l9_debt_resolver.acquisition.errors import JobLimitError
from l9_debt_resolver.acquisition.models import FailedJob, FailedStep
from l9_debt_resolver.providers.github.provider import (
    GitHubActionsProvider,
)
from l9_debt_resolver.providers.github.transport import HTTPResponse
from l9_debt_resolver.remote.errors import RerunTimeoutError
from l9_debt_resolver.remote.github import GitHubRerunProvider

# ---------------------------------------------------------------------------
# Fake transport injected in place of GitHubTransport.
# ---------------------------------------------------------------------------


class FakeTransport:
    def __init__(
        self,
        *,
        json_document: dict[str, Any] | None = None,
        bytes_response: HTTPResponse | None = None,
    ) -> None:
        self._json_document = json_document or {}
        self._bytes_response = bytes_response
        self._base_url = "https://api.github.com"
        self._token = "token"
        self.json_calls: list[str] = []
        self.bytes_calls: list[str] = []

    async def get_json(
        self,
        path: str,
    ) -> tuple[dict[str, Any], HTTPResponse]:
        self.json_calls.append(path)
        response = HTTPResponse(status=200, headers={}, body=b"{}")
        return self._json_document, response

    async def get_bytes(
        self,
        path: str,
        *,
        accept: str = "application/vnd.github+json",
    ) -> HTTPResponse:
        self.bytes_calls.append(path)
        assert self._bytes_response is not None
        return self._bytes_response


def _run_document() -> dict[str, Any]:
    return {
        "id": 100,
        "status": "completed",
        "conclusion": "failure",
        "head_sha": "a" * 40,
        "event": "pull_request",
        "workflow_id": 10,
        "created_at": "2026-07-18T00:00:00Z",
        "updated_at": "2026-07-18T00:01:00Z",
    }


def _jobs_document(count: int = 1) -> dict[str, Any]:
    return {
        "jobs": [
            {
                "id": index,
                "name": f"failing-{index}",
                "status": "completed",
                "conclusion": "failure",
                "steps": [
                    {
                        "number": 1,
                        "name": "pytest",
                        "conclusion": "failure",
                    }
                ],
                "labels": ["ubuntu-latest"],
            }
            for index in range(1, count + 1)
        ]
    }


def _provider() -> GitHubActionsProvider:
    return GitHubActionsProvider(token="token")


# ---------------------------------------------------------------------------
# GitHubActionsProvider
# ---------------------------------------------------------------------------


def test_provider_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    provider = GitHubActionsProvider.from_environment()
    assert isinstance(provider, GitHubActionsProvider)


@pytest.mark.asyncio
async def test_identify_failed_run() -> None:
    provider = _provider()
    provider._transport = FakeTransport(json_document=_run_document())
    run = await provider.identify_failed_run(
        repository="Quantum-L9/example",
        run_id="100",
    )
    assert run.run_id == "100"
    assert run.conclusion == "failure"
    assert run.head_sha == "a" * 40


@pytest.mark.asyncio
async def test_identify_failed_run_bad_repository() -> None:
    provider = _provider()
    provider._transport = FakeTransport(json_document=_run_document())
    with pytest.raises(ValueError):
        await provider.identify_failed_run(
            repository="no-slash",
            run_id="100",
        )


@pytest.mark.asyncio
async def test_retrieve_failed_jobs() -> None:
    provider = _provider()
    provider._transport = FakeTransport(json_document=_jobs_document())
    jobs = await provider.retrieve_failed_jobs(
        repository="Quantum-L9/example",
        run_id="100",
    )
    assert len(jobs) == 1
    assert jobs[0].job_id == "1"
    assert jobs[0].failed_steps[0].name == "pytest"


@pytest.mark.asyncio
async def test_retrieve_failed_jobs_job_limit() -> None:
    config = AcquisitionConfig(
        limits=AcquisitionLimits(maximum_jobs_per_run=1),
    )
    provider = GitHubActionsProvider(token="token", config=config)
    provider._transport = FakeTransport(json_document=_jobs_document(count=2))
    with pytest.raises(JobLimitError):
        await provider.retrieve_failed_jobs(
            repository="Quantum-L9/example",
            run_id="100",
        )


def _failed_job() -> FailedJob:
    return FailedJob(
        provider="github_actions",
        run_id="100",
        job_id="200",
        name="failing",
        status="completed",
        conclusion="failure",
        started_at=None,
        completed_at=None,
        runner_name=None,
        labels=(),
        failed_steps=(
            FailedStep(number=1, name="pytest", conclusion="failure"),
        ),
    )


@pytest.mark.asyncio
async def test_retrieve_failed_log() -> None:
    provider = _provider()
    body = b"E   assert 1 == 2\nFAILED tests/test_x.py\n"
    provider._transport = FakeTransport(
        bytes_response=HTTPResponse(
            status=200,
            headers={
                "content-length": str(len(body)),
                "content-type": "text/plain",
                "etag": "log-etag",
            },
            body=body,
        )
    )
    acquired = await provider.retrieve_failed_log(
        repository="Quantum-L9/example",
        run_id="100",
        job=_failed_job(),
    )
    assert acquired.redacted_text
    assert acquired.provenance.job_id == "200"
    assert acquired.evidence.job_name == "failing"
    assert acquired.evidence.conclusion == "failure"


@pytest.mark.asyncio
async def test_retrieve_failed_log_truncates_over_limit() -> None:
    config = AcquisitionConfig(
        limits=AcquisitionLimits(maximum_log_bytes_per_job=8),
    )
    provider = GitHubActionsProvider(token="token", config=config)
    body = b"0123456789ABCDEF"
    provider._transport = FakeTransport(
        bytes_response=HTTPResponse(
            status=200,
            headers={"content-length": str(len(body))},
            body=body,
        )
    )
    acquired = await provider.retrieve_failed_log(
        repository="Quantum-L9/example",
        run_id="100",
        job=_failed_job(),
    )
    assert acquired.provenance.raw_byte_count == 8


# ---------------------------------------------------------------------------
# GitHubRerunProvider — observe / dispatch
# ---------------------------------------------------------------------------


class RerunFakeTransport:
    def __init__(self, document: dict[str, Any]) -> None:
        self._document = document
        self._base_url = "https://api.github.com"
        self._token = "token"

    async def get_json(
        self,
        path: str,
    ) -> tuple[dict[str, Any], HTTPResponse]:
        response = HTTPResponse(status=200, headers={}, body=b"{}")
        return self._document, response


def _rerun_provider() -> GitHubRerunProvider:
    return GitHubRerunProvider(token="token")


@pytest.mark.asyncio
async def test_observe_completed_run() -> None:
    provider = _rerun_provider()
    provider._transport = RerunFakeTransport(
        {
            "workflow_runs": [
                {
                    "id": 999,
                    "head_sha": "a" * 40,
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-07-20T00:00:00Z",
                }
            ]
        }
    )
    observation = await provider.observe(
        repository="Quantum-L9/example",
        original_run_id="100",
        expected_head_sha="a" * 40,
        timeout_seconds=5,
        poll_interval_seconds=0,
    )
    assert observation.rerun_id == "999"
    assert observation.status == "completed"
    assert observation.conclusion == "success"
    assert observation.poll_count == 1


@pytest.mark.asyncio
async def test_observe_timeout_incomplete_run() -> None:
    provider = _rerun_provider()
    provider._transport = RerunFakeTransport(
        {
            "workflow_runs": [
                {
                    "id": 999,
                    "head_sha": "a" * 40,
                    "status": "in_progress",
                    "conclusion": None,
                    "created_at": "2026-07-20T00:00:00Z",
                }
            ]
        }
    )
    with pytest.raises(RerunTimeoutError):
        await provider.observe(
            repository="Quantum-L9/example",
            original_run_id="100",
            expected_head_sha="a" * 40,
            timeout_seconds=0,
            poll_interval_seconds=0,
        )


@pytest.mark.asyncio
async def test_observe_timeout_no_matching_run() -> None:
    provider = _rerun_provider()
    provider._transport = RerunFakeTransport({"workflow_runs": []})
    with pytest.raises(RerunTimeoutError):
        await provider.observe(
            repository="Quantum-L9/example",
            original_run_id="100",
            expected_head_sha="a" * 40,
            timeout_seconds=0,
            poll_interval_seconds=0,
        )


@pytest.mark.asyncio
async def test_dispatch_failed_jobs_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Resp:
        status = 204

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    def fake_urlopen(request: Any, timeout: float | None = None) -> _Resp:
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    await _rerun_provider().dispatch_failed_jobs(
        repository="Quantum-L9/example",
        run_id="100",
    )


@pytest.mark.asyncio
async def test_dispatch_failed_jobs_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Resp:
        status = 200

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    def fake_urlopen(request: Any, timeout: float | None = None) -> _Resp:
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RuntimeError):
        await _rerun_provider().dispatch_failed_jobs(
            repository="Quantum-L9/example",
            run_id="100",
        )


@pytest.mark.asyncio
async def test_dispatch_failed_jobs_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import email.message
    import io

    def fake_urlopen(request: Any, timeout: float | None = None) -> Any:
        raise HTTPError(
            url="https://api.github.com/x",
            code=500,
            msg="error",
            hdrs=email.message.Message(),  # type: ignore[arg-type]
            fp=io.BytesIO(b""),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RuntimeError):
        await _rerun_provider().dispatch_failed_jobs(
            repository="Quantum-L9/example",
            run_id="100",
        )
