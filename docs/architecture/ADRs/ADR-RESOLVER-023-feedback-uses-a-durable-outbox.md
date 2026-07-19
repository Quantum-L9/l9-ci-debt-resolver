# ADR-RESOLVER-023: Feedback uses a durable outbox
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
Every validated feedback event is written atomically to a local owner-only
outbox before delivery.
Successful delivery records a receipt. Exhausted or permanent failures enter
dead-letter state.
