# Quantum-L9 CI Debt Resolver
`l9-ci-debt-resolver` is the evidence-first failure-diagnosis and bounded
recovery component of the Quantum-L9 CI constellation.
## Authority model
```text
actual failed CI log
        ↓
failed job metadata
        ↓
SDK repository evidence
        ↓
historical context

Historical context may support diagnosis. It cannot override current failed
logs.

RESOLVER-P0

P0 establishes:

* repository ownership boundaries;
* deterministic canonical identities;
* typed CI evidence;
* typed failure classifications;
* resolver attempt lifecycle;
* deterministic terminal states;
* corpus-safe resolution-event contracts;
* schema validation;
* package, CLI, tests, and CI foundations.

P0 does not acquire logs, inspect repositories, remediate code, mutate Git,
observe reruns, deliver Intelligence feedback, or delegate to PR_Repair.

Validation

python -m pip install -e '.[dev]'
pytest
ruff check .
mypy src
l9-debt-resolver capabilities

Contract validation

l9-debt-resolver validate \
  ci-run-evidence \
  evidence.json

Success invariant

Local diagnosis, local validation, commit creation, and push do not prove a
failure is resolved.

Only a successful CI rerun may produce clean.

Prohibited behavior

The Resolver does not:

* infer root cause from historical memory alone;
* classify from job names alone;
* weaken tests or policy gates;
* broaden patch scope without evidence;
* duplicate SDK semantic identities;
* retry identical strategies indefinitely;
* push protected branches;
* force-push;
* merge automatically.
## RESOLVER-P1: failed-log acquisition
The resolver now retrieves:
# 1. workflow-run metadata;
# 2. all failed jobs using bounded pagination;
# 3. each failed job log independently;
# 4. response provenance and content hashes;
# 5. a completeness assessment;
# 6. redacted evidence suitable for local persistence.
```text
GitHub Actions
      ↓
run metadata
      ↓
failed jobs
      ↓
per-job logs
      ↓
size and completeness checks
      ↓
secret and path redaction
      ↓
typed CI evidence
      ↓
evidence_ready
or
insufficient_log_evidence

Authentication

Set one of:

export GITHUB_TOKEN='...'
export GH_TOKEN='...'

Tokens are read from the environment and are never persisted.

Acquire one run

l9-debt-resolver acquire-github-run \
  --repository Quantum-L9/example \
  --run-id 123456789

Exit codes:

* 0: evidence is ready or the run is clean;
* 2: evidence is incomplete and remediation is prohibited;
* nonzero exception: provider or contract failure.

Privacy

Raw logs are ephemeral. The resolver may persist only:

* redacted logs;
* SHA-256 hashes;
* typed evidence;
* provenance;
* completeness limitations.

It does not persist unredacted CI logs.
## RESOLVER-P2: repository correlation and classification
P2 correlates complete failed-log evidence with an SDK-owned repository
snapshot.
```text
complete failed log
       ↓
safe stack-frame extraction
       ↓
SDK repository snapshot
       ↓
canonical repository entities
       ├── related tests
       ├── applicable contracts
       └── canonical findings
       ↓
CI root-cause signals
       ↓
classification trace
       ↓
automatic | approval_required | unsupported

SDK authority boundary

The resolver does not manufacture SDK snapshot, entity, contract, finding,
validation-plan, or validation-result identities.

The included document adapter consumes a public SDK exchange document. It
exists for integration tests, offline execution, and compatibility while the
SDK transport is deployed.

Correlate and classify

l9-debt-resolver correlate-classify \
  --evidence-bundle evidence-bundle.json \
  --SDK-knowledge sdk-knowledge.json

The command exits with:

* 0 when a supported category is classified;
* 2 when the result is unsupported;
* another nonzero code for invalid evidence or SDK failures.

Classification safety

Automatic eligibility requires:

* complete failed-log evidence;
* an explicit failed-log tool or failure signature;
* confidence of at least 0.90;
* no conflicting high-confidence category;
* a category permitted for automatic remediation.

Infrastructure failures remain unsupported. Security failures require
approval.
## RESOLVER-P2: repository correlation and classification
P2 correlates complete failed-log evidence with an SDK-owned repository
snapshot.
```text
complete failed log
       ↓
safe stack-frame extraction
       ↓
SDK repository snapshot
       ↓
canonical repository entities
       ├── related tests
       ├── applicable contracts
       └── canonical findings
       ↓
CI root-cause signals
       ↓
classification trace
       ↓
automatic | approval_required | unsupported

SDK authority boundary

The resolver does not manufacture SDK snapshot, entity, contract, finding,
validation-plan, or validation-result identities.

The included document adapter consumes a public SDK exchange document. It
exists for integration tests, offline execution, and compatibility while the
SDK transport is deployed.

Correlate and classify

l9-debt-resolver correlate-classify \
  --evidence-bundle evidence-bundle.json \
  --SDK-knowledge sdk-knowledge.json

The command exits with:

