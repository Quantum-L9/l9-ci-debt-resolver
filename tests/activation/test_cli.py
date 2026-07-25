from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from l9_debt_resolver import cli
from l9_debt_resolver.classification.models import ClassificationTrace
from l9_debt_resolver.contracts.errors import SchemaValidationError
from l9_debt_resolver.contracts.models import CIRunEvidence
from l9_debt_resolver.feedback.http_transport import HTTPSFeedbackTransport
from tests.correlation.test_service import SDK_document
from tests.feedback.test_file_transport import event
from tests.runtime.test_remediation_rollback import plan, trace


def _run(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["l9-debt-resolver", *argv])
    return cli.main()


def _stdout_json(capsys: pytest.CaptureFixture[str]) -> Any:
    captured = capsys.readouterr()
    return json.loads(captured.out.strip())


def _evidence_bundle_document() -> dict[str, Any]:
    raw_hash = hashlib.sha256(b"log").hexdigest()
    return {
        "schema_version": "l9.evidence-bundle/v1",
        "repository": "Quantum-L9/example",
        "revision": "abcdef1234567",
        "redacted_log": (
            'File "/home/runner/work/repo/repo/src/app.py", '
            "line 42, in execute\n"
            "AssertionError\n"
            "Error: Process completed with exit code 1.\n"
        ),
        "evidence": {
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
        },
        "failed_job": {
            "provider": "github_actions",
            "run_id": "100",
            "job_id": "200",
            "name": "tests",
            "status": "completed",
            "conclusion": "failure",
            "started_at": None,
            "completed_at": None,
            "runner_name": None,
            "labels": [],
            "failed_steps": [
                {"number": 1, "name": "pytest", "conclusion": "failure"},
            ],
        },
    }


def _ci_run_evidence_document() -> dict[str, Any]:
    return CIRunEvidence(
        evidence_id="evidence_" + "a" * 64,
        provider="github_actions",
        run_id="100",
        job_id="200",
        job_name="tests",
        failed_command="pytest",
        conclusion="failure",
        log_sha256=hashlib.sha256(b"log").hexdigest(),
        log_size_bytes=3,
        log_completeness="complete",
        authority_class="RUNTIME_LOG",
        artifact_provenance={},
        observed_at="2026-07-19T00:00:00Z",
        limitations=(),
    ).as_dict()


def _sdk_validation_document() -> dict[str, Any]:
    return {
        "schema_version": "l9.sdk-validation-document/v1",
        "validation_plan": {
            "validation_plan_id": "validation-plan-1",
            "repository_snapshot_id": "snapshot-1",
            "classification_id": ("classification_" + "a" * 64),
            "remediation_plan_id": ("remediation_plan_" + "1" * 64),
            "full_gate_required": False,
            "limitations": [],
            "steps": [
                {
                    "step_id": "original",
                    "kind": "original_failure",
                    "command": ["python3", "-c", "raise SystemExit(0)"],
                },
                {
                    "step_id": "test",
                    "kind": "targeted_test",
                    "command": ["python3", "-c", "raise SystemExit(0)"],
                },
                {
                    "step_id": "contract",
                    "kind": "affected_contract",
                    "command": ["python3", "-c", "raise SystemExit(0)"],
                },
                {"step_id": "graph", "kind": "graph_delta", "command": None},
            ],
        },
        "validation_result_id": "validation-result-1",
    }


def _write(path: Path, value: Any) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_build_parser_returns_parser() -> None:
    parser = cli.build_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_load_classification_trace_round_trips(tmp_path: Path) -> None:
    source = trace()
    path = _write(tmp_path / "trace.json", source.as_dict())
    loaded = cli._load_classification_trace(path)
    assert isinstance(loaded, ClassificationTrace)
    assert loaded.classification_id == source.classification_id
    assert loaded.category == source.category
    assert loaded.matched_signals == source.matched_signals
    assert loaded.remediation_eligibility == source.remediation_eligibility


