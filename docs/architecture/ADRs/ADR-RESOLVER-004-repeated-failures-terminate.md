
ADR-RESOLVER-004: Repeated identical failures terminate

* Status: Accepted
* Phase: RESOLVER-P0

Decision

When a rerun produces the same failure fingerprint, the current strategy
terminates as repeated_failure.

The Resolver does not conduct unbounded speculative retries.
