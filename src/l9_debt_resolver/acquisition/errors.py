from __future__ import annotations


class AcquisitionError(RuntimeError):
    """Base failed-log acquisition error."""


class AuthenticationError(AcquisitionError):
    """Provider authentication is unavailable or rejected."""


class AuthorizationError(AcquisitionError):
    """Provider denied access to a required resource."""


class RemoteResponseError(AcquisitionError):
    """Provider returned an invalid or terminal response."""


class RetryExhaustedError(AcquisitionError):
    """A retryable operation exhausted its bounded attempts."""


class PaginationLimitError(AcquisitionError):
    """Provider pagination exceeded the configured safety limit."""


class JobLimitError(AcquisitionError):
    """A run exceeded the configured failed-job safety limit."""


class LogSizeLimitError(AcquisitionError):
    """A log or run exceeded the configured byte limit."""


class UnsupportedLogFormatError(AcquisitionError):
    """A downloaded log uses an unsupported serialization."""
