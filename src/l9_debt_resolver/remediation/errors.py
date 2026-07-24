from __future__ import annotations


class RemediationError(RuntimeError):
    """Base remediation failure."""


class RemediationNotEligibleError(RemediationError):
    """Classification cannot authorize remediation."""


class ApprovalRequiredError(RemediationError):
    """Explicit approval is missing, expired, or incomplete."""


class ProtectedPathError(RemediationError):
    """A remediation targets a protected path."""


class PatchPreconditionError(RemediationError):
    """A patch precondition does not match the workspace."""


class PatchBoundError(RemediationError):
    """A patch exceeds configured safety bounds."""


class TransactionError(RemediationError):
    """A transactional workspace operation failed."""


class ValidationFailedError(RemediationError):
    """SDK-owned validation rejected the remediation."""
