from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from l9_debt_resolver.remote.errors import (
    BranchPolicyError,
    ProtectedBranchError,
    PushAuthorizationError,
)
from l9_debt_resolver.remote.models import (
    PushAuthorization,
)
from l9_debt_resolver.remote.policy import (
    deterministic_branch_name,
    validate_branch_name,
    validate_push_authorization,
)


def test_deterministic_branch() -> None:
    value = deterministic_branch_name(
        failure_fingerprint=("failure_" + "a" * 64),
        attempt_number=2,
    )
    assert value == ("resolver/aaaaaaaaaaaaaaaa/attempt-2")


@pytest.mark.parametrize(
    "branch",
    [
        "feature/random",
        "resolver/../main",
        "resolver/",
    ],
)
def test_invalid_branch_is_rejected(
    branch: str,
) -> None:
    with pytest.raises(BranchPolicyError):
        validate_branch_name(branch)


@pytest.mark.parametrize(
    "branch",
    ["main", "master", "production"],
)
def test_protected_branch_is_rejected(
    branch: str,
) -> None:
    with pytest.raises(ProtectedBranchError):
        validate_branch_name(branch)


def test_push_authorization_scope() -> None:
    now = datetime.now(UTC)
    authorization = PushAuthorization(
        authorization_id="authorization-1",
        repository="Quantum-L9/example",
        remote="origin",
        branch="resolver/abc/attempt-1",
        expires_at=(now + timedelta(minutes=10)).isoformat(),
    )
    validate_push_authorization(
        authorization=authorization,
        repository="Quantum-L9/example",
        remote="origin",
        branch="resolver/abc/attempt-1",
        now=now,
    )


def test_expired_authorization_is_rejected() -> None:
    now = datetime.now(UTC)
    authorization = PushAuthorization(
        authorization_id="authorization-1",
        repository="Quantum-L9/example",
        remote="origin",
        branch="resolver/abc/attempt-1",
        expires_at=(now - timedelta(minutes=1)).isoformat(),
    )
    with pytest.raises(PushAuthorizationError):
        validate_push_authorization(
            authorization=authorization,
            repository="Quantum-L9/example",
            remote="origin",
            branch="resolver/abc/attempt-1",
            now=now,
        )
