# ADR-RESOLVER-008: Raw CI logs are ephemeral
- Status: Accepted
- Phase: RESOLVER-P1
## Decision
Raw failed logs exist only in bounded acquisition memory.
Only redacted logs, hashes, typed evidence, and provenance may be persisted.
## Excluded data
- credentials;
- tokens;
- private keys;
- email addresses;
- absolute paths;
- repository checkout roots.
