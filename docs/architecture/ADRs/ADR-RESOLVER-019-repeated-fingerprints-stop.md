# ADR-RESOLVER-019: Repeated failure fingerprints stop the loop
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
When a rerun produces the same failure fingerprint, the attempt terminates as
`repeated_failure`.
The resolver does not perform unbounded speculative retries.
