# ADR-RESOLVER-007: Missing and incomplete logs fail closed
- Status: Accepted
- Phase: RESOLVER-P1
## Decision
A failed job without a complete failed log produces
`insufficient_log_evidence`.
It cannot authorize classification-driven remediation.
## Rationale
A partial log may omit the originating command, first failure, stack trace,
compiler context, or provider termination marker.
