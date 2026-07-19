# ADR-RESOLVER-014: Validation planning remains SDK-owned
- Status: Accepted
- Phase: RESOLVER-P3
## Decision
The resolver executes only SDK-authorized validation plans.
It does not independently choose tests, affected contracts, package gates, or
full-validation scope.
