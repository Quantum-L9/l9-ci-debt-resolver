
Resolver Roadmap

All phases RESOLVER-P0 through RESOLVER-P6 are consolidated and implemented in this repository. The local gate
(ruff check . && mypy src && pytest) and the per-phase GitHub Actions workflows validate every phase.

RESOLVER-P0 - Contract alignment

Status: Implemented

* repository ownership boundary
* dependency boundary
* canonical identity encoding
* typed CI evidence
* typed failure classification
* attempt lifecycle
* terminal states
* corpus-safe events
* schema validation
* package and CLI foundation

RESOLVER-P1 - Failed-log acquisition

Status: Implemented

* failed-run acquisition
* failed-job acquisition
* authoritative failed-log acquisition
* bounded pagination
* bounded retry
* truncation detection
* provenance
* secret and path redaction

RESOLVER-P2 - Repository correlation

Status: Implemented

* SDK repository snapshots
* stack-frame extraction
* SDK entity correlation
* related tests
* applicable contracts
* canonical finding correlation
* root-cause classification

RESOLVER-P3 - Bounded validation

Status: Implemented

* remediation eligibility
* approval enforcement
* protected-path enforcement
* bounded transactional changes
* SDK validation plans
* original failure reproduction
* targeted tests
* graph-delta validation
* rollback

RESOLVER-P4 - Remote resolution loop

Status: Implemented

* exact revision enforcement
* expected worktree enforcement
* deterministic repair branches
* deterministic commits
* explicit push authorization
* non-force push
* rerun dispatch
* bounded rerun observation
* repeated-failure detection
* terminal states

RESOLVER-P5 - Intelligence feedback

Status: Implemented

* privacy-safe resolution events
* repository pseudonymization
* repeated-failure telemetry
* deterministic event identities
* durable outbox
* bounded retries
* dead-letter state
* corpus-safe provenance

RESOLVER-P6 - PR_Repair delegation

Status: Implemented here, unsupported in v0.1 - no delegate implements
l9.pr-repair-request/v1 or l9.pr-repair-proposal/v1. See
docs/repair-authority-v0.1.md.

* proposal-only delegation
* bounded privacy-safe context
* repository and path pseudonymization
* signed callbacks
* replay protection
* proposal scope validation
* proposal-to-remediation conversion
* retained Resolver authority
