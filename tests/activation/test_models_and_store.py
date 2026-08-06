from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from l9_debt_resolver.acquisition.models import (
    AcquiredLog,
    AcquisitionReport,
    LogProvenance,
)
from l9_debt_resolver.acquisition.store import AcquisitionArtifactStore
from l9_debt_resolver.contracts.models import CIRunEvidence
from l9_debt_resolver.delegation.errors import (
    DelegationExpiredError,
    DelegationProposalError,
    DelegationSignatureError,
)
from l9_debt_resolver.delegation.identity import (
    proposal_signature,
    stable_hash,
)
from l9_debt_resolver.delegation.models import (
    PRRepairOperation,
    PRRepairProposal,
)
from l9_debt_resolver.delegation.proposal import validate_proposal_contract
from l9_debt_resolver.resolution.models import ResolutionOutcome
from tests.delegation.test_file_transport import request


def test_resolution_outcome_as_dict() -> None:
    outcome = ResolutionOutcome(
        outcome_id="outcome_" + "a" * 64,
        attempt_id="attempt_" + "b" * 64,
        terminal_state="clean",
        original_failure_fingerprint="failure_" + "c" * 64,
        observed_failure_fingerprint=None,
        repository="Quantum-L9/example",
        branch="main",
        commit_sha="d" * 40,
        original_run_id="100",
        rerun_id="101",
        evidence_ids=("evidence_" + "e" * 64,),
        limitations=("partial",),
    )
    document = outcome.as_dict()
    assert document["schema_version"] == "l9.resolution-outcome/v1"
    assert document["outcome_id"] == outcome.outcome_id
    assert document["attempt_id"] == outcome.attempt_id
    assert document["terminal_state"] == "clean"
    assert document["observed_failure_fingerprint"] is None
    assert document["commit_sha"] == "d" * 40
    assert document["rerun_id"] == "101"
    assert document["evidence_ids"] == ["evidence_" + "e" * 64]
    assert document["limitations"] == ["partial"]
    assert isinstance(document["evidence_ids"], list)


def _evidence() -> CIRunEvidence:
    raw_hash = hashlib.sha256(b"log").hexdigest()
    return CIRunEvidence(
        evidence_id="evidence_" + "a" * 64,
        provider="github_actions",
        run_id="100",
        job_id="200",
        job_name="tests",
        failed_command="pytest",
        conclusion="failure",
        log_sha256=raw_hash,
        log_size_bytes=3,
        log_completeness="complete",
        authority_class="RUNTIME_LOG",
        artifact_provenance={"source": "github_actions_job_log"},
        observed_at="2026-07-18T00:00:00Z",
        limitations=(),
    )


def _provenance() -> LogProvenance:
    return LogProvenance(
        provider="github_actions",
        api_version="2022-11-28",
        repository="Quantum-L9/example",
        run_id="100",
        job_id="200",
        retrieval_id="retrieval_" + "b" * 64,
        retrieved_at="2026-07-18T00:00:00Z",
        etag=None,
        content_length=3,
        content_type="text/plain",
        raw_sha256=hashlib.sha256(b"log").hexdigest(),
        redacted_sha256=hashlib.sha256(b"log").hexdigest(),
        raw_byte_count=3,
        redacted_byte_count=3,
        completeness="complete",
        limitations=(),
    )


def _report() -> AcquisitionReport:
    return AcquisitionReport(
        acquisition_id="acquisition_" + "a" * 64,
        provider="github_actions",
        repository="Quantum-L9/example",
        run_id="100",
        run_status="completed",
        run_conclusion="failure",
        failed_job_count=1,
        evidence=(_evidence(),),
        total_raw_bytes=3,
        terminal_state="evidence_acquired",
        started_at="2026-07-18T00:00:00Z",
        completed_at="2026-07-18T00:01:00Z",
        limitations=(),
    )


def test_acquisition_store_persist_round_trip(tmp_path: Path) -> None:
    store = AcquisitionArtifactStore(tmp_path)
    report = _report()
    log = AcquiredLog(
        evidence=_evidence(),
        provenance=_provenance(),
        redacted_text="AssertionError\n",
    )
    destination = store.persist(report=report, logs=(log,))

    assert destination == tmp_path / report.acquisition_id
    report_path = destination / "report.json"
    assert report_path.exists()
    persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted_report == report.as_dict()
    assert persisted_report["evidence_count"] == 1
    assert persisted_report["complete_evidence_count"] == 1

    job_root = destination / "jobs" / log.evidence.job_id
    evidence_path = job_root / "evidence.json"
    provenance_path = job_root / "provenance.json"
    redacted_path = job_root / "redacted.log"
    assert json.loads(evidence_path.read_text(encoding="utf-8")) == (
        log.evidence.as_dict()
    )
    assert json.loads(provenance_path.read_text(encoding="utf-8")) == (
        log.provenance.as_dict()
    )
    assert redacted_path.read_text(encoding="utf-8") == "AssertionError\n"


def test_acquisition_store_persist_without_logs(tmp_path: Path) -> None:
    store = AcquisitionArtifactStore(tmp_path)
    destination = store.persist(report=_report())
    assert (destination / "report.json").exists()
    assert not (destination / "jobs").exists()


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sign(item: PRRepairProposal, key: bytes) -> PRRepairProposal:
    return replace(
        item,
        signature=proposal_signature(
            unsigned_document=item.unsigned_dict(),
            callback_key=key,
        ),
    )


