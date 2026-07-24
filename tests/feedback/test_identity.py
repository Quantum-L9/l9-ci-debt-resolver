from __future__ import annotations

from l9_debt_resolver.feedback.identity import (
    idempotency_key,
    repository_pseudonym,
)


def test_repository_pseudonym_is_deterministic() -> None:
    key = b"a" * 32
    first = repository_pseudonym(
        repository="Quantum-L9/example",
        pseudonym_key=key,
    )
    second = repository_pseudonym(
        repository="Quantum-L9/example",
        pseudonym_key=key,
    )
    assert first == second
    assert "Quantum-L9" not in first


def test_idempotency_excludes_timestamp() -> None:
    first = idempotency_key(
        {
            "failure": "failure-1",
            "terminal": "clean",
        }
    )
    second = idempotency_key(
        {
            "failure": "failure-1",
            "terminal": "clean",
        }
    )
    assert first == second
