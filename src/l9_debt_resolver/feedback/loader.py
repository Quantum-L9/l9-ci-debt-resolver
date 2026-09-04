from __future__ import annotations

import json
from pathlib import Path

from ..contracts.schema import SchemaValidator, schema_root
from .models import FeedbackEvent
from .privacy import validate_feedback_event

_SCHEMA_NAME = "intelligence-feedback-event.schema.json"


def load_feedback_event(
    path: Path,
) -> FeedbackEvent:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("feedback event must be an object")
    if value.get("schema_version") != "l9.intelligence-feedback-event/v1":
        raise ValueError("unsupported feedback event version")
    # Privacy conformance is not schema conformance. The publish path used to
    # check privacy alone, so an event whose validation.duration_bucket sat
    # outside the schema's enum was delivered with a "delivered" receipt --
    # while `l9-debt-resolver validate intelligence-feedback-event` refused the
    # same document. Enforce the contract schema at the publish ingress too, so
    # the resolver cannot ship what its own validator rejects.
    SchemaValidator(schema_root() / _SCHEMA_NAME).validate(value)
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
