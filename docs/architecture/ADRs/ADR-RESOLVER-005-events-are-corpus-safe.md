
ADR-RESOLVER-005: Resolver events are correction-versioned and corpus-safe

* Status: Accepted
* Phase: RESOLVER-P0

Decision

Corpus-facing events contain aggregate classification, resolution, validation,
and hashed provenance data.

They exclude raw logs, source content, patches, paths, credentials, and
developer identity.