* 0 when a supported category is classified;
* 2 when the result is unsupported;
* another nonzero code for invalid evidence or SDK failures.

Classification safety

Automatic eligibility requires:

* complete failed-log evidence;
* an explicit failed-log tool or failure signature;
* confidence of at least 0.90;
* no conflicting high-confidence category;
* a category permitted for automatic remediation.

Infrastructure failures remain unsupported. Security failures require
approval.
## RESOLVER-P3: bounded remediation and validation
P3 applies only evidence-supported local changes.
```text
classification trace
        ↓
eligibility and approval policy
        ↓
protected-path checks
        ↓
exact file and text preconditions
        ↓
transactional local patch
        ↓
SDK validation plan
        ├── original failure reproduction
        ├── targeted tests
        ├── affected contracts
        ├── graph delta
        └── full gate when required
        ↓
pass → commit local transaction
fail → rollback

Execute an offline remediation

l9-debt-resolver remediate-offline \
  --workspace /path/to/repository \
  --classification-trace classification-trace.json \
  --remediation-plan remediation-plan.json \
  --sdk-validation sdk-validation.json

P3 never creates branches, pushes commits, observes reruns, or merges changes.

Protected paths

P3 blocks changes under:

* .git/
* .github/workflows/
* .l9/
* schemas/
* security/
* compliance/
* governance/

These paths have no P3 override.

Validation behavior

A remediation is retained only when:

* the original failed command or equivalent passes;
* targeted tests pass;
* affected contracts pass;
* graph delta matches the approved plan;
* the SDK returns a canonical passing validation result.
## RESOLVER-P4: remote resolution loop
P4 moves a validated local remediation onto an authorized repair branch and
observes the resulting CI run.
```text
validated local remediation
        ↓
exact-revision verification
        ↓
expected-worktree verification
        ↓
deterministic repair branch
        ↓
deterministic commit
        ↓
authorized non-force push
        ↓
CI rerun dispatch
        ↓
bounded observation
        ↓
success             → clean
same fingerprint    → repeated_failure
different failure   → new_failure
timeout             → rerun_timeout
attempt exhaustion  → attempt_limit_reached

P4 never force-pushes, pushes protected branches, creates tags, or merges.

The rerun failure must pass through the normal P1 and P2 evidence pipeline to
produce the observed failure fingerprint.
## RESOLVER-P5: Intelligence feedback
P5 emits privacy-safe resolution outcomes to the Intelligence subsystem.
```text
resolution outcome
        ↓
aggregate event construction
        ↓
repository pseudonymization
        ↓
privacy validation
        ↓
deterministic event ID
        ↓
durable outbox
        ↓
bounded delivery retries
        ├── delivered
        ├── duplicate
        └── dead_letter

Feedback payloads include

* failure fingerprint and category;
* confidence bucket;
* terminal state;
* repeated-failure indicator;
* attempt number;
* remediation class;
* changed-file count;
* changed-line bucket;
* validation outcome;
* canonical SDK finding and contract IDs;
* capability profile;
* hashed provenance.

Feedback payloads exclude

* raw logs;
* source code;
* patches and diffs;
* file paths;
* branch names;
* commit messages;
* credentials;
* developer identity;
* raw repository names.

JSON-file delivery

l9-debt-resolver publish-feedback \
  --event feedback-event.json \
  --outbox .resolver-feedback-outbox \
  --transport json-file \
  --destination feedback-export

HTTPS delivery

export L9_FEEDBACK_TOKEN='...'
l9-debt-resolver publish-feedback \
  --event feedback-event.json \
  --outbox .resolver-feedback-outbox \
  --transport https \
  --destination https://intelligence.example/api/v1/events

Drain pending feedback

l9-debt-resolver drain-feedback-outbox \
  --outbox .resolver-feedback-outbox \
  --transport json-file \
  --destination feedback-export
## RESOLVER-P6: constrained PR_Repair delegation
P6 delegates proposal generation only.
```text
unsupported or approval-required classification
        ↓
privacy-safe bounded request
        ↓
repository and path pseudonymization
        ↓
PR_Repair proposal generation
        ↓
signed callback
        ↓
replay, identity, scope, and bounds validation
        ↓
Resolver remediation plan
        ↓
normal P3 validation and rollback
        ↓
normal P4 branch, push, rerun, and terminal states

PR_Repair receives

* failure fingerprint;
* classification category and confidence bucket;
* normalized failure signatures;
* canonical SDK entity, finding, contract, and test IDs;
* capability profile;
* path tokens;
* remediation bounds;
* callback nonce.

PR_Repair does not receive

* raw logs;
* source files;
* repository paths;
* patches or diffs;
* credentials;
* repository owner or name;
* branch or commit data;
* developer identity.

Authority remains with Resolver

PR_Repair cannot mutate a repository, execute validation, push a branch,
trigger CI, merge changes, alter attempt limits, or emit terminal states.

Accepted proposals re-enter the normal RESOLVER-P3 pipeline.
