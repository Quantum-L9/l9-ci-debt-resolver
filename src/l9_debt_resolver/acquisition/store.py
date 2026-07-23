from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import AcquiredLog, AcquisitionReport


class AcquisitionArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def persist(
        self,
        *,
        report: AcquisitionReport,
        logs: tuple[AcquiredLog, ...] = (),
    ) -> Path:
        destination = self._root / report.acquisition_id
        destination.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )
        _atomic_json(
            destination / "report.json",
            report.as_dict(),
        )
        for log in logs:
            job_root = destination / "jobs" / log.evidence.job_id
            job_root.mkdir(
                parents=True,
                exist_ok=True,
                mode=0o700,
            )
            _atomic_json(
                job_root / "evidence.json",
                log.evidence.as_dict(),
            )
            _atomic_json(
                job_root / "provenance.json",
                log.provenance.as_dict(),
            )
            _atomic_text(
                job_root / "redacted.log",
                log.redacted_text,
            )
        return destination


def _atomic_json(
    path: Path,
    value: Any,
) -> None:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    _atomic_text(path, text)


def _atomic_text(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
