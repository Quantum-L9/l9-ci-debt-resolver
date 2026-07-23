from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.remote.git import GitRepository
from l9_debt_resolver.remote.ledger import AttemptLedger
from l9_debt_resolver.remote.models import (
    PushAuthorization,
    RemoteAttempt,
    RemoteOperationRecord,
)
from l9_debt_resolver.remote.policy import (
    deterministic_branch_name,
    validate_branch_name,
    validate_push_authorization,
)
from l9_debt_resolver.resolution.models import (
    ResolutionOutcome,
)
from l9_debt_resolver.resolution.terminal import (
    determine_terminal_state,
)


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


class RemoteResolutionService:
    def __init__(
        self,
        *,
        rerun_provider: object,
        attempt_ledger: AttemptLedger,
    ) -> None:
        self._rerun_provider = rerun_provider
        self._ledger = attempt_ledger

    async def execute(
        self,
        *,
        workspace_root: Path,
        repository: str,
        remote: str,
        original_run_id: str,
        classification_trace: ClassificationTrace,
        remediation_plan_id: str,
        validation_result_id: str,
        base_revision: str,
        expected_changed_paths: tuple[str, ...],
        push_authorization: PushAuthorization,
        observed_failure_fingerprint: (str | None) = None,
    ) -> tuple[
        RemoteAttempt,
        ResolutionOutcome,
    ]:
        classification = classification_trace.classification
        attempt_number = self._ledger.next_attempt(classification.failure_fingerprint)
        branch = deterministic_branch_name(
            failure_fingerprint=(classification.failure_fingerprint),
            attempt_number=attempt_number,
        )
        validate_branch_name(branch)
        validate_push_authorization(
            authorization=push_authorization,
            repository=repository,
            remote=remote,
            branch=branch,
        )
        started_at = utc_now()
        operations = []
        repository_adapter = GitRepository(workspace_root=workspace_root)
        await repository_adapter.verify_revision(base_revision)
        await repository_adapter.verify_expected_changes(expected_changed_paths)
        operations.append(
            RemoteOperationRecord(
                operation="verify_workspace",
                result="passed",
                observed_at=utc_now(),
                metadata={"changed_paths": list(expected_changed_paths)},
            )
        )
        await repository_adapter.create_branch(branch)
        operations.append(
            RemoteOperationRecord(
                operation="create_branch",
                result="passed",
                observed_at=utc_now(),
                metadata={"branch": branch},
            )
        )
        await repository_adapter.stage_paths(expected_changed_paths)
        commit_message = (
            "RESOLVER-P4 bounded remediation\n\n"
            f"Failure-Fingerprint: "
            f"{classification.failure_fingerprint}\n"
            f"Classification-ID: "
            f"{classification.classification_id}\n"
            f"Remediation-Plan-ID: "
            f"{remediation_plan_id}\n"
            f"Validation-Result-ID: "
            f"{validation_result_id}\n"
        )
        commit_sha = await repository_adapter.commit(
            message=commit_message,
            author_name="Quantum-L9 Resolver",
            author_email="resolver@invalid.local",
        )
        operations.append(
            RemoteOperationRecord(
                operation="commit",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "commit_sha": commit_sha,
                },
            )
        )
        await repository_adapter.push(
            remote=remote,
            branch=branch,
        )
        operations.append(
            RemoteOperationRecord(
                operation="push",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "remote": remote,
                    "branch": branch,
                },
            )
        )
        await self._rerun_provider.dispatch_failed_jobs(
            repository=repository,
            run_id=original_run_id,
        )
        operations.append(
            RemoteOperationRecord(
                operation="dispatch_rerun",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "original_run_id": original_run_id,
                },
            )
        )
        observation = await self._rerun_provider.observe(
            repository=repository,
            original_run_id=original_run_id,
            expected_head_sha=commit_sha,
        )
        operations.append(
            RemoteOperationRecord(
                operation="observe_rerun",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "rerun_id": observation.rerun_id,
                    "status": observation.status,
                    "conclusion": observation.conclusion,
                },
            )
        )
        attempt_id = namespaced_identity(
            "remote_attempt_",
            {
                "failure_fingerprint": (classification.failure_fingerprint),
                "attempt_number": attempt_number,
                "repository": repository,
                "branch": branch,
                "commit_sha": commit_sha,
                "original_run_id": original_run_id,
                "rerun_id": observation.rerun_id,
            },
        )
        attempt = RemoteAttempt(
            attempt_id=attempt_id,
            failure_fingerprint=(classification.failure_fingerprint),
            attempt_number=attempt_number,
            repository=repository,
            base_revision=base_revision,
            branch=branch,
            remote=remote,
            commit_sha=commit_sha,
            original_run_id=original_run_id,
            rerun_id=observation.rerun_id,
            status="completed",
            started_at=started_at,
            completed_at=utc_now(),
            operations=tuple(operations),
            limitations=observation.limitations,
        )
        terminal_state = determine_terminal_state(
            rerun_conclusion=observation.conclusion,
            original_fingerprint=(classification.failure_fingerprint),
            observed_fingerprint=(observed_failure_fingerprint),
        )
        outcome = ResolutionOutcome(
            outcome_id=namespaced_identity(
                "resolution_outcome_",
                {
                    "attempt_id": attempt_id,
                    "terminal_state": terminal_state,
                    "original_fingerprint": (classification.failure_fingerprint),
                    "observed_fingerprint": (observed_failure_fingerprint),
                    "rerun_id": observation.rerun_id,
                },
            ),
            attempt_id=attempt_id,
            terminal_state=terminal_state,
            original_failure_fingerprint=(classification.failure_fingerprint),
            observed_failure_fingerprint=(observed_failure_fingerprint),
            repository=repository,
            branch=branch,
            commit_sha=commit_sha,
            original_run_id=original_run_id,
            rerun_id=observation.rerun_id,
            evidence_ids=(classification.evidence_ids),
            limitations=observation.limitations,
        )
        return attempt, outcome
