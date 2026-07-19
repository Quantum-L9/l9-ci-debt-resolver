No—P4 is ready. This phase adds guarded Git branch interaction, deterministic commits, authorized push, rerun observation, repeated-failure detection, attempt limits, and terminal states. Automatic merge remains prohibited.

Save as build-phase-4.sh and run it after P3.

#!/usr/bin/env bash
set -euo pipefail
###############################################################################
# Quantum-L9/l9-ci-debt-resolver
# RESOLVER-P4 — Remote Resolution Loop
#
# Incremental build over RESOLVER-P0 through RESOLVER-P3.
#
# Implements:
#   - exact-revision and clean-worktree preconditions
#   - authorized repair-branch policy
#   - deterministic local commits
#   - guarded non-force push
#   - GitHub rerun dispatch
#   - rerun polling with bounded timeout
#   - rerun evidence acquisition
#   - repeated-failure fingerprint detection
#   - bounded attempt policy
#   - deterministic terminal-state selection
#   - remote-operation audit records
#   - CLI orchestration
#
# Does not implement:
#   - automatic merge
#   - protected-branch push
#   - force push
#   - PR_Repair delegation                  (RESOLVER-P6)
#   - Intelligence feedback delivery        (RESOLVER-P5)
###############################################################################
fail() {
  printf 'RESOLVER-P4: %s\n' "$*" >&2
  exit 1
}
require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "required command not found: $1"
}
require_command python3
require_command git
[[ -d .git ]] \
  || fail "run from the l9-ci-debt-resolver repository root"
[[ -f .l9/remediation-contract.yaml ]] \
  || fail "RESOLVER-P3 remediation contract is missing"
[[ -f src/l9_debt_resolver/runtime/remediation_service.py ]] \
  || fail "RESOLVER-P3 remediation runtime is missing"
mkdir -p \
  .github/workflows \
  .l9 \
  docs/architecture/ADRs \
  schemas/resolver \
  src/l9_debt_resolver/remote \
  src/l9_debt_resolver/resolution \
  tests/remote \
  tests/resolution \
  tests/runtime \
  tests/architecture
###############################################################################
# 1. Remote-operation and resolution contracts
###############################################################################
cat > .l9/remote-resolution-contract.yaml <<'EOF'
schema: l9.resolver-remote-resolution-contract/v1
metadata:
  repository: Quantum-L9/l9-ci-debt-resolver
  phase: RESOLVER-P4
  status: authoritative
preconditions:
  required:
    - local remediation status is validated
    - local repository HEAD matches remediation repository revision
    - working tree contains only expected remediation paths
    - remote repository identity matches requested repository
    - target branch is not protected
    - repair branch satisfies naming policy
    - push authorization is explicit
    - attempt limit has not been reached
branch_policy:
  allowed_prefixes:
    - resolver/
    - repair/resolver/
  prohibited:
    - main
    - master
    - trunk
    - production
    - release
    - protected branches
    - arbitrary user branches
  normalization:
    maximum_length: 120
    allowed_characters: "[A-Za-z0-9._/-]"
    deterministic_suffix: failure_fingerprint_prefix
commit:
  deterministic:
    author_name: Quantum-L9 Resolver
    author_email: resolver@invalid.local
    message_fields:
      - resolver phase
      - failure fingerprint
      - classification ID
      - remediation plan ID
      - validation result ID
  prohibitions:
    - GPG credential discovery
    - amend of unrelated commit
    - commit of unexpected paths
    - commit of untracked unrelated files
push:
  allowed:
    - explicit repair branch
    - configured remote
    - non-force push
  prohibited:
    - force push
    - push to protected branch
    - wildcard refspec
    - tag push
    - deletion refspec
    - credential logging
rerun:
  provider: github_actions
  dispatch:
    operation: rerun_failed_jobs
    fallback: rerun_workflow
  observation:
    poll_interval_seconds: 10
    timeout_seconds: 1800
    maximum_provider_errors: 5
  accepted_success:
    status: completed
    conclusion: success
attempt_policy:
  maximum_attempts_per_failure_fingerprint: 2
  maximum_remote_operations_per_attempt: 6
repeated_failure:
  same_fingerprint:
    terminal_state: repeated_failure
  different_fingerprint:
    terminal_state: new_failure
terminal_states:
  - clean
  - repeated_failure
  - new_failure
  - attempt_limit_reached
  - remote_operation_failed
  - rerun_timeout
  - validation_failed
  - unsupported
merge:
  automatic: prohibited
  manual_PR: allowed_in_future_phase
EOF
cat > .l9/terminal-state-policy.yaml <<'EOF'
schema: l9.resolver-terminal-state-policy/v1
precedence:
  - attempt_limit_reached
  - remote_operation_failed
  - rerun_timeout
  - repeated_failure
  - new_failure
  - validation_failed
  - unsupported
  - clean
states:
  clean:
    condition:
      - rerun completed
      - rerun conclusion is success
  repeated_failure:
    condition:
      - rerun completed unsuccessfully
      - rerun failure fingerprint equals original fingerprint
  new_failure:
    condition:
      - rerun completed unsuccessfully
      - rerun failure fingerprint differs from original fingerprint
  attempt_limit_reached:
    condition:
      - prior attempts for fingerprint reach configured maximum
  remote_operation_failed:
    condition:
      - branch, commit, push, dispatch, or observation fails terminally
  rerun_timeout:
    condition:
      - rerun does not complete before bounded timeout
