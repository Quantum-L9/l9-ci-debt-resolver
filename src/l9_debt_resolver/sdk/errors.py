from __future__ import annotations


class SDKIntegrationError(RuntimeError):
    """Base SDK integration failure."""


class SDKUnavailableError(SDKIntegrationError):
    """The public SDK knowledge service is unavailable."""


class SDKContractError(SDKIntegrationError):
    """SDK knowledge does not satisfy the public exchange contract."""


class SnapshotMismatchError(SDKIntegrationError):
    """SDK knowledge belongs to another repository revision."""
