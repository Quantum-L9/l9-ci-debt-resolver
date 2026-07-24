from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from l9_debt_resolver.contracts.models import CIRunEvidence


@dataclass(frozen=True)
class FailedRun:
    provider: str
    repository: str
    run_id: str
    status: str
    conclusion: str | None
    head_sha: str
    event: str
    workflow_id: str | None
    created_at: str | None
    updated_at: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "repository": self.repository,
            "run_id": self.run_id,
            "status": self.status,
            "conclusion": self.conclusion,
            "head_sha": self.head_sha,
            "event": self.event,
            "workflow_id": self.workflow_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class FailedStep:
    number: int
    name: str
    conclusion: str


@dataclass(frozen=True)
class FailedJob:
    provider: str
    run_id: str
    job_id: str
    name: str
    status: str
    conclusion: str
    started_at: str | None
    completed_at: str | None
    runner_name: str | None
    labels: tuple[str, ...]
    failed_steps: tuple[FailedStep, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.failed-job/v1",
            "provider": self.provider,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "name": self.name,
            "status": self.status,
            "conclusion": self.conclusion,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "runner_name": self.runner_name,
            "labels": list(self.labels),
            "failed_steps": [
                {
                    "number": step.number,
                    "name": step.name,
                    "conclusion": step.conclusion,
                }
                for step in self.failed_steps
            ],
        }


@dataclass(frozen=True)
class LogProvenance:
    provider: str
    api_version: str
    repository: str
    run_id: str
    job_id: str
    retrieval_id: str
    retrieved_at: str
    etag: str | None
    content_length: int | None
    content_type: str | None
    raw_sha256: str
    redacted_sha256: str
    raw_byte_count: int
    redacted_byte_count: int
    completeness: str
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.log-provenance/v1",
            "provider": self.provider,
            "api_version": self.api_version,
            "repository": self.repository,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "retrieval_id": self.retrieval_id,
            "retrieved_at": self.retrieved_at,
            "etag": self.etag,
            "content_length": self.content_length,
            "content_type": self.content_type,
            "raw_sha256": self.raw_sha256,
            "redacted_sha256": self.redacted_sha256,
            "raw_byte_count": self.raw_byte_count,
            "redacted_byte_count": self.redacted_byte_count,
            "completeness": self.completeness,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class AcquiredLog:
    evidence: CIRunEvidence
    provenance: LogProvenance
    redacted_text: str


@dataclass(frozen=True)
class AcquisitionReport:
    acquisition_id: str
    provider: str
    repository: str
    run_id: str
    run_status: str
    run_conclusion: str | None
    failed_job_count: int
    evidence: tuple[CIRunEvidence, ...]
    total_raw_bytes: int
    terminal_state: str
    started_at: str
    completed_at: str
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        complete_count = sum(
            item.log_completeness == "complete" for item in self.evidence
        )
        return {
            "schema_version": "l9.acquisition-report/v1",
            "acquisition_id": self.acquisition_id,
            "provider": self.provider,
            "repository": self.repository,
            "run_id": self.run_id,
            "run_status": self.run_status,
            "run_conclusion": self.run_conclusion,
            "failed_job_count": self.failed_job_count,
            "evidence_count": len(self.evidence),
            "complete_evidence_count": complete_count,
            "total_raw_bytes": self.total_raw_bytes,
            "terminal_state": self.terminal_state,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "evidence": [item.as_dict() for item in self.evidence],
            "limitations": list(self.limitations),
        }