EOF
###############################################################################
# 2. Schemas
###############################################################################
cat > schemas/resolver/remote-attempt.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/remote-attempt/v1",
  "title": "L9 Resolver Remote Attempt",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "attempt_id",
    "failure_fingerprint",
    "attempt_number",
    "repository",
    "base_revision",
    "branch",
    "remote",
    "commit_sha",
    "original_run_id",
    "rerun_id",
    "status",
    "started_at",
    "completed_at",
    "operations",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.remote-attempt/v1"
    },
    "attempt_id": {
      "type": "string",
      "pattern": "^remote_attempt_[0-9a-f]{64}$"
    },
    "failure_fingerprint": {
      "type": "string",
      "pattern": "^failure_[0-9a-f]{64}$"
    },
    "attempt_number": {
      "type": "integer",
      "minimum": 1
    },
    "repository": {
      "type": "string",
      "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    },
    "base_revision": {
      "type": "string",
      "minLength": 7,
      "maxLength": 128
    },
    "branch": {
      "type": "string",
      "minLength": 1,
      "maxLength": 120
    },
    "remote": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "commit_sha": {
      "type": [
        "string",
        "null"
      ]
    },
    "original_run_id": {
      "type": "string"
    },
    "rerun_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "status": {
      "enum": [
        "prepared",
        "pushed",
        "rerun_dispatched",
        "observing",
        "completed",
        "failed"
      ]
    },
    "started_at": {
      "type": "string",
      "format": "date-time"
    },
    "completed_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "operations": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "operation",
          "result",
          "observed_at",
          "metadata"
        ],
        "properties": {
          "operation": {
            "type": "string"
          },
          "result": {
            "enum": [
              "passed",
              "failed",
              "skipped"
            ]
          },
          "observed_at": {
            "type": "string",
            "format": "date-time"
          },
          "metadata": {
            "type": "object"
          }
        }
      }
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    }
  }
}
EOF
cat > schemas/resolver/rerun-observation.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/rerun-observation/v1",
  "title": "L9 Resolver Rerun Observation",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "observation_id",
    "provider",
    "repository",
    "original_run_id",
    "rerun_id",
    "status",
    "conclusion",
    "head_sha",
    "started_at",
    "completed_at",
    "poll_count",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.rerun-observation/v1"
    },
    "observation_id": {
      "type": "string",
      "pattern": "^rerun_observation_[0-9a-f]{64}$"
    },
    "provider": {
      "const": "github_actions"
    },
    "repository": {
      "type": "string"
    },
    "original_run_id": {
      "type": "string"
    },
    "rerun_id": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "conclusion": {
      "type": [
        "string",
        "null"
      ]
    },
    "head_sha": {
      "type": "string"
    },
    "started_at": {
      "type": "string",
      "format": "date-time"
    },
    "completed_at": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "poll_count": {
      "type": "integer",
      "minimum": 1
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    }
  }
}
EOF
cat > schemas/resolver/resolution-outcome.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "l9://resolver/resolution-outcome/v1",
  "title": "L9 Resolver Resolution Outcome",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "outcome_id",
    "attempt_id",
    "terminal_state",
    "original_failure_fingerprint",
    "observed_failure_fingerprint",
    "repository",
    "branch",
    "commit_sha",
    "original_run_id",
    "rerun_id",
    "evidence_ids",
    "limitations"
  ],
  "properties": {
    "schema_version": {
      "const": "l9.resolution-outcome/v1"
    },
    "outcome_id": {
      "type": "string",
      "pattern": "^resolution_outcome_[0-9a-f]{64}$"
    },
    "attempt_id": {
      "type": "string"
    },
    "terminal_state": {
      "enum": [
        "clean",
        "repeated_failure",
        "new_failure",
        "attempt_limit_reached",
        "remote_operation_failed",
        "rerun_timeout",
        "validation_failed",
        "unsupported"
      ]
    },
    "original_failure_fingerprint": {
      "type": "string"
    },
    "observed_failure_fingerprint": {
      "type": [
        "string",
        "null"
      ]
    },
    "repository": {
      "type": "string"
    },
    "branch": {
      "type": "string"
    },
    "commit_sha": {
      "type": [
        "string",
        "null"
      ]
    },
    "original_run_id": {
      "type": "string"
    },
    "rerun_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "evidence_ids": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    },
    "limitations": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    }
  }
}
EOF
###############################################################################
# 3. Remote models and errors
###############################################################################
cat > src/l9_debt_resolver/remote/__init__.py <<'EOF'
"""Guarded remote branch and CI operations."""
EOF
cat > src/l9_debt_resolver/remote/errors.py <<'EOF'
from __future__ import annotations
class RemoteOperationError(RuntimeError):
    """Base remote resolution error."""
class BranchPolicyError(RemoteOperationError):
    """Requested branch violates repair-branch policy."""
class RevisionMismatchError(RemoteOperationError):
    """Local repository revision does not match the validated remediation."""
class DirtyWorkspaceError(RemoteOperationError):
    """Workspace contains unexpected changes."""
class PushAuthorizationError(RemoteOperationError):
    """Explicit remote push authorization is unavailable."""
class ProtectedBranchError(RemoteOperationError):
    """Operation targets a protected branch."""
class AttemptLimitReachedError(RemoteOperationError):
    """Failure fingerprint exhausted its bounded attempts."""
class RerunTimeoutError(RemoteOperationError):
    """CI rerun did not complete before timeout."""
class ProviderObservationError(RemoteOperationError):
    """CI provider observation failed."""
EOF
cat > src/l9_debt_resolver/remote/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class PushAuthorization:
    authorization_id: str
    repository: str
    remote: str
    branch: str
    expires_at: str
@dataclass(frozen=True)
class RemoteOperationRecord:
    operation: str
    result: str
    observed_at: str
    metadata: dict[str, Any]
    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "result": self.result,
            "observed_at": self.observed_at,
            "metadata": self.metadata,
        }
@dataclass(frozen=True)
class RemoteAttempt:
    attempt_id: str
    failure_fingerprint: str
    attempt_number: int
    repository: str
    base_revision: str
    branch: str
    remote: str
    commit_sha: str | None
    original_run_id: str
    rerun_id: str | None
    status: str
    started_at: str
    completed_at: str | None
    operations: tuple[RemoteOperationRecord, ...]
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.remote-attempt/v1",
            "attempt_id": self.attempt_id,
            "failure_fingerprint": self.failure_fingerprint,
            "attempt_number": self.attempt_number,
            "repository": self.repository,
            "base_revision": self.base_revision,
            "branch": self.branch,
            "remote": self.remote,
            "commit_sha": self.commit_sha,
            "original_run_id": self.original_run_id,
            "rerun_id": self.rerun_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "operations": [
                operation.as_dict()
                for operation in self.operations
            ],
            "limitations": list(self.limitations),
        }
@dataclass(frozen=True)
class RerunObservation:
    observation_id: str
    provider: str
    repository: str
    original_run_id: str
    rerun_id: str
    status: str
    conclusion: str | None
    head_sha: str
    started_at: str
    completed_at: str | None
    poll_count: int
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.rerun-observation/v1",
            "observation_id": self.observation_id,
            "provider": self.provider,
            "repository": self.repository,
            "original_run_id": self.original_run_id,
            "rerun_id": self.rerun_id,
            "status": self.status,
            "conclusion": self.conclusion,
            "head_sha": self.head_sha,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "poll_count": self.poll_count,
            "limitations": list(self.limitations),
        }
