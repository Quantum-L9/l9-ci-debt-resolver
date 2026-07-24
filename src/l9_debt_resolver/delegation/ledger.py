from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)

from .models import (
    DelegationRecord,
    PRRepairRequest,
)


class DelegationLedger:
    def __init__(
        self,
        *,
        directory: Path,
    ) -> None:
        self._directory = directory

    def create(
        self,
        request: PRRepairRequest,
    ) -> DelegationRecord:
        record = DelegationRecord(
            record_id=namespaced_identity(
                "delegation_record_",
                {
                    "request_id": (request.request_id),
                    "idempotency_key": (request.idempotency_key),
                },
            ),
            request=request,
            state="pending",
            delivery_attempts=0,
            proposal_id=None,
            terminal_state=None,
            created_at=request.created_at,
            updated_at=request.created_at,
            limitations=request.limitations,
        )
        existing = self.get(record.record_id)
        if existing is not None:
            return existing
        self.save(record)
        return record

    def save(
        self,
        record: DelegationRecord,
    ) -> None:
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination = self._directory / f"{record.record_id}.json"
        encoded = (
            json.dumps(
                record.as_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(
            dir=self._directory,
            prefix=".delegation-record.",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(
                descriptor,
                "wb",
            ) as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                destination,
            )
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def get(
        self,
        record_id: str,
    ) -> DelegationRecord | None:
        path = self._directory / f"{record_id}.json"
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return _parse_record(value)


def _parse_record(
    value: object,
) -> DelegationRecord:
    if not isinstance(value, dict):
        raise ValueError("delegation record must be an object")
    request_value = value["request"]
    request = PRRepairRequest(
        request_id=request_value["request_id"],
        idempotency_key=(request_value["idempotency_key"]),
        repository_pseudonym=(request_value["repository_pseudonym"]),
        failure_fingerprint=(request_value["failure_fingerprint"]),
        classification=dict(request_value["classification"]),
        repository_context=dict(request_value["repository_context"]),
        constraints=dict(request_value["constraints"]),
        callback=dict(request_value["callback"]),
        created_at=request_value["created_at"],
        expires_at=request_value["expires_at"],
        limitations=tuple(request_value["limitations"]),
    )
    return DelegationRecord(
        record_id=value["record_id"],
        request=request,
        state=value["state"],
        delivery_attempts=int(value["delivery_attempts"]),
        proposal_id=value.get("proposal_id"),
        terminal_state=value.get("terminal_state"),
        created_at=value["created_at"],
        updated_at=value["updated_at"],
        limitations=tuple(value["limitations"]),
    )
