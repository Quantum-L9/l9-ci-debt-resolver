from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from l9_debt_resolver.delegation.errors import (
    DelegationSignatureError,
)
from l9_debt_resolver.delegation.identity import (
    proposal_signature,
    stable_hash,
)
from l9_debt_resolver.delegation.models import (
    PRRepairProposal,
)
from l9_debt_resolver.delegation.proposal import (
    validate_proposal_contract,
)
from tests.delegation.test_file_transport import request


def proposal(
    callback_key: bytes,
) -> PRRepairProposal:
    item = PRRepairProposal(
        proposal_id=("pr_repair_proposal_" + "a" * 64),
        request_id=request().request_id,
        failure_fingerprint=(request().failure_fingerprint),
        snapshot_id_hash=stable_hash("snapshot"),
        status="unsupported",
        remediation_class=None,
        operations=(),
        requested_validation_classes=(),
        rationale="unable to propose safely",
        limitations=("insufficient_context",),
        issued_at=(datetime.now(UTC).isoformat().replace("+00:00", "Z")),
        callback_nonce=(request().callback["nonce"]),
        signature="",
    )
    return replace(
        item,
        signature=proposal_signature(
            unsigned_document=(item.unsigned_dict()),
            callback_key=callback_key,
        ),
    )


def test_valid_signature_is_accepted() -> None:
    key = b"a" * 32
    validate_proposal_contract(
        request=request(),
        proposal=proposal(key),
        callback_key=key,
        repository_snapshot_id="snapshot",
    )


def test_invalid_signature_is_rejected() -> None:
    key = b"a" * 32
    item = replace(
        proposal(key),
        signature="0" * 64,
    )
    with pytest.raises(DelegationSignatureError):
        validate_proposal_contract(
            request=request(),
            proposal=item,
            callback_key=key,
            repository_snapshot_id="snapshot",
        )
