from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import (
    PatchBoundError,
    PatchPreconditionError,
    TransactionError,
)
from .models import (
    AppliedChange,
    RemediationPlan,
    TransactionResult,
)
from .policy import RemediationBounds, validate_mutable_path


@dataclass(frozen=True)
class OriginalFile:
    path: Path
    existed: bool
    content: bytes


class WorkspaceTransaction:
    def __init__(
        self,
        *,
        workspace_root: Path,
        bounds: RemediationBounds,
    ) -> None:
        self._root = workspace_root.resolve()
        self._bounds = bounds
        self._originals: dict[Path, OriginalFile] = {}
        self._committed = False

    def apply(
        self,
        plan: RemediationPlan,
    ) -> TransactionResult:
        staged: dict[Path, bytes] = {}
        for operation in plan.operations:
            validate_mutable_path(operation.path)
            target = self._resolve_target(operation.path)
            if target not in staged:
                current = self._read_target(target)
                if len(current) > self._bounds.maximum_file_bytes:
                    raise PatchBoundError(f"file exceeds byte limit: {operation.path}")
                staged[target] = current
                self._originals[target] = OriginalFile(
                    path=target,
                    existed=target.exists(),
                    content=current,
                )
            current = staged[target]
            current_sha256 = hashlib.sha256(current).hexdigest()
            if current_sha256 != operation.expected_file_sha256:
                raise PatchPreconditionError(f"file hash mismatch: {operation.path}")
            replacement_sha256 = hashlib.sha256(
                operation.replacement_text.encode("utf-8")
            ).hexdigest()
            if replacement_sha256 != operation.replacement_sha256:
                raise PatchPreconditionError(
                    f"replacement hash mismatch: {operation.path}"
                )
            text = current.decode("utf-8")
            occurrences = text.count(operation.expected_text)
            if occurrences != 1:
                raise PatchPreconditionError(
                    f"expected text must occur exactly once in "
                    f"{operation.path}; found {occurrences}"
                )
            updated = text.replace(
                operation.expected_text,
                operation.replacement_text,
                1,
            )
            staged[target] = updated.encode("utf-8")
        changes = []
        for target, updated in sorted(
            staged.items(),
            key=lambda item: item[0].as_posix(),
        ):
            original = self._originals[target].content
            changed_lines = _changed_line_count(
                original.decode("utf-8"),
                updated.decode("utf-8"),
            )
            changes.append(
                AppliedChange(
                    path=target.relative_to(self._root).as_posix(),
                    before_sha256=hashlib.sha256(original).hexdigest(),
                    after_sha256=hashlib.sha256(updated).hexdigest(),
                    changed_line_count=changed_lines,
                )
            )
        total_lines = sum(change.changed_line_count for change in changes)
        if total_lines > self._bounds.maximum_changed_lines:
            raise PatchBoundError("remediation exceeds changed-line limit")
        try:
            for target, updated in staged.items():
                _atomic_write(target, updated)
        except Exception as error:
            self.rollback()
            raise TransactionError("transactional patch write failed") from error
        return TransactionResult(
            changes=tuple(changes),
            worktree_digest=_worktree_digest(
                self._root,
                tuple(change.path for change in changes),
            ),
        )

    def commit(self) -> None:
        self._committed = True
        self._originals.clear()

    def rollback(self) -> None:
        if self._committed:
            return
        errors = []
        for original in self._originals.values():
            try:
                if original.existed:
                    _atomic_write(
                        original.path,
                        original.content,
                    )
                elif original.path.exists():
                    original.path.unlink()
            except Exception as error:
                errors.append(error)
        self._originals.clear()
        if errors:
            raise TransactionError("workspace rollback was incomplete")

    def _resolve_target(self, path: str) -> Path:
        candidate = (self._root / path).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as error:
            raise PatchPreconditionError(f"path escapes workspace: {path}") from error
        if not candidate.is_file():
            raise PatchPreconditionError(f"target file does not exist: {path}")
        return candidate

    @staticmethod
    def _read_target(path: Path) -> bytes:
        return path.read_bytes()


def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.resolver.",
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _changed_line_count(
    before: str,
    after: str,
) -> int:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    maximum = max(len(before_lines), len(after_lines))
    count = 0
    for index in range(maximum):
        before_value = before_lines[index] if index < len(before_lines) else None
        after_value = after_lines[index] if index < len(after_lines) else None
        if before_value != after_value:
            count += 1
    return count


def _worktree_digest(
    root: Path,
    paths: tuple[str, ...],
) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        content = (root / path).read_bytes()
        digest.update(path.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()
