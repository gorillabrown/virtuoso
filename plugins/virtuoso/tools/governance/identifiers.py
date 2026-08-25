"""External identifiers — registrations that name a board, project, database, or
service rather than a file on disk.

Redesign item 17: a registered external identifier is a *valid* registration. It
must never be reported as a missing filesystem path, and it must never be handed
to ``os.path`` for an existence check.

Grammar (deliberately permissive about the opaque part, strict about the shape)::

    <scheme>:<opaque>

``scheme`` is a lowercase URI-style scheme (``[a-z][a-z0-9+.-]*``). ``opaque`` is
any non-empty run of non-whitespace characters. Examples::

    monday:board/1234567890
    jira:project/ABC
    github:repo/example-org/example-repo
    postgres:table/public.work_items
    https://example.invalid/boards/42

Anything that parses is *well-formed*; whether the far side actually exists is a
question only the host's connector can answer, and the registry never pretends
otherwise (presence is reported as ``external``, never ``absent``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SCHEME_RE = re.compile(r"^([a-z][a-z0-9+.\-]*):(\S+)$")

# Schemes that name a filesystem location. Registering one of these as an
# `external` identifier is a role-type mismatch, not an external register.
_FILESYSTEM_SCHEMES = {"file"}

# Windows drive letters (``c:\...``) parse as a one-character scheme. They are
# paths, not external identifiers, and must be rejected here so the path
# validator sees them instead.
_DRIVE_RE = re.compile(r"^[a-zA-Z]:[\\/]")


@dataclass(frozen=True)
class ExternalIdentifier:
    raw: str
    scheme: str
    opaque: str

    @property
    def kind(self) -> str:
        """The first path segment of the opaque part (``board``, ``project``,
        ``table``, ...), or ``""`` when the identifier carries no segment."""
        return self.opaque.split("/", 1)[0] if "/" in self.opaque else ""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.raw


def looks_external(value: str) -> bool:
    """True when ``value`` is *shaped* like an external identifier. Used to route
    a registration to external handling before any filesystem call happens."""
    if not isinstance(value, str) or not value.strip():
        return False
    value = value.strip()
    if _DRIVE_RE.match(value):
        return False
    match = _SCHEME_RE.match(value)
    if not match:
        return False
    return match.group(1) not in _FILESYSTEM_SCHEMES


def parse(value: str) -> ExternalIdentifier:
    """Parse ``value`` into an :class:`ExternalIdentifier`.

    Raises ``ValueError`` with a diagnosable message when the value is malformed
    — a malformed external identifier is a validation finding (item 19), not a
    silently-ignored registration.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("external identifier is empty")
    value = value.strip()
    if _DRIVE_RE.match(value):
        raise ValueError(
            "%r is a filesystem path (drive letter), not an external identifier" % value
        )
    match = _SCHEME_RE.match(value)
    if not match:
        raise ValueError(
            "%r is not a well-formed external identifier "
            "(expected '<scheme>:<opaque>', e.g. 'monday:board/1234567890')" % value
        )
    scheme, opaque = match.group(1), match.group(2)
    if scheme in _FILESYSTEM_SCHEMES:
        raise ValueError(
            "%r names a filesystem location; register it as a path, not an "
            "external identifier" % value
        )
    return ExternalIdentifier(raw=value, scheme=scheme, opaque=opaque)


def validate(value: str) -> list[str]:
    """Return a list of human-readable findings (empty when ``value`` is sound)."""
    try:
        parse(value)
    except ValueError as exc:
        return [str(exc)]
    return []
