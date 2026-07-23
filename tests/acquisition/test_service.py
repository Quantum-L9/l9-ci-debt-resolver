from __future__ import annotations

import hashlib

import pytest

from l9_debt_resolver.acquisition.models import (
    AcquiredLog,
    FailedJob,
    FailedRun,
    FailedStep,
    LogProvenance,
)
from l9_debt_resolver.acquisition.service import (
    FailedLogAcquisitionService,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)


class Provider:
    def __init__(self, completeness: str) -> None:
        self.completeness = completeness

    async def identify_failed_run(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> FailedRun:
        return FailedRun(
            provider="github_actions",
            repository=repository,
            run_id=run_id,
            status="completed",
            conclusion="failure",
            head_sha="a" * 40,
            event="pull_request",
            workflow_id="10",
            created_at=None,
            updated_at=None,
        )

    async def retrieve_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> tuple[FailedJob, ...]:
        del repository
        return (
            FailedJob(
                provider="github_actions",
                run_id=run_id,
                job_id="200",
                name="test",
                status="completed",
                conclusion="failure",
                started_at=None,
                completed_at=None,
                runner_name=None,
                labels=(),
                failed_steps=(
                    FailedStep(
                        number=1,
                        name="pytest",
                        conclusion="failure",
                    ),
                ),
            ),
        )

    async def retrieve_failed_log(
        self,
        *,
        repository: str,
        run_id: str,
        job: FailedJob,
    ) -> AcquiredLog:
        raw_hash = hashlib.sha256(b"log").hexdigest()
        evidence = CIRunEvidence(
            evidence_id="evidence_" + "a" * 64,
            provider="github_actions",
            run_id=run_id,
            job_id=job.job_id,
            job_name=job.name,
            failed_command="pytest",
            conclusion="failure",
            log_sha256=raw_hash,
            log_size_bytes=3,
            log_completeness=self.completeness,
            authority_class="RUNTIME_LOG",
            artifact_provenance={
                "source": "github_actions_job_log",
                "retrieval_id": ("retrieval_" + "b" * 64),
                "retrieved_at": ("2026-07-18T00:00:00Z"),
            },
            observed_at="2026-07-18T00:00:00Z",
            limitations=(),
        )
        provenance = LogProvenance(
            provider="github_actions",
            api_version="2022-11-28",
            repository=repository,
            run_id=run_id,
            job_id=job.job_id,
            retrieval_id="retrieval_" + "b" * 64,
            retrieved_at="2026-07-18T00:00:00Z",
            etag=None,
            content_length=3,
            content_type="text/plain",
            raw_sha256=raw_hash,
            redacted_sha256=raw_hash,
            raw_byte_count=3,
            redacted_byte_count=3,
            completeness=self.completeness,
            limitations=(),
        )
        return AcquiredLog(
            evidence=evidence,
            provenance=provenance,
            redacted_text="log",
        )


@pytest.mark.asyncio
async def test_complete_evidence_is_ready() -> None:
    service = FailedLogAcquisitionService(
        Provider("complete"),
        clock=lambda: "2026-07-18T00:00:00Z",
    )
    report = await service.acquire(
        repository="Quantum-L9/example",
        run_id="100",
    )
    assert report.terminal_state == "evidence_ready"


@pytest.mark.asyncio
async def test_incomplete_evidence_fails_closed() -> None:
    service = FailedLogAcquisitionService(
        Provider("truncated"),
        clock=lambda: "2026-07-18T00:00:00Z",
    )
    report = await service.acquire(
        repository="Quantum-L9/example",
        run_id="100",
    )
    assert report.terminal_state == "insufficient_log_evidence"
