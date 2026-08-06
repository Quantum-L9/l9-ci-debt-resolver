from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from l9_debt_resolver.classification.models import (
    ClassificationSignal,
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import RepositoryCorrelation
from l9_debt_resolver.feedback.builder import build_feedback_event
from l9_debt_resolver.feedback.delivery import FeedbackDeliveryService
from l9_debt_resolver.feedback.file_transport import (
    JSONFileFeedbackTransport,
)
from l9_debt_resolver.feedback.outbox import FeedbackOutbox
from l9_debt_resolver.remote.ledger import AttemptLedger
from l9_debt_resolver.remote.models import (
    PushAuthorization,
    RerunObservation,
)
from l9_debt_resolver.remote.policy import deterministic_branch_name
from l9_debt_resolver.resolution.models import ResolutionOutcome
from l9_debt_resolver.runtime import capabilities as capabilities_module
from l9_debt_resolver.runtime import diagnosis_service
from l9_debt_resolver.runtime.capabilities import resolver_capabilities
from l9_debt_resolver.runtime.correlation_service import (
    CorrelationAndClassificationResult,
    ResolverCorrelationRuntime,
)
from l9_debt_resolver.runtime.feedback_service import ResolverFeedbackService
from l9_debt_resolver.runtime.remote_resolution_service import (
    RemoteResolutionService,
)
from l9_debt_resolver.sdk.document_adapter import (
    DocumentSDKKnowledgeProvider,
)
from tests.correlation.test_service import SDK_document, bundle

PSEUDONYM_KEY = b"p" * 32


@pytest.mark.asyncio
async def test_correlation_runtime_execute() -> None:
    runtime = ResolverCorrelationRuntime(
        SDK=DocumentSDKKnowledgeProvider(SDK_document())
    )
    result = await runtime.execute(bundle())
    assert isinstance(result, CorrelationAndClassificationResult)
    assert result.correlation.repository_snapshot_id == "snapshot-1"
    assert result.classification.category == "test_failure"
    document = result.as_dict()
    assert document["schema_version"] == ("l9.correlation-classification-result/v1")
    assert "correlation" in document
    assert "classification" in document


def test_diagnosis_service_reexports_runtime() -> None:
    assert diagnosis_service.ResolverCorrelationRuntime is ResolverCorrelationRuntime
    assert (
        diagnosis_service.CorrelationAndClassificationResult
        is CorrelationAndClassificationResult
    )
    assert set(diagnosis_service.__all__) == {
        "CorrelationAndClassificationResult",
        "ResolverCorrelationRuntime",
    }


def test_resolver_capabilities_shape() -> None:
    capabilities = resolver_capabilities()
    assert capabilities == capabilities_module.resolver_capabilities()
    assert capabilities["schema_version"] == "l9.resolver-capabilities/v1"
    assert capabilities["phase"] == "RESOLVER-P6"
    grants = capabilities["capabilities"]
    assert grants["PR_Repair_delegation"] is True
    assert grants["automatic_merge"] is False
    assert grants["PR_Repair_push_authority"] is False
    assert isinstance(capabilities["limitations"], list)
    assert capabilities["limitations"]


async def _real_event() -> tuple[
    RepositoryCorrelation,
    ClassificationTrace,
]:
    runtime = ResolverCorrelationRuntime(
        SDK=DocumentSDKKnowledgeProvider(SDK_document())
    )
    result = await runtime.execute(bundle())
    return result.correlation, result.classification


def _outcome() -> ResolutionOutcome:
    return ResolutionOutcome(
        outcome_id="resolution_outcome_" + "1" * 64,
        attempt_id="remote_attempt_" + "2" * 64,
        terminal_state="clean",
        original_failure_fingerprint="failure_" + "b" * 64,
        observed_failure_fingerprint=None,
        repository="Quantum-L9/example",
        branch="resolver/x/attempt-1",
        commit_sha="a" * 40,
        original_run_id="100",
        rerun_id="rerun-1",
        evidence_ids=("evidence_" + "a" * 64,),
        limitations=(),
    )


@pytest.mark.asyncio
async def test_feedback_service_publish_and_drain(tmp_path: Path) -> None:
    correlation, classification = await _real_event()
    event = build_feedback_event(
        repository="Quantum-L9/example",
        pseudonym_key=PSEUDONYM_KEY,
        provider="github_actions",
        resolver_version="0.6.0",
        attempt_number=1,
        classification_trace=classification,
        correlation=correlation,
        resolution_outcome=_outcome(),
        remediation_class="bounded_source",
        changed_file_count=1,
        changed_line_count=5,
        validation_result="passed",
        validation_result_id="validation-result-1",
        validation_step_count=4,
        validation_duration_bucket="10_60s",
        graph_delta_accepted=True,
        remediation_plan_id="remediation_plan_" + "1" * 64,
    )
    delivery = FeedbackDeliveryService(
        outbox=FeedbackOutbox(directory=tmp_path / "outbox"),
        transport=JSONFileFeedbackTransport(directory=tmp_path / "sink"),
    )
    service = ResolverFeedbackService(delivery)
    receipt = await service.publish(event)
    assert receipt.status == "delivered"
    assert receipt.event_id == event.event_id
    drained = await service.drain_outbox()
    assert isinstance(drained, tuple)


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _remote_trace() -> ClassificationTrace:
    return ClassificationTrace(
        classification_id="classification_" + "a" * 64,
        failure_fingerprint="failure_" + "b" * 64,
        category="test_failure",
        confidence=0.95,
        evidence_ids=("evidence_" + "c" * 64,),
        matched_signals=(
            ClassificationSignal(
                signal="1 failed",
                category="test_failure",
                weight=0.95,
                source="failed_log",
            ),
        ),
        failed_command="pytest",
        repository_snapshot_id="snapshot-1",
        affected_entities=(),
        related_tests=(),
        applicable_contracts=(),
        correlated_finding_ids=(),
        remediation_eligibility="automatic",
        limitations=(),
    )


class _FakeRerunProvider:
    def __init__(self) -> None:
        self.dispatched: tuple[str, str] | None = None
        self.observed_head: str | None = None

    async def dispatch_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> None:
        self.dispatched = (repository, run_id)

    async def observe(
        self,
        *,
        repository: str,
        original_run_id: str,
        expected_head_sha: str,
    ) -> RerunObservation:
        self.observed_head = expected_head_sha
        return RerunObservation(
            observation_id="rerun_observation_" + "1" * 64,
            provider="github_actions",
            repository=repository,
            original_run_id=original_run_id,
            rerun_id="rerun-1",
            status="completed",
            conclusion="success",
            head_sha=expected_head_sha,
            started_at="2026-07-19T00:00:00Z",
            completed_at="2026-07-19T00:01:00Z",
            poll_count=1,
            limitations=(),
        )


@pytest.mark.asyncio
async def test_remote_resolution_execute_happy_path(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    remote_path = tmp_path / "remote.git"
    _git(workspace, "init")
    _git(workspace, "config", "user.email", "test@example.invalid")
    _git(workspace, "config", "user.name", "Test")
    target = workspace / "app.py"
    target.write_text("before\n", encoding="utf-8")
    _git(workspace, "add", "app.py")
    _git(workspace, "commit", "--no-gpg-sign", "-m", "initial")
    _git(remote_path.parent, "init", "--bare", str(remote_path))
    _git(workspace, "remote", "add", "origin", str(remote_path))
    base_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    target.write_text("after\n", encoding="utf-8")

    trace = _remote_trace()
    branch = deterministic_branch_name(
        failure_fingerprint=trace.failure_fingerprint,
        attempt_number=1,
    )
    expires = (
        (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    )
    authorization = PushAuthorization(
        authorization_id="push_authorization_" + "d" * 44,
        repository="Quantum-L9/example",
        remote="origin",
        branch=branch,
        expires_at=expires,
    )
    provider = _FakeRerunProvider()
    ledger = AttemptLedger(path=tmp_path / "attempt-ledger.json")
    service = RemoteResolutionService(
        rerun_provider=provider,
        attempt_ledger=ledger,
    )
    attempt, outcome = await service.execute(
        workspace_root=workspace,
        repository="Quantum-L9/example",
        remote="origin",
        original_run_id="100",
        classification_trace=trace,
        remediation_plan_id="remediation_plan_" + "1" * 64,
        validation_result_id="validation-result-1",
        base_revision=base_revision,
        expected_changed_paths=("app.py",),
        push_authorization=authorization,
        observed_failure_fingerprint=None,
    )
    assert outcome.terminal_state == "clean"
    assert outcome.rerun_id == "rerun-1"
    assert attempt.status == "completed"
    assert attempt.branch == branch
    assert attempt.attempt_number == 1
    assert provider.dispatched == ("Quantum-L9/example", "100")
    assert {record.operation for record in attempt.operations} == {
        "verify_workspace",
        "create_branch",
        "commit",
        "push",
        "dispatch_rerun",
        "observe_rerun",
    }