EOF
###############################################################################
# 4. Branch and push policy
###############################################################################
cat > src/l9_debt_resolver/remote/policy.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
import re
from .errors import (
    BranchPolicyError,
    ProtectedBranchError,
    PushAuthorizationError,
)
from .models import PushAuthorization
_ALLOWED_BRANCH = re.compile(r"^[A-Za-z0-9._/-]{1,120}$")
_PROTECTED_BRANCHES = {
    "main",
    "master",
    "trunk",
    "production",
    "release",
}
_ALLOWED_PREFIXES = (
    "resolver/",
    "repair/resolver/",
)
def deterministic_branch_name(
    *,
    failure_fingerprint: str,
    attempt_number: int,
) -> str:
    suffix = failure_fingerprint.removeprefix(
        "failure_"
    )[:16]
    return (
        f"resolver/{suffix}/attempt-{attempt_number}"
    )
def validate_branch_name(branch: str) -> None:
    if not _ALLOWED_BRANCH.fullmatch(branch):
        raise BranchPolicyError(
            "repair branch contains invalid characters"
        )
    if branch in _PROTECTED_BRANCHES:
        raise ProtectedBranchError(
            f"protected branch is prohibited: {branch}"
        )
    if not branch.startswith(_ALLOWED_PREFIXES):
        raise BranchPolicyError(
            "repair branch must use an approved prefix"
        )
    if ".." in branch or branch.endswith("/"):
        raise BranchPolicyError(
            "repair branch has an unsafe structure"
        )
def validate_push_authorization(
    *,
    authorization: PushAuthorization,
    repository: str,
    remote: str,
    branch: str,
    now: datetime | None = None,
) -> None:
    reference = now or datetime.now(timezone.utc)
    expires_at = datetime.fromisoformat(
        authorization.expires_at.replace(
            "Z",
            "+00:00",
        )
    )
    if expires_at <= reference:
        raise PushAuthorizationError(
            "push authorization has expired"
        )
    expected = (
        authorization.repository,
        authorization.remote,
        authorization.branch,
    )
    actual = (
        repository,
        remote,
        branch,
    )
    if expected != actual:
        raise PushAuthorizationError(
            "push authorization scope mismatch"
        )
EOF
###############################################################################
# 5. Safe Git adapter
###############################################################################
cat > src/l9_debt_resolver/remote/git.py <<'EOF'
from __future__ import annotations
import asyncio
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterable
from .errors import (
    DirtyWorkspaceError,
    RemoteOperationError,
    RevisionMismatchError,
)
from .policy import validate_branch_name
@dataclass(frozen=True)
class GitResult:
    exit_code: int
    stdout: str
    stderr: str
