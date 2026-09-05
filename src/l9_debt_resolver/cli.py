from __future__ import annotations

import argparse
import asyncio
import json
import os
from importlib.metadata import version
from pathlib import Path
from typing import Any

from .acquisition.evidence_bundle import BundleProjection
from .acquisition.service import (
    FailedLogAcquisitionService,
)
from .classification.models import (
    ClassificationSignal,
    ClassificationTrace,
)
from .contracts.schema import SchemaValidator, schema_root
from .correlation.loader import load_evidence_bundle
from .feedback.builder import build_feedback_event
from .feedback.delivery import FeedbackDeliveryService
from .feedback.file_transport import JSONFileFeedbackTransport
from .feedback.http_transport import HTTPSFeedbackTransport
from .feedback.loader import load_feedback_event
from .feedback.observation import observed_failure_outcome
from .feedback.outbox import FeedbackOutbox
from .feedback.privacy import validate_feedback_event
from .feedback.protocol import FeedbackTransport
from .providers.github.provider import (
    GitHubActionsProvider,
)
from .remediation.loader import load_remediation_plan
from .runtime.capabilities import resolver_capabilities
from .runtime.correlation_service import ResolverCorrelationRuntime
from .runtime.feedback_service import ResolverFeedbackService
from .runtime.remediation_service import RemediationService
from .sdk.document_adapter import DocumentSDKKnowledgeProvider
from .sdk.finding_bundle_adapter import FindingBundleKnowledgeAdapter
from .validation.json_gateway import JSONSDKValidationGateway


def emit(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="l9-debt-resolver")
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )
    commands.add_parser("capabilities")
    validate = commands.add_parser("validate")
    validate.add_argument(
        "schema",
        choices=[
            "ci-run-evidence",
            "ci-failure-classification",
            "resolver-attempt",
            "resolver-terminal-state",
            "remediation-record",
            "resolution-event",
            "failed-run-reference",
            "failed-job",
            "log-provenance",
            "acquisition-report",
            "evidence-bundle",
            "stack-frame",
            "repository-correlation",
            "classification-trace",
            "remediation-plan",
            "validation-transcript",
            "intelligence-feedback-event",
            "feedback-delivery-receipt",
            "feedback-outbox-record",
            "sdk-knowledge-document",
        ],
    )
    validate.add_argument("document", type=Path)

    knowledge = commands.add_parser(
        "build-sdk-knowledge",
        help=(
            "Project a public l9.finding-bundle/v1 onto the resolver-owned "
            "l9.sdk-knowledge-document/v1 that correlate-classify consumes."
        ),
    )
    knowledge.add_argument("bundle", type=Path)
    knowledge.add_argument(
        "--repository",
        required=True,
        help=(
            "GitHub owner/name. Required because a finding bundle does not name "
            "the repository it scanned -- snapshot.repository_root is a local "
            "path, not an identity."
        ),
    )
    knowledge.add_argument(
        "--repository-root",
        type=Path,
        help="Optional checkout root for resolver-side entity and test context.",
    )
    knowledge.add_argument("--output", type=Path)

    correlate = commands.add_parser("correlate-classify")
    correlate.add_argument(
        "--evidence-bundle",
        required=True,
        type=Path,
    )
    correlate.add_argument(
        "--SDK-knowledge",
        required=True,
        type=Path,
    )

    acquire = commands.add_parser("acquire-github-run")
    acquire.add_argument(
        "--repository",
        required=True,
        help="GitHub owner/name repository",
    )
    acquire.add_argument(
        "--run-id",
        required=True,
    )
    acquire.add_argument(
        "--repository-root",
        default=None,
        help=("Optional checkout root to redact from logs"),
    )
    acquire.add_argument(
        "--api-url",
        default="https://api.github.com",
    )
    # Without this the resolver could not feed its own classifier: acquisition
    # emitted l9.acquisition-report/v1 and correlate-classify consumed
    # l9.evidence-bundle/v1, and nothing converted one to the other. The log
    # body the bundle requires exists only during acquisition, so it is written
    # here or not at all.
    acquire.add_argument(
        "--emit-bundles",
        default=None,
        type=Path,
        help=(
            "Directory to write one l9.evidence-bundle/v1 per complete failed "
            "job, for correlate-classify --evidence-bundle."
        ),
    )

    # `build_feedback_event` already existed and nothing called it. The only
    # producer of the `ResolutionOutcome` it needs was the remote-rerun path, so
    # a failure the resolver acquired and classified but did not repair -- its
    # most common state -- had no route to an intelligence feedback event.
    feedback_build = commands.add_parser(
        "build-feedback-event",
        help=(
            "Correlate and classify an evidence bundle, then project the result "
            "onto l9.intelligence-feedback-event/v1 for publish-feedback."
        ),
    )
    feedback_build.add_argument(
        "--evidence-bundle",
        required=True,
        type=Path,
    )
    feedback_build.add_argument(
        "--SDK-knowledge",
        required=True,
        type=Path,
    )
    feedback_build.add_argument(
        "--repository",
        required=True,
        help="GitHub owner/name. Pseudonymised in the event; never emitted raw.",
    )
    feedback_build.add_argument("--run-id", required=True)
    feedback_build.add_argument(
        "--branch",
        default="unknown",
        help="Branch the failure was observed on. Not emitted -- the event "
        "contract forbids a branch field -- but part of the outcome record.",
    )
    feedback_build.add_argument("--provider", default="github_actions")
    feedback_build.add_argument(
        "--attempt-number",
        type=int,
        default=1,
    )
    feedback_build.add_argument(
        "--pseudonym-key-environment",
        default="L9_FEEDBACK_PSEUDONYM_KEY",
        help=(
            "Environment variable holding the repository-pseudonym key "
            "(>= 32 bytes). The key never appears in the event or in argv."
        ),
    )
    feedback_build.add_argument("--output", type=Path)

    remediate = commands.add_parser("remediate-offline")
    remediate.add_argument(
        "--workspace",
        required=True,
        type=Path,
    )
    remediate.add_argument(
        "--classification-trace",
        required=True,
        type=Path,
    )
    remediate.add_argument(
        "--remediation-plan",
        required=True,
        type=Path,
    )
    remediate.add_argument(
        "--SDK-validation",
        required=True,
        type=Path,
    )

    for feedback_command in ("publish-feedback", "drain-feedback"):
        feedback = commands.add_parser(feedback_command)
        if feedback_command == "publish-feedback":
            feedback.add_argument(
                "--event",
                required=True,
                type=Path,
            )
        feedback.add_argument(
            "--outbox",
            required=True,
            type=Path,
        )
        feedback.add_argument(
            "--transport",
            choices=["json-file", "https"],
            default="json-file",
        )
        feedback.add_argument(
            "--destination",
            required=True,
            help="Directory for json-file transport, or endpoint URL for https",
        )
        feedback.add_argument(
            "--token-environment",
            default="L9_FEEDBACK_TOKEN",
            help="Environment variable holding the bearer token for https",
        )
    return parser


