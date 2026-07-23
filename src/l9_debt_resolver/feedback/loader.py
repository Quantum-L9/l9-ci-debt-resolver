from __future__ import annotations

import json
from pathlib import Path

from .models import FeedbackEvent
from .privacy import validate_feedback_event


def load_feedback_event(
    path: Path,
) -> FeedbackEvent:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("feedback event must be an object")
    if value.get("schema_version") != "l9.intelligence-feedback-event/v1":
        raise ValueError("unsupported feedback event version")
    validate_feedback_event(value)
    return FeedbackEvent(
        event_id=value["event_id"],
        idempotency_key=(value["idempotency_key"]),
        event_type=value["event_type"],
        repository_pseudonym=(value["repository_pseudonym"]),
        provider=value["provider"],
        resolver_version=(value["resolver_version"]),
        occurred_at=value["occurred_at"],
        failure=dict(value["failure"]),
        resolution=dict(value["resolution"]),
        validation=dict(value["validation"]),
        correlation=dict(value["correlation"]),
        provenance=dict(value["provenance"]),
        limitations=tuple(value["limitations"]),
    )