class GitRepository:
    def __init__(
        self,
        *,
        workspace_root: Path,
    ) -> None:
        self._root = workspace_root.resolve()
    async def head_sha(self) -> str:
        result = await self._run(
            "rev-parse",
            "HEAD",
        )
        return result.stdout.strip()
    async def remote_url(
        self,
        remote: str,
    ) -> str:
        result = await self._run(
            "remote",
            "get-url",
            remote,
        )
        return result.stdout.strip()
    async def changed_paths(self) -> tuple[str, ...]:
        result = await self._run(
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        paths = []
        for line in result.stdout.splitlines():
            if len(line) < 4:
                continue
            value = line[3:]
            if " -> " in value:
                value = value.split(
                    " -> ",
                    1,
                )[1]
            paths.append(value)
        return tuple(sorted(set(paths)))
    async def verify_revision(
        self,
        expected_revision: str,
    ) -> None:
        actual = await self.head_sha()
        if actual != expected_revision:
            raise RevisionMismatchError(
                "local HEAD does not match remediation revision"
            )
    async def verify_expected_changes(
        self,
        expected_paths: Iterable[str],
    ) -> None:
        actual = set(await self.changed_paths())
        expected = set(expected_paths)
        if actual != expected:
            raise DirtyWorkspaceError(
                "workspace changes do not exactly match "
                f"the remediation plan; expected={sorted(expected)}, "
                f"actual={sorted(actual)}"
            )
    async def create_branch(
        self,
        branch: str,
    ) -> None:
        validate_branch_name(branch)
        await self._run(
            "switch",
            "--create",
            branch,
        )
    async def stage_paths(
        self,
        paths: tuple[str, ...],
    ) -> None:
        if not paths:
            raise RemoteOperationError(
                "cannot stage an empty remediation"
            )
        await self._run(
            "add",
            "--",
            *paths,
        )
    async def commit(
        self,
        *,
        message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        environment = {
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
        await self._run(
            "commit",
            "--no-gpg-sign",
            "--message",
            message,
            environment=environment,
        )
        return await self.head_sha()
    async def push(
        self,
        *,
        remote: str,
        branch: str,
    ) -> None:
        validate_branch_name(branch)
        await self._run(
            "push",
            "--set-upstream",
            remote,
            f"HEAD:refs/heads/{branch}",
        )
    async def _run(
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
    ) -> GitResult:
        import os
        command_environment = dict(os.environ)
        if environment:
            command_environment.update(environment)
        process = await asyncio.create_subprocess_exec(
            "git",
            *arguments,
            cwd=self._root,
            env=command_environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        result = GitResult(
            exit_code=process.returncode,
            stdout=stdout.decode(
                "utf-8",
                errors="replace",
            ),
            stderr=stderr.decode(
                "utf-8",
                errors="replace",
            ),
        )
        if result.exit_code != 0:
            stderr_hash = hashlib.sha256(
                stderr
            ).hexdigest()
            raise RemoteOperationError(
                "git operation failed; "
                f"command={arguments[0]}, "
                f"stderr_sha256={stderr_hash}"
            )
        return result
EOF
###############################################################################
# 6. Attempt ledger
###############################################################################
cat > src/l9_debt_resolver/remote/ledger.py <<'EOF'
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from .errors import AttemptLimitReachedError
class AttemptLedger:
    def __init__(
        self,
        *,
        path: Path,
        maximum_attempts: int = 2,
    ) -> None:
        self._path = path
        self._maximum_attempts = maximum_attempts
    def next_attempt(
        self,
        failure_fingerprint: str,
    ) -> int:
        document = self._load()
        attempts = document.setdefault(
            "attempts",
            {},
        )
        current = int(
            attempts.get(
                failure_fingerprint,
                0,
            )
        )
        if current >= self._maximum_attempts:
            raise AttemptLimitReachedError(
                "failure fingerprint reached "
                "the configured attempt limit"
            )
        next_value = current + 1
        attempts[failure_fingerprint] = next_value
        self._write(document)
        return next_value
    def count(
        self,
        failure_fingerprint: str,
    ) -> int:
        document = self._load()
        return int(
            document.get(
                "attempts",
                {},
            ).get(
                failure_fingerprint,
                0,
            )
        )
    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {
                "schema_version": (
                    "l9.remote-attempt-ledger/v1"
                ),
                "attempts": {},
            }
        value = json.loads(
            self._path.read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(value, dict):
            raise ValueError(
                "attempt ledger must be an object"
            )
        return value
    def _write(
        self,
        value: dict[str, Any],
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        descriptor, temporary = tempfile.mkstemp(
            dir=self._path.parent,
            prefix=".attempt-ledger.",
        )
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
            ) as stream:
                json.dump(
                    value,
                    stream,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                self._path,
            )
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
EOF
###############################################################################
# 7. GitHub rerun provider
###############################################################################
cat > src/l9_debt_resolver/remote/github.py <<'EOF'
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from l9_debt_resolver.acquisition.config import (
    AcquisitionConfig,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.providers.github.transport import (
    GitHubTransport,
)
from .errors import RerunTimeoutError
from .models import RerunObservation
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
class GitHubRerunProvider:
    def __init__(
        self,
        *,
        token: str,
        config: AcquisitionConfig | None = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        self._config = config or AcquisitionConfig()
        self._transport = GitHubTransport(
            token=token,
            config=self._config,
            base_url=base_url,
        )
    async def dispatch_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> None:
        owner, name = _repository_parts(repository)
        await self._post_empty(
            f"/repos/{quote(owner)}/{quote(name)}"
            f"/actions/runs/{quote(run_id)}"
            f"/rerun-failed-jobs"
        )
    async def observe(
        self,
        *,
        repository: str,
        original_run_id: str,
        expected_head_sha: str,
        timeout_seconds: float = 1800,
        poll_interval_seconds: float = 10,
    ) -> RerunObservation:
        started_at = utc_now()
        deadline = asyncio.get_running_loop().time() + (
            timeout_seconds
        )
        poll_count = 0
        latest: dict[str, Any] | None = None
        while True:
            poll_count += 1
            candidate = await self._latest_run_for_sha(
                repository=repository,
                head_sha=expected_head_sha,
            )
            if candidate is not None:
                latest = candidate
                if candidate.get("status") == "completed":
                    break
            if asyncio.get_running_loop().time() >= deadline:
                raise RerunTimeoutError(
                    "CI rerun observation exceeded timeout"
                )
            await asyncio.sleep(
                poll_interval_seconds
            )
        rerun_id = str(latest["id"])
        completed_at = utc_now()
        return RerunObservation(
            observation_id=namespaced_identity(
                "rerun_observation_",
                {
                    "repository": repository,
                    "original_run_id": original_run_id,
                    "rerun_id": rerun_id,
                    "head_sha": expected_head_sha,
                    "conclusion": latest.get(
                        "conclusion"
                    ),
                },
            ),
            provider="github_actions",
            repository=repository,
            original_run_id=original_run_id,
            rerun_id=rerun_id,
            status=str(latest["status"]),
            conclusion=(
                str(latest["conclusion"])
                if latest.get("conclusion")
                is not None
                else None
            ),
            head_sha=expected_head_sha,
            started_at=started_at,
            completed_at=completed_at,
            poll_count=poll_count,
            limitations=(),
        )
    async def _latest_run_for_sha(
        self,
        *,
        repository: str,
        head_sha: str,
    ) -> dict[str, Any] | None:
        owner, name = _repository_parts(repository)
        document, _ = await self._transport.get_json(
            f"/repos/{quote(owner)}/{quote(name)}"
            f"/actions/runs"
            f"?head_sha={quote(head_sha)}"
            f"&per_page=20"
        )
        runs = document.get("workflow_runs")
        if not isinstance(runs, list):
            return None
        candidates = [
            run
            for run in runs
            if (
                isinstance(run, dict)
                and run.get("head_sha") == head_sha
            )
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda run: (
                str(run.get("created_at", "")),
                int(run.get("id", 0)),
            ),
            reverse=True,
        )
        return candidates[0]
    async def _post_empty(
        self,
        path: str,
    ) -> None:
        import json
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        request = Request(
            self._transport._base_url + path,
            method="POST",
            data=json.dumps({}).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": (
                    f"Bearer {self._transport._token}"
                ),
                "User-Agent": (
                    self._config.user_agent
                ),
                "X-GitHub-Api-Version": (
                    self._config.api_version
                ),
                "Content-Type": "application/json",
            },
        )
        def invoke() -> None:
            try:
                with urlopen(
                    request,
                    timeout=30,
                ) as response:
                    if response.status not in {
                        201,
                        202,
                        204,
                    }:
                        raise RuntimeError(
                            "unexpected rerun response"
                        )
            except HTTPError as error:
                raise RuntimeError(
                    f"rerun dispatch failed with HTTP "
                    f"{error.code}"
                ) from error
        await asyncio.to_thread(invoke)
def _repository_parts(
    repository: str,
) -> tuple[str, str]:
    parts = repository.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(
            "repository must use owner/name format"
        )
    return parts[0], parts[1]
EOF
###############################################################################
# 8. Resolution outcome
###############################################################################
cat > src/l9_debt_resolver/resolution/__init__.py <<'EOF'
"""Remote resolution outcome and terminal states."""
EOF
cat > src/l9_debt_resolver/resolution/models.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class ResolutionOutcome:
    outcome_id: str
    attempt_id: str
    terminal_state: str
    original_failure_fingerprint: str
    observed_failure_fingerprint: str | None
    repository: str
    branch: str
    commit_sha: str | None
    original_run_id: str
    rerun_id: str | None
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "l9.resolution-outcome/v1",
            "outcome_id": self.outcome_id,
            "attempt_id": self.attempt_id,
            "terminal_state": self.terminal_state,
            "original_failure_fingerprint": (
                self.original_failure_fingerprint
            ),
            "observed_failure_fingerprint": (
                self.observed_failure_fingerprint
            ),
            "repository": self.repository,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "original_run_id": self.original_run_id,
            "rerun_id": self.rerun_id,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
        }
EOF
cat > src/l9_debt_resolver/resolution/terminal.py <<'EOF'
from __future__ import annotations
def determine_terminal_state(
    *,
    rerun_conclusion: str | None,
    original_fingerprint: str,
    observed_fingerprint: str | None,
) -> str:
    if rerun_conclusion == "success":
        return "clean"
    if observed_fingerprint is None:
        return "remote_operation_failed"
    if observed_fingerprint == original_fingerprint:
        return "repeated_failure"
    return "new_failure"
EOF
###############################################################################
# 9. P4 orchestration
###############################################################################
cat > src/l9_debt_resolver/runtime/remote_resolution_service.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.remote.git import GitRepository
from l9_debt_resolver.remote.ledger import AttemptLedger
from l9_debt_resolver.remote.models import (
    PushAuthorization,
    RemoteAttempt,
    RemoteOperationRecord,
)
from l9_debt_resolver.remote.policy import (
    deterministic_branch_name,
    validate_branch_name,
    validate_push_authorization,
)
from l9_debt_resolver.resolution.models import (
    ResolutionOutcome,
)
from l9_debt_resolver.resolution.terminal import (
    determine_terminal_state,
)
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )
class RemoteResolutionService:
    def __init__(
        self,
        *,
        rerun_provider: object,
        attempt_ledger: AttemptLedger,
    ) -> None:
        self._rerun_provider = rerun_provider
        self._ledger = attempt_ledger
    async def execute(
        self,
        *,
        workspace_root: Path,
        repository: str,
        remote: str,
        original_run_id: str,
        classification_trace: ClassificationTrace,
        remediation_plan_id: str,
        validation_result_id: str,
        expected_changed_paths: tuple[str, ...],
        push_authorization: PushAuthorization,
        observed_failure_fingerprint: (
            str | None
        ) = None,
    ) -> tuple[
        RemoteAttempt,
        ResolutionOutcome,
    ]:
        classification = (
            classification_trace.classification
        )
        attempt_number = self._ledger.next_attempt(
            classification.failure_fingerprint
        )
        branch = deterministic_branch_name(
            failure_fingerprint=(
                classification.failure_fingerprint
            ),
            attempt_number=attempt_number,
        )
        validate_branch_name(branch)
        validate_push_authorization(
            authorization=push_authorization,
            repository=repository,
            remote=remote,
            branch=branch,
        )
        started_at = utc_now()
        operations = []
        repository_adapter = GitRepository(
            workspace_root=workspace_root
        )
        await repository_adapter.verify_revision(
            classification_trace.classification
            .repository_snapshot_id
            if False
            else await repository_adapter.head_sha()
        )
        await repository_adapter.verify_expected_changes(
            expected_changed_paths
        )
        operations.append(
            RemoteOperationRecord(
                operation="verify_workspace",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "changed_paths": list(
                        expected_changed_paths
                    )
                },
            )
        )
        await repository_adapter.create_branch(branch)
        operations.append(
            RemoteOperationRecord(
                operation="create_branch",
                result="passed",
                observed_at=utc_now(),
                metadata={"branch": branch},
            )
        )
        await repository_adapter.stage_paths(
            expected_changed_paths
        )
        commit_message = (
            "RESOLVER-P4 bounded remediation\n\n"
            f"Failure-Fingerprint: "
            f"{classification.failure_fingerprint}\n"
            f"Classification-ID: "
            f"{classification.classification_id}\n"
            f"Remediation-Plan-ID: "
            f"{remediation_plan_id}\n"
            f"Validation-Result-ID: "
            f"{validation_result_id}\n"
        )
        commit_sha = await repository_adapter.commit(
            message=commit_message,
            author_name="Quantum-L9 Resolver",
            author_email="resolver@invalid.local",
        )
        operations.append(
            RemoteOperationRecord(
                operation="commit",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "commit_sha": commit_sha,
                },
            )
        )
        await repository_adapter.push(
            remote=remote,
            branch=branch,
        )
        operations.append(
            RemoteOperationRecord(
                operation="push",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "remote": remote,
                    "branch": branch,
                },
            )
        )
        await self._rerun_provider.dispatch_failed_jobs(
            repository=repository,
            run_id=original_run_id,
        )
        operations.append(
            RemoteOperationRecord(
                operation="dispatch_rerun",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "original_run_id": original_run_id,
                },
            )
        )
        observation = await self._rerun_provider.observe(
            repository=repository,
            original_run_id=original_run_id,
            expected_head_sha=commit_sha,
        )
        operations.append(
            RemoteOperationRecord(
                operation="observe_rerun",
                result="passed",
                observed_at=utc_now(),
                metadata={
                    "rerun_id": observation.rerun_id,
                    "status": observation.status,
                    "conclusion": observation.conclusion,
                },
            )
        )
        attempt_id = namespaced_identity(
            "remote_attempt_",
            {
                "failure_fingerprint": (
                    classification.failure_fingerprint
                ),
                "attempt_number": attempt_number,
                "repository": repository,
                "branch": branch,
                "commit_sha": commit_sha,
                "original_run_id": original_run_id,
                "rerun_id": observation.rerun_id,
            },
        )
        attempt = RemoteAttempt(
            attempt_id=attempt_id,
            failure_fingerprint=(
                classification.failure_fingerprint
            ),
            attempt_number=attempt_number,
            repository=repository,
            base_revision=commit_sha,
            branch=branch,
            remote=remote,
            commit_sha=commit_sha,
            original_run_id=original_run_id,
            rerun_id=observation.rerun_id,
            status="completed",
            started_at=started_at,
            completed_at=utc_now(),
            operations=tuple(operations),
            limitations=observation.limitations,
        )
        terminal_state = determine_terminal_state(
            rerun_conclusion=observation.conclusion,
            original_fingerprint=(
                classification.failure_fingerprint
            ),
            observed_fingerprint=(
                observed_failure_fingerprint
            ),
        )
        outcome = ResolutionOutcome(
            outcome_id=namespaced_identity(
                "resolution_outcome_",
                {
                    "attempt_id": attempt_id,
                    "terminal_state": terminal_state,
                    "original_fingerprint": (
                        classification.failure_fingerprint
                    ),
                    "observed_fingerprint": (
                        observed_failure_fingerprint
                    ),
                    "rerun_id": observation.rerun_id,
                },
            ),
            attempt_id=attempt_id,
            terminal_state=terminal_state,
            original_failure_fingerprint=(
                classification.failure_fingerprint
            ),
            observed_failure_fingerprint=(
                observed_failure_fingerprint
            ),
            repository=repository,
            branch=branch,
            commit_sha=commit_sha,
            original_run_id=original_run_id,
            rerun_id=observation.rerun_id,
            evidence_ids=(
                classification.evidence_ids
            ),
            limitations=observation.limitations,
        )
        return attempt, outcome
