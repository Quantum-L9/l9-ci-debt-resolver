from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResolutionOutcome:
    outcome_id: str
    attempt_id: str
    terminal_state: str
    original_failure_fingerprint: str
    observed_failure_fingerprint: str | None
    repository: str
    branch: str
    commit_sha: str | None
    original_run_id: str
    rerun_id: str | None
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.resolution-outcome/v1",
            "outcome_id": self.outcome_id,
            "attempt_id": self.attempt_id,
            "terminal_state": self.terminal_state,
            "original_failure_fingerprint": (self.original_failure_fingerprint),
            "observed_failure_fingerprint": (self.observed_failure_fingerprint),
            "repository": self.repository,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "original_run_id": self.original_run_id,
            "rerun_id": self.rerun_id,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
        }