def test_capabilities(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _run(monkeypatch, ["capabilities"]) == 0
    payload = _stdout_json(capsys)
    assert payload["schema_version"] == "l9.resolver-capabilities/v1"


def test_validate_valid_document(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    document = _write(tmp_path / "evidence.json", _ci_run_evidence_document())
    code = _run(
        monkeypatch,
        ["validate", "ci-run-evidence", str(document)],
    )
    assert code == 0
    payload = _stdout_json(capsys)
    assert payload["status"] == "valid"
    assert payload["schema"] == "ci-run-evidence"
    assert payload["schema_version"] == "l9.resolver-contract-validation/v1"


def test_validate_invalid_document_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    document = _write(
        tmp_path / "bad.json",
        {"schema_version": "l9.ci-run-evidence/v1", "unexpected": True},
    )
    with pytest.raises(SchemaValidationError):
        _run(monkeypatch, ["validate", "ci-run-evidence", str(document)])


def test_correlate_classify(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    bundle_path = _write(
        tmp_path / "bundle.json",
        _evidence_bundle_document(),
    )
    sdk_path = _write(tmp_path / "sdk.json", SDK_document())
    code = _run(
        monkeypatch,
        [
            "correlate-classify",
            "--evidence-bundle",
            str(bundle_path),
            "--SDK-knowledge",
            str(sdk_path),
        ],
    )
    payload = _stdout_json(capsys)
    assert payload["schema_version"] == (
        "l9.correlation-classification-result/v1"
    )
    category = payload["classification"]["category"]
    assert code == (0 if category != "unsupported" else 2)


def test_acquire_github_run_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_acquire(**_: Any) -> dict[str, Any]:
        return {"terminal_state": "evidence_ready"}

    monkeypatch.setattr(cli, "acquire_github_run", fake_acquire)
    code = _run(
        monkeypatch,
        [
            "acquire-github-run",
            "--repository",
            "Quantum-L9/example",
            "--run-id",
            "100",
        ],
    )
    assert code == 0
    assert _stdout_json(capsys)["terminal_state"] == "evidence_ready"


def test_acquire_github_run_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_acquire(**_: Any) -> dict[str, Any]:
        return {"terminal_state": "insufficient_log_evidence"}

    monkeypatch.setattr(cli, "acquire_github_run", fake_acquire)
    code = _run(
        monkeypatch,
        [
            "acquire-github-run",
            "--repository",
            "Quantum-L9/example",
            "--run-id",
            "100",
        ],
    )
    assert code == 2
    capsys.readouterr()


def test_remediate_offline(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "src/app.py"
    target.parent.mkdir(parents=True)
    before = "value = 'old'\n"
    target.write_text(before, encoding="utf-8")

    trace_path = _write(tmp_path / "trace.json", trace().as_dict())
    plan_doc = _remediation_plan_document(before)
    plan_path = _write(tmp_path / "plan.json", plan_doc)
    sdk_path = _write(
        tmp_path / "sdk-validation.json",
        _sdk_validation_document(),
    )

    code = _run(
        monkeypatch,
        [
            "remediate-offline",
            "--workspace",
            str(workspace),
            "--classification-trace",
            str(trace_path),
            "--remediation-plan",
            str(plan_path),
            "--SDK-validation",
            str(sdk_path),
        ],
    )
    payload = _stdout_json(capsys)
    assert payload["status"] == "validated"
    assert code == 0
    assert target.read_text(encoding="utf-8") == "value = 'new'\n"


def test_publish_feedback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    event_path = _write(tmp_path / "event.json", event().as_dict())
    outbox = tmp_path / "outbox"
    destination = tmp_path / "delivered"
    code = _run(
        monkeypatch,
        [
            "publish-feedback",
            "--event",
            str(event_path),
            "--outbox",
            str(outbox),
            "--transport",
            "json-file",
            "--destination",
            str(destination),
        ],
    )
    payload = _stdout_json(capsys)
    assert payload["status"] in {"delivered", "duplicate"}
    assert code == 0


def test_drain_feedback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    outbox = tmp_path / "outbox"
    destination = tmp_path / "delivered"
    code = _run(
        monkeypatch,
        [
            "drain-feedback",
            "--outbox",
            str(outbox),
            "--transport",
            "json-file",
            "--destination",
            str(destination),
        ],
    )
    assert code == 0
    assert isinstance(_stdout_json(capsys), list)


def test_feedback_transport_https_requires_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("L9_FEEDBACK_TOKEN", raising=False)
    with pytest.raises(ValueError):
        cli._feedback_transport(
            transport_name="https",
            destination="https://feedback.example/ingest",
            token_environment="L9_FEEDBACK_TOKEN",
        )


def test_feedback_transport_https_with_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("L9_FEEDBACK_TOKEN", "secret-token")
    transport = cli._feedback_transport(
        transport_name="https",
        destination="https://feedback.example/ingest",
        token_environment="L9_FEEDBACK_TOKEN",
    )
    assert isinstance(transport, HTTPSFeedbackTransport)


def _remediation_plan_document(before: str) -> dict[str, Any]:
    source = plan(before)
    operation = source.operations[0]
    return {
        "schema_version": "l9.remediation-plan/v1",
        "plan_id": source.plan_id,
        "classification_id": source.classification_id,
        "failure_fingerprint": source.failure_fingerprint,
        "repository_snapshot_id": source.repository_snapshot_id,
        "repository_revision": source.repository_revision,
        "remediation_class": source.remediation_class,
        "evidence_ids": list(source.evidence_ids),
        "justification": source.justification,
        "operations": [
            {
                "operation_id": operation.operation_id,
                "path": operation.path,
                "expected_file_sha256": operation.expected_file_sha256,
                "expected_text": operation.expected_text,
                "replacement_text": operation.replacement_text,
                "replacement_sha256": operation.replacement_sha256,
                "evidence_ids": list(operation.evidence_ids),
                "justification": operation.justification,
            }
        ],
        "expected_changed_paths": list(source.expected_changed_paths),
        "expected_package_boundaries": list(
            source.expected_package_boundaries
        ),
        "expected_contract_ids": list(source.expected_contract_ids),
        "expected_dependency_edges": list(source.expected_dependency_edges),
        "validation_plan_id": source.validation_plan_id,
        "approval": None,
    }