def _operation() -> PRRepairOperation:
    return PRRepairOperation(
        operation_id="operation_" + "a" * 64,
        path_token=request().repository_context["allowed_path_tokens"][0],
        expected_file_sha256="e" * 64,
        expected_text_sha256="f" * 64,
        replacement_text="new",
        replacement_sha256=hashlib.sha256(b"new").hexdigest(),
        evidence_id_hashes=("1" * 64,),
        justification="fix",
    )


def _proposed(key: bytes) -> PRRepairProposal:
    item = PRRepairProposal(
        proposal_id="pr_repair_proposal_" + "a" * 64,
        request_id=request().request_id,
        failure_fingerprint=request().failure_fingerprint,
        snapshot_id_hash=stable_hash("snapshot"),
        status="proposed",
        remediation_class="bounded_source",
        operations=(_operation(),),
        requested_validation_classes=(
            "affected_contract",
            "graph_delta",
            "original_failure",
            "targeted_test",
        ),
        rationale="fix the failure",
        limitations=(),
        issued_at=_now(),
        callback_nonce=request().callback["nonce"],
        signature="",
    )
    return _sign(item, key)


def _validate(item: PRRepairProposal, key: bytes) -> None:
    validate_proposal_contract(
        request=request(),
        proposal=item,
        callback_key=key,
        repository_snapshot_id="snapshot",
    )


def test_validate_proposal_contract_accepts_valid_proposed() -> None:
    key = b"a" * 32
    _validate(_proposed(key), key)


def test_validate_proposal_contract_request_id_mismatch() -> None:
    key = b"a" * 32
    item = replace(_proposed(key), request_id="other")
    with pytest.raises(DelegationProposalError, match="request identity"):
        _validate(item, key)


def test_validate_proposal_contract_fingerprint_mismatch() -> None:
    key = b"a" * 32
    item = replace(_proposed(key), failure_fingerprint="failure_" + "0" * 64)
    with pytest.raises(DelegationProposalError, match="fingerprint mismatch"):
        _validate(item, key)


def test_validate_proposal_contract_snapshot_mismatch() -> None:
    key = b"a" * 32
    with pytest.raises(DelegationProposalError, match="snapshot identity"):
        validate_proposal_contract(
            request=request(),
            proposal=_proposed(key),
            callback_key=key,
            repository_snapshot_id="different",
        )


def test_validate_proposal_contract_nonce_mismatch() -> None:
    key = b"a" * 32
    item = replace(_proposed(key), callback_nonce="9" * 64)
    with pytest.raises(DelegationProposalError, match="nonce mismatch"):
        _validate(item, key)


def test_validate_proposal_contract_expired() -> None:
    key = b"a" * 32
    stale = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    item = replace(_proposed(key), issued_at=stale.replace("+00:00", "Z"))
    with pytest.raises(DelegationExpiredError):
        _validate(item, key)


def test_validate_proposal_contract_bad_signature() -> None:
    key = b"a" * 32
    item = replace(_proposed(key), signature="0" * 64)
    with pytest.raises(DelegationSignatureError):
        _validate(item, key)


def test_validate_proposal_contract_unsupported_with_operations() -> None:
    key = b"a" * 32
    item = _sign(replace(_proposed(key), status="unsupported"), key)
    with pytest.raises(DelegationProposalError, match="cannot contain operations"):
        _validate(item, key)


def test_validate_proposal_contract_unsupported_without_operations() -> None:
    key = b"a" * 32
    item = _sign(
        replace(_proposed(key), status="unsupported", operations=()),
        key,
    )
    _validate(item, key)


def test_validate_proposal_contract_unknown_status() -> None:
    key = b"a" * 32
    item = _sign(replace(_proposed(key), status="weird"), key)
    with pytest.raises(DelegationProposalError, match="unknown proposal status"):
        _validate(item, key)


def test_validate_proposal_contract_missing_remediation_class() -> None:
    key = b"a" * 32
    item = _sign(replace(_proposed(key), remediation_class=None), key)
    with pytest.raises(DelegationProposalError, match="requires a class"):
        _validate(item, key)


def test_validate_proposal_contract_class_not_allowed() -> None:
    key = b"a" * 32
    item = _sign(replace(_proposed(key), remediation_class="reckless"), key)
    with pytest.raises(DelegationProposalError, match="class is not allowed"):
        _validate(item, key)


def test_validate_proposal_contract_exceeds_operation_limit() -> None:
    key = b"a" * 32
    base = request()
    tight_request = replace(
        base,
        constraints={**base.constraints, "maximum_operations": 0},
    )
    with pytest.raises(DelegationProposalError, match="operation limit"):
        validate_proposal_contract(
            request=tight_request,
            proposal=_proposed(key),
            callback_key=key,
            repository_snapshot_id="snapshot",
        )


def test_validate_proposal_contract_unknown_path_token() -> None:
    key = b"a" * 32
    operation = replace(_operation(), path_token="path_" + "9" * 64)
    item = _sign(replace(_proposed(key), operations=(operation,)), key)
    with pytest.raises(DelegationProposalError, match="unknown path token"):
        _validate(item, key)


def test_validate_proposal_contract_replacement_hash_mismatch() -> None:
    key = b"a" * 32
    operation = replace(_operation(), replacement_sha256="0" * 64)
    item = _sign(replace(_proposed(key), operations=(operation,)), key)
    with pytest.raises(DelegationProposalError, match="replacement hash mismatch"):
        _validate(item, key)


def test_validate_proposal_contract_missing_validation_classes() -> None:
    key = b"a" * 32
    item = _sign(
        replace(_proposed(key), requested_validation_classes=("targeted_test",)),
        key,
    )
    with pytest.raises(DelegationProposalError, match="required validation"):
        _validate(item, key)
