from __future__ import annotations

from typing import Any


def resolver_capabilities() -> dict[str, Any]:
    return {
        "schema_version": "l9.resolver-capabilities/v1",
        "phase": "RESOLVER-P6",
        "capabilities": {
            "contract_validation": True,
            "typed_CI_evidence": True,
            "failed_log_acquisition": True,
            "SDK_repository_snapshots": True,
            "root_cause_classification": True,
            "bounded_remediation": True,
            "SDK_validation_execution": True,
            "repair_branch_policy": True,
            "CI_rerun_observation": True,
            "terminal_state_emission": True,
            "privacy_safe_feedback_events": True,
            # The delegation protocol is built, typed, and tested on this side.
            # No delegate implements it: `l9.pr-repair-request/v1` and
            # `l9.pr-repair-proposal/v1` appear in no other repository in the
            # constellation, PR_Repair included. Reporting the capability as
            # available would advertise a channel with nothing on the far end,
            # so it is reported as unavailable until a delegate exists. See
            # `delegation_status` below and `docs/repair-authority-v0.1.md`.
            "PR_Repair_delegation": False,
            "typed_delegation_requests": True,
            "bounded_delegation_context": True,
            "repository_pseudonymization": True,
            "path_tokenization": True,
            "signed_proposal_callbacks": True,
            "callback_replay_protection": True,
            "proposal_identity_binding": True,
            "proposal_privacy_validation": True,
            "proposal_scope_validation": True,
            "proposal_to_remediation_conversion": True,
            "durable_delegation_ledger": True,
            "bounded_delegation_retries": True,
            "json_file_PR_Repair_transport": True,
            "https_PR_Repair_transport": True,
            "PR_Repair_repository_mutation": False,
            "PR_Repair_validation_authority": False,
            "PR_Repair_push_authority": False,
            "PR_Repair_merge_authority": False,
            "PR_Repair_terminal_state_authority": False,
            "automatic_merge": False,
        },
        "delegation_status": {
            "status": "unsupported",
            "reason": (
                "No delegate implements l9.pr-repair-request/v1 or "
                "l9.pr-repair-proposal/v1. PR_Repair is a standalone "
                "pull-request assistant in v0.1 and is not part of the debt "
                "pipeline."
            ),
            "request_contract": "l9.pr-repair-request/v1",
            "proposal_contract": "l9.pr-repair-proposal/v1",
            "repair_authority": "l9-ci-debt-resolver",
            # The transports below are implemented and tested. They are inert:
            # a transport with no delegate on the far end carries nothing. They
            # are listed so the capability document is not read as "the
            # resolver can reach PR_Repair over HTTPS today".
            "inert_transports": [
                "json_file_PR_Repair_transport",
                "https_PR_Repair_transport",
            ],
        },
        "limitations": [
            "PR_Repair delegation is unsupported in v0.1: no delegate "
            "implements the request or proposal contract.",
            "The resolver is the only debt-pipeline repair planner and "
            "applier in v0.1.",
            "PR_Repair may generate proposals only.",
            "Resolver retains all mutation and validation authority.",
            "Resolver retains branch, push, rerun, attempt, and "
            "terminal-state authority.",
            "Raw logs, source content, paths, patches, credentials, and "
            "identity are excluded from delegation.",
            "Automatic merge remains prohibited.",
        ],
    }
