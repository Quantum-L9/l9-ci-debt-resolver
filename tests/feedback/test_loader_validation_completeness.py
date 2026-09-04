"""Both resolver feedback gates must run on both feedback paths.

The resolver had two validators and two entry points, and each entry point ran
exactly one of them:

* ``l9-debt-resolver validate intelligence-feedback-event`` ran the contract
  schema and not the privacy validator, so an event carrying a raw CI log in a
  free-text ``limitations`` entry was reported ``status: valid``.
* ``publish-feedback`` (through ``load_feedback_event``) ran the privacy
  validator and not the schema, so an event whose ``validation.duration_bucket``
  sat outside the schema enum was delivered with a ``delivered`` receipt --
  a document the resolver's own ``validate`` subcommand refuses.

Neither gate was missing; each was simply absent from one path. These tests pin
both gates to both paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from l9_debt_resolver.contracts.errors import SchemaValidationError
from l9_debt_resolver.feedback.errors import FeedbackPrivacyError
from l9_debt_resolver.feedback.loader import load_feedback_event
from tests.feedback.test_file_transport import event


def _document() -> dict[str, Any]:
    return json.loads(json.dumps(event().as_dict()))


def _write(tmp_path: Path, document: dict[str, Any]) -> Path:
    path = tmp_path / "event.json"
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_clean_event_still_loads(tmp_path: Path) -> None:
    """The control. Without it the rejections below prove nothing."""
    document = _document()

    loaded = load_feedback_event(_write(tmp_path, document))

    assert loaded.event_id == document["event_id"]
    assert loaded.as_dict()["schema_version"] == "l9.intelligence-feedback-event/v1"


def test_publish_path_rejects_a_schema_invalid_event(tmp_path: Path) -> None:
    """The regression: this exact document used to be delivered."""
    document = _document()
    document["validation"] = dict(document["validation"])
    document["validation"]["duration_bucket"] = "1_5_minutes"

    with pytest.raises(SchemaValidationError) as caught:
        load_feedback_event(_write(tmp_path, document))

    assert "duration_bucket" in str(caught.value)


def test_publish_path_still_rejects_a_privacy_violating_event(tmp_path: Path) -> None:
    """The privacy gate must survive the schema gate being added ahead of it."""
    document = _document()
    document["limitations"] = [
        'raw log: File "/home/runner/work/repo/repo/src/service.py", line 42'
    ]

    with pytest.raises((FeedbackPrivacyError, SchemaValidationError)):
        load_feedback_event(_write(tmp_path, document))


def test_privacy_violation_in_free_text_limitations_is_caught(tmp_path: Path) -> None:
    """Name the field: free text is where a raw log actually hides.

    Every structured field in the event is a hash, a bucket or an enum. The
    ``limitations`` array is the one place an arbitrary string travels, so it is
    the one place worth pinning explicitly.
    """
    document = _document()
    document["limitations"] = [
        'File "/home/runner/work/l9/l9/src/service.py", line 42, in handle'
    ]

    with pytest.raises(FeedbackPrivacyError) as caught:
        load_feedback_event(_write(tmp_path, document))

    assert "limitations" in str(caught.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_type", "not_a_real_event_type"),
        ("provider", ""),
        ("repository_pseudonym", "Quantum-L9/plain-text-repository"),
    ],
)
def test_publish_path_rejects_other_schema_violations(
    tmp_path: Path, field: str, value: str
) -> None:
    document = _document()
    document[field] = value

    with pytest.raises((SchemaValidationError, FeedbackPrivacyError)):
        load_feedback_event(_write(tmp_path, document))


def test_unsupported_schema_version_is_still_rejected_first(tmp_path: Path) -> None:
    """The cheap version guard must keep running before the expensive validators."""
    document = _document()
    document["schema_version"] = "l9.intelligence-feedback-event/v99"

    with pytest.raises(ValueError, match="unsupported feedback event version"):
        load_feedback_event(_write(tmp_path, document))
