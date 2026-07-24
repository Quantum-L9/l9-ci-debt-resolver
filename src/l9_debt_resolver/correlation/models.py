from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from l9_debt_resolver.sdk.models import (
    SDKContractReference,
    SDKFindingReference,
    SDKRepositoryEntity,
)


@dataclass(frozen=True)
class EvidenceBundle:
    repository: str
    revision: str
    evidence: Any
    redacted_log: str
    failed_job: Any


@dataclass(frozen=True)
class StackFrame:
    frame_id: str
    path: str
    line: int | None
    column: int | None
    symbol_hint: str | None
    language_family: str
    log_line_number: int
    confidence: float
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.stack-frame/v1",
            "frame_id": self.frame_id,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "symbol_hint": self.symbol_hint,
            "language_family": self.language_family,
            "log_line_number": self.log_line_number,
            "confidence": self.confidence,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class RepositoryCorrelation:
    correlation_id: str
    evidence_id: str
    repository_snapshot_id: str
    stack_frames: tuple[StackFrame, ...]
    repository_entities: tuple[SDKRepositoryEntity, ...]
    related_tests: tuple[SDKRepositoryEntity, ...]
    applicable_contracts: tuple[SDKContractReference, ...]
    correlated_findings: tuple[SDKFindingReference, ...]
    unresolved_locations: tuple[StackFrame, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.repository-correlation/v1",
            "correlation_id": self.correlation_id,
            "evidence_id": self.evidence_id,
            "repository_snapshot_id": self.repository_snapshot_id,
            "stack_frames": [frame.as_dict() for frame in self.stack_frames],
            "repository_entities": [
                {
                    "entity_id": entity.entity_id,
                    "kind": entity.kind,
                    "path": entity.path,
                    "start_line": entity.start_line,
                    "end_line": entity.end_line,
                    "symbol": entity.symbol,
                    "language": entity.language,
                    "metadata": entity.metadata,
                }
                for entity in self.repository_entities
            ],
            "related_tests": [
                {
                    "entity_id": entity.entity_id,
                    "kind": entity.kind,
                    "path": entity.path,
                    "start_line": entity.start_line,
                    "end_line": entity.end_line,
                    "symbol": entity.symbol,
                    "language": entity.language,
                    "metadata": entity.metadata,
                }
                for entity in self.related_tests
            ],
            "applicable_contracts": [
                {
                    "contract_id": contract.contract_id,
                    "kind": contract.kind,
                    "subject_entity_ids": list(contract.subject_entity_ids),
                    "metadata": contract.metadata,
                }
                for contract in self.applicable_contracts
            ],
            "correlated_findings": [
                {
                    "finding_id": finding.finding_id,
                    "rule_id": finding.rule_id,
                    "severity": finding.severity,
                    "entity_ids": list(finding.entity_ids),
                    "evidence_ids": list(finding.evidence_ids),
                    "metadata": finding.metadata,
                }
                for finding in self.correlated_findings
            ],
            "unresolved_locations": [
                frame.as_dict() for frame in self.unresolved_locations
            ],
            "limitations": list(self.limitations),
        }
