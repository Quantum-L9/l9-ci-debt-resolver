from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from .acquisition.service import (
    FailedLogAcquisitionService,
)
from .classification.models import (
    ClassificationSignal,
    ClassificationTrace,
)
from .contracts.schema import SchemaValidator, schema_root
from .correlation.loader import load_evidence_bundle
from .feedback.delivery import FeedbackDeliveryService
from .feedback.file_transport import JSONFileFeedbackTransport
from .feedback.http_transport import HTTPSFeedbackTransport
from .feedback.loader import load_feedback_event
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
) -> dict[str, Any]:
    provider = GitHubActionsProvider.from_environment(
        repository_root=repository_root,
        base_url=api_url,
    )
    service = FailedLogAcquisitionService(provider)
    report = await service.acquire(
        repository=repository,
        run_id=run_id,
    )
    return report.as_dict()


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
