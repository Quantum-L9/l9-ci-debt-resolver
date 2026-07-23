from __future__ import annotations

import re
from collections import defaultdict

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.correlation.models import (
    EvidenceBundle,
    RepositoryCorrelation,
)

from .models import (
    ClassificationSignal,
    ClassificationTrace,
)
from .rules import COMMAND_RULES, RULES


class RootCauseClassifier:
    AUTOMATIC_MINIMUM = 0.90
    APPROVAL_MINIMUM = 0.70

    async def classify(
        self,
        *,
        bundle: EvidenceBundle,
        correlation: RepositoryCorrelation,
    ) -> ClassificationTrace:
        if bundle.evidence.log_completeness != "complete":
            raise ValueError("classification requires complete runtime-log evidence")
        signals = self._collect_signals(
            bundle=bundle,
            correlation=correlation,
        )
        category_scores: dict[str, float] = defaultdict(float)
        for signal in signals:
            category_scores[signal.category] += signal.weight
        limitations = set(correlation.limitations)
        if not category_scores:
            category = "unsupported"
            confidence = 0.0
            limitations.add("no supported root-cause signal was detected")
        else:
            ranked = sorted(
                category_scores.items(),
                key=lambda value: (
                    -value[1],
                    value[0],
                ),
            )
            category, raw_score = ranked[0]
            confidence = min(0.99, raw_score)
            if (
                len(ranked) > 1
                and ranked[1][1] >= 0.70
                and abs(raw_score - ranked[1][1]) < 0.15
            ):
                category = "unsupported"
                confidence = min(confidence, 0.49)
                limitations.add("conflicting high-confidence root-cause signals")
        explicit_log_signal = any(signal.source == "failed_log" for signal in signals)
        if not explicit_log_signal and category != "unsupported":
            category = "unsupported"
            confidence = min(confidence, 0.49)
            limitations.add(
                "classification lacks an explicit failed-log tool signature"
            )
        if category == "infrastructure":
            confidence = min(confidence, 0.89)
            eligibility = "unsupported"
        elif category == "security_failure":
            eligibility = "approval_required"
        elif category == "unsupported":
            eligibility = "unsupported"
        elif confidence >= self.AUTOMATIC_MINIMUM:
            eligibility = "automatic"
        elif confidence >= self.APPROVAL_MINIMUM:
            eligibility = "approval_required"
        else:
            eligibility = "unsupported"
        affected_entities = tuple(
            entity.entity_id for entity in correlation.repository_entities
        )
        related_tests = tuple(entity.entity_id for entity in correlation.related_tests)
        applicable_contracts = tuple(
            contract.contract_id for contract in correlation.applicable_contracts
        )
        finding_ids = tuple(
            finding.finding_id for finding in correlation.correlated_findings
        )
        fingerprint_material = {
            "category": category,
            "failed_command": _normalize_command(bundle.evidence.failed_command),
            "log_hash": bundle.evidence.log_sha256,
            "entity_ids": list(affected_entities),
            "contract_ids": list(applicable_contracts),
            "finding_ids": list(finding_ids),
        }
        failure_fingerprint = namespaced_identity(
            "failure_",
            fingerprint_material,
        )
        classification_material = {
            "failure_fingerprint": failure_fingerprint,
            "snapshot_id": (correlation.repository_snapshot_id),
            "signals": [signal.as_dict() for signal in signals],
            "confidence": round(confidence, 4),
            "eligibility": eligibility,
        }
        return ClassificationTrace(
            classification_id=namespaced_identity(
                "classification_",
                classification_material,
            ),
            failure_fingerprint=failure_fingerprint,
            category=category,
            confidence=round(confidence, 4),
            evidence_ids=(bundle.evidence.evidence_id,),
            matched_signals=signals,
            failed_command=bundle.evidence.failed_command,
            repository_snapshot_id=(correlation.repository_snapshot_id),
            affected_entities=affected_entities,
            related_tests=related_tests,
            applicable_contracts=applicable_contracts,
            correlated_finding_ids=finding_ids,
            remediation_eligibility=eligibility,
            limitations=tuple(sorted(limitations)),
        )

    def _collect_signals(
        self,
        *,
        bundle: EvidenceBundle,
        correlation: RepositoryCorrelation,
    ) -> tuple[ClassificationSignal, ...]:
        signals: list[ClassificationSignal] = []
        for rule in RULES:
            if rule.pattern.search(bundle.redacted_log):
                signals.append(
                    ClassificationSignal(
                        signal=rule.name,
                        category=rule.category,
                        weight=rule.weight,
                        source="failed_log",
                    )
                )
        command = bundle.evidence.failed_command or ""
        for pattern, category in COMMAND_RULES:
            if pattern.search(command):
                signals.append(
                    ClassificationSignal(
                        signal="failed_command_tool",
                        category=category,
                        weight=0.20,
                        source="failed_command",
                    )
                )
        if correlation.repository_entities:
            entity_categories = _metadata_categories(
                entity.metadata for entity in correlation.repository_entities
            )
            for category in entity_categories:
                signals.append(
                    ClassificationSignal(
                        signal="SDK_entity_category",
                        category=category,
                        weight=0.10,
                        source="SDK_entity",
                    )
                )
        contract_categories = _metadata_categories(
            contract.metadata for contract in correlation.applicable_contracts
        )
        for category in contract_categories:
            signals.append(
                ClassificationSignal(
                    signal="SDK_contract_category",
                    category=category,
                    weight=0.05,
                    source="SDK_contract",
                )
            )
        finding_categories = _metadata_categories(
            finding.metadata for finding in correlation.correlated_findings
        )
        for category in finding_categories:
            signals.append(
                ClassificationSignal(
                    signal="SDK_finding_category",
                    category=category,
                    weight=0.10,
                    source="SDK_finding",
                )
            )
        return tuple(
            sorted(
                signals,
                key=lambda signal: (
                    signal.category,
                    signal.source,
                    signal.signal,
                    signal.weight,
                ),
            )
        )


_ALLOWED_CATEGORIES = {
    "configuration",
    "dependency",
    "compilation",
    "test_failure",
    "lint_failure",
    "type_failure",
    "generated_file_drift",
    "security_failure",
    "infrastructure",
    "unsupported",
}


def _metadata_categories(
    metadata_values: object,
) -> tuple[str, ...]:
    categories: set[str] = set()
    for metadata in metadata_values:
        value = metadata.get("CI_failure_category")
        if isinstance(value, str) and value in _ALLOWED_CATEGORIES:
            categories.add(value)
    return tuple(sorted(categories))


def _normalize_command(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value.strip())[:2000]
