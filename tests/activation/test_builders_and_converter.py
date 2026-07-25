from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from l9_debt_resolver.classification.engine import RootCauseClassifier
from l9_debt_resolver.classification.models import ClassificationTrace
from l9_debt_resolver.correlation.models import RepositoryCorrelation
from l9_debt_resolver.correlation.service import (
    RepositoryCorrelationService,
)
from l9_debt_resolver.delegation.builder import (
    _confidence_bucket as delegation_confidence_bucket,
)
from l9_debt_resolver.delegation.builder import build_pr_repair_request
from l9_debt_resolver.delegation.converter import (
    convert_proposal_to_remediation_plan,
)
from l9_debt_resolver.delegation.errors import (
    DelegationNotEligibleError,
    DelegationProposalError,
)
from l9_debt_resolver.delegation.identity import (
    proposal_signature,
    stable_hash,
)
from l9_debt_resolver.delegation.ledger import DelegationLedger
from l9_debt_resolver.delegation.models import (
    PRRepairOperation,
    PRRepairProposal,
    PRRepairRequest,
)
from l9_debt_resolver.delegation.nonce_ledger import CallbackNonceLedger
from l9_debt_resolver.feedback.builder import (
    _changed_line_bucket,
    _confidence_bucket,
    build_feedback_event,
)
from l9_debt_resolver.remediation.models import RemediationPlan
from l9_debt_resolver.resolution.models import ResolutionOutcome
from l9_debt_resolver.runtime.delegation_service import (
    DelegationCallbackService,
    utc_now,
)
from l9_debt_resolver.sdk.document_adapter import (
    DocumentSDKKnowledgeProvider,
)
from tests.correlation.test_service import SDK_document, bundle

PSEUDONYM_KEY = b"p" * 32
PATH_TOKEN_KEY = b"t" * 32
CALLBACK_KEY = b"c" * 32

FILE_TEXT = "def compute():\n    return 1\n\n\ndef helper():\n    return 2\n"
UNIQUE_FRAGMENT = "    return 1\n"
REPLACEMENT = "    return 42\n"


async def _pipeline() -> tuple[RepositoryCorrelation, ClassificationTrace]:
    provider = DocumentSDKKnowledgeProvider(SDK_document())
    correlation = await RepositoryCorrelationService(provider).correlate(bundle())
    classification = await RootCauseClassifier().classify(
        bundle=bundle(),
        correlation=correlation,
    )
    return correlation, classification


