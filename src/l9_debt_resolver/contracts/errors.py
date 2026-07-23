from __future__ import annotations


class ContractError(ValueError):
    """Base contract failure."""


class SchemaValidationError(ContractError):
    """A document violates its JSON Schema contract."""


class IdentityError(ContractError):
    """Canonical identity material is invalid."""


class AttemptTransitionError(ContractError):
    """A resolver attempt transition is not permitted."""


class TerminalStateError(ContractError):
    """A terminal state invariant is violated."""


class CorpusSafetyError(ContractError):
    """A resolution event contains prohibited data."""
