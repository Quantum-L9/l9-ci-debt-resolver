from __future__ import annotations

from pathlib import Path

import pytest

from l9_debt_resolver.delegation.file_transport import (
    JSONFilePRRepairTransport,
)
from l9_debt_resolver.delegation.models import (
    PRRepairRequest,
)


def request() -> PRRepairRequest:
    return PRRepairRequest(
        request_id=("pr_repair_request_" + "a" * 64),
        idempotency_key=("pr_repair_idempotency_" + "b" * 64),
        repository_pseudonym=("repository_" + "c" * 64),
        failure_fingerprint=("failure_" + "d" * 64),
        classification={
            "category": "test_failure",
            "confidence_bucket": "medium",
            "remediation_eligibility": ("approval_required"),
            "failed_command_hash": "e" * 64,
            "normalized_error_signatures": ["assertion failed"],
        },
        repository_context={
            "snapshot_id_hash": "f" * 64,
            "entity_ids": ["entity:1"],
            "finding_ids": [],
            "contract_ids": [],
            "related_test_ids": ["test:1"],
            "language_families": ["python"],
            "capability_profile": ["python"],
            "allowed_path_tokens": ["path_" + "1" * 64],
        },
        constraints={
            "maximum_changed_files": 10,
            "maximum_changed_lines": 500,
            "maximum_operations": 50,
            "allowed_remediation_classes": ["bounded_source"],
            "protected_paths_enforced": True,
            "validation_required": True,
            "remote_authority_granted": False,
        },
        callback={
            "callback_id": ("callback_" + "2" * 64),
            "nonce": "3" * 64,
            "signature_algorithm": ("HMAC-SHA256"),
        },
        created_at="2026-07-19T00:00:00Z",
        expires_at="2026-07-19T00:15:00Z",
        limitations=(),
    )


@pytest.mark.asyncio
async def test_file_transport_is_idempotent(
    tmp_path: Path,
) -> None:
    transport = JSONFilePRRepairTransport(directory=tmp_path)
    first = await transport.deliver(request())
    second = await transport.deliver(request())
    assert first == second
    assert len(list(tmp_path.glob("*.json"))) == 1
