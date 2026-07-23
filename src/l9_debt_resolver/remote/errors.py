from __future__ import annotations


class RemoteOperationError(RuntimeError):
    """Base remote resolution error."""


class BranchPolicyError(RemoteOperationError):
    """Requested branch violates repair-branch policy."""


class RevisionMismatchError(RemoteOperationError):
    """Local repository revision does not match the validated remediation."""


class DirtyWorkspaceError(RemoteOperationError):
    """Workspace contains unexpected changes."""


class PushAuthorizationError(RemoteOperationError):
    """Explicit remote push authorization is unavailable."""


class ProtectedBranchError(RemoteOperationError):
    """Operation targets a protected branch."""


class AttemptLimitReachedError(RemoteOperationError):
    """Failure fingerprint exhausted its bounded attempts."""


class RerunTimeoutError(RemoteOperationError):
    """CI rerun did not complete before timeout."""


class ProviderObservationError(RemoteOperationError):
    """CI provider observation failed."""
