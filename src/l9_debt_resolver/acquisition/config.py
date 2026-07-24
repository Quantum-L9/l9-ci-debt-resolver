from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    maximum_attempts: int = 4
    initial_backoff_seconds: float = 0.25
    maximum_backoff_seconds: float = 4.0
    maximum_retry_after_seconds: float = 30.0
    retryable_statuses: frozenset[int] = frozenset(
        {
            408,
            425,
            429,
            500,
            502,
            503,
            504,
        }
    )

    def __post_init__(self) -> None:
        if self.maximum_attempts < 1:
            raise ValueError("maximum_attempts must be positive")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds cannot be negative")
        if self.maximum_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError(
                "maximum_backoff_seconds cannot be smaller than initial_backoff_seconds"
            )


@dataclass(frozen=True)
class AcquisitionLimits:
    page_size: int = 100
    maximum_pages: int = 100
    maximum_jobs_per_run: int = 1000
    maximum_log_bytes_per_job: int = 50 * 1024 * 1024
    maximum_total_log_bytes: int = 500 * 1024 * 1024

    def __post_init__(self) -> None:
        positive = {
            "page_size": self.page_size,
            "maximum_pages": self.maximum_pages,
            "maximum_jobs_per_run": self.maximum_jobs_per_run,
            "maximum_log_bytes_per_job": (self.maximum_log_bytes_per_job),
            "maximum_total_log_bytes": (self.maximum_total_log_bytes),
        }
        for name, value in positive.items():
            if value < 1:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class AcquisitionConfig:
    retry: RetryPolicy = RetryPolicy()
    limits: AcquisitionLimits = AcquisitionLimits()
    api_version: str = "2022-11-28"
    user_agent: str = "l9-ci-debt-resolver/0.2.0"
