# ADR-RESOLVER-021: Intelligence feedback is aggregate-only
- Status: Accepted
- Phase: RESOLVER-P5
## Decision
Feedback events contain classifications, fingerprints, canonical IDs, counts,
buckets, terminal states, and hashed provenance.
They do not contain raw logs, source code, patches, diffs, paths, credentials,
or developer identity.
