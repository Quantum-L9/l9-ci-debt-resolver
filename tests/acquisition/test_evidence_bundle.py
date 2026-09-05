"""Acquisition must be able to feed the resolver's own classifier.

`acquire-github-run` emitted `l9.acquisition-report/v1`; `correlate-classify`
consumed `l9.evidence-bundle/v1`; nothing converted one into the other. The
report carries a list of evidence and no log body, the bundle describes one job
and requires the body, and neither the `failed_job` object nor the revision
survived the report projection. So the resolver could acquire real evidence from
a real failed run and still have no way to classify it -- which is why the
Resolver -> Intelligence seam stayed unestablished even after acquisition itself
was fixed.

The load-bearing assertion in this module is
`test_a_projected_bundle_is_accepted_by_the_real_consumer`: the bundle goes
through `load_evidence_bundle`, the same function `correlate-classify` calls.
Everything else guards a way of getting that wrong.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from l9_debt_resolver.acquisition.evidence_bundle import project_bundles
from l9_debt_resolver.acquisition.models import (
    AcquiredLog,
    FailedJob,
    FailedRun,
    FailedStep,
    LogProvenance,
)
from l9_debt_resolver.acquisition.service import FailedLogAcquisitionService
from l9_debt_resolver.contracts.models import CIRunEvidence
from l9_debt_resolver.contracts.schema import SchemaValidator, schema_root
from l9_debt_resolver.correlation.loader import load_evidence_bundle

HEAD_SHA = "c" * 40


def _job(job_id: str, name: str) -> FailedJob:
    return FailedJob(
        provider="github_actions",
        run_id="100",
        job_id=job_id,
        name=name,
        status="completed",
        conclusion="failure",
        started_at=None,
        completed_at=None,
        runner_name=None,
        labels=(),
        failed_steps=(FailedStep(number=1, name="pytest", conclusion="failure"),),
    )


def _acquired(
    job: FailedJob,
    *,
    completeness: str = "complete",
    text: str = "##[error]Process completed with exit code 1.",
) -> AcquiredLog:
    digest = hashlib.sha256(text.encode()).hexdigest()
    evidence = CIRunEvidence(
        # Distinct per job on purpose: a positional join between sorted evidence
        # and the unsorted job list would mismatch them, and identical ids would
        # hide it. Derived by digest so it also satisfies the contract's
        # ^evidence_[0-9a-f]{64}$ -- a hand-padded id fails schema validation.
        evidence_id="evidence_" + hashlib.sha256(job.job_id.encode()).hexdigest(),
        provider="github_actions",
        run_id=job.run_id,
        job_id=job.job_id,
        job_name=job.name,
        failed_command="pytest",
        conclusion="failure",
        log_sha256=digest,
        log_size_bytes=len(text),
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
    provenance = LogProvenance(
        provider="github_actions",
        api_version="2022-11-28",
        repository="Quantum-L9/example",
        run_id=job.run_id,
        job_id=job.job_id,
        retrieval_id="retrieval_" + "b" * 64,
        retrieved_at="2026-07-18T00:00:00Z",
        etag=None,
        content_length=len(text),
        content_type="text/plain",
        raw_sha256=digest,
        redacted_sha256=digest,
        raw_byte_count=len(text),
        redacted_byte_count=len(text),
        completeness=completeness,
        limitations=(),
    )
    return AcquiredLog(evidence=evidence, provenance=provenance, redacted_text=text)


class MultiJobProvider:
    """Two failed jobs, returned in an order that sorting will change."""

    def __init__(self, *, completeness: str = "complete") -> None:
        self.completeness = completeness
        # job_id "9" sorts after "10" as a string, so the fetch order and the
        # sorted-evidence order differ.
        self.jobs = (_job("9", "late"), _job("10", "early"))

    async def identify_failed_run(self, *, repository: str, run_id: str) -> FailedRun:
        return FailedRun(
            provider="github_actions",
            repository=repository,
            run_id=run_id,
            status="completed",
            conclusion="failure",
            head_sha=HEAD_SHA,
            event="pull_request",
            workflow_id="10",
            created_at=None,
            updated_at=None,
        )

    async def retrieve_failed_jobs(
        self, *, repository: str, run_id: str
    ) -> tuple[FailedJob, ...]:
        del repository, run_id
        return self.jobs

    async def retrieve_failed_log(
        self, *, repository: str, run_id: str, job: FailedJob
    ) -> AcquiredLog:
        del repository, run_id
        return _acquired(job, completeness=self.completeness)


def _service(provider: object) -> FailedLogAcquisitionService:
    return FailedLogAcquisitionService(
        provider,  # type: ignore[arg-type]
        clock=lambda: "2026-07-18T00:00:00Z",
    )


class TestProjection:
    @pytest.mark.asyncio
    async def test_a_projected_bundle_is_accepted_by_the_real_consumer(
        self, tmp_path: Path
    ) -> None:
        """The round trip that was impossible before this module existed."""
        outcome = await _service(MultiJobProvider()).acquire_with_bundles(
            repository="Quantum-L9/example",
            run_id="100",
        )
        assert outcome.projection.bundles

        path = tmp_path / "bundle.json"
        path.write_text(
            json.dumps(outcome.projection.bundles[0]),
            encoding="utf-8",
        )
        # load_evidence_bundle is what correlate-classify calls. It raises on any
        # missing or mistyped field, so acceptance here is the seam.
        bundle = load_evidence_bundle(path)
        assert bundle.repository == "Quantum-L9/example"
        assert bundle.revision == HEAD_SHA
        assert bundle.redacted_log
        assert bundle.failed_job.job_id in {"9", "10"}

    @pytest.mark.asyncio
    async def test_every_bundle_validates_against_the_published_schema(self) -> None:
        outcome = await _service(MultiJobProvider()).acquire_with_bundles(
            repository="Quantum-L9/example",
            run_id="100",
        )
        validator = SchemaValidator(schema_root() / "evidence-bundle.schema.json")
        for bundle in outcome.projection.bundles:
            validator.validate(bundle)

    @pytest.mark.asyncio
    async def test_each_bundle_pairs_its_own_job_with_its_own_log(self) -> None:
        """The defect a positional join would introduce.

        Evidence is sorted before the report is built, while jobs are fetched in
        provider order. Joining the two by index afterwards would attach job
        "10"'s metadata to job "9"'s log, and every schema check would still
        pass because both shapes are well formed.
        """
        outcome = await _service(MultiJobProvider()).acquire_with_bundles(
            repository="Quantum-L9/example",
            run_id="100",
        )
        assert len(outcome.projection.bundles) == 2
        for bundle in outcome.projection.bundles:
            assert bundle["failed_job"]["job_id"] == bundle["evidence"]["job_id"]
            assert bundle["failed_job"]["name"] == bundle["evidence"]["job_name"]

    @pytest.mark.asyncio
    async def test_the_revision_is_the_run_head_sha(self) -> None:
        """The bundle requires a revision and the report names none."""
        outcome = await _service(MultiJobProvider()).acquire_with_bundles(
            repository="Quantum-L9/example",
            run_id="100",
        )
        assert {b["revision"] for b in outcome.projection.bundles} == {HEAD_SHA}

    @pytest.mark.asyncio
    async def test_the_report_contract_is_unchanged(self) -> None:
        """l9.acquisition-report/v1 is additionalProperties:false.

        The bundles travel beside the report, never inside it, so the published
        artifact must still validate exactly as before.
        """
        outcome = await _service(MultiJobProvider()).acquire_with_bundles(
            repository="Quantum-L9/example",
            run_id="100",
        )
        SchemaValidator(schema_root() / "acquisition-report.schema.json").validate(
            outcome.report.as_dict()
        )
        assert "redacted_log" not in outcome.report.as_dict()
        assert "bundles" not in outcome.report.as_dict()

    @pytest.mark.asyncio
    async def test_acquire_still_returns_only_the_report(self) -> None:
        """Existing callers are untouched."""
        report = await _service(MultiJobProvider()).acquire(
            repository="Quantum-L9/example",
            run_id="100",
        )
        assert report.terminal_state == "evidence_ready"


class TestCompletenessGate:
    @pytest.mark.asyncio
    async def test_a_truncated_log_is_not_projected(self) -> None:
        """Classifying a partial log invents a category from absent bytes."""
        outcome = await _service(
            MultiJobProvider(completeness="possibly_truncated")
        ).acquire_with_bundles(repository="Quantum-L9/example", run_id="100")
        assert outcome.projection.bundles == ()
        assert any(
            "not assessed complete" in item for item in outcome.projection.limitations
        )
        assert any(
            "correlate-classify has no input" in item
            for item in outcome.projection.limitations
        )

    def test_a_complete_but_empty_log_is_refused_not_written_invalid(self) -> None:
        """`redacted_log` has minLength 1, so an empty body cannot be a bundle."""
        job = _job("9", "late")
        projection = project_bundles(
            repository="Quantum-L9/example",
            revision=HEAD_SHA,
            pairs=((job, _acquired(job, text="")),),
        )
        assert projection.bundles == ()
        assert any("empty redacted log" in item for item in projection.limitations)

    def test_no_jobs_projects_nothing_without_raising(self) -> None:
        projection = project_bundles(
            repository="Quantum-L9/example",
            revision=HEAD_SHA,
            pairs=(),
        )
        assert projection.bundles == ()
        assert projection.as_index()["bundle_count"] == 0
