from __future__ import annotations

from pathlib import Path

from l9_debt_resolver.feedback.outbox import (
    FeedbackOutbox,
)
from tests.feedback.test_file_transport import event


def test_outbox_enqueue_is_idempotent(
    tmp_path: Path,
) -> None:
    outbox = FeedbackOutbox(directory=tmp_path)
    first = outbox.enqueue(
        event(),
        now="2026-07-19T00:00:00Z",
    )
    second = outbox.enqueue(
        event(),
        now="2026-07-19T00:00:01Z",
    )
    assert first.record_id == second.record_id
    assert len(list(tmp_path.glob("feedback_outbox_*.json"))) == 1
