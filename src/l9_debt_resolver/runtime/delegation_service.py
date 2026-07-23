from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.delegation.converter import (
    convert_proposal_to_remediation_plan,
)
from l9_debt_resolver.delegation.ledger import (
    DelegationLedger,
)
from l9_debt_resolver.delegation.models import (
    DelegationRecord,
    PRRepairProposal,
)
from l9_debt_resolver.delegation.nonce_ledger import (
    CallbackNonceLedger,
)
from l9_debt_resolver.delegation.proposal import (
    validate_proposal_contract,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
)


def utc_now() -> str:
    return (
        datetime.now(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


class DelegationCallbackService:
    def __init__(
        self,
        *,
        ledger: DelegationLedger,
        nonce_ledger: CallbackNonceLedger,
    ) -> None:
        self._ledger = ledger
        self._nonce_ledger = nonce_ledger

    def accept_proposal(
        self,
        *,
        record: DelegationRecord,
        proposal: PRRepairProposal,
        callback_key: bytes,
        workspace_root: Path,
        path_token_map: dict[str, str],
        classification_trace: ClassificationTrace,
        repository_snapshot_id: str,
        repository_revision: str,
        validation_plan_id: str,
    ) -> tuple[
        DelegationRecord,
        RemediationPlan | None,
    ]:
        validate_proposal_contract(
            request=record.request,
            proposal=proposal,
            callback_key=callback_key,
            repository_snapshot_id=(repository_snapshot_id),
        )
        self._nonce_ledger.consume(
            request_id=proposal.request_id,
            nonce=proposal.callback_nonce,
            proposal_id=proposal.proposal_id,
        )
        if proposal.status == "unsupported":
            updated = replace(
                record,
                state="unsupported",
                proposal_id=proposal.proposal_id,
                terminal_state=("delegation_unsupported"),
                updated_at=utc_now(),
                limitations=tuple(
                    sorted(
                        {
                            *record.limitations,
                            *proposal.limitations,
                        }
                    )
                ),
            )
            self._ledger.save(updated)
            return updated, None
        remediation_plan = convert_proposal_to_remediation_plan(
            workspace_root=workspace_root,
            request=record.request,
            proposal=proposal,
            path_token_map=path_token_map,
            classification_trace=(classification_trace),
            repository_snapshot_id=(repository_snapshot_id),
            repository_revision=(repository_revision),
            validation_plan_id=(validation_plan_id),
        )
        updated = replace(
            record,
            state="proposal_accepted",
            proposal_id=proposal.proposal_id,
            terminal_state="proposal_accepted",
            updated_at=utc_now(),
            limitations=tuple(
                sorted(
                    {
                        *record.limitations,
                        *proposal.limitations,
                    }
                )
            ),
        )
        self._ledger.save(updated)
        return updated, remediation_plan