def _outcome(terminal_state: str = "clean") -> ResolutionOutcome:
    return ResolutionOutcome(
        outcome_id="resolution_outcome_" + "1" * 64,
        attempt_id="remote_attempt_" + "2" * 64,
        terminal_state=terminal_state,
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
async def test_build_feedback_event_is_schema_valid() -> None:
    correlation, classification = await _pipeline()
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
    assert event.event_type == "resolution_succeeded"
    assert event.event_id.startswith("feedback_event_")
    assert event.repository_pseudonym.startswith("repository_")
    assert event.resolution["remote_push_performed"] is True
    assert event.correlation["entity_count"] == 1


@pytest.mark.asyncio
async def test_build_feedback_event_unsupported_terminal_state() -> None:
    correlation, classification = await _pipeline()
    outcome = replace(
        _outcome("unsupported"),
        commit_sha=None,
        rerun_id=None,
    )
    event = build_feedback_event(
        repository="Quantum-L9/example",
        pseudonym_key=PSEUDONYM_KEY,
        provider="github_actions",
        resolver_version="0.6.0",
        attempt_number=2,
        classification_trace=classification,
        correlation=correlation,
        resolution_outcome=outcome,
        remediation_class=None,
        changed_file_count=-3,
        changed_line_count=None,
        validation_result="not_run",
        validation_result_id=None,
        validation_step_count=0,
        validation_duration_bucket="unknown",
        graph_delta_accepted=None,
        remediation_plan_id=None,
    )
    assert event.event_type == "unsupported"
    assert event.resolution["changed_file_count"] == 0
    assert event.resolution["changed_line_bucket"] == "unknown"
    assert event.resolution["remote_push_performed"] is False


def test_feedback_bucket_helpers_cover_branches() -> None:
    assert _confidence_bucket(0.99) == "very_high"
    assert _confidence_bucket(0.92) == "high"
    assert _confidence_bucket(0.75) == "medium"
    assert _confidence_bucket(0.10) == "low"
    assert _changed_line_bucket(None) == "unknown"
    assert _changed_line_bucket(0) == "0"
    assert _changed_line_bucket(5) == "1_10"
    assert _changed_line_bucket(30) == "11_50"
    assert _changed_line_bucket(80) == "51_100"
    assert _changed_line_bucket(200) == "101_250"
    assert _changed_line_bucket(400) == "251_500"
    assert _changed_line_bucket(9000) == "gt_500"


def test_delegation_confidence_bucket_cover_branches() -> None:
    assert delegation_confidence_bucket(0.99) == "very_high"
    assert delegation_confidence_bucket(0.91) == "high"
    assert delegation_confidence_bucket(0.80) == "medium"
    assert delegation_confidence_bucket(0.30) == "low"


async def _delegation_setup() -> tuple[
    RepositoryCorrelation,
    ClassificationTrace,
    PRRepairRequest,
    dict[str, str],
]:
    correlation, classification = await _pipeline()
    eligible = replace(
        classification,
        remediation_eligibility="approval_required",
    )
    request, token_map = build_pr_repair_request(
        repository="Quantum-L9/example",
        repository_pseudonym_key=PSEUDONYM_KEY,
        path_token_key=PATH_TOKEN_KEY,
        allowed_paths=("src/app.py",),
        classification_trace=eligible,
        correlation=correlation,
        normalized_error_signatures=("assertion failed",),
    )
    return correlation, eligible, request, token_map


@pytest.mark.asyncio
async def test_build_pr_repair_request_is_schema_valid() -> None:
    _, _, request, token_map = await _delegation_setup()
    assert request.request_id.startswith("pr_repair_request_")
    assert request.classification["remediation_eligibility"] == "approval_required"
    assert list(token_map) == request.repository_context["allowed_path_tokens"]
    assert request.constraints["remote_authority_granted"] is False


@pytest.mark.asyncio
async def test_build_pr_repair_request_rejects_automatic() -> None:
    correlation, classification = await _pipeline()
    automatic = replace(classification, remediation_eligibility="automatic")
    with pytest.raises(DelegationNotEligibleError):
        build_pr_repair_request(
            repository="Quantum-L9/example",
            repository_pseudonym_key=PSEUDONYM_KEY,
            path_token_key=PATH_TOKEN_KEY,
            allowed_paths=("src/app.py",),
            classification_trace=automatic,
            correlation=correlation,
            normalized_error_signatures=(),
        )


@pytest.mark.asyncio
async def test_build_pr_repair_request_requires_evidence() -> None:
    correlation, classification = await _pipeline()
    eligible = replace(
        classification,
        remediation_eligibility="approval_required",
        evidence_ids=(),
    )
    with pytest.raises(DelegationNotEligibleError):
        build_pr_repair_request(
            repository="Quantum-L9/example",
            repository_pseudonym_key=PSEUDONYM_KEY,
            path_token_key=PATH_TOKEN_KEY,
            allowed_paths=("src/app.py",),
            classification_trace=eligible,
            correlation=correlation,
            normalized_error_signatures=(),
        )


@pytest.mark.asyncio
async def test_build_pr_repair_request_requires_snapshot() -> None:
    correlation, classification = await _pipeline()
    eligible = replace(classification, remediation_eligibility="approval_required")
    without_snapshot = replace(correlation, repository_snapshot_id="")
    with pytest.raises(DelegationNotEligibleError):
        build_pr_repair_request(
            repository="Quantum-L9/example",
            repository_pseudonym_key=PSEUDONYM_KEY,
            path_token_key=PATH_TOKEN_KEY,
            allowed_paths=("src/app.py",),
            classification_trace=eligible,
            correlation=without_snapshot,
            normalized_error_signatures=(),
        )


@pytest.mark.asyncio
async def test_convert_rejects_file_hash_mismatch(tmp_path: Path) -> None:
    _, classification, request, token_map = await _delegation_setup()
    token = next(iter(token_map))
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir(parents=True)
    target.write_text("def compute():\n    return 999\n", encoding="utf-8")
    proposal = _signed_proposal(
        request=request,
        classification=classification,
        token=token,
        status="proposed",
    )
    with pytest.raises(DelegationProposalError):
        convert_proposal_to_remediation_plan(
            workspace_root=tmp_path,
            request=request,
            proposal=proposal,
            path_token_map=token_map,
            classification_trace=classification,
            repository_snapshot_id="snapshot-1",
            repository_revision="abcdef1234567",
            validation_plan_id="validation-plan-1",
        )


@pytest.mark.asyncio
async def test_convert_rejects_missing_target(tmp_path: Path) -> None:
    _, classification, request, token_map = await _delegation_setup()
    proposal = _signed_proposal(
        request=request,
        classification=classification,
        token=next(iter(token_map)),
        status="proposed",
    )
    with pytest.raises(DelegationProposalError):
        convert_proposal_to_remediation_plan(
            workspace_root=tmp_path,
            request=request,
            proposal=proposal,
            path_token_map=token_map,
            classification_trace=classification,
            repository_snapshot_id="snapshot-1",
            repository_revision="abcdef1234567",
            validation_plan_id="validation-plan-1",
        )


def _proposal_operation(
    *,
    token: str,
    classification: ClassificationTrace,
) -> PRRepairOperation:
    file_hash = hashlib.sha256(FILE_TEXT.encode("utf-8")).hexdigest()
    text_hash = hashlib.sha256(UNIQUE_FRAGMENT.encode("utf-8")).hexdigest()
    replacement_hash = hashlib.sha256(REPLACEMENT.encode("utf-8")).hexdigest()
    evidence_hashes = tuple(
        sorted(
            stable_hash(evidence_id)
            for evidence_id in classification.evidence_ids
        )
    )
    return PRRepairOperation(
        operation_id="pr_repair_operation_" + "9" * 44,
        path_token=token,
        expected_file_sha256=file_hash,
        expected_text_sha256=text_hash,
        replacement_text=REPLACEMENT,
        replacement_sha256=replacement_hash,
        evidence_id_hashes=evidence_hashes,
        justification="tighten bounded fragment",
    )


def _signed_proposal(
    *,
    request: PRRepairRequest,
    classification: ClassificationTrace,
    token: str,
    status: str,
) -> PRRepairProposal:
    operations = (
        (_proposal_operation(token=token, classification=classification),)
        if status == "proposed"
        else ()
    )
    validation_classes = (
        (
            "affected_contract",
            "graph_delta",
            "original_failure",
            "targeted_test",
        )
        if status == "proposed"
        else ()
    )
    base = PRRepairProposal(
        proposal_id="pr_repair_proposal_" + "a" * 64,
        request_id=request.request_id,
        failure_fingerprint=request.failure_fingerprint,
        snapshot_id_hash=stable_hash("snapshot-1"),
        status=status,
        remediation_class="bounded_source" if status == "proposed" else None,
        operations=operations,
        requested_validation_classes=validation_classes,
        rationale="bounded remediation proposal",
        limitations=("delegated_scope",),
        issued_at=utc_now(),
        callback_nonce=request.callback["nonce"],
        signature="",
    )
    return replace(
        base,
        signature=proposal_signature(
            unsigned_document=base.unsigned_dict(),
            callback_key=CALLBACK_KEY,
        ),
    )


@pytest.mark.asyncio
async def test_convert_proposal_to_remediation_plan(tmp_path: Path) -> None:
    _, classification, request, token_map = await _delegation_setup()
    token = next(iter(token_map))
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir(parents=True)
    target.write_text(FILE_TEXT, encoding="utf-8")
    proposal = _signed_proposal(
        request=request,
        classification=classification,
        token=token,
        status="proposed",
    )
    plan = convert_proposal_to_remediation_plan(
        workspace_root=tmp_path,
        request=request,
        proposal=proposal,
        path_token_map=token_map,
        classification_trace=classification,
        repository_snapshot_id="snapshot-1",
        repository_revision="abcdef1234567",
        validation_plan_id="validation-plan-1",
    )
    assert isinstance(plan, RemediationPlan)
    assert plan.plan_id.startswith("remediation_plan_")
    assert plan.expected_changed_paths == ("src/app.py",)
    assert plan.operations[0].replacement_text == REPLACEMENT
    assert plan.operations[0].expected_text == UNIQUE_FRAGMENT


@pytest.mark.asyncio
async def test_convert_rejects_unsupported_status(tmp_path: Path) -> None:
    _, classification, request, token_map = await _delegation_setup()
    proposal = _signed_proposal(
        request=request,
        classification=classification,
        token=next(iter(token_map)),
        status="unsupported",
    )
    with pytest.raises(DelegationProposalError):
        convert_proposal_to_remediation_plan(
            workspace_root=tmp_path,
            request=request,
            proposal=proposal,
            path_token_map=token_map,
            classification_trace=classification,
            repository_snapshot_id="snapshot-1",
            repository_revision="abcdef1234567",
            validation_plan_id="validation-plan-1",
        )


@pytest.mark.asyncio
async def test_delegation_service_accepts_proposed(tmp_path: Path) -> None:
    _, classification, request, token_map = await _delegation_setup()
    token = next(iter(token_map))
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir(parents=True)
    target.write_text(FILE_TEXT, encoding="utf-8")
    ledger = DelegationLedger(directory=tmp_path / "ledger")
    nonce_ledger = CallbackNonceLedger(path=tmp_path / "nonce.json")
    record = ledger.create(request)
    service = DelegationCallbackService(
        ledger=ledger,
        nonce_ledger=nonce_ledger,
    )
    proposal = _signed_proposal(
        request=request,
        classification=classification,
        token=token,
        status="proposed",
    )
    updated, plan = service.accept_proposal(
        record=record,
        proposal=proposal,
        callback_key=CALLBACK_KEY,
        workspace_root=tmp_path,
        path_token_map=token_map,
        classification_trace=classification,
        repository_snapshot_id="snapshot-1",
        repository_revision="abcdef1234567",
        validation_plan_id="validation-plan-1",
    )
    assert updated.state == "proposal_accepted"
    assert updated.proposal_id == proposal.proposal_id
    assert plan is not None
    assert plan.expected_changed_paths == ("src/app.py",)
    assert ledger.get(record.record_id).state == "proposal_accepted"


@pytest.mark.asyncio
async def test_delegation_service_accepts_unsupported(tmp_path: Path) -> None:
    _, classification, request, token_map = await _delegation_setup()
    ledger = DelegationLedger(directory=tmp_path / "ledger")
    nonce_ledger = CallbackNonceLedger(path=tmp_path / "nonce.json")
    record = ledger.create(request)
    service = DelegationCallbackService(
        ledger=ledger,
        nonce_ledger=nonce_ledger,
    )
    proposal = _signed_proposal(
        request=request,
        classification=classification,
        token=next(iter(token_map)),
        status="unsupported",
    )
    updated, plan = service.accept_proposal(
        record=record,
        proposal=proposal,
        callback_key=CALLBACK_KEY,
        workspace_root=tmp_path,
        path_token_map=token_map,
        classification_trace=classification,
        repository_snapshot_id="snapshot-1",
        repository_revision="abcdef1234567",
        validation_plan_id="validation-plan-1",
    )
    assert updated.state == "unsupported"
    assert updated.terminal_state == "delegation_unsupported"
    assert plan is None
