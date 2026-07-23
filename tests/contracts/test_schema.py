from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from l9_debt_resolver.contracts.errors import (
    SchemaValidationError,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)
from l9_debt_resolver.contracts.schema import (
    SchemaValidator,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas" / "resolver"


def test_evidence_schema_accepts_typed_document() -> None:
    evidence = CIRunEvidence(
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
    )
    SchemaValidator(SCHEMAS / "ci-run-evidence.schema.json").validate(
        evidence.as_dict()
    )


def test_unknown_property_is_rejected() -> None:
    validator = SchemaValidator(SCHEMAS / "ci-run-evidence.schema.json")
    with pytest.raises(SchemaValidationError):
        validator.validate(
            {
                "schema_version": ("l9.ci-run-evidence/v1"),
                "unexpected": True,
            }
        )


def test_cross_schema_reference_resolves() -> None:
    validator = SchemaValidator(SCHEMAS / "resolver-attempt.schema.json")
    validator.validate(
        {
            "schema_version": ("l9.resolver-attempt/v1"),
            "attempt_id": ("attempt_" + "a" * 64),
            "failure_fingerprint": ("failure_" + "b" * 64),
            "attempt_number": 1,
            "state": "created",
            "evidence_ids": [],
            "classification_id": None,
            "remediation_plan_id": None,
            "validation_result_id": None,
            "original_run_id": "100",
            "rerun_id": None,
            "created_at": "2026-07-19T00:00:00Z",
            "updated_at": "2026-07-19T00:00:00Z",
            "limitations": [],
        }
    )
