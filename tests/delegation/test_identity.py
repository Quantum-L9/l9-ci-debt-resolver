from __future__ import annotations

from l9_debt_resolver.delegation.identity import (
    path_token,
    proposal_signature,
    verify_proposal_signature,
)


def test_path_tokens_are_deterministic() -> None:
    key = b"a" * 32
    first = path_token(
        repository_path="src/app.py",
        path_key=key,
    )
    second = path_token(
        repository_path="src/app.py",
        path_key=key,
    )
    assert first == second
    assert "src/app.py" not in first


def test_proposal_signature_verifies() -> None:
    key = b"b" * 32
    document = {
        "proposal_id": "proposal-1",
        "request_id": "request-1",
    }
    signature = proposal_signature(
        unsigned_document=document,
        callback_key=key,
    )
    assert verify_proposal_signature(
        unsigned_document=document,
        signature=signature,
        callback_key=key,
    )
