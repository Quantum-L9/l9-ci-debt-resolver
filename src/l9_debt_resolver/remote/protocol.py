from __future__ import annotations

from typing import Protocol

from .models import RerunObservation


class RerunProvider(Protocol):
    """CI rerun dispatch and observation surface required by RESOLVER-P4.

    Structural contract satisfied by ``GitHubRerunProvider``. The remote
    resolution loop depends on this narrow protocol rather than a concrete
    provider so alternative CI backends can be wired in without changing the
    runtime.
    """

    async def dispatch_failed_jobs(
        self,
        *,
        repository: str,
        run_id: str,
    ) -> None: ...

    async def observe(
        self,
        *,
        repository: str,
        original_run_id: str,
        expected_head_sha: str,
    ) -> RerunObservation: ...
