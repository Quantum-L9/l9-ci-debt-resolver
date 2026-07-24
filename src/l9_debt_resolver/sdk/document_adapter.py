from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from l9_debt_resolver.correlation.models import StackFrame

from .errors import (
    SDKContractError,
    SnapshotMismatchError,
)
from .models import (
    SDKContractReference,
    SDKFindingReference,
    SDKRepositoryEntity,
    SDKSnapshot,
)


class DocumentSDKKnowledgeProvider:
    """
    Public exchange-document adapter.
    This adapter is intentionally not an SDK schema implementation. It consumes
    canonical identities and records exported by the public SDK boundary.
    """

    def __init__(self, document: dict[str, Any]) -> None:
        self._document = document
        if document.get("schema_version") != "l9.sdk-knowledge-document/v1":
            raise SDKContractError("unsupported SDK knowledge document")
        self._snapshot = _snapshot(document.get("snapshot"))
        self._entities = tuple(_entity(value) for value in _list(document, "entities"))
        self._tests = tuple(_entity(value) for value in _list(document, "tests"))
        self._contracts = tuple(
            _contract(value) for value in _list(document, "contracts")
        )
        self._findings = tuple(_finding(value) for value in _list(document, "findings"))

    @classmethod
    def from_path(
        cls,
        path: Path,
    ) -> DocumentSDKKnowledgeProvider:
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise SDKContractError("SDK knowledge document must be an object")
        return cls(document)

    async def open_repository_snapshot(
        self,
        *,
        repository: str,
        revision: str,
    ) -> SDKSnapshot:
        if (
            self._snapshot.repository != repository
            or self._snapshot.revision != revision
        ):
            raise SnapshotMismatchError(
                "SDK snapshot does not match repository revision"
            )
        return self._snapshot

    async def resolve_repository_entities(
        self,
        *,
        snapshot_id: str,
        locations: tuple[StackFrame, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        self._require_snapshot(snapshot_id)
        matched: dict[str, SDKRepositoryEntity] = {}
        for frame in locations:
            for entity in self._entities:
                if entity.path != frame.path:
                    continue
                if (
                    frame.line is not None
                    and entity.start_line is not None
                    and entity.end_line is not None
                    and not (entity.start_line <= frame.line <= entity.end_line)
                ):
                    continue
                matched[entity.entity_id] = entity
        return _sorted_entities(matched.values())

    async def find_related_tests(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        self._require_snapshot(snapshot_id)
        subjects = set(entity_ids)
        matched = []
        for test in self._tests:
            related = test.metadata.get(
                "related_entity_ids",
                [],
            )
            if isinstance(related, list) and subjects.intersection(
                str(value) for value in related
            ):
                matched.append(test)
        return _sorted_entities(matched)

    async def find_applicable_contracts(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKContractReference, ...]:
        self._require_snapshot(snapshot_id)
        subjects = set(entity_ids)
        return tuple(
            sorted(
                (
                    contract
                    for contract in self._contracts
                    if subjects.intersection(contract.subject_entity_ids)
                ),
                key=lambda contract: contract.contract_id,
            )
        )

    async def correlate_findings(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
    ) -> tuple[SDKFindingReference, ...]:
        self._require_snapshot(snapshot_id)
        entities = set(entity_ids)
        evidence = set(evidence_ids)
        return tuple(
            sorted(
                (
                    finding
                    for finding in self._findings
                    if (
                        entities.intersection(finding.entity_ids)
                        or evidence.intersection(finding.evidence_ids)
                    )
                ),
                key=lambda finding: finding.finding_id,
            )
        )

    def _require_snapshot(
        self,
        snapshot_id: str,
    ) -> None:
        if snapshot_id != self._snapshot.snapshot_id:
            raise SnapshotMismatchError("unknown SDK snapshot identity")


def _snapshot(value: object) -> SDKSnapshot:
    document = _object(value, "snapshot")
    return SDKSnapshot(
        snapshot_id=_required_string(
            document,
            "snapshot_id",
        ),
        repository=_required_string(
            document,
            "repository",
        ),
        revision=_required_string(
            document,
            "revision",
        ),
        capability_profile=tuple(
            sorted(_string_list(document.get("capability_profile", [])))
        ),
        limitations=tuple(sorted(_string_list(document.get("limitations", [])))),
    )


def _entity(value: object) -> SDKRepositoryEntity:
    document = _object(value, "entity")
    return SDKRepositoryEntity(
        entity_id=_required_string(
            document,
            "entity_id",
        ),
        kind=_required_string(
            document,
            "kind",
        ),
        path=_optional_string(document.get("path")),
        start_line=_optional_integer(document.get("start_line")),
        end_line=_optional_integer(document.get("end_line")),
        symbol=_optional_string(document.get("symbol")),
        language=_optional_string(document.get("language")),
        metadata=_metadata(document),
    )


def _contract(value: object) -> SDKContractReference:
    document = _object(value, "contract")
    return SDKContractReference(
        contract_id=_required_string(
            document,
            "contract_id",
        ),
        kind=_required_string(
            document,
            "kind",
        ),
        subject_entity_ids=tuple(
            sorted(
                _string_list(
                    document.get(
                        "subject_entity_ids",
                        [],
                    )
                )
            )
        ),
        metadata=_metadata(document),
    )


def _finding(value: object) -> SDKFindingReference:
    document = _object(value, "finding")
    return SDKFindingReference(
        finding_id=_required_string(
            document,
            "finding_id",
        ),
        rule_id=_required_string(
            document,
            "rule_id",
        ),
        severity=_required_string(
            document,
            "severity",
        ),
        entity_ids=tuple(sorted(_string_list(document.get("entity_ids", [])))),
        evidence_ids=tuple(sorted(_string_list(document.get("evidence_ids", [])))),
        metadata=_metadata(document),
    )


def _list(
    document: dict[str, Any],
    key: str,
) -> list[object]:
    value = document.get(key)
    if not isinstance(value, list):
        raise SDKContractError(f"SDK knowledge field {key} must be a list")
    return value


def _object(
    value: object,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SDKContractError(f"SDK {label} must be an object")
    return value


def _required_string(
    document: dict[str, Any],
    key: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise SDKContractError(f"SDK field {key} must be a non-empty string")
    return value


def _optional_string(
    value: object,
) -> str | None:
    return value if isinstance(value, str) else None


def _optional_integer(
    value: object,
) -> int | None:
    return value if isinstance(value, int) else None


def _string_list(
    value: object,
) -> list[str]:
    if not isinstance(value, list):
        raise SDKContractError("SDK list field has an invalid type")
    return [item for item in value if isinstance(item, str)]


def _metadata(
    document: dict[str, Any],
) -> dict[str, Any]:
    value = document.get("metadata", {})
    if not isinstance(value, dict):
        raise SDKContractError("SDK metadata must be an object")
    return dict(value)


def _sorted_entities(
    entities: object,
) -> tuple[SDKRepositoryEntity, ...]:
    unique = {entity.entity_id: entity for entity in entities}
    return tuple(
        sorted(
            unique.values(),
            key=lambda entity: entity.entity_id,
        )
    )
