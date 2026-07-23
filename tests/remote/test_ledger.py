from __future__ import annotations

from pathlib import Path

import pytest

from l9_debt_resolver.remote.errors import (
    AttemptLimitReachedError,
)
from l9_debt_resolver.remote.ledger import (
    AttemptLedger,
)


def test_attempts_are_bounded(
    tmp_path: Path,
) -> None:
    ledger = AttemptLedger(
        path=tmp_path / "ledger.json",
        maximum_attempts=2,
    )
    fingerprint = "failure_" + "a" * 64
    assert ledger.next_attempt(fingerprint) == 1
    assert ledger.next_attempt(fingerprint) == 2
    with pytest.raises(AttemptLimitReachedError):
        ledger.next_attempt(fingerprint)
