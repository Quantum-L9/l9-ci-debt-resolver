from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from l9_debt_resolver.correlation.loader import load_evidence_bundle
from l9_debt_resolver.feedback.loader import load_feedback_event
from l9_debt_resolver.feedback.models import FeedbackEvent
from l9_debt_resolver.remediation.loader import load_remediation_plan


def _evidence_document() -> dict[str, object]:
    raw_hash = hashlib.sha256(b"log").hexdigest()
    return {
        "schema_version": "l9.ci-run-evidence/v1",
        "evidence_id": "evidence_" + "a" * 64,
        "provider": "github_actions",
        "run_id": "100",
        "job_id": "200",
        "job_name": "tests",
        "failed_command": "pytest",
        "conclusion": "failure",
        "log_sha256": raw_hash,
        "log_size_bytes": 3,
        "log_completeness": "complete",
        "authority_class": "RUNTIME_LOG",
        "artifact_provenance": {
            "source": "github_actions_job_log",
            "retrieval_id": "retrieval_" + "b" * 64,
            "retrieved_at": "2026-07-18T00:00:00Z",
        },
        "observed_at": "2026-07-18T00:00:00Z",
        "limitations": [],
    }


def _failed_job_document() -> dict[str, object]:
    return {
        "schema_version": "l9.failed-job/v1",
        "provider": "github_actions",
        "run_id": "100",
        "job_id": "200",
        "name": "tests",
        "status": "completed",
        "conclusion": "failure",
        "started_at": None,
        "completed_at": None,
        "runner_name": None,
        "labels": ["ubuntu", "self-hosted"],
        "failed_steps": [
            {"number": 1, "name": "pytest", "conclusion": "failure"},
        ],
    }


def _evidence_bundle_document() -> dict[str, object]:
    return {
        "schema_version": "l9.evidence-bundle/v1",
        "repository": "Quantum-L9/example",
        "revision": "abcdef1234567",
        "evidence": _evidence_document(),
        "redacted_log": "AssertionError\n",
        "failed_job": _failed_job_document(),
    }


def _write_json(path: Path, document: object) -> Path:
    path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )
    return path


def test_load_evidence_bundle_round_trip(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "bundle.json",
        _evidence_bundle_document(),
    )
    bundle = load_evidence_bundle(path)
    assert bundle.repository == "Quantum-L9/example"
    assert bundle.revision == "abcdef1234567"
    assert bundle.evidence.evidence_id == "evidence_" + "a" * 64
    assert bundle.evidence.failed_command == "pytest"
    assert bundle.evidence.log_completeness == "complete"
    assert bundle.evidence.limitations == ()
    assert bundle.failed_job.name == "tests"
    assert bundle.failed_job.labels == ("self-hosted", "ubuntu")
    assert bundle.failed_job.failed_steps[0].name == "pytest"
    assert bundle.failed_job.failed_steps[0].number == 1


def test_load_evidence_bundle_optional_failed_command_none(
    tmp_path: Path,
) -> None:
    document = _evidence_bundle_document()
    evidence = document["evidence"]
    assert isinstance(evidence, dict)
    evidence["failed_command"] = None
    path = _write_json(tmp_path / "bundle.json", document)
    bundle = load_evidence_bundle(path)
    assert bundle.evidence.failed_command is None


def test_load_evidence_bundle_rejects_non_object(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "bundle.json", ["not", "object"])
    with pytest.raises(ValueError, match="must be a JSON object"):
        load_evidence_bundle(path)


def test_load_evidence_bundle_rejects_bad_version(tmp_path: Path) -> None:
    document = _evidence_bundle_document()
    document["schema_version"] = "l9.evidence-bundle/v2"
    path = _write_json(tmp_path / "bundle.json", document)
    with pytest.raises(ValueError, match="unsupported evidence bundle"):
        load_evidence_bundle(path)


def test_load_evidence_bundle_rejects_missing_string(tmp_path: Path) -> None:
    document = _evidence_bundle_document()
    del document["repository"]
    path = _write_json(tmp_path / "bundle.json", document)
    with pytest.raises(ValueError, match="repository must be a string"):
        load_evidence_bundle(path)


def test_load_evidence_bundle_rejects_non_integer_size(
    tmp_path: Path,
) -> None:
    document = _evidence_bundle_document()
    evidence = document["evidence"]
    assert isinstance(evidence, dict)
    evidence["log_size_bytes"] = "3"
    path = _write_json(tmp_path / "bundle.json", document)
    with pytest.raises(ValueError, match="log_size_bytes must be an integer"):
        load_evidence_bundle(path)


def _operation_document() -> dict[str, object]:
    return {
        "operation_id": "operation_" + "f" * 64,
        "path": "src/app.py",
        "expected_file_sha256": hashlib.sha256(b"old").hexdigest(),
        "expected_text": "old",
        "replacement_text": "new",
        "replacement_sha256": hashlib.sha256(b"new").hexdigest(),
        "evidence_ids": ["evidence_" + "c" * 64],
        "justification": "fix test",
    }


def _remediation_plan_document() -> dict[str, object]:
    return {
        "schema_version": "l9.remediation-plan/v1",
        "plan_id": "remediation_plan_" + "1" * 64,
        "classification_id": "classification_" + "a" * 64,
        "failure_fingerprint": "failure_" + "b" * 64,
        "repository_snapshot_id": "snapshot-1",
        "repository_revision": "2" * 40,
        "remediation_class": "bounded_source",
        "evidence_ids": ["evidence_" + "c" * 64],
        "justification": "fix test",
        "operations": [_operation_document()],
        "expected_changed_paths": ["src/app.py"],
        "expected_package_boundaries": [],
        "expected_contract_ids": ["contract-1"],
        "expected_dependency_edges": [],
        "validation_plan_id": "validation-plan-1",
        "approval": None,
    }


