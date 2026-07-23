from __future__ import annotations

import pytest

from l9_debt_resolver.classification.engine import (
    RootCauseClassifier,
)
from tests.classification.test_engine import correlation
from tests.correlation.test_service import bundle


@pytest.mark.asyncio
async def test_classification_identity_is_deterministic() -> None:
    classifier = RootCauseClassifier()
    value = bundle()
    correlated = correlation()
    first = await classifier.classify(
        bundle=value,
        correlation=correlated,
    )
    second = await classifier.classify(
        bundle=value,
        correlation=correlated,
    )
    assert first == second
    assert first.classification_id == second.classification_id
    assert first.failure_fingerprint == second.failure_fingerprint
