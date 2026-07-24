from __future__ import annotations

from pathlib import Path

import pytest

from l9_debt_resolver.delegation.errors import (
    DelegationReplayError,
)
from l9_debt_resolver.delegation.nonce_ledger import (
    CallbackNonceLedger,
)


def test_nonce_is_single_use(
    tmp_path: Path,
) -> None:
    ledger = CallbackNonceLedger(path=tmp_path / "nonces.json")
    ledger.consume(
        request_id="request-1",
        nonce="a" * 64,
        proposal_id="proposal-1",
    )
    with pytest.raises(DelegationReplayError):
        ledger.consume(
            request_id="request-1",
            nonce="a" * 64,
            proposal_id="proposal-2",
        )