async def acquire_github_run(
    *,
    repository: str,
    run_id: str,
    repository_root: str | None,
    api_url: str,
    emit_bundles: Path | None = None,
) -> dict[str, Any]:
    provider = GitHubActionsProvider.from_environment(
        repository_root=repository_root,
        base_url=api_url,
    )
    service = FailedLogAcquisitionService(provider)
    outcome = await service.acquire_with_bundles(
        repository=repository,
        run_id=run_id,
    )
    if emit_bundles is not None:
        _write_evidence_bundles(outcome.projection, emit_bundles)
    return outcome.report.as_dict()


def _write_evidence_bundles(
    projection: BundleProjection,
    directory: Path,
) -> None:
    """Write each projected bundle, validated before it reaches disk.

    Same posture as `build-sdk-knowledge`: a document `correlate-classify`
    would refuse must never be written, because a file on disk that looks like
    classification input and is not is worse than no file.
    """
    validator = SchemaValidator(schema_root() / "evidence-bundle.schema.json")
    directory.mkdir(parents=True, exist_ok=True)
    for bundle in projection.bundles:
        validator.validate(bundle)
        evidence_id = str(bundle["evidence"]["evidence_id"])
        (directory / f"{evidence_id}.json").write_text(
            json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    (directory / "index.json").write_text(
        json.dumps(projection.as_index(), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _load_classification_trace(
    path: Path,
) -> ClassificationTrace:
    value = json.loads(path.read_text(encoding="utf-8"))
    matched_signals = tuple(
        ClassificationSignal(
            signal=str(signal["signal"]),
            category=str(signal["category"]),
            weight=float(signal["weight"]),
            source=str(signal["source"]),
        )
        for signal in value.get("matched_signals", [])
    )
    return ClassificationTrace(
        classification_id=value["classification_id"],
        failure_fingerprint=value["failure_fingerprint"],
        category=value["category"],
        confidence=float(value["confidence"]),
        evidence_ids=tuple(value["evidence_ids"]),
        matched_signals=matched_signals,
        failed_command=value.get("failed_command"),
        repository_snapshot_id=value["repository_snapshot_id"],
        affected_entities=tuple(value.get("affected_entities", ())),
        related_tests=tuple(value.get("related_tests", ())),
        applicable_contracts=tuple(value.get("applicable_contracts", ())),
        correlated_finding_ids=tuple(value.get("correlated_finding_ids", ())),
        remediation_eligibility=value["remediation_eligibility"],
        limitations=tuple(value.get("limitations", ())),
    )


async def remediate_offline(
    *,
    workspace: Path,
    classification_trace_path: Path,
    remediation_plan_path: Path,
    SDK_validation_path: Path,
) -> dict[str, Any]:
    classification_trace = _load_classification_trace(classification_trace_path)
    remediation_plan = load_remediation_plan(remediation_plan_path)
    gateway = JSONSDKValidationGateway(document_path=SDK_validation_path)
    result = await RemediationService(validation_gateway=gateway).execute(
        workspace_root=workspace,
        classification_trace=classification_trace,
        remediation_plan=remediation_plan,
    )
    return result.as_dict()


def _feedback_transport(
    *,
    transport_name: str,
    destination: str,
    token_environment: str,
) -> FeedbackTransport:
    import os

    if transport_name == "json-file":
        return JSONFileFeedbackTransport(directory=Path(destination))
    token = os.environ.get(token_environment)
    if not token:
        raise ValueError(
            f"feedback token environment variable {token_environment} is missing"
        )
    return HTTPSFeedbackTransport(
        endpoint=destination,
        bearer_token=token,
    )


async def publish_feedback(
    *,
    event_path: Path,
    outbox_path: Path,
    transport_name: str,
    destination: str,
    token_environment: str,
) -> dict[str, Any]:
    event = load_feedback_event(event_path)
    service = ResolverFeedbackService(
        FeedbackDeliveryService(
            outbox=FeedbackOutbox(directory=outbox_path),
            transport=_feedback_transport(
                transport_name=transport_name,
                destination=destination,
                token_environment=token_environment,
            ),
        )
    )
    receipt = await service.publish(event)
    return receipt.as_dict()


async def drain_feedback(
    *,
    outbox_path: Path,
    transport_name: str,
    destination: str,
    token_environment: str,
) -> list[dict[str, Any]]:
    service = ResolverFeedbackService(
        FeedbackDeliveryService(
            outbox=FeedbackOutbox(directory=outbox_path),
            transport=_feedback_transport(
                transport_name=transport_name,
                destination=destination,
                token_environment=token_environment,
            ),
        )
    )
    receipts = await service.drain_outbox()
    return [receipt.as_dict() for receipt in receipts]


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "capabilities":
        emit(resolver_capabilities())
        return 0

    if arguments.command == "build-sdk-knowledge":
        document = FindingBundleKnowledgeAdapter().build_from_path(
            arguments.bundle,
            repository=arguments.repository,
            repository_root=arguments.repository_root,
        )
        # Validated against the resolver's own schema before it is written, so a
        # document that correlate-classify would refuse never reaches disk.
        SchemaValidator(schema_root() / "sdk-knowledge-document.schema.json").validate(
            document
        )
        if arguments.output:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(
                json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
                + "\n",
                encoding="utf-8",
            )
        else:
            emit(document)
        return 0
    if arguments.command == "build-feedback-event":
        key = os.environ.get(arguments.pseudonym_key_environment, "")
        if len(key.encode("utf-8")) < 32:
            raise SystemExit(
                f"{arguments.pseudonym_key_environment} must hold at least 32 "
                "bytes; the repository pseudonym is an HMAC and a short key "
                "makes it reversible by hashing a candidate list"
            )
        bundle = load_evidence_bundle(arguments.evidence_bundle)
        SDK = DocumentSDKKnowledgeProvider.from_path(arguments.SDK_knowledge)
        # Correlation runs in-process rather than reading a previously written
        # correlate-classify document: there is no loader for
        # `RepositoryCorrelation`, and re-parsing our own output would risk the
        # event describing something subtly different from what the classifier
        # produced.
        result = asyncio.run(ResolverCorrelationRuntime(SDK=SDK).execute(bundle))
        outcome = observed_failure_outcome(
            classification=result.classification,
            repository=arguments.repository,
            run_id=arguments.run_id,
            branch=arguments.branch,
        )
        event = build_feedback_event(
            repository=arguments.repository,
            pseudonym_key=key.encode("utf-8"),
            provider=arguments.provider,
            resolver_version=version("l9-ci-debt-resolver"),
            attempt_number=arguments.attempt_number,
            classification_trace=result.classification,
            correlation=result.correlation,
            resolution_outcome=outcome,
            # Nothing was repaired, rerun or validated. Each of these is the
            # contract's own value for "did not happen" rather than a zero that
            # would read as a clean no-op repair.
            remediation_class=None,
            changed_file_count=0,
            changed_line_count=0,
            validation_result="not_run",
            validation_result_id=None,
            validation_step_count=0,
            validation_duration_bucket="unknown",
            graph_delta_accepted=None,
            remediation_plan_id=None,
        )
        document = event.as_dict()
        # Validated twice on purpose: the privacy validator (already run inside
        # build_feedback_event) enforces the redaction posture, and the schema
        # enforces the shape Intelligence's consumer requires. Passing one does
        # not imply the other.
        SchemaValidator(
            schema_root() / "intelligence-feedback-event.schema.json"
        ).validate(document)
        if arguments.output:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(
                json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
                + "\n",
                encoding="utf-8",
            )
        else:
            emit(document)
        return 0
    if arguments.command == "correlate-classify":
        bundle = load_evidence_bundle(arguments.evidence_bundle)
        SDK = DocumentSDKKnowledgeProvider.from_path(arguments.SDK_knowledge)
        runtime = ResolverCorrelationRuntime(SDK=SDK)
        result = asyncio.run(runtime.execute(bundle))
        emit(result.as_dict())
        return 0 if result.classification.category != "unsupported" else 2
    if arguments.command == "acquire-github-run":
        report = asyncio.run(
            acquire_github_run(
                repository=arguments.repository,
                run_id=arguments.run_id,
                repository_root=(arguments.repository_root),
                api_url=arguments.api_url,
                emit_bundles=arguments.emit_bundles,
            )
        )
        emit(report)
        terminal = report["terminal_state"]
        return (
            0
            if terminal
            in {
                "evidence_ready",
                "clean",
            }
            else 2
        )
    if arguments.command == "remediate-offline":
        remediation_result = asyncio.run(
            remediate_offline(
                workspace=arguments.workspace,
                classification_trace_path=(arguments.classification_trace),
                remediation_plan_path=(arguments.remediation_plan),
                SDK_validation_path=(arguments.SDK_validation),
            )
        )
        emit(remediation_result)
        return 0 if remediation_result["status"] == "validated" else 2
    if arguments.command == "publish-feedback":
        receipt = asyncio.run(
            publish_feedback(
                event_path=arguments.event,
                outbox_path=arguments.outbox,
                transport_name=arguments.transport,
                destination=arguments.destination,
                token_environment=(arguments.token_environment),
            )
        )
        emit(receipt)
        return 0 if receipt.get("status") in {"delivered", "duplicate"} else 2
    if arguments.command == "drain-feedback":
        receipts = asyncio.run(
            drain_feedback(
                outbox_path=arguments.outbox,
                transport_name=arguments.transport,
                destination=arguments.destination,
                token_environment=(arguments.token_environment),
            )
        )
        emit(receipts)
        return 0
    schema_path = schema_root() / f"{arguments.schema}.schema.json"
    document = json.loads(arguments.document.read_text(encoding="utf-8"))
    SchemaValidator(schema_path).validate(document)
    # Schema conformance is not privacy conformance. `validate` used to run the
    # schema alone, so an operator pre-flighting a feedback event that carried a
    # raw CI log in a free-text field was told "status: valid" -- while the
    # publish path, which does run the privacy validator, would refuse the very
    # same document. Run both here so the check answers the question an operator
    # is actually asking before publishing.
    if arguments.schema == "intelligence-feedback-event":
        validate_feedback_event(document)
    emit(
        {
            "schema_version": ("l9.resolver-contract-validation/v1"),
            "status": "valid",
            "schema": arguments.schema,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
