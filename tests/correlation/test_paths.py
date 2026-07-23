from __future__ import annotations

import pytest

from l9_debt_resolver.correlation.errors import (
    UnsafePathError,
)
from l9_debt_resolver.correlation.paths import (
    normalize_log_path,
)


def test_repository_relative_path_is_preserved() -> None:
    assert normalize_log_path("src/example/service.py") == "src/example/service.py"


def test_absolute_path_is_reduced() -> None:
    assert (
        normalize_log_path("/home/runner/work/repo/repo/src/example.py")
        == "src/example.py"
    )


def test_windows_path_is_reduced() -> None:
    assert (
        normalize_log_path(r"C:\work\repo\tests\test_example.py")
        == "tests/test_example.py"
    )


@pytest.mark.parametrize(
    "value",
    [
        "../secret.py",
        "src/../../secret.py",
        "[REDACTED:UNIX_PATH]",
        "",
    ],
)
def test_unsafe_paths_are_rejected(value: str) -> None:
    with pytest.raises(UnsafePathError):
        normalize_log_path(value)
