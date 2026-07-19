
ADR-RESOLVER-009: SDK owns repository knowledge

* Status: Accepted
* Phase: RESOLVER-P2

Decision

Repository snapshots, repository entities, contracts, findings, validation
plans, and validation results remain SDK-owned.

The resolver consumes these through a public adapter and does not create local
canonical equivalents.
