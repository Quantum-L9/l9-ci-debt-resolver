from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PRRepairRequest:
    request_id: str
    idempotency_key: str
    repository_pseudonym: str
    failure_fingerprint: str
    classification: dict[str, Any]
    repository_context: dict[str, Any]
    constraints: dict[str, Any]
    callback: dict[str, Any]
    created_at: str
    expires_at: str
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ("l9.pr-repair-request/v1"),
            "request_id": self.request_id,
            "idempotency_key": self.idempotency_key,
            "repository_pseudonym": (self.repository_pseudonym),
            "failure_fingerprint": (self.failure_fingerprint),
            "classification": self.classification,
            "repository_context": (self.repository_context),
            "constraints": self.constraints,
            "callback": self.callback,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class PRRepairOperation:
    operation_id: str
    path_token: str
    expected_file_sha256: str
    expected_text_sha256: str
    replacement_text: str
    replacement_sha256: str
    evidence_id_hashes: tuple[str, ...]
    justification: str


@dataclass(frozen=True)
class PRRepairProposal:
    proposal_id: str
    request_id: str
    failure_fingerprint: str
    snapshot_id_hash: str
    status: str
    remediation_class: str | None
    operations: tuple[PRRepairOperation, ...]
    requested_validation_classes: tuple[str, ...]
    rationale: str
    limitations: tuple[str, ...]
    issued_at: str
    callback_nonce: str
    signature: str

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ("l9.pr-repair-proposal/v1"),
            "proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "failure_fingerprint": (self.failure_fingerprint),
            "snapshot_id_hash": (self.snapshot_id_hash),
            "status": self.status,
            "remediation_class": (self.remediation_class),
            "operations": [
                {
                    "operation_id": item.operation_id,
                    "path_token": item.path_token,
                    "expected_file_sha256": (item.expected_file_sha256),
                    "expected_text_sha256": (item.expected_text_sha256),
                    "replacement_text": (item.replacement_text),
                    "replacement_sha256": (item.replacement_sha256),
                    "evidence_id_hashes": list(item.evidence_id_hashes),
                    "justification": (item.justification),
                }
                for item in self.operations
            ],
            "requested_validation_classes": list(self.requested_validation_classes),
            "rationale": self.rationale,
            "limitations": list(self.limitations),
            "issued_at": self.issued_at,
            "callback_nonce": self.callback_nonce,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.unsigned_dict(),
            "signature": self.signature,
        }


@dataclass(frozen=True)
class DelegationRecord:
    record_id: str
    request: PRRepairRequest
    state: str
    delivery_attempts: int
    proposal_id: str | None
    terminal_state: str | None
    created_at: str
    updated_at: str
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ("l9.delegation-record/v1"),
            "record_id": self.record_id,
            "request": self.request.as_dict(),
            "state": self.state,
            "delivery_attempts": (self.delivery_attempts),
            "proposal_id": self.proposal_id,
            "terminal_state": self.terminal_state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "limitations": list(self.limitations),
        }
