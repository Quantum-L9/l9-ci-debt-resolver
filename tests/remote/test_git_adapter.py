from __future__ import annotations

import subprocess
from pathlib import Path

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
    repository = GitRepository(workspace_root=tmp_path)
    await repository.verify_expected_changes(("app.py",))
    with pytest.raises(DirtyWorkspaceError):
        await repository.verify_expected_changes(("other.py",))
