# ADR-RESOLVER-017: P4 pushes only deterministic repair branches
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
P4 may create and push only resolver-owned repair branches.
Protected branches, arbitrary branches, tags, deletion refspecs, and force
pushes are prohibited.
