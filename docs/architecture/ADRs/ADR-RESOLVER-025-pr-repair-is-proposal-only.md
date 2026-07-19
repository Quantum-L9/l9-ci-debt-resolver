# ADR-RESOLVER-025: PR_Repair is proposal-only
- Status: Accepted
- Phase: RESOLVER-P6
## Decision
PR_Repair may return bounded remediation proposals.
It receives no repository mutation, validation, branch, push, rerun, merge,
attempt-limit, or terminal-state authority.
