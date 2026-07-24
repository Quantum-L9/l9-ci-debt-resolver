from __future__ import annotations

import pytest

from l9_debt_resolver.acquisition.redaction import (
    LogRedactor,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "[REDACTED:BEARER_TOKEN]",
        ),
        (
            "token=github_pat_abcdefghijklmnopqrstuvwxyz123456",
            "[REDACTED:GITHUB_TOKEN]",
        ),
        (
            "email alice@example.com",
            "[REDACTED:EMAIL]",
        ),
        (
            "failed at /home/alice/repository/file.py",
            "[REDACTED:UNIX_PATH]",
        ),
        (
            r"failed at C:\Users\alice\repository\file.py",
            "[REDACTED:WINDOWS_PATH]",
        ),
    ],
)
def test_sensitive_content_is_redacted(
    raw: str,
    expected: str,
) -> None:
    result = LogRedactor().redact(raw)
    assert expected in result.text
    assert raw != result.text


def test_repository_root_is_redacted() -> None:
    result = LogRedactor("/workspace/project").redact(
        "/workspace/project/src/module.py failed"
    )
    assert "/workspace/project" not in result.text
    assert "[REDACTED:REPOSITORY_ROOT]" in result.text
