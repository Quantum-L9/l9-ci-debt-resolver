from __future__ import annotations

import pytest

from l9_debt_resolver.contracts.errors import (
    CorpusSafetyError,
)
from l9_debt_resolver.contracts.privacy import (
    validate_corpus_safe_document,
)


@pytest.mark.parametrize(
    "document",
    [
        {"raw_log": "failure"},
        {"source_content": "print('x')"},
        {"patch": "diff --git"},
        {"developer_email": "dev@example.com"},
        {"value": "Bearer abcdefghijklmnop"},
        {"value": "/home/alice/project/app.py"},
    ],
)
def test_sensitive_corpus_data_is_rejected(
    document: dict[str, object],
) -> None:
    with pytest.raises(CorpusSafetyError):
        validate_corpus_safe_document(document)


def test_aggregate_event_data_is_allowed() -> None:
    validate_corpus_safe_document(
        {
            "failure_fingerprint": ("failure_" + "a" * 64),
            "terminal_state": "repeated_failure",
            "changed_file_count": 2,
            "finding_ids": ["finding:1"],
        }
    )
