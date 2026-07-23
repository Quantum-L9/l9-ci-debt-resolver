from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from .acquisition.service import (
    FailedLogAcquisitionService,
)
from .contracts.schema import SchemaValidator
from .correlation.loader import load_evidence_bundle
from .feedback.delivery import FeedbackDeliveryService
from .feedback.file_transport import JSONFileFeedbackTransport
from .feedback.http_transport import HTTPSFeedbackTransport
from .feedback.loader import load_feedback_event
from .feedback.outbox import FeedbackOutbox
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


def schema_root() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "resolver"


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
):
    from .classification.models import ClassificationTrace
    from .contracts.models import FailureClassification

    value = json.loads(path.read_text(encoding="utf-8"))
    classification = FailureClassification(
        classification_id=value["classification_id"],
        failure_fingerprint=value["failure_fingerprint"],
        category=value["category"],
        confidence=float(value["confidence"]),
        evidence_ids=tuple(value["evidence_ids"]),
        failed_command=value.get("failed_command"),
        repository_snapshot_id=value["repository_snapshot_id"],
        affected_entities=tuple(value["correlated_entity_ids"]),
        remediation_eligibility=value["remediation_eligibility"],
        limitations=tuple(value["limitations"]),
    )
    return ClassificationTrace(
        trace_id=value["trace_id"],
        classification=classification,
        correlation_id=value["correlation_id"],
        correlated_entity_ids=tuple(value["correlated_entity_ids"]),
        correlated_finding_ids=tuple(value["correlated_finding_ids"]),
        related_test_ids=tuple(value["related_test_ids"]),
        applicable_contract_ids=tuple(value["applicable_contract_ids"]),
        matched_signatures=tuple(value["matched_signatures"]),
        conflicting_signatures=tuple(value["conflicting_signatures"]),
        limitations=tuple(value["limitations"]),
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
):
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
    schema_path = schema_root() / f"{arguments.schema}.schema.json"
    document = json.loads(arguments.document.read_text(encoding="utf-8"))
    SchemaValidator(schema_path).validate(document)
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
