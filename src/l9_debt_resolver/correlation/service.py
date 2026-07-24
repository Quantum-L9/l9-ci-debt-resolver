from __future__ import annotations

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.sdk.protocol import (
    SDKKnowledgeProvider,
)

from .errors import IncompleteEvidenceError
from .models import (
    EvidenceBundle,
    RepositoryCorrelation,
)
from .stack_frames import extract_stack_frames


class RepositoryCorrelationService:
    def __init__(
        self,
        SDK: SDKKnowledgeProvider,
    ) -> None:
        self._SDK = SDK

    async def correlate(
        self,
        bundle: EvidenceBundle,
    ) -> RepositoryCorrelation:
        if bundle.evidence.log_completeness != "complete":
            raise IncompleteEvidenceError(
                "repository correlation requires a complete failed runtime log"
            )
        snapshot = await self._SDK.open_repository_snapshot(
            repository=bundle.repository,
            revision=bundle.revision,
        )
        frames = extract_stack_frames(bundle.redacted_log)
        entities = await self._SDK.resolve_repository_entities(
            snapshot_id=snapshot.snapshot_id,
            locations=frames,
        )
        entity_ids = tuple(sorted({entity.entity_id for entity in entities}))
        related_tests = await self._SDK.find_related_tests(
            snapshot_id=snapshot.snapshot_id,
            entity_ids=entity_ids,
        )
        contracts = await self._SDK.find_applicable_contracts(
            snapshot_id=snapshot.snapshot_id,
            entity_ids=entity_ids,
        )
        findings = await self._SDK.correlate_findings(
            snapshot_id=snapshot.snapshot_id,
            entity_ids=entity_ids,
            evidence_ids=(bundle.evidence.evidence_id,),
        )
        resolved_paths = {entity.path for entity in entities if entity.path is not None}
        unresolved = tuple(
            frame for frame in frames if frame.path not in resolved_paths
        )
        limitations = set(snapshot.limitations)
        if not frames:
            limitations.add(
                "no repository source locations were extracted from the failed log"
            )
        if frames and not entities:
            limitations.add(
                "SDK resolved no repository entities for extracted source locations"
            )
        if unresolved:
            limitations.add("one or more log locations were unresolved")
        correlation_material = {
            "evidence_id": bundle.evidence.evidence_id,
            "snapshot_id": snapshot.snapshot_id,
            "frame_ids": [frame.frame_id for frame in frames],
            "entity_ids": list(entity_ids),
            "test_ids": [test.entity_id for test in related_tests],
            "contract_ids": [contract.contract_id for contract in contracts],
            "finding_ids": [finding.finding_id for finding in findings],
        }
        return RepositoryCorrelation(
            correlation_id=namespaced_identity(
                "correlation_",
                correlation_material,
            ),
            evidence_id=bundle.evidence.evidence_id,
            repository_snapshot_id=snapshot.snapshot_id,
            stack_frames=frames,
            repository_entities=tuple(
                sorted(
                    entities,
                    key=lambda entity: entity.entity_id,
                )
            ),
            related_tests=tuple(
                sorted(
                    related_tests,
                    key=lambda entity: entity.entity_id,
                )
            ),
            applicable_contracts=tuple(
                sorted(
                    contracts,
                    key=lambda contract: contract.contract_id,
                )
            ),
            correlated_findings=tuple(
                sorted(
                    findings,
                    key=lambda finding: finding.finding_id,
                )
            ),
            unresolved_locations=tuple(
                sorted(
                    unresolved,
                    key=lambda frame: frame.frame_id,
                )
            ),
            limitations=tuple(sorted(limitations)),
        )
