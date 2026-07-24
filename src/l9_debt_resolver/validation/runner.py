from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path

from .models import (
    ValidationStep,
    ValidationStepResult,
)

_ALLOWED_EXECUTABLES = {
    "python",
    "python3",
    "pytest",
    "ruff",
    "mypy",
    "npm",
    "pnpm",
    "yarn",
    "go",
    "cargo",
    "dotnet",
    "java",
    "gradle",
    "./gradlew",
    "make",
}


class ValidationCommandRunner:
    def __init__(
        self,
        *,
        timeout_seconds: float = 900.0,
    ) -> None:
        self._timeout_seconds = timeout_seconds

    async def execute(
        self,
        *,
        workspace_root: Path,
        step: ValidationStep,
    ) -> ValidationStepResult:
        if step.command is None:
            return ValidationStepResult(
                step_id=step.step_id,
                kind=step.kind,
                command_sha256=None,
                exit_code=None,
                duration_bucket="unknown",
                stdout_sha256=None,
                stderr_sha256=None,
                result="incomplete",
            )
        if not step.command:
            raise ValueError("validation command cannot be empty")
        executable = step.command[0]
        if executable not in _ALLOWED_EXECUTABLES:
            raise ValueError(f"validation executable is not allowed: {executable}")
        command_hash = hashlib.sha256(
            "\x00".join(step.command).encode("utf-8")
        ).hexdigest()
        environment = {
            key: value
            for key, value in os.environ.items()
            if key
            not in {
                "GITHUB_TOKEN",
                "GH_TOKEN",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AZURE_CLIENT_SECRET",
                "GOOGLE_APPLICATION_CREDENTIALS",
            }
        }
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *step.command,
            cwd=workspace_root,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            elapsed = time.monotonic() - started
            return ValidationStepResult(
                step_id=step.step_id,
                kind=step.kind,
                command_sha256=command_hash,
                exit_code=None,
                duration_bucket=_duration_bucket(elapsed),
                stdout_sha256=None,
                stderr_sha256=None,
                result="failed",
            )
        elapsed = time.monotonic() - started
        return ValidationStepResult(
            step_id=step.step_id,
            kind=step.kind,
            command_sha256=command_hash,
            exit_code=process.returncode,
            duration_bucket=_duration_bucket(elapsed),
            stdout_sha256=hashlib.sha256(stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr).hexdigest(),
            result=("passed" if process.returncode == 0 else "failed"),
        )


def _duration_bucket(seconds: float) -> str:
    if seconds < 1:
        return "lt_1s"
    if seconds < 10:
        return "1_10s"
    if seconds < 60:
        return "10_60s"
    if seconds < 300:
        return "1_5m"
    if seconds < 900:
        return "5_15m"
    return "gt_15m"
