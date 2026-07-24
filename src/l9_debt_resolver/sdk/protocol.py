from __future__ import annotations

from typing import Protocol

from l9_debt_resolver.correlation.models import (
    StackFrame,
)

from .models import (
    SDKContractReference,
    SDKFindingReference,
    SDKRepositoryEntity,
    SDKSnapshot,
)


class SDKKnowledgeProvider(Protocol):
    async def open_repository_snapshot(
        self,
        *,
        repository: str,
        revision: str,
    ) -> SDKSnapshot:
        """Open a canonical SDK-owned repository snapshot."""

    async def resolve_repository_entities(
        self,
        *,
        snapshot_id: str,
        locations: tuple[StackFrame, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        """Resolve log locations to canonical SDK entities."""

    async def find_related_tests(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKRepositoryEntity, ...]:
        """Return canonical SDK test entities related to entities."""

    async def find_applicable_contracts(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
    ) -> tuple[SDKContractReference, ...]:
        """Return SDK-owned contracts applicable to entities."""

    async def correlate_findings(
        self,
        *,
        snapshot_id: str,
        entity_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
    ) -> tuple[SDKFindingReference, ...]:
        """Return canonical SDK findings associated with the failure."""
