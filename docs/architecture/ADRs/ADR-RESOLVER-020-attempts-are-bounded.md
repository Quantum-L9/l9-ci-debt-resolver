# ADR-RESOLVER-020: Remote attempts are bounded by fingerprint
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
Each failure fingerprint receives at most two remote remediation attempts.
Further execution terminates as `attempt_limit_reached`.
