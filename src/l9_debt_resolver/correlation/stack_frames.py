from __future__ import annotations

import re
from dataclasses import dataclass

from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)

from .errors import UnsafePathError
from .models import StackFrame
from .paths import normalize_log_path


@dataclass(frozen=True)
class FramePattern:
    language_family: str
    confidence: float
    pattern: re.Pattern[str]


_PATTERNS = (
    FramePattern(
        language_family="python",
        confidence=0.98,
        pattern=re.compile(
            r'File ["\'](?P<path>[^"\']+)["\'], '
            r"line (?P<line>\d+)"
            r"(?:, in (?P<symbol>[^\r\n]+))?"
        ),
    ),
    FramePattern(
        language_family="javascript_typescript",
        confidence=0.96,
        pattern=re.compile(
            r"(?:at\s+(?:(?P<symbol>[^\s(]+)\s+\()?)"
            r"(?P<path>[^()\s]+?\.(?:js|jsx|ts|tsx|mjs|cjs))"
            r":(?P<line>\d+):(?P<column>\d+)\)?"
        ),
    ),
    FramePattern(
        language_family="java_kotlin",
        confidence=0.94,
        pattern=re.compile(
            r"at\s+(?P<symbol>[\w.$<>]+)"
            r"\((?P<path>[^():]+\.(?:java|kt))"
            r":(?P<line>\d+)\)"
        ),
    ),
    FramePattern(
        language_family="rust",
        confidence=0.93,
        pattern=re.compile(
            r"-->\s+(?P<path>[^:\r\n]+\.rs)"
            r":(?P<line>\d+):(?P<column>\d+)"
        ),
    ),
    FramePattern(
        language_family="go",
        confidence=0.92,
        pattern=re.compile(
            r"(?P<path>[^\s:]+\.go)"
            r":(?P<line>\d+)"
            r"(?::(?P<column>\d+))?"
        ),
    ),
    FramePattern(
        language_family="dotnet",
        confidence=0.92,
        pattern=re.compile(
            r"in\s+(?P<path>[^:\r\n]+\.(?:cs|fs|vb))"
            r":line\s+(?P<line>\d+)"
        ),
    ),
    FramePattern(
        language_family="generic",
        confidence=0.82,
        pattern=re.compile(
            r"(?P<path>[A-Za-z0-9_./\\-]+"
            r"\.(?:py|js|jsx|ts|tsx|java|kt|go|rs|cs|fs|vb"
            r"|c|cc|cpp|h|hpp|rb|php|swift|scala|sh|yaml|yml"
            r"|json|toml|xml))"
            r":(?P<line>\d+)"
            r"(?::(?P<column>\d+))?"
        ),
    ),
)


def extract_stack_frames(
    redacted_log: str,
) -> tuple[StackFrame, ...]:
    frames: dict[
        tuple[str, int | None, int | None],
        StackFrame,
    ] = {}
    for log_line_number, log_line in enumerate(
        redacted_log.splitlines(),
        start=1,
    ):
        for frame_pattern in _PATTERNS:
            for match in frame_pattern.pattern.finditer(log_line):
                raw_path = match.group("path")
                try:
                    path = normalize_log_path(raw_path)
                except UnsafePathError:
                    continue
                line = _positive_integer(match.groupdict().get("line"))
                column = _positive_integer(match.groupdict().get("column"))
                symbol = _clean_symbol(match.groupdict().get("symbol"))
                key = (
                    path,
                    line,
                    column,
                )
                candidate = StackFrame(
                    frame_id=namespaced_identity(
                        "frame_",
                        {
                            "path": path,
                            "line": line,
                            "column": column,
                            "symbol": symbol,
                            "log_line_number": log_line_number,
                        },
                    ),
                    path=path,
                    line=line,
                    column=column,
                    symbol_hint=symbol,
                    language_family=(frame_pattern.language_family),
                    log_line_number=log_line_number,
                    confidence=frame_pattern.confidence,
                    limitations=(),
                )
                current = frames.get(key)
                if current is None or candidate.confidence > current.confidence:
                    frames[key] = candidate
    return tuple(
        sorted(
            frames.values(),
            key=lambda frame: (
                frame.path,
                frame.line or 0,
                frame.column or 0,
                frame.symbol_hint or "",
                frame.frame_id,
            ),
        )
    )


def _positive_integer(
    value: str | None,
) -> int | None:
    if value is None:
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _clean_symbol(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped[:1000] if stripped else None
