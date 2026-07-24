from __future__ import annotations


class DelegationError(RuntimeError):
    """Base delegation failure."""


class DelegationNotEligibleError(DelegationError):
    """Failure is not eligible for PR_Repair delegation."""


class DelegationPrivacyError(DelegationError):
    """Delegation data contains prohibited information."""


class DelegationSignatureError(DelegationError):
    """Proposal signature is invalid."""


class DelegationReplayError(DelegationError):
    """Callback nonce was already consumed."""


class DelegationExpiredError(DelegationError):
    """Request or callback timestamp has expired."""


class DelegationProposalError(DelegationError):
    """Proposal violates the Resolver delegation contract."""


class DelegationDeliveryError(DelegationError):
    """Request delivery failed."""


class DelegationRetryableError(DelegationDeliveryError):
    """Request delivery may be retried."""


class DelegationPermanentError(DelegationDeliveryError):
    """Request delivery must not be retried."""
