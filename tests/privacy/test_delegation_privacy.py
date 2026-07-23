from __future__ import annotations

import pytest

from l9_debt_resolver.delegation.errors import (
    DelegationPrivacyError,
)
from l9_debt_resolver.delegation.privacy import (
    validate_request,
)


@pytest.mark.parametrize(
    "document",
    [
        {"raw_log": "failure"},
        {"source_code": "print('x')"},
        {"repository_path": "src/app.py"},
        {"developer": "alice"},
        {"value": "ghp_abcdefghijklmnopqrstuvwxyz"},
        {"value": "/home/alice/project"},
        {"value": "alice@example.com"},
    ],
)
def test_sensitive_request_is_rejected(
    document: dict[str, object],
) -> None:
    with pytest.raises(DelegationPrivacyError):
        validate_request(document)


def test_bounded_aggregate_request_is_allowed() -> None:
    validate_request(
        {
            "failure_fingerprint": ("failure_" + "a" * 64),
            "entity_ids": ["entity:1"],
            "allowed_path_tokens": ["path_" + "b" * 64],
        }
    )
