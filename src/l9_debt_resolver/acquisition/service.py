from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)

from .evidence_bundle import BundleProjection, project_bundles
from .models import (
    AcquiredLog,
    AcquisitionReport,
    FailedJob,
    FailedRun,
)


@dataclass(frozen=True)
class AcquisitionOutcome:
    """The report, plus the classification input projected from the same fetch.

    `AcquisitionReport` is the published artifact and deliberately carries no
    log body. `correlate-classify` needs one, and the body exists only during
    acquisition -- so the bundles are returned alongside the report rather than
    re-fetched later or bolted onto a contract that forbids extra fields.
    """

    report: AcquisitionReport
    projection: BundleProjection


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


class AcquisitionProvider(Protocol):
    async def identify_failed_run(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> FailedRun:
        """Retrieve provider run metadata."""

    async def retrieve_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> tuple[FailedJob, ...]:
        """Retrieve all failed jobs."""

    async def retrieve_failed_log(
        self,
        *,
        repository: str,
        run_id: str,
        job: FailedJob,
    ) -> AcquiredLog:
        """Retrieve and sanitize one failed job log."""


class FailedLogAcquisitionService:
    def __init__(
        self,
        provider: AcquisitionProvider,
        *,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self._provider = provider
        self._clock = clock

    async def acquire(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> AcquisitionReport:
        """The published acquisition report.

        Kept as the default entry point so every existing caller is unaffected;
        callers that need classification input use `acquire_with_bundles`.
        """
        outcome = await self.acquire_with_bundles(
            repository=repository,
            run_id=run_id,
        )
        return outcome.report

    async def acquire_with_bundles(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> AcquisitionOutcome:
        started_at = self._clock()
        run = await self._provider.identify_failed_run(
            repository=repository,
            run_id=run_id,
        )
        jobs = await self._provider.retrieve_failed_jobs(
            repository=repository,
            run_id=run_id,
        )
        if not jobs:
            terminal_state = (
                "clean" if run.conclusion == "success" else "insufficient_log_evidence"
            )
            completed_at = self._clock()
            return AcquisitionOutcome(
                report=AcquisitionReport(
                    acquisition_id=namespaced_identity(
                        "acquisition_",
                        {
                            "repository": repository,
                            "run_id": run_id,
                            "started_at": started_at,
                        },
                    ),
                    provider=run.provider,
                    repository=repository,
                    run_id=run_id,
                    run_status=run.status,
                    run_conclusion=run.conclusion,
                    failed_job_count=0,
                    evidence=(),
                    total_raw_bytes=0,
                    terminal_state=terminal_state,
                    started_at=started_at,
                    completed_at=completed_at,
                    limitations=(
                        ()
                        if terminal_state == "clean"
                        else ("failed run contained no retrievable failed jobs",)
                    ),
                ),
                # A clean run has nothing to classify, and a run with no
                # retrievable jobs has nothing to classify it from. Neither is
                # an error here; both are an empty projection.
                projection=project_bundles(
                    repository=repository,
                    revision=run.head_sha,
                    pairs=(),
                ),
            )
        # The job is retained beside its log. `l9.evidence-bundle/v1` requires
        # the `failed_job` object, and pairing is only knowable at the point of
        # the fetch -- evidence is sorted below, so a positional join afterwards
        # would silently mismatch jobs to logs.
        pairs: list[tuple[FailedJob, AcquiredLog]] = []
        for job in jobs:
            pairs.append(
                (
                    job,
                    await self._provider.retrieve_failed_log(
                        repository=repository,
                        run_id=run_id,
                        job=job,
                    ),
                )
            )
        acquired: list[AcquiredLog] = [item for _, item in pairs]
        evidence = tuple(
            sorted(
                (item.evidence for item in acquired),
                key=lambda item: (
                    item.run_id,
                    item.job_id,
                    item.evidence_id,
                ),
            )
        )
        complete_count = sum(item.log_completeness == "complete" for item in evidence)
        all_complete = complete_count == len(jobs)
        limitations = sorted(
            {limitation for item in evidence for limitation in item.limitations}
        )
        if not all_complete:
            limitations.append("one or more failed jobs lack complete logs")
        completed_at = self._clock()
        projection = project_bundles(
            repository=repository,
            revision=run.head_sha,
            pairs=tuple(pairs),
        )
        return AcquisitionOutcome(
            report=AcquisitionReport(
                acquisition_id=namespaced_identity(
                    "acquisition_",
                    {
                        "repository": repository,
                        "run_id": run_id,
                        "evidence_ids": [item.evidence_id for item in evidence],
                    },
                ),
                provider=run.provider,
                repository=repository,
                run_id=run_id,
                run_status=run.status,
                run_conclusion=run.conclusion,
                failed_job_count=len(jobs),
                evidence=evidence,
                total_raw_bytes=sum(
                    item.provenance.raw_byte_count for item in acquired
                ),
                terminal_state=(
                    "evidence_ready" if all_complete else "insufficient_log_evidence"
                ),
                started_at=started_at,
                completed_at=completed_at,
                limitations=tuple(sorted(set(limitations))),
            ),
            projection=projection,
        )
