from __future__ import annotations

import re
from pathlib import PurePosixPath

from .errors import UnsafePathError

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


def normalize_log_path(value: str) -> str:
    if "[REDACTED:" in value:
        raise UnsafePathError("path is unavailable or redacted")
    path = value.strip().strip("'\"()[]{}")
    path = path.replace("\\", "/")
    if not path or "[REDACTED:" in path or "\x00" in path:
        raise UnsafePathError("path is unavailable or redacted")
    if _WINDOWS_DRIVE.match(path):
        parts = path.split("/")
        path = _select_repository_suffix(parts)
    elif path.startswith("/"):
        parts = path.split("/")
        path = _select_repository_suffix(parts)
    while path.startswith("./"):
        path = path[2:]
    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise UnsafePathError("absolute path could not be reduced safely")
    if ".." in pure.parts:
        raise UnsafePathError("repository traversal path is prohibited")
    normalized = pure.as_posix()
    if not normalized or normalized == ".":
        raise UnsafePathError("empty normalized path")
    return normalized


def _select_repository_suffix(parts: list[str]) -> str:
    cleaned = [part for part in parts if part]
    anchors = (
        "src",
        "tests",
        "test",
        "lib",
        "app",
        "packages",
        "services",
        "cmd",
        "internal",
        "pkg",
        "crates",
    )
    for index, part in enumerate(cleaned):
        if part in anchors and index < len(cleaned) - 1:
            return "/".join(cleaned[index:])
    if len(cleaned) >= 2:
        return "/".join(cleaned[-2:])
    raise UnsafePathError("absolute path lacks a safe repository suffix")
