# ADR-RESOLVER-024: Feedback delivery is idempotent
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
Event identity and idempotency keys are deterministic for a resolution outcome.
HTTP 409 is treated as successful duplicate acknowledgement.
