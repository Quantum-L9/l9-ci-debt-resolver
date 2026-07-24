from __future__ import annotations


class FeedbackError(RuntimeError):
    """Base feedback error."""


class FeedbackPrivacyError(FeedbackError):
    """An event contains prohibited or unsafe information."""


class FeedbackSchemaError(FeedbackError):
    """An event violates the public feedback schema."""


class FeedbackDeliveryError(FeedbackError):
    """A feedback event could not be delivered."""


class PermanentDeliveryError(FeedbackDeliveryError):
    """Delivery failed permanently and must not be retried."""


class RetryableDeliveryError(FeedbackDeliveryError):
    """Delivery failed transiently and may be retried."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
