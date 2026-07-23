from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.providers.github.transport import (
    GitHubTransport,
)

from .errors import RerunTimeoutError
from .models import RerunObservation


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


class GitHubRerunProvider:
    def __init__(
        self,
        *,
        token: str,
        config: AcquisitionConfig | None = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        self._config = config or AcquisitionConfig()
        self._transport = GitHubTransport(
            token=token,
            config=self._config,
            base_url=base_url,
        )

    async def dispatch_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> None:
        owner, name = _repository_parts(repository)
        await self._post_empty(
            f"/repos/{quote(owner)}/{quote(name)}"
            f"/actions/runs/{quote(run_id)}"
            f"/rerun-failed-jobs"
        )

    async def observe(
        self,
        *,
        repository: str,
        original_run_id: str,
        expected_head_sha: str,
        timeout_seconds: float = 1800,
        poll_interval_seconds: float = 10,
    ) -> RerunObservation:
        started_at = utc_now()
        deadline = asyncio.get_running_loop().time() + (timeout_seconds)
        poll_count = 0
        latest: dict[str, Any] | None = None
        while True:
            poll_count += 1
            candidate = await self._latest_run_for_sha(
                repository=repository,
                head_sha=expected_head_sha,
            )
            if candidate is not None:
                latest = candidate
                if candidate.get("status") == "completed":
                    break
            if asyncio.get_running_loop().time() >= deadline:
                raise RerunTimeoutError("CI rerun observation exceeded timeout")
            await asyncio.sleep(poll_interval_seconds)
        rerun_id = str(latest["id"])
        completed_at = utc_now()
        return RerunObservation(
            observation_id=namespaced_identity(
                "rerun_observation_",
                {
                    "repository": repository,
                    "original_run_id": original_run_id,
                    "rerun_id": rerun_id,
                    "head_sha": expected_head_sha,
                    "conclusion": latest.get("conclusion"),
                },
            ),
            provider="github_actions",
            repository=repository,
            original_run_id=original_run_id,
            rerun_id=rerun_id,
            status=str(latest["status"]),
            conclusion=(
                str(latest["conclusion"])
                if latest.get("conclusion") is not None
                else None
            ),
            head_sha=expected_head_sha,
            started_at=started_at,
            completed_at=completed_at,
            poll_count=poll_count,
            limitations=(),
        )

    async def _latest_run_for_sha(
        self,
        *,
        repository: str,
        head_sha: str,
    ) -> dict[str, Any] | None:
        owner, name = _repository_parts(repository)
        document, _ = await self._transport.get_json(
            f"/repos/{quote(owner)}/{quote(name)}"
            f"/actions/runs"
            f"?head_sha={quote(head_sha)}"
            f"&per_page=20"
        )
        runs = document.get("workflow_runs")
        if not isinstance(runs, list):
            return None
        candidates = [
            run
            for run in runs
            if (isinstance(run, dict) and run.get("head_sha") == head_sha)
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda run: (
                str(run.get("created_at", "")),
                int(run.get("id", 0)),
            ),
            reverse=True,
        )
        return candidates[0]

    async def _post_empty(
        self,
        path: str,
    ) -> None:
        import json
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen

        request = Request(
            self._transport._base_url + path,
            method="POST",
            data=json.dumps({}).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": (f"Bearer {self._transport._token}"),
                "User-Agent": (self._config.user_agent),
                "X-GitHub-Api-Version": (self._config.api_version),
                "Content-Type": "application/json",
            },
        )

        def invoke() -> None:
            try:
                with urlopen(
                    request,
                    timeout=30,
                ) as response:
                    if response.status not in {
                        201,
                        202,
                        204,
                    }:
                        raise RuntimeError("unexpected rerun response")
            except HTTPError as error:
                raise RuntimeError(
                    f"rerun dispatch failed with HTTP {error.code}"
                ) from error

        await asyncio.to_thread(invoke)


def _repository_parts(
    repository: str,
) -> tuple[str, str]:
    parts = repository.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repository must use owner/name format")
    return parts[0], parts[1]
