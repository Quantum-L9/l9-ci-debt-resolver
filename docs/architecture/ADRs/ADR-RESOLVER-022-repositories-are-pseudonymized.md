# ADR-RESOLVER-022: Repository identity is pseudonymized
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
The raw repository owner and name are never transmitted in feedback events.
Repository identity is represented by HMAC-SHA256 using an operator-controlled
secret key.
