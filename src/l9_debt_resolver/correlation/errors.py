from __future__ import annotations


class CorrelationError(RuntimeError):
    """Base repository-correlation failure."""


class IncompleteEvidenceError(CorrelationError):
    """Correlation requires complete primary failed-log evidence."""


class UnsafePathError(CorrelationError):
    """A log path cannot be safely interpreted as repository-relative."""
