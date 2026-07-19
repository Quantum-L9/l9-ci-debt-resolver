# ADR-RESOLVER-018: Only successful rerun defines clean
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
Local validation and successful push do not define resolution.
The resolver emits `clean` only after the provider reports a completed,
successful rerun for the pushed commit.
