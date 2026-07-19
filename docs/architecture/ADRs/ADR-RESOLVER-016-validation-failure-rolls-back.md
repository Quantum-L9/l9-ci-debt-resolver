# ADR-RESOLVER-016: Any validation failure rolls back remediation
- Status: Accepted
- Phase: RESOLVER-P3
## Decision
Original-failure reproduction, targeted tests, affected contracts, graph
delta, full gates, and the canonical SDK validation result must all pass.
Otherwise the workspace is restored to its pre-remediation state.
