from __future__ import annotations

import pytest

from l9_debt_resolver.feedback.errors import (
    FeedbackPrivacyError,
)
from l9_debt_resolver.feedback.privacy import (
    validate_feedback_event,
)


@pytest.mark.parametrize(
    "document",
    [
        {"raw_log": "failure"},
        {"patch_body": "diff --git"},
        {"developer_email": "dev@example.com"},
        {"value": "Bearer abcdefghijklmnop"},
        {"value": "/home/alice/project/app.py"},
        {"value": "192.168.1.1"},
        {"value": "https://user:pass@example.com/api"},
    ],
)
def test_sensitive_feedback_is_rejected(
    document: dict[str, object],
) -> None:
    with pytest.raises(FeedbackPrivacyError):
        validate_feedback_event(document)


def test_safe_aggregate_feedback_is_allowed() -> None:
    validate_feedback_event(
        {
            "event_type": "repeated_failure",
            "changed_file_count": 2,
            "failure_fingerprint": ("failure_" + "a" * 64),
        }
    )
