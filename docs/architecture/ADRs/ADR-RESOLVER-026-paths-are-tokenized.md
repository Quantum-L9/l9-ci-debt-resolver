# ADR-RESOLVER-026: Delegated paths are tokenized
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
Repository paths are represented by HMAC-SHA256 path tokens in delegation
requests and callbacks.
Only the Resolver retains the token-to-path map.
