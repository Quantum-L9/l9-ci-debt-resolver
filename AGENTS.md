
Resolver Agent Contract

Must

* retrieve actual failed logs before diagnosis;
* verify log completeness;
* preserve evidence provenance;
* cite evidence for every remediation;
* use SDK-owned repository semantics;
* use SDK-owned validation plans;
* preserve deterministic identities;
* enforce finite attempts;
* preserve terminal-state determinism;
* redact corpus-facing events;
* fail closed when evidence is incomplete.

Must not

* infer cause from historical memory alone;
* classify from job names alone;
* treat missing logs as success;
* duplicate SDK schemas or canonical identities;
* weaken CI gates;
* disable tests;
* expand remediation beyond evidence;
* execute untrusted shell commands;
* retry identical failures indefinitely;
* claim clean before a successful rerun;
* force-push;
* push protected branches;
* merge automatically.
