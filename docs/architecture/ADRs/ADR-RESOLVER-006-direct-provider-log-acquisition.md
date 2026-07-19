# ADR-RESOLVER-006: Failed logs are acquired through provider APIs
- Status: Accepted
- Phase: RESOLVER-P1
## Decision
The resolver uses explicit CI-provider API contracts for failed-run metadata,
failed-job discovery, and individual job-log retrieval.
Human-oriented CLI output is not treated as a canonical machine contract.
## Consequences
- provider metadata remains structured;
- pagination is explicit;
- retries are bounded;
- provenance includes API response metadata;
- each failed job receives an independently verifiable evidence record.