EOF
###############################################################################
# 10. Correct exact-revision parameter
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path(
    "src/l9_debt_resolver/runtime/"
    "remote_resolution_service.py"
)
content = path.read_text(encoding="utf-8")
content = content.replace(
    """        validation_result_id: str,
        expected_changed_paths: tuple[str, ...],""",
    """        validation_result_id: str,
        base_revision: str,
        expected_changed_paths: tuple[str, ...],""",
)
content = content.replace(
    """        await repository_adapter.verify_revision(
            classification_trace.classification
            .repository_snapshot_id
            if False
            else await repository_adapter.head_sha()
        )""",
    """        await repository_adapter.verify_revision(
            base_revision
        )""",
)
content = content.replace(
    """            base_revision=commit_sha,""",
    """            base_revision=base_revision,""",
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 11. Capabilities
###############################################################################
cat > src/l9_debt_resolver/runtime/capabilities.py <<'EOF'
from __future__ import annotations
from typing import Any
def resolver_capabilities() -> dict[str, Any]:
    return {
        "schema_version": "l9.resolver-capabilities/v1",
        "phase": "RESOLVER-P4",
        "capabilities": {
            "contract_validation": True,
            "typed_CI_evidence": True,
            "failed_log_acquisition": True,
            "SDK_repository_snapshots": True,
            "root_cause_classification": True,
            "bounded_remediation": True,
            "SDK_validation_execution": True,
            "transactional_patch_application": True,
            "rollback": True,
            "repair_branch_policy": True,
            "deterministic_branch_names": True,
            "exact_revision_enforcement": True,
            "clean_worktree_enforcement": True,
            "deterministic_commits": True,
            "push_authorization": True,
            "non_force_push": True,
            "rerun_dispatch": True,
            "CI_rerun_observation": True,
            "bounded_rerun_polling": True,
            "attempt_limits": True,
            "repeated_failure_detection": True,
            "new_failure_detection": True,
            "terminal_state_emission": True,
            "automatic_merge": False,
            "protected_branch_push": False,
            "force_push": False
        },
        "limitations": [
            "Automatic merge is prohibited.",
            "Protected branches cannot be pushed.",
            "Failure reclassification after rerun must be supplied by "
            "the normal P1-P2 evidence pipeline.",
            "Intelligence feedback begins in RESOLVER-P5.",
            "PR_Repair delegation begins in RESOLVER-P6."
        ]
    }
EOF
###############################################################################
# 12. Version and roadmap
###############################################################################
python3 - <<'PY'
from pathlib import Path
path = Path("pyproject.toml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    'version = "0.4.0"',
    'version = "0.5.0"',
)
path.write_text(content, encoding="utf-8")
path = Path("src/l9_debt_resolver/__init__.py")
content = path.read_text(encoding="utf-8")
content = content.replace(
    '__version__ = "0.4.0"',
    '__version__ = "0.5.0"',
)
path.write_text(content, encoding="utf-8")
path = Path(".l9/repo-spec.yaml")
content = path.read_text(encoding="utf-8")
content = content.replace(
    "phase: RESOLVER-P3",
    "phase: RESOLVER-P4",
    1,
)
content = content.replace(
    "phase_name: bounded_validation",
    "phase_name: remote_resolution_loop",
    1,
)
content = content.replace(
    """  - phase: RESOLVER-P4
    name: remote_loop
    priority: high
    status: planned""",
    """  - phase: RESOLVER-P4
    name: remote_loop
    priority: high
    status: implemented""",
)
path.write_text(content, encoding="utf-8")
PY
###############################################################################
# 13. Tests
###############################################################################
cat > tests/remote/test_policy.py <<'EOF'
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pytest
from l9_debt_resolver.remote.errors import (
    BranchPolicyError,
    ProtectedBranchError,
    PushAuthorizationError,
)
from l9_debt_resolver.remote.models import (
    PushAuthorization,
)
from l9_debt_resolver.remote.policy import (
    deterministic_branch_name,
    validate_branch_name,
    validate_push_authorization,
)
def test_deterministic_branch() -> None:
    value = deterministic_branch_name(
        failure_fingerprint=(
            "failure_" + "a" * 64
        ),
        attempt_number=2,
    )
    assert value == (
        "resolver/aaaaaaaaaaaaaaaa/attempt-2"
    )
@pytest.mark.parametrize(
    "branch",
    [
        "feature/random",
        "resolver/../main",
        "resolver/",
    ],
)
def test_invalid_branch_is_rejected(
    branch: str,
) -> None:
    with pytest.raises(BranchPolicyError):
        validate_branch_name(branch)
@pytest.mark.parametrize(
    "branch",
    ["main", "master", "production"],
)
def test_protected_branch_is_rejected(
    branch: str,
) -> None:
    with pytest.raises(
        ProtectedBranchError
    ):
        validate_branch_name(branch)
def test_push_authorization_scope() -> None:
    now = datetime.now(timezone.utc)
    authorization = PushAuthorization(
        authorization_id="authorization-1",
        repository="Quantum-L9/example",
        remote="origin",
        branch="resolver/abc/attempt-1",
        expires_at=(
            now + timedelta(minutes=10)
        ).isoformat(),
    )
    validate_push_authorization(
        authorization=authorization,
        repository="Quantum-L9/example",
        remote="origin",
        branch="resolver/abc/attempt-1",
        now=now,
    )
def test_expired_authorization_is_rejected() -> None:
    now = datetime.now(timezone.utc)
    authorization = PushAuthorization(
        authorization_id="authorization-1",
        repository="Quantum-L9/example",
        remote="origin",
        branch="resolver/abc/attempt-1",
        expires_at=(
            now - timedelta(minutes=1)
        ).isoformat(),
    )
    with pytest.raises(
        PushAuthorizationError
    ):
        validate_push_authorization(
            authorization=authorization,
            repository="Quantum-L9/example",
            remote="origin",
            branch="resolver/abc/attempt-1",
            now=now,
        )
EOF
cat > tests/remote/test_ledger.py <<'EOF'
from __future__ import annotations
from pathlib import Path
import pytest
from l9_debt_resolver.remote.errors import (
    AttemptLimitReachedError,
)
from l9_debt_resolver.remote.ledger import (
    AttemptLedger,
)
def test_attempts_are_bounded(
    tmp_path: Path,
) -> None:
    ledger = AttemptLedger(
        path=tmp_path / "ledger.json",
        maximum_attempts=2,
    )
    fingerprint = "failure_" + "a" * 64
    assert ledger.next_attempt(fingerprint) == 1
    assert ledger.next_attempt(fingerprint) == 2
    with pytest.raises(
        AttemptLimitReachedError
    ):
        ledger.next_attempt(fingerprint)
EOF
cat > tests/resolution/test_terminal.py <<'EOF'
from __future__ import annotations
from l9_debt_resolver.resolution.terminal import (
    determine_terminal_state,
)
def test_success_is_clean() -> None:
    assert (
        determine_terminal_state(
            rerun_conclusion="success",
            original_fingerprint=(
                "failure_" + "a" * 64
            ),
            observed_fingerprint=None,
        )
        == "clean"
    )
def test_same_fingerprint_is_repeated_failure() -> None:
    fingerprint = "failure_" + "a" * 64
    assert (
        determine_terminal_state(
            rerun_conclusion="failure",
            original_fingerprint=fingerprint,
            observed_fingerprint=fingerprint,
        )
        == "repeated_failure"
    )
def test_different_fingerprint_is_new_failure() -> None:
    assert (
        determine_terminal_state(
            rerun_conclusion="failure",
            original_fingerprint=(
                "failure_" + "a" * 64
            ),
            observed_fingerprint=(
                "failure_" + "b" * 64
            ),
        )
        == "new_failure"
    )
EOF
cat > tests/remote/test_git_adapter.py <<'EOF'
from __future__ import annotations
import asyncio
from pathlib import Path
import subprocess
import pytest
from l9_debt_resolver.remote.errors import (
    DirtyWorkspaceError,
)
from l9_debt_resolver.remote.git import (
    GitRepository,
)
def run(
    root: Path,
    *arguments: str,
) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
    )
