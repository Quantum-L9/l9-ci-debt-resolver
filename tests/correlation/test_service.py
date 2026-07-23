from __future__ import annotations

import hashlib

import pytest

from l9_debt_resolver.acquisition.models import (
    FailedJob,
    FailedStep,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)
from l9_debt_resolver.correlation.models import (
    EvidenceBundle,
)
from l9_debt_resolver.correlation.service import (
    RepositoryCorrelationService,
)
from l9_debt_resolver.sdk.document_adapter import (
    DocumentSDKKnowledgeProvider,
)


def bundle(completeness: str = "complete") -> EvidenceBundle:
    raw_hash = hashlib.sha256(b"log").hexdigest()
    evidence = CIRunEvidence(
        evidence_id="evidence_" + "a" * 64,
        provider="github_actions",
        run_id="100",
        job_id="200",
        job_name="tests",
        failed_command="pytest",
        conclusion="failure",
        log_sha256=raw_hash,
        log_size_bytes=3,
        log_completeness=completeness,
        authority_class="RUNTIME_LOG",
        artifact_provenance={
            "source": "github_actions_job_log",
            "retrieval_id": "retrieval_" + "b" * 64,
            "retrieved_at": "2026-07-18T00:00:00Z",
        },
        observed_at="2026-07-18T00:00:00Z",
        limitations=(),
    )
    job = FailedJob(
        provider="github_actions",
        run_id="100",
        job_id="200",
        name="tests",
        status="completed",
        conclusion="failure",
        started_at=None,
        completed_at=None,
        runner_name=None,
        labels=(),
        failed_steps=(
            FailedStep(
                number=1,
                name="pytest",
                conclusion="failure",
            ),
        ),
    )
    return EvidenceBundle(
        repository="Quantum-L9/example",
        revision="abcdef1234567",
        evidence=evidence,
        redacted_log=(
            'File "/home/runner/work/repo/repo/src/app.py", '
            "line 42, in execute\n"
            "AssertionError\n"
            "Error: Process completed with exit code 1.\n"
        ),
        failed_job=job,
    )


def SDK_document() -> dict[str, object]:
    return {
        "schema_version": "l9.sdk-knowledge-document/v1",
        "repository": "Quantum-L9/example",
        "revision": "abcdef1234567",
        "snapshot": {
            "snapshot_id": "snapshot-1",
            "repository": "Quantum-L9/example",
            "revision": "abcdef1234567",
            "capability_profile": ["python"],
            "limitations": [],
        },
        "entities": [
            {
                "entity_id": "entity-1",
                "kind": "function",
                "path": "src/app.py",
                "start_line": 1,
                "end_line": 100,
                "symbol": "execute",
                "language": "python",
                "metadata": {"CI_failure_category": "test_failure"},
            }
        ],
        "tests": [],
        "contracts": [],
        "findings": [],
    }


@pytest.mark.asyncio
async def test_repository_correlation() -> None:
    service = RepositoryCorrelationService(DocumentSDKKnowledgeProvider(SDK_document()))
    result = await service.correlate(bundle())
    assert result.repository_snapshot_id == "snapshot-1"
    assert [entity.entity_id for entity in result.repository_entities] == ["entity-1"]
