from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClassificationSignal:
    signal: str
    category: str
    weight: float
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "category": self.category,
            "weight": self.weight,
            "source": self.source,
        }


@dataclass(frozen=True)
class ClassificationTrace:
    classification_id: str
    failure_fingerprint: str
    category: str
    confidence: float
    evidence_ids: tuple[str, ...]
    matched_signals: tuple[ClassificationSignal, ...]
    failed_command: str | None
    repository_snapshot_id: str
    affected_entities: tuple[str, ...]
    related_tests: tuple[str, ...]
    applicable_contracts: tuple[str, ...]
    correlated_finding_ids: tuple[str, ...]
    remediation_eligibility: str
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.classification-trace/v1",
            "classification_id": self.classification_id,
            "failure_fingerprint": self.failure_fingerprint,
            "category": self.category,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "matched_signals": [signal.as_dict() for signal in self.matched_signals],
            "failed_command": self.failed_command,
            "repository_snapshot_id": (self.repository_snapshot_id),
            "affected_entities": list(self.affected_entities),
            "related_tests": list(self.related_tests),
            "applicable_contracts": list(self.applicable_contracts),
            "correlated_finding_ids": list(self.correlated_finding_ids),
            "remediation_eligibility": (self.remediation_eligibility),
            "limitations": list(self.limitations),
        }