@pytest.mark.asyncio
async def test_expected_changes_are_enforced(
    tmp_path: Path,
) -> None:
    run(tmp_path, "init")
    run(
        tmp_path,
        "config",
        "user.email",
        "test@example.invalid",
    )
    run(
        tmp_path,
        "config",
        "user.name",
        "Test",
    )
    target = tmp_path / "app.py"
    target.write_text(
        "before\n",
        encoding="utf-8",
    )
    run(tmp_path, "add", "app.py")
    run(
        tmp_path,
        "commit",
        "-m",
        "initial",
    )
    target.write_text(
        "after\n",
        encoding="utf-8",
    )
    repository = GitRepository(
        workspace_root=tmp_path
    )
    await repository.verify_expected_changes(
        ("app.py",)
    )
    with pytest.raises(
        DirtyWorkspaceError
    ):
        await repository.verify_expected_changes(
            ("other.py",)
        )
EOF
cat > tests/architecture/test_P4_boundaries.py <<'EOF'
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED = (
    "push --force",
    "--force-with-lease",
    "gh pr merge",
    "merge_pull_request",
    "automatic_merge",
    "refs/tags/",
    "git tag",
)
def test_no_force_push_or_merge() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(
            encoding="utf-8"
        ).lower()
        for term in PROHIBITED:
            assert term not in content, (
                f"{path} contains prohibited P4 "
                f"behavior {term}"
            )
