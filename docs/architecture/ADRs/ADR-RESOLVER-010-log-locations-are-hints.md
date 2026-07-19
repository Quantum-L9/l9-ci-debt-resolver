
ADR-RESOLVER-010: Failed-log source locations are correlation hints

* Status: Accepted
* Phase: RESOLVER-P2

Decision

Paths, lines, columns, symbols, and stack frames extracted from CI logs are
resolver-owned hints.

They become repository-semantic evidence only after SDK correlation.

Absolute paths are reduced to safe repository-relative candidates. Traversal
paths and redaction placeholders are rejected.
