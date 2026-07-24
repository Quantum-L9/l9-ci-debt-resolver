from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SDKSnapshot:
    snapshot_id: str
    repository: str
    revision: str
    capability_profile: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class SDKRepositoryEntity:
    entity_id: str
    kind: str
    path: str | None
    start_line: int | None
    end_line: int | None
    symbol: str | None
    language: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SDKContractReference:
    contract_id: str
    kind: str
    subject_entity_ids: tuple[str, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SDKFindingReference:
    finding_id: str
    rule_id: str
    severity: str
    entity_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    metadata: dict[str, Any]