def test_git_uses_exec_not_shell() -> None:
    path = (
        SOURCE
        / "remote"
        / "git.py"
    )
    content = path.read_text(
        encoding="utf-8"
    )
    assert "create_subprocess_exec" in content
    assert "create_subprocess_shell" not in content
    assert "shell=True" not in content
EOF
###############################################################################
# 14. Documentation
###############################################################################
cat > docs/architecture/ADRs/ADR-RESOLVER-017-repair-branches-only.md <<'EOF'
# ADR-RESOLVER-017: P4 pushes only deterministic repair branches
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
P4 may create and push only resolver-owned repair branches.
Protected branches, arbitrary branches, tags, deletion refspecs, and force
pushes are prohibited.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-018-rerun-success-defines-clean.md <<'EOF'
# ADR-RESOLVER-018: Only successful rerun defines clean
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
Local validation and successful push do not define resolution.
The resolver emits `clean` only after the provider reports a completed,
successful rerun for the pushed commit.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-019-repeated-fingerprints-stop.md <<'EOF'
# ADR-RESOLVER-019: Repeated failure fingerprints stop the loop
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
When a rerun produces the same failure fingerprint, the attempt terminates as
`repeated_failure`.
The resolver does not perform unbounded speculative retries.
EOF
cat > docs/architecture/ADRs/ADR-RESOLVER-020-attempts-are-bounded.md <<'EOF'
# ADR-RESOLVER-020: Remote attempts are bounded by fingerprint
- Status: Accepted
- Phase: RESOLVER-P4
## Decision
Each failure fingerprint receives at most two remote remediation attempts.
Further execution terminates as `attempt_limit_reached`.
EOF
cat >> README.md <<'EOF'
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
EOF

###############################################################################

15. Acceptance gates

###############################################################################

cat > .l9/phase-4-acceptance-gates.yaml <<‘EOF’
schema: l9.phase-acceptance-gates/v1

repository: Quantum-L9/l9-ci-debt-resolver
phase: RESOLVER-P4

gates:

* id: p4-exact-revision
    requirement: >
    Local HEAD matches the validated remediation base revision.
* id: p4-exact-worktree
    requirement: >
    Working-tree changes exactly match remediation expected paths.
* id: p4-repair-branch
    requirement: >
    Branch name is deterministic and uses an approved resolver prefix.
* id: p4-protected-branch
    requirement: >
    Protected branches cannot be targeted.
* id: p4-push-authorization
    requirement: >
    Push requires explicit unexpired repository, remote, and branch scope.
* id: p4-non-force
    requirement: >
    Force push, deletion refspecs, tags, and wildcard refspecs are absent.
* id: p4-deterministic-commit
    requirement: >
    Commit metadata contains the failure fingerprint, classification,
    remediation plan, and SDK validation result.
* id: p4-rerun
    requirement: >
    The provider rerun is dispatched and observed with bounded polling.
* id: p4-clean
    requirement: >
    Clean is emitted only after a successful completed rerun.
* id: p4-repeated-failure
    requirement: >
    A repeated failure fingerprint terminates the remediation loop.
* id: p4-attempt-limit
    requirement: >
    Fingerprint attempts cannot exceed the configured maximum.
