# ADR-RESOLVER-028: Accepted proposals re-enter P3
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
An accepted PR_Repair proposal is converted into a normal Resolver remediation
plan.
It must pass the existing P3 protected-path, bounds, transaction, SDK
validation, graph-delta, and rollback controls before any remote operation.
