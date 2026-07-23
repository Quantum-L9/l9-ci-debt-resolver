from __future__ import annotations

from l9_debt_resolver.providers.github.parser import (
    parse_failed_jobs,
    parse_run,
)


def test_parse_run() -> None:
    run = parse_run(
        {
            "id": 100,
            "status": "completed",
            "conclusion": "failure",
            "head_sha": "a" * 40,
            "event": "pull_request",
            "workflow_id": 10,
            "created_at": "2026-07-18T00:00:00Z",
            "updated_at": "2026-07-18T00:01:00Z",
        },
        repository="Quantum-L9/example",
    )
    assert run.run_id == "100"
    assert run.conclusion == "failure"


def test_only_failed_jobs_are_returned() -> None:
    jobs = parse_failed_jobs(
        {
            "jobs": [
                {
                    "id": 1,
                    "name": "passing",
                    "status": "completed",
                    "conclusion": "success",
                    "steps": [],
                    "labels": ["ubuntu-latest"],
                },
                {
                    "id": 2,
                    "name": "failing",
                    "status": "completed",
                    "conclusion": "failure",
                    "steps": [
                        {
                            "number": 1,
                            "name": "pytest",
                            "conclusion": "failure",
                        }
                    ],
                    "labels": ["ubuntu-latest"],
                },
            ]
        },
        run_id="100",
    )
    assert len(jobs) == 1
    assert jobs[0].job_id == "2"
    assert jobs[0].failed_steps[0].name == "pytest"