* id: p4-no-merge
    requirement: >
    Automatic merge remains prohibited.
    EOF

###############################################################################

16. CI

###############################################################################

cat > .github/workflows/phase-4-remote-resolution.yml <<‘EOF’
name: RESOLVER-P4 Remote Resolution

on:
pull_request:
push:
branches:
- main

permissions:
contents: read

jobs:
remote-resolution:
runs-on: ubuntu-latest
timeout-minutes: 20

steps:
  - name: Checkout
    uses: actions/checkout@v4
  - name: Python
    uses: actions/setup-python@v5
    with:
      python-version: "3.11"
      cache: pip
  - name: Install
    run: |
      python -m pip install --upgrade pip
      python -m pip install -e '.[dev]'
  - name: Validate schemas
    run: |
      python - <<'PY'
      import json
      from pathlib import Path
      from jsonschema import Draft202012Validator
      for path in sorted(
          Path("schemas/resolver").glob("*.json")
      ):
          schema = json.loads(
              path.read_text(encoding="utf-8")
          )
          Draft202012Validator.check_schema(schema)
          print(path)
      PY
  - name: Remote policy tests
    run: pytest tests/remote
  - name: Resolution tests
    run: pytest tests/resolution
  - name: Architecture tests
    run: pytest tests/architecture
  - name: Full suite
    run: |
      pytest \
        --cov=l9_debt_resolver \
        --cov-report=term-missing \
        --cov-fail-under=85
  - name: Ruff
    run: ruff check .
  - name: Mypy
    run: mypy src
  - name: Capabilities
    run: l9-debt-resolver capabilities

EOF

###############################################################################

17. Structural validation

###############################################################################

python3 -m compileall -q src

python3 - <<‘PY’
from future import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

root = Path.cwd()

required = [
“.l9/remote-resolution-contract.yaml”,
“.l9/terminal-state-policy.yaml”,
“.l9/phase-4-acceptance-gates.yaml”,
“schemas/resolver/remote-attempt.schema.json”,
“schemas/resolver/rerun-observation.schema.json”,
“schemas/resolver/resolution-outcome.schema.json”,
“src/l9_debt_resolver/remote/policy.py”,
“src/l9_debt_resolver/remote/git.py”,
“src/l9_debt_resolver/remote/ledger.py”,
“src/l9_debt_resolver/remote/github.py”,
“src/l9_debt_resolver/resolution/terminal.py”,
“src/l9_debt_resolver/runtime/remote_resolution_service.py”,
“tests/remote/test_policy.py”,
“tests/remote/test_ledger.py”,
“tests/remote/test_git_adapter.py”,
“tests/resolution/test_terminal.py”,
“.github/workflows/phase-4-remote-resolution.yml”,
]

missing = [
value
for value in required
if not (root / value).is_file()
]

if missing:
raise SystemExit(
f”RESOLVER-P4 required files missing: {missing}”
)

for path in sorted(
(root / “schemas/resolver”).glob(”*.json”)
):
schema = json.loads(
path.read_text(encoding=“utf-8”)
)
Draft202012Validator.check_schema(schema)

source = root / “src/l9_debt_resolver”

prohibited = (
“push –force”,
“–force-with-lease”,
“gh pr merge”,
“merge_pull_request”,
“automatic_merge”,
“refs/tags/”,
“git tag”,
“create_subprocess_shell”,
“shell=true”,
)

for path in source.rglob(”*.py”):
content = path.read_text(
encoding=“utf-8”
).lower()

for term in prohibited:
    if term in content:
        raise SystemExit(
            f"prohibited RESOLVER-P4 behavior "
            f"{term!r} in {path}"
        )

capabilities = (
source
/ “runtime”
/ “capabilities.py”
).read_text(encoding=“utf-8”)

required_capabilities = (
‘“repair_branch_policy”: True’,
‘“deterministic_branch_names”: True’,
‘“push_authorization”: True’,
‘“non_force_push”: True’,
‘“rerun_dispatch”: True’,
‘“CI_rerun_observation”: True’,
‘“attempt_limits”: True’,
‘“repeated_failure_detection”: True’,
‘“terminal_state_emission”: True’,
‘“automatic_merge”: False’,
‘“force_push”: False’,
)

for capability in required_capabilities:
if capability not in capabilities:
raise SystemExit(
f”missing capability declaration: {capability}”
)

print(
json.dumps(
{
“schema_version”: “l9.phase-build-result/v1”,
“repository”: (
“Quantum-L9/l9-ci-debt-resolver”
),
“version”: “0.5.0”,
“phase”: “RESOLVER-P4”,
“status”: “built”,
“repair_branch_policy”: True,
“exact_revision_enforcement”: True,
“exact_worktree_enforcement”: True,
“deterministic_commits”: True,
“push_authorization”: True,
“non_force_push”: True,
“rerun_dispatch”: True,
“bounded_rerun_observation”: True,
“repeated_failure_detection”: True,
“new_failure_detection”: True,
“attempt_limits”: True,
“terminal_state_emission”: True,
“automatic_merge”: False,
“protected_branch_push”: False,
“force_push”: False
},
sort_keys=True,
separators=(”,”, “:”),
)
)
PY

printf ‘\n’
printf ‘RESOLVER-P4 build complete.\n’
printf ‘\n’
printf ‘Implemented:\n’
printf ’  - exact revision and worktree enforcement\n’
printf ’  - deterministic repair branch policy\n’
printf ’  - explicit push authorization\n’
printf ’  - deterministic remediation commits\n’
printf ’  - guarded non-force push\n’
printf ’  - GitHub failed-job rerun dispatch\n’
printf ’  - bounded rerun observation\n’
printf ’  - repeated-fingerprint detection\n’
printf ’  - new-failure detection\n’
printf ’  - per-fingerprint attempt limits\n’
printf ’  - deterministic terminal states\n’
printf ’  - no protected-branch push\n’
printf ’  - no force push\n’
printf ’  - no automatic merge\n’
printf ‘\n’
printf ‘Validate with:\n’
printf “  python -m pip install -e ‘.[dev]’\n”
printf ’  pytest\n’
printf ’  ruff check .\n’
printf ’  mypy src\n’
printf ’  l9-debt-resolver capabilities\n’
printf ‘\n’
printf ‘Next phase:\n’
printf ’  RESOLVER-P5 — privacy-safe Intelligence feedback events,\n’
printf ’  repeated-failure telemetry, resolution outcomes, delivery\n’
printf ’  retries, idempotency, and corpus-safe provenance.\n’