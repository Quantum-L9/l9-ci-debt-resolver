from __future__ import annotations

import pytest

from l9_debt_resolver.contracts.canonical import (
    canonical_json,
    namespaced_identity,
)
from l9_debt_resolver.contracts.errors import (
    IdentityError,
)


def test_mapping_order_does_not_change_identity() -> None:
    first = namespaced_identity(
        "example_",
        {
            "a": 1,
            "b": 2,
        },
    )
    second = namespaced_identity(
        "example_",
        {
            "b": 2,
            "a": 1,
        },
    )
    assert first == second


def test_identity_has_expected_shape() -> None:
    value = namespaced_identity(
        "evidence_",
        {"value": 1},
    )
    assert value.startswith("evidence_")
    assert len(value) == len("evidence_") + 64


def test_non_finite_numbers_are_rejected() -> None:
    with pytest.raises(IdentityError):
        canonical_json(
            {
                "value": float("nan"),
            }
        )
