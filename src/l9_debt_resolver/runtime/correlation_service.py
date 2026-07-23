from __future__ import annotations

from dataclasses import dataclass

from l9_debt_resolver.classification.engine import (
    RootCauseClassifier,
)
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.correlation.models import (
    EvidenceBundle,
    RepositoryCorrelation,
)
from l9_debt_resolver.correlation.service import (
    RepositoryCorrelationService,
)
from l9_debt_resolver.sdk.protocol import (
    SDKKnowledgeProvider,
)


@dataclass(frozen=True)
class CorrelationAndClassificationResult:
    correlation: RepositoryCorrelation
    classification: ClassificationTrace

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": ("l9.correlation-classification-result/v1"),
            "correlation": self.correlation.as_dict(),
            "classification": self.classification.as_dict(),
        }


class ResolverCorrelationRuntime:
    def __init__(
        self,
        *,
        SDK: SDKKnowledgeProvider,
    ) -> None:
        self._correlation = RepositoryCorrelationService(SDK)
        self._classifier = RootCauseClassifier()

    async def execute(
        self,
        bundle: EvidenceBundle,
    ) -> CorrelationAndClassificationResult:
        correlation = await self._correlation.correlate(bundle)
        classification = await self._classifier.classify(
            bundle=bundle,
            correlation=correlation,
        )
        return CorrelationAndClassificationResult(
            correlation=correlation,
            classification=classification,
        )
