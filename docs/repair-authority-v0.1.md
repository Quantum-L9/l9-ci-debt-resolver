# Repair authority in constellation v0.1

## The decision

| System | v0.1 role |
|---|---|
| `l9-ci-debt-resolver` | The debt pipeline's repair planner and local applier. Sole repair authority. |
| `PR_Repair` | A standalone pull-request assistant. Not part of the debt pipeline. |

Resolver → PR_Repair delegation is **unsupported** in v0.1.

## Why

This repository defines a careful delegation boundary in
`l9.pr-repair-request/v1` and `l9.pr-repair-proposal/v1`. It is not a sketch:
paths are pseudonymised to `path_<sha256>` tokens, constraints pin
`remote_authority_granted` to `false`, `protected_paths_enforced` and
`validation_required` to `true`, and the proposal `status` enum admits only
`proposed` or `unsupported` — a delegate may propose, never conclude. The
resolver then re-verifies `expected_file_sha256` and `expected_text_sha256`
before applying anything.

The protocol is sound. What it lacks is a delegate. Neither contract token
appears anywhere in `PR_Repair`, or in any other repository in the
constellation. `PR_Repair` instead runs a parallel loop with its own finding
model, clustering, classification, approval gate, protected-path policy,
worktree isolation, patch generator, patch applier, verification, learning, and
rollback.

Two systems each built as the organisation's repair owner is a resolvable
problem only if someone resolves it. v0.1 resolves it by scope rather than by
integration: the resolver keeps debt-pipeline repair, and `PR_Repair` is
documented as a separate product. Nothing is deleted on either side.

## What this repository asserts

`resolver_capabilities()` reports `PR_Repair_delegation: false` and carries a
`delegation_status` block naming the two unimplemented contracts. The file and
HTTPS delegation transports remain implemented and tested — they are real code
— and are listed there as `inert_transports`, because a transport with no
delegate on the far end carries nothing.

`tests/activation/test_runtime_services.py` holds this: no PR_Repair authority
grant may be true, every transport must be declared inert, and the delegation
status must stay `unsupported`.

## What would change the decision

Either outcome is acceptable; leaving both systems claiming repair ownership is
not.

1. **`PR_Repair` becomes a bounded proposer.** It implements
   `l9.pr-repair-request/v1` and `l9.pr-repair-proposal/v1` and drops its own
   executor, verification, and push path. `delegation_status` then moves to
   `supported` and the capability grant returns to `true`.
2. **Delegation is retired.** If `PR_Repair` stays independent, this
   repository's delegation phase is removed rather than left dormant, and these
   contracts are withdrawn.

Until one of those happens, the delegation code stays in place and reports
itself unavailable — which is accurate, and cheaper to reverse than a deletion.
