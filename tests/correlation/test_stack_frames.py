from __future__ import annotations

from l9_debt_resolver.correlation.stack_frames import (
    extract_stack_frames,
)


def test_python_frame() -> None:
    frames = extract_stack_frames(
        'File "/home/runner/work/repo/repo/src/app.py", line 42, in execute'
    )
    assert len(frames) == 1
    assert frames[0].path == "src/app.py"
    assert frames[0].line == 42
    assert frames[0].symbol_hint == "execute"
    assert frames[0].language_family == "python"


def test_typescript_frame() -> None:
    frames = extract_stack_frames("at execute (/workspace/project/src/app.ts:10:8)")
    assert len(frames) == 1
    assert frames[0].path == "src/app.ts"
    assert frames[0].line == 10
    assert frames[0].column == 8


def test_frames_are_deterministic() -> None:
    log = "src/b.py:20:1 error\nsrc/a.py:10:2 error\nsrc/b.py:20:1 error\n"
    first = extract_stack_frames(log)
    second = extract_stack_frames(log)
    assert first == second
    assert [frame.path for frame in first] == [
        "src/a.py",
        "src/b.py",
    ]
