from __future__ import annotations

import pytest

from l9_debt_resolver.correlation.models import (
    StackFrame,
)
from l9_debt_resolver.sdk.document_adapter import (
    DocumentSDKKnowledgeProvider,
)
from l9_debt_resolver.sdk.errors import (
    SnapshotMismatchError,
)


def document() -> dict[str, object]:
    return {
        "schema_version": "l9.sdk-knowledge-document/v1",
        "repository": "Quantum-L9/example",
        "revision": "abcdef1234567",
        "snapshot": {
            "snapshot_id": "snapshot-1",
            "repository": "Quantum-L9/example",
            "revision": "abcdef1234567",
            "capability_profile": ["python"],
            "limitations": [],
        },
        "entities": [
            {
                "entity_id": "entity-1",
                "kind": "function",
                "path": "src/app.py",
                "start_line": 1,
                "end_line": 100,
                "symbol": "execute",
                "language": "python",
                "metadata": {"CI_failure_category": "test_failure"},
            }
        ],
        "tests": [
            {
                "entity_id": "test-1",
                "kind": "test",
                "path": "tests/test_app.py",
                "start_line": 1,
                "end_line": 50,
                "symbol": "test_execute",
                "language": "python",
                "metadata": {"related_entity_ids": ["entity-1"]},
            }
        ],
        "contracts": [
            {
                "contract_id": "contract-1",
                "kind": "behavior",
                "subject_entity_ids": ["entity-1"],
                "metadata": {"CI_failure_category": "test_failure"},
            }
        ],
        "findings": [
            {
                "finding_id": "finding-1",
                "rule_id": "rule-1",
                "severity": "error",
                "entity_ids": ["entity-1"],
                "evidence_ids": [],
                "metadata": {"CI_failure_category": "test_failure"},
            }
        ],
    }


@pytest.mark.asyncio
async def test_snapshot_and_entity_correlation() -> None:
    adapter = DocumentSDKKnowledgeProvider(document())
    snapshot = await adapter.open_repository_snapshot(
        repository="Quantum-L9/example",
        revision="abcdef1234567",
    )
    entities = await adapter.resolve_repository_entities(
        snapshot_id=snapshot.snapshot_id,
        locations=(
            StackFrame(
                frame_id="frame-" + "a" * 64,
                path="src/app.py",
                line=42,
                column=None,
                symbol_hint="execute",
                language_family="python",
                log_line_number=1,
                confidence=0.98,
                limitations=(),
            ),
        ),
    )
    assert snapshot.snapshot_id == "snapshot-1"
    assert [entity.entity_id for entity in entities] == ["entity-1"]


@pytest.mark.asyncio
async def test_snapshot_mismatch_fails() -> None:
    adapter = DocumentSDKKnowledgeProvider(document())
    with pytest.raises(SnapshotMismatchError):
        await adapter.open_repository_snapshot(
            repository="Quantum-L9/example",
            revision="different",
        )
