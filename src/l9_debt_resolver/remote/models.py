from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PushAuthorization:
    authorization_id: str
    repository: str
    remote: str
    branch: str
    expires_at: str


@dataclass(frozen=True)
class RemoteOperationRecord:
    operation: str
    result: str
    observed_at: str
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "result": self.result,
            "observed_at": self.observed_at,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class RemoteAttempt:
    attempt_id: str
    failure_fingerprint: str
    attempt_number: int
    repository: str
    base_revision: str
    branch: str
    remote: str
    commit_sha: str | None
    original_run_id: str
    rerun_id: str | None
    status: str
    started_at: str
    completed_at: str | None
    operations: tuple[RemoteOperationRecord, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.remote-attempt/v1",
            "attempt_id": self.attempt_id,
            "failure_fingerprint": self.failure_fingerprint,
            "attempt_number": self.attempt_number,
            "repository": self.repository,
            "base_revision": self.base_revision,
            "branch": self.branch,
            "remote": self.remote,
            "commit_sha": self.commit_sha,
            "original_run_id": self.original_run_id,
            "rerun_id": self.rerun_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "operations": [operation.as_dict() for operation in self.operations],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class RerunObservation:
    observation_id: str
    provider: str
    repository: str
    original_run_id: str
    rerun_id: str
    status: str
    conclusion: str | None
    head_sha: str
    started_at: str
    completed_at: str | None
    poll_count: int
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.rerun-observation/v1",
            "observation_id": self.observation_id,
            "provider": self.provider,
            "repository": self.repository,
            "original_run_id": self.original_run_id,
            "rerun_id": self.rerun_id,
            "status": self.status,
            "conclusion": self.conclusion,
            "head_sha": self.head_sha,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "poll_count": self.poll_count,
            "limitations": list(self.limitations),
        }
