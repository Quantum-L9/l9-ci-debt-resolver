from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .errors import (
    DelegationExpiredError,
    DelegationProposalError,
    DelegationSignatureError,
)
from .identity import (
    stable_hash,
    verify_proposal_signature,
)
from .models import (
    PRRepairOperation,
    PRRepairProposal,
    PRRepairRequest,
)
from .privacy import validate_proposal


def load_proposal(
    path: Path,
) -> PRRepairProposal:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DelegationProposalError("proposal must be an object")
    operations = tuple(
        _parse_operation(item)
        for item in value.get(
            "operations",
            [],
        )
    )
    proposal = PRRepairProposal(
        proposal_id=str(value["proposal_id"]),
        request_id=str(value["request_id"]),
        failure_fingerprint=str(value["failure_fingerprint"]),
        snapshot_id_hash=str(value["snapshot_id_hash"]),
        status=str(value["status"]),
        remediation_class=(
            str(value["remediation_class"])
            if value.get("remediation_class") is not None
            else None
        ),
        operations=operations,
        requested_validation_classes=tuple(
            sorted(
                str(item)
                for item in value.get(
                    "requested_validation_classes",
                    [],
                )
            )
        ),
        rationale=str(value["rationale"]),
        limitations=tuple(
            sorted(
                str(item)
                for item in value.get(
                    "limitations",
                    [],
                )
            )
        ),
        issued_at=str(value["issued_at"]),
        callback_nonce=str(value["callback_nonce"]),
        signature=str(value["signature"]),
    )
    validate_proposal(proposal.as_dict())
    return proposal


def validate_proposal_contract(
    *,
    request: PRRepairRequest,
    proposal: PRRepairProposal,
    callback_key: bytes,
    repository_snapshot_id: str,
) -> None:
    if proposal.request_id != request.request_id:
        raise DelegationProposalError("proposal request identity mismatch")
    if proposal.failure_fingerprint != request.failure_fingerprint:
        raise DelegationProposalError("proposal failure fingerprint mismatch")
    if proposal.snapshot_id_hash != stable_hash(repository_snapshot_id):
        raise DelegationProposalError("proposal snapshot identity mismatch")
    if proposal.callback_nonce != request.callback["nonce"]:
        raise DelegationProposalError("proposal callback nonce mismatch")
    issued_at = datetime.fromisoformat(
        proposal.issued_at.replace(
            "Z",
            "+00:00",
        )
    )
    now = datetime.now(UTC)
    if abs((now - issued_at).total_seconds()) > 300:
        raise DelegationExpiredError(
            "proposal callback timestamp is outside the permitted tolerance"
        )
    if not verify_proposal_signature(
        unsigned_document=(proposal.unsigned_dict()),
        signature=proposal.signature,
        callback_key=callback_key,
    ):
        raise DelegationSignatureError("proposal callback signature is invalid")
    if proposal.status == "unsupported":
        if proposal.operations:
            raise DelegationProposalError(
                "unsupported proposal cannot contain operations"
            )
        return
    if proposal.status != "proposed":
        raise DelegationProposalError("unknown proposal status")
    if not proposal.remediation_class:
        raise DelegationProposalError("proposed remediation requires a class")
    allowed_classes = set(request.constraints["allowed_remediation_classes"])
    if proposal.remediation_class not in allowed_classes:
        raise DelegationProposalError("proposal remediation class is not allowed")
    maximum_operations = int(request.constraints["maximum_operations"])
    if len(proposal.operations) > maximum_operations:
        raise DelegationProposalError("proposal exceeds operation limit")
    allowed_tokens = set(request.repository_context["allowed_path_tokens"])
    total_replacement_bytes = 0
    for operation in proposal.operations:
        if operation.path_token not in allowed_tokens:
            raise DelegationProposalError("proposal references unknown path token")
        replacement_bytes = operation.replacement_text.encode("utf-8")
        total_replacement_bytes += len(replacement_bytes)
        if len(replacement_bytes) > 1048576:
            raise DelegationProposalError("replacement exceeds per-operation limit")
        actual_replacement_hash = hashlib.sha256(replacement_bytes).hexdigest()
        if actual_replacement_hash != operation.replacement_sha256:
            raise DelegationProposalError("replacement hash mismatch")
    if total_replacement_bytes > 10485760:
        raise DelegationProposalError("proposal exceeds total replacement limit")
    required_validation = {
        "original_failure",
        "targeted_test",
        "affected_contract",
        "graph_delta",
    }
    if not required_validation.issubset(set(proposal.requested_validation_classes)):
        raise DelegationProposalError("proposal lacks required validation classes")


def _parse_operation(
    value: object,
) -> PRRepairOperation:
    if not isinstance(value, dict):
        raise DelegationProposalError("proposal operation must be an object")
    return PRRepairOperation(
        operation_id=str(value["operation_id"]),
        path_token=str(value["path_token"]),
        expected_file_sha256=str(value["expected_file_sha256"]),
        expected_text_sha256=str(value["expected_text_sha256"]),
        replacement_text=str(value["replacement_text"]),
        replacement_sha256=str(value["replacement_sha256"]),
        evidence_id_hashes=tuple(
            sorted(str(item) for item in value["evidence_id_hashes"])
        ),
        justification=str(value["justification"]),
    )
