from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from l9_debt_resolver.acquisition.models import (
    FailedJob,
    FailedStep,
)
from l9_debt_resolver.contracts.models import (
    CIRunEvidence,
)

from .models import EvidenceBundle


def load_evidence_bundle(
    path: Path,
) -> EvidenceBundle:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("evidence bundle must be a JSON object")
    if document.get("schema_version") != "l9.evidence-bundle/v1":
        raise ValueError("unsupported evidence bundle version")
    return EvidenceBundle(
        repository=_string(document, "repository"),
        revision=_string(document, "revision"),
        evidence=_evidence(_object(document, "evidence")),
        redacted_log=_string(
            document,
            "redacted_log",
        ),
        failed_job=_failed_job(_object(document, "failed_job")),
    )


def _evidence(
    document: dict[str, Any],
) -> CIRunEvidence:
    provenance = _object(
        document,
        "artifact_provenance",
    )
    return CIRunEvidence(
        evidence_id=_string(document, "evidence_id"),
        provider=_string(document, "provider"),
        run_id=_string(document, "run_id"),
        job_id=_string(document, "job_id"),
        job_name=_string(document, "job_name"),
        failed_command=_optional_string(document.get("failed_command")),
        conclusion=_string(document, "conclusion"),
        log_sha256=_string(document, "log_sha256"),
        log_size_bytes=_integer(
            document,
            "log_size_bytes",
        ),
        log_completeness=_string(
            document,
            "log_completeness",
        ),
        authority_class=_string(
            document,
            "authority_class",
        ),
        artifact_provenance=provenance,
        observed_at=_string(document, "observed_at"),
        limitations=tuple(_string_list(document.get("limitations", []))),
    )


def _failed_job(
    document: dict[str, Any],
) -> FailedJob:
    steps = []
    for value in _list(document, "failed_steps"):
        step = _object_value(value, "failed step")
        steps.append(
            FailedStep(
                number=_integer(step, "number"),
                name=_string(step, "name"),
                conclusion=_string(
                    step,
                    "conclusion",
                ),
            )
        )
    return FailedJob(
        provider=_string(document, "provider"),
        run_id=_string(document, "run_id"),
        job_id=_string(document, "job_id"),
        name=_string(document, "name"),
        status=_string(document, "status"),
        conclusion=_string(document, "conclusion"),
        started_at=_optional_string(document.get("started_at")),
        completed_at=_optional_string(document.get("completed_at")),
        runner_name=_optional_string(document.get("runner_name")),
        labels=tuple(sorted(_string_list(document.get("labels", [])))),
        failed_steps=tuple(steps),
    )


def _string(
    document: dict[str, Any],
    key: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _integer(
    document: dict[str, Any],
    key: str,
) -> int:
    value = document.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _optional_string(
    value: object,
) -> str | None:
    return value if isinstance(value, str) else None


def _object(
    document: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    return _object_value(document.get(key), key)


def _object_value(
    value: object,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _list(
    document: dict[str, Any],
    key: str,
) -> list[object]:
    value = document.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


def _string_list(
    value: object,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("value must be a list")
    return [item for item in value if isinstance(item, str)]
