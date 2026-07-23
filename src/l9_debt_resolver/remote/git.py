from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

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
            raise RemoteOperationError("cannot stage an empty remediation")
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
            stderr_hash = hashlib.sha256(stderr).hexdigest()
            raise RemoteOperationError(
                "git operation failed; "
                f"command={arguments[0]}, "
                f"stderr_sha256={stderr_hash}"
            )
        return result
