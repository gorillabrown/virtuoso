"""Exception hierarchy for the governance layer.

Every failure the governance layer raises carries a machine-readable ``code`` so
CLI callers can map it into the published status contract (see ``result.py``)
without string-matching a message.
"""
from __future__ import annotations


class GovernanceError(Exception):
    """Base class. ``code`` is the stable machine identifier for the failure."""

    code = "governance-error"

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}

    def as_dict(self) -> dict:
        return {"code": self.code, "message": str(self), "detail": self.detail}


class RegistryError(GovernanceError):
    code = "registry-error"


class SchemaVersionError(RegistryError):
    """The registry declares a schema version this plugin cannot serve."""

    code = "schema-version-unsupported"


class RegistryValidationError(RegistryError):
    """One or more registered roles failed validation (see ``detail['findings']``)."""

    code = "registry-invalid"


class RoleNotRegistered(RegistryError):
    """A ceremony asked for a role the project has not registered. There is no
    conventional-path fallback: registering the role is the fix (item 87)."""

    code = "role-not-registered"


class UnsafePathError(RegistryError):
    """A registered path escapes the project root, is unsafely absolute, or the
    role/path types disagree."""

    code = "unsafe-path"


class ProviderError(GovernanceError):
    code = "provider-error"


class CapabilityError(ProviderError):
    """A ceremony asked a provider for a capability it does not implement."""

    code = "capability-unsupported"


class ConcurrencyError(ProviderError):
    """The item changed between read and write (optimistic-concurrency guard)."""

    code = "concurrent-modification"


class RepairError(GovernanceError):
    code = "repair-failed"


class BackupError(GovernanceError):
    code = "backup-failed"
