# ADR-RESOLVER-027: PR_Repair callbacks are signed and single-use
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
Every proposal callback requires an HMAC-SHA256 signature, bounded timestamp,
request identity, proposal identity, and single-use nonce.
Replayed callbacks are rejected.
