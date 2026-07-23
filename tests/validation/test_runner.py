from __future__ import annotations

from pathlib import Path

import pytest

from l9_debt_resolver.validation.models import (
    ValidationStep,
)
from l9_debt_resolver.validation.runner import (
    ValidationCommandRunner,
)


@pytest.mark.asyncio
async def test_allowed_command_executes(
    tmp_path: Path,
) -> None:
    result = await ValidationCommandRunner().execute(
        workspace_root=tmp_path,
        step=ValidationStep(
            step_id="step-1",
            kind="targeted_test",
            command=(
                "python3",
                "-c",
                "raise SystemExit(0)",
            ),
            contract_id=None,
            test_id=None,
        ),
    )
    assert result.result == "passed"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_unapproved_executable_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError):
        await ValidationCommandRunner().execute(
            workspace_root=tmp_path,
            step=ValidationStep(
                step_id="step-1",
                kind="targeted_test",
                command=("bash", "-c", "true"),
                contract_id=None,
                test_id=None,
            ),
        )
