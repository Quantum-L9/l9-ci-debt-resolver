from __future__ import annotations

import re
from datetime import UTC, datetime

from .errors import (
    BranchPolicyError,
    ProtectedBranchError,
    PushAuthorizationError,
)
from .models import PushAuthorization

_ALLOWED_BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,120}$")
_PROTECTED_BRANCHES = {
    "main",
    "master",
    "trunk",
    "production",
    "release",
}
_ALLOWED_PREFIXES = (
    "resolver/",
    "repair/resolver/",
)


def deterministic_branch_name(
    *,
    failure_fingerprint: str,
    attempt_number: int,
) -> str:
    suffix = failure_fingerprint.removeprefix("failure_")[:16]
    return f"resolver/{suffix}/attempt-{attempt_number}"


def validate_branch_name(branch: str) -> None:
    if not _ALLOWED_BRANCH.fullmatch(branch):
        raise BranchPolicyError("repair branch contains invalid characters")
    if branch in _PROTECTED_BRANCHES:
        raise ProtectedBranchError(f"protected branch is prohibited: {branch}")
    if not branch.startswith(_ALLOWED_PREFIXES):
        raise BranchPolicyError("repair branch must use an approved prefix")
    if ".." in branch or branch.endswith("/"):
        raise BranchPolicyError("repair branch has an unsafe structure")


def validate_push_authorization(
    *,
    authorization: PushAuthorization,
    repository: str,
    remote: str,
    branch: str,
    now: datetime | None = None,
) -> None:
    reference = now or datetime.now(UTC)
    expires_at = datetime.fromisoformat(
        authorization.expires_at.replace(
            "Z",
            "+00:00",
        )
    )
    if expires_at <= reference:
        raise PushAuthorizationError("push authorization has expired")
    expected = (
        authorization.repository,
        authorization.remote,
        authorization.branch,
    )
    actual = (
        repository,
        remote,
        branch,
    )
    if expected != actual:
        raise PushAuthorizationError("push authorization scope mismatch")
