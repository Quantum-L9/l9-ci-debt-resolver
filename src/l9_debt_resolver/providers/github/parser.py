from __future__ import annotations

from typing import Any

from l9_debt_resolver.acquisition.errors import (
    RemoteResponseError,
)
from l9_debt_resolver.acquisition.models import (
    FailedJob,
    FailedRun,
    FailedStep,
)

_FAILED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
}


def parse_run(
    document: dict[str, Any],
    *,
    repository: str,
) -> FailedRun:
    run_id = document.get("id")
    status = document.get("status")
    head_sha = document.get("head_sha")
    event = document.get("event")
    if run_id is None or not isinstance(status, str):
        raise RemoteResponseError("GitHub run metadata is incomplete")
    if not isinstance(head_sha, str) or not head_sha:
        raise RemoteResponseError("GitHub run lacks a head SHA")
    if not isinstance(event, str) or not event:
        raise RemoteResponseError("GitHub run lacks an event")
    conclusion = document.get("conclusion")
    if conclusion is not None and not isinstance(
        conclusion,
        str,
    ):
        raise RemoteResponseError("GitHub run conclusion is invalid")
    workflow_id = document.get("workflow_id")
    return FailedRun(
        provider="github_actions",
        repository=repository,
        run_id=str(run_id),
        status=status,
        conclusion=conclusion,
        head_sha=head_sha,
        event=event,
        workflow_id=(str(workflow_id) if workflow_id is not None else None),
        created_at=_optional_string(document.get("created_at")),
        updated_at=_optional_string(document.get("updated_at")),
    )


def parse_failed_jobs(
    document: dict[str, Any],
    *,
    run_id: str,
) -> tuple[FailedJob, ...]:
    jobs = document.get("jobs")
    if not isinstance(jobs, list):
        raise RemoteResponseError("GitHub jobs response lacks jobs")
    parsed: list[FailedJob] = []
    for item in jobs:
        if not isinstance(item, dict):
            raise RemoteResponseError("GitHub returned an invalid job")
        conclusion = item.get("conclusion")
        if conclusion not in _FAILED_CONCLUSIONS:
            continue
        job_id = item.get("id")
        name = item.get("name")
        status = item.get("status")
        if job_id is None or not isinstance(name, str) or not isinstance(status, str):
            raise RemoteResponseError("GitHub failed-job metadata is incomplete")
        steps_value = item.get("steps", [])
        failed_steps: list[FailedStep] = []
        if not isinstance(steps_value, list):
            raise RemoteResponseError("GitHub job steps are invalid")
        for step in steps_value:
            if not isinstance(step, dict):
                continue
            step_conclusion = step.get("conclusion")
            if step_conclusion not in _FAILED_CONCLUSIONS:
                continue
            number = step.get("number", 0)
            step_name = step.get("name", "")
            failed_steps.append(
                FailedStep(
                    number=(int(number) if isinstance(number, int) else 0),
                    name=(step_name if isinstance(step_name, str) else ""),
                    conclusion=str(step_conclusion),
                )
            )
        labels = item.get("labels", [])
        parsed.append(
            FailedJob(
                provider="github_actions",
                run_id=run_id,
                job_id=str(job_id),
                name=name,
                status=status,
                conclusion=str(conclusion),
                started_at=_optional_string(item.get("started_at")),
                completed_at=_optional_string(item.get("completed_at")),
                runner_name=_optional_string(item.get("runner_name")),
                labels=tuple(
                    sorted({label for label in labels if isinstance(label, str)})
                ),
                failed_steps=tuple(
                    sorted(
                        failed_steps,
                        key=lambda step: (
                            step.number,
                            step.name,
                        ),
                    )
                ),
            )
        )
    return tuple(
        sorted(
            parsed,
            key=lambda job: (
                job.name,
                job.job_id,
            ),
        )
    )


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None
