# ADR-RESOLVER-013: P3 remediation is transactional and local
- Status: Accepted
- Phase: RESOLVER-P3
## Decision
P3 may mutate only the local workspace.
Every original file is captured before mutation. Any patch, validation, graph
delta, or SDK result failure causes rollback.
Remote branch interaction begins only in P4.