def test_load_remediation_plan_without_approval(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "plan.json",
        _remediation_plan_document(),
    )
    plan = load_remediation_plan(path)
    assert plan.plan_id == "remediation_plan_" + "1" * 64
    assert plan.remediation_class == "bounded_source"
    assert plan.evidence_ids == ("evidence_" + "c" * 64,)
    assert plan.expected_changed_paths == ("src/app.py",)
    assert plan.validation_plan_id == "validation-plan-1"
    assert plan.approval is None
    assert len(plan.operations) == 1
    operation = plan.operations[0]
    assert operation.path == "src/app.py"
    assert operation.replacement_text == "new"
    assert operation.justification == "fix test"


def test_load_remediation_plan_with_approval(tmp_path: Path) -> None:
    document = _remediation_plan_document()
    document["approval"] = {
        "approval_id": "approval_" + "9" * 64,
        "approved_paths": ["src/app.py"],
        "approved_at": "2026-07-19T00:00:00Z",
        "expires_at": "2026-07-19T01:00:00Z",
    }
    path = _write_json(tmp_path / "plan.json", document)
    plan = load_remediation_plan(path)
    assert plan.approval is not None
    assert plan.approval.approval_id == "approval_" + "9" * 64
    assert plan.approval.approved_paths == ("src/app.py",)
    assert plan.approval.expires_at == "2026-07-19T01:00:00Z"


def test_load_remediation_plan_rejects_non_object(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "plan.json", 42)
    with pytest.raises(ValueError, match="must be an object"):
        load_remediation_plan(path)


def test_load_remediation_plan_rejects_bad_version(tmp_path: Path) -> None:
    document = _remediation_plan_document()
    document["schema_version"] = "l9.remediation-plan/v2"
    path = _write_json(tmp_path / "plan.json", document)
    with pytest.raises(ValueError, match="unsupported remediation plan"):
        load_remediation_plan(path)


def test_load_remediation_plan_rejects_non_array_operations(
    tmp_path: Path,
) -> None:
    document = _remediation_plan_document()
    document["operations"] = {}
    path = _write_json(tmp_path / "plan.json", document)
    with pytest.raises(ValueError, match="operations must be an array"):
        load_remediation_plan(path)


def _feedback_event() -> FeedbackEvent:
    return FeedbackEvent(
        event_id="feedback_event_" + "a" * 64,
        idempotency_key="feedback_idempotency_" + "b" * 64,
        event_type="resolution_succeeded",
        repository_pseudonym="repository_" + "c" * 64,
        provider="github_actions",
        resolver_version="0.6.0",
        occurred_at="2026-07-19T00:00:00Z",
        failure={
            "fingerprint": "failure_" + "d" * 64,
            "category": "test_failure",
            "confidence_bucket": "high",
            "repeated": False,
            "attempt_number": 1,
            "observed_fingerprint_changed": None,
        },
        resolution={
            "terminal_state": "clean",
            "remediation_class": "bounded_source",
            "changed_file_count": 1,
            "changed_line_bucket": "1_10",
            "remote_push_performed": True,
            "rerun_observed": True,
        },
        validation={
            "result": "passed",
            "result_id_hash": "e" * 64,
            "step_count": 4,
            "duration_bucket": "10_60s",
            "graph_delta_accepted": True,
        },
        correlation={
            "capability_profile": ["python"],
            "finding_ids": [],
            "contract_ids": [],
            "language_families": ["python"],
            "entity_count": 1,
            "related_test_count": 1,
        },
        provenance={
            "snapshot_id_hash": "f" * 64,
            "evidence_id_hashes": ["1" * 64],
            "classification_id_hash": "2" * 64,
            "remediation_plan_id_hash": "3" * 64,
            "attempt_id_hash": "4" * 64,
            "rerun_id_hash": "5" * 64,
        },
        limitations=(),
    )


def test_load_feedback_event_round_trip(tmp_path: Path) -> None:
    original = _feedback_event()
    path = _write_json(tmp_path / "event.json", original.as_dict())
    loaded = load_feedback_event(path)
    assert loaded.event_id == original.event_id
    assert loaded.idempotency_key == original.idempotency_key
    assert loaded.event_type == original.event_type
    assert loaded.repository_pseudonym == original.repository_pseudonym
    assert loaded.provider == original.provider
    assert loaded.resolver_version == original.resolver_version
    assert loaded.failure == original.failure
    assert loaded.resolution == original.resolution
    assert loaded.validation == original.validation
    assert loaded.correlation == original.correlation
    assert loaded.provenance == original.provenance
    assert loaded.limitations == original.limitations


def test_load_feedback_event_rejects_non_object(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "event.json", "nope")
    with pytest.raises(ValueError, match="must be an object"):
        load_feedback_event(path)


def test_load_feedback_event_rejects_bad_version(tmp_path: Path) -> None:
    document = _feedback_event().as_dict()
    document["schema_version"] = "l9.intelligence-feedback-event/v2"
    path = _write_json(tmp_path / "event.json", document)
    with pytest.raises(ValueError, match="unsupported feedback event"):
        load_feedback_event(path)
