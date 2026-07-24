from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from l9_debt_resolver.acquisition.completeness import (
    assess_log_completeness,
)
from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
)
from l9_debt_resolver.acquisition.errors import (
    JobLimitError,
    PaginationLimitError,
    RemoteResponseError,
)
from l9_debt_resolver.acquisition.models import (
    AcquiredLog,
    FailedJob,
    FailedRun,
    LogProvenance,
)
from l9_debt_resolver.acquisition.redaction import (
    LogRedactor,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.contracts.models import CIRunEvidence

from .parser import parse_failed_jobs, parse_run
from .transport import GitHubTransport


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


class GitHubActionsProvider:
    def __init__(
        self,
        *,
        token: str,
        config: AcquisitionConfig | None = None,
        repository_root: str | None = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        self._config = config or AcquisitionConfig()
        self._transport = GitHubTransport(
            token=token,
            config=self._config,
            base_url=base_url,
        )
        self._redactor = LogRedactor(repository_root)

    @classmethod
    def from_environment(
        cls,
        *,
        config: AcquisitionConfig | None = None,
        repository_root: str | None = None,
        base_url: str = "https://api.github.com",
    ) -> GitHubActionsProvider:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        return cls(
            token=token,
            config=config,
            repository_root=repository_root,
            base_url=base_url,
        )

    async def identify_failed_run(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> FailedRun:
        owner, name = _repository_parts(repository)
        document, _ = await self._transport.get_json(
            f"/repos/{quote(owner)}/{quote(name)}/actions/runs/{quote(run_id)}"
        )
        return parse_run(
            document,
            repository=repository,
        )

    async def retrieve_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> tuple[FailedJob, ...]:
        owner, name = _repository_parts(repository)
        jobs: list[FailedJob] = []
        for page in range(
            1,
            self._config.limits.maximum_pages + 1,
        ):
            document, _ = await self._transport.get_json(
                f"/repos/{quote(owner)}/{quote(name)}"
                f"/actions/runs/{quote(run_id)}/jobs"
                f"?filter=latest"
                f"&per_page={self._config.limits.page_size}"
                f"&page={page}"
            )
            page_jobs = parse_failed_jobs(
                document,
                run_id=run_id,
            )
            jobs.extend(page_jobs)
            if len(jobs) > self._config.limits.maximum_jobs_per_run:
                raise JobLimitError("run exceeded the configured job limit")
            raw_jobs = document.get("jobs")
            if not isinstance(raw_jobs, list):
                raise RemoteResponseError("GitHub jobs page is invalid")
            if len(raw_jobs) < self._config.limits.page_size:
                break
        else:
            raise PaginationLimitError(
                "GitHub jobs pagination exceeded the configured page limit"
            )
        unique = {job.job_id: job for job in jobs}
        return tuple(
            sorted(
                unique.values(),
                key=lambda job: (
                    job.name,
                    job.job_id,
                ),
            )
        )

    async def retrieve_failed_log(
        self,
        *,
        repository: str,
        run_id: str,
        job: FailedJob,
    ) -> AcquiredLog:
        owner, name = _repository_parts(repository)
        response = await self._transport.get_bytes(
            f"/repos/{quote(owner)}/{quote(name)}"
            f"/actions/jobs/{quote(job.job_id)}/logs",
            accept="application/vnd.github+json",
        )
        raw = response.body
        limit = self._config.limits.maximum_log_bytes_per_job
        exceeded_limit = len(raw) > limit
        if exceeded_limit:
            raw = raw[:limit]
        content_length = _content_length(response.headers.get("content-length"))
        assessment = assess_log_completeness(
            raw=raw,
            content_length=content_length,
            exceeded_limit=exceeded_limit,
            download_complete=True,
        )
        decoded = raw.decode(
            "utf-8",
            errors="replace",
        )
        redaction = self._redactor.redact(decoded)
        redacted_bytes = redaction.text.encode("utf-8")
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        redacted_sha256 = hashlib.sha256(redacted_bytes).hexdigest()
        retrieved_at = utc_now()
        retrieval_material: dict[str, Any] = {
            "provider": "github_actions",
            "repository": repository,
            "run_id": run_id,
            "job_id": job.job_id,
            "raw_sha256": raw_sha256,
            "retrieved_at": retrieved_at,
        }
        retrieval_id = namespaced_identity(
            "retrieval_",
            retrieval_material,
        )
        limitations = tuple(
            sorted(
                {
                    *assessment.limitations,
                    *(
                        ("log redaction classes: " + ",".join(redaction.classes),)
                        if redaction.classes
                        else ()
                    ),
                }
            )
        )
        provenance = LogProvenance(
            provider="github_actions",
            api_version=self._config.api_version,
            repository=repository,
            run_id=run_id,
            job_id=job.job_id,
            retrieval_id=retrieval_id,
            retrieved_at=retrieved_at,
            etag=response.headers.get("etag"),
            content_length=content_length,
            content_type=response.headers.get("content-type"),
            raw_sha256=raw_sha256,
            redacted_sha256=redacted_sha256,
            raw_byte_count=len(raw),
            redacted_byte_count=len(redacted_bytes),
            completeness=assessment.state,
            limitations=limitations,
        )
        failed_command = job.failed_steps[0].name if job.failed_steps else None
        evidence_material = {
            "provider": "github_actions",
            "run_id": run_id,
            "job_id": job.job_id,
            "raw_sha256": raw_sha256,
            "completeness": assessment.state,
        }
        evidence = CIRunEvidence(
            evidence_id=namespaced_identity(
                "evidence_",
                evidence_material,
            ),
            provider="github_actions",
            run_id=run_id,
            job_id=job.job_id,
            job_name=job.name,
            failed_command=failed_command,
            conclusion=_normalize_conclusion(job.conclusion),
            log_sha256=raw_sha256,
            log_size_bytes=len(raw),
            log_completeness=assessment.state,
            authority_class="RUNTIME_LOG",
            artifact_provenance={
                "source": ("github_actions_job_log"),
                "retrieval_id": retrieval_id,
                "retrieved_at": retrieved_at,
            },
            observed_at=retrieved_at,
            limitations=limitations,
        )
        return AcquiredLog(
            evidence=evidence,
            provenance=provenance,
            redacted_text=redaction.text,
        )


def _repository_parts(
    repository: str,
) -> tuple[str, str]:
    parts = repository.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("repository must use owner/name format")
    return parts[0], parts[1]


def _content_length(
    value: str | None,
) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _normalize_conclusion(
    value: str,
) -> str:
    allowed = {
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
    }
    return value if value in allowed else "unknown"
