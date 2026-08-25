"""Versioned governance registry schema (redesign items 13-21).

Two artifacts, one authority
----------------------------
The **machine manifest** (``Virtuoso/workspace-layout.json``) holds the
structured configuration and is the only authority. The **human registry**
(``Virtuoso.Governance.Readme.md``) is a *synchronized view* of it with
protected user-extension sections. Divergence between the two produces a
diagnostic, never an automatic overwrite (item 13).

Every registry declares its own ``schemaVersion`` and the plugin range it is
compatible with (item 14), so an older plugin refuses a newer registry loudly
instead of reinterpreting it.

Authority is *declared*, never inferred from a role's name (item 6). A role
called ``sprintCatalog`` is authoritative only when the project says so.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- versions ---------------------------------------------------------------

SCHEMA_VERSION = 2
#: Schema versions this plugin can read. Anything outside the range is refused
#: with ``SchemaVersionError`` rather than silently reinterpreted.
SUPPORTED_SCHEMA_VERSIONS = (1, 2)
#: Plugin versions a v2 registry written by this build declares compatibility with.
PLUGIN_COMPATIBILITY = ">=1.4.0 <2.0.0"

MANIFEST_RELPATH = "Virtuoso/workspace-layout.json"
README_RELPATH = "Virtuoso.Governance.Readme.md"
MARKER_RELPATH = "Virtuoso/.virtuoso"

# --- controlled vocabularies -------------------------------------------------

#: Authority classifications (item 16). ``unknown`` exists for conservative
#: migration only (item 21): it is neither writable nor authoritative.
AUTHORITIES = (
    "live",       # live operational authority
    "terminal",   # append-only terminal record
    "mirror",     # compatibility mirror, generated from a live role
    "report",     # generated report / presentation output
    "evidence",   # historical evidence (close-outs, audits)
    "archive",    # immutable archive
    "reference",  # informational reference
    "unknown",    # unclassified legacy role — not writable, not authoritative
)

MUTABILITIES = (
    "read-write",
    "append-only",
    "generated",   # written only by its registered generator
    "read-only",
    "immutable",   # hash-verified; never written by any ceremony
)

PROVIDERS = (
    "markdown",
    "csv",
    "xlsx",
    "jsonl",
    "json",
    "directory",
    "snapshot",
    "connector",
    "issue-tracker",
    "database",
    "external",
    "none",
)

#: Providers whose registration is an external identifier rather than a path.
EXTERNAL_PROVIDERS = frozenset({"connector", "issue-tracker", "database", "external"})
#: Providers whose registration is a directory.
DIRECTORY_PROVIDERS = frozenset({"directory"})

CLASSIFICATIONS = ("active", "historical", "unknown")
ORIGINS = ("authored", "generated", "unknown")
VALIDATIONS = ("exists", "markdown", "csv-headers", "xlsx", "external", "hash", "none")

#: Authority levels no ceremony may write to, whatever ``allowedWriters`` says.
NON_WRITABLE_AUTHORITIES = frozenset({"archive", "unknown"})
#: Mutability values no ceremony may write to directly.
NON_WRITABLE_MUTABILITIES = frozenset({"read-only", "immutable"})

#: Prefix reserved for project-defined roles and metadata. A key under this
#: prefix is round-tripped verbatim and never relabeled or discarded by an
#: upgrade (item 18).
EXTENSION_PREFIX = "x-"


def is_extension_key(key: str) -> bool:
    return isinstance(key, str) and key.startswith(EXTENSION_PREFIX)


# --- role specification ------------------------------------------------------


@dataclass
class RoleSpec:
    """One registered role. Carries the full item-15 metadata set.

    Exactly one of ``path`` / ``external`` is set. ``presence`` is *computed* at
    read time (never stored) and is one of ``present`` / ``absent`` /
    ``external`` / ``unverifiable``.
    """

    name: str
    path: str = ""
    external: str = ""
    provider: str = "none"
    authority: str = "unknown"
    mutability: str = "read-only"
    owner: str = ""                       # owning ceremony
    allowed_writers: list[str] = field(default_factory=list)
    validation: str = "exists"
    classification: str = "unknown"
    origin: str = "unknown"
    generated_from: str = ""              # source role, for derived artifacts (item 57)
    generated_by: str = ""                # registered generator command (item 60)
    label: str = ""                       # human label for the readme view
    description: str = ""
    extra: dict = field(default_factory=dict)   # x-* metadata, round-tripped verbatim

    # computed, never persisted
    presence: str = "unverifiable"
    absolute: str = ""

    # -- derived properties --------------------------------------------------

    @property
    def is_external(self) -> bool:
        return bool(self.external)

    @property
    def is_directory(self) -> bool:
        return self.provider in DIRECTORY_PROVIDERS

    @property
    def target(self) -> str:
        return self.external or self.path

    @property
    def expect(self) -> str:
        if self.is_external:
            return "external"
        if self.is_directory:
            return "directory"
        return "file"

    def writable_by(self, actor: str) -> bool:
        """Whether ``actor`` may write this role. Authority and mutability veto
        first: an archive, an unclassified legacy role, and anything read-only or
        immutable are unwritable no matter who asks."""
        if self.authority in NON_WRITABLE_AUTHORITIES:
            return False
        if self.mutability in NON_WRITABLE_MUTABILITIES:
            return False
        if not self.allowed_writers:
            return False
        return actor in self.allowed_writers or "*" in self.allowed_writers

    # -- serialization -------------------------------------------------------

    def to_manifest(self) -> dict:
        data: dict = {}
        if self.external:
            data["external"] = self.external
        else:
            data["path"] = self.path
        data["provider"] = self.provider
        data["authority"] = self.authority
        data["mutability"] = self.mutability
        if self.owner:
            data["owner"] = self.owner
        if self.allowed_writers:
            data["allowedWriters"] = list(self.allowed_writers)
        data["validation"] = self.validation
        data["classification"] = self.classification
        data["origin"] = self.origin
        if self.generated_from:
            data["generatedFrom"] = self.generated_from
        if self.generated_by:
            data["generatedBy"] = self.generated_by
        if self.label:
            data["label"] = self.label
        if self.description:
            data["description"] = self.description
        for key, value in self.extra.items():
            data[key] = value
        return data

    @classmethod
    def from_manifest(cls, name: str, data) -> "RoleSpec":
        """Build a RoleSpec from a manifest entry.

        A bare string entry is a v1-shaped ``role: path`` pair; it is accepted
        here so callers can parse without a separate branch, but it lands with
        ``authority='unknown'`` — conservative migration (item 21), never a
        guess at authority from the role's name (item 6).
        """
        if isinstance(data, str):
            return cls(name=name, path=data)
        if not isinstance(data, dict):
            return cls(name=name)
        extra = {k: v for k, v in data.items() if is_extension_key(k)}
        return cls(
            name=name,
            path=str(data.get("path") or ""),
            external=str(data.get("external") or ""),
            provider=str(data.get("provider") or "none"),
            authority=str(data.get("authority") or "unknown"),
            mutability=str(data.get("mutability") or "read-only"),
            owner=str(data.get("owner") or ""),
            allowed_writers=[str(w) for w in data.get("allowedWriters", []) if isinstance(w, str)],
            validation=str(data.get("validation") or "exists"),
            classification=str(data.get("classification") or "unknown"),
            origin=str(data.get("origin") or "unknown"),
            generated_from=str(data.get("generatedFrom") or ""),
            generated_by=str(data.get("generatedBy") or ""),
            label=str(data.get("label") or ""),
            description=str(data.get("description") or ""),
            extra=extra,
        )


# --- the plugin's own role vocabulary ---------------------------------------
#
# These are *defaults applied at `create` time only*. They are written into the
# manifest explicitly, so authority is always something the project declares and
# can change — never something a ceremony infers at read time.

DEFAULT_ROLES: dict[str, dict] = {
    "roadmap": {
        "provider": "markdown",
        "authority": "live",
        "mutability": "read-write",
        "owner": "roadmap-review",
        "allowedWriters": ["roadmap-review", "next-pointer", "mid-dispatch-decision",
                           "pointer-closeout"],
        "validation": "markdown",
        "classification": "active",
        "origin": "authored",
        "label": "Roadmap / specification store",
    },
    "workRegister": {
        "provider": "csv",
        "authority": "live",
        "mutability": "read-write",
        "owner": "roadmap-review",
        "allowedWriters": ["roadmap-review", "next-pointer", "pointer-closeout"],
        "validation": "csv-headers",
        "classification": "active",
        "origin": "authored",
        "label": "Live work register",
    },
    "terminalLedger": {
        "provider": "markdown",
        "authority": "terminal",
        "mutability": "append-only",
        "owner": "pointer-closeout",
        "allowedWriters": ["pointer-closeout"],
        "validation": "markdown",
        "classification": "active",
        "origin": "authored",
        "label": "Terminal completion ledger (append-only)",
    },
    "lessons": {
        "provider": "markdown",
        "authority": "reference",
        "mutability": "append-only",
        "owner": "pointer-closeout",
        "allowedWriters": ["pointer-closeout", "roadmap-review", "mid-dispatch-decision"],
        "validation": "markdown",
        "classification": "active",
        "origin": "authored",
        "label": "Lessons / retrospective",
    },
    "closeOuts": {
        "provider": "directory",
        "authority": "evidence",
        "mutability": "append-only",
        "owner": "pointer-closeout",
        "allowedWriters": ["pointer-closeout"],
        "validation": "exists",
        "classification": "active",
        "origin": "authored",
        "label": "Close-outs (directory)",
    },
    "issues": {
        "provider": "directory",
        "authority": "reference",
        "mutability": "read-write",
        "owner": "mid-dispatch-decision",
        "allowedWriters": ["mid-dispatch-decision", "next-pointer", "pointer-closeout",
                           "roadmap-review"],
        "validation": "exists",
        "classification": "active",
        "origin": "authored",
        "label": "Issues (directory)",
    },
    "roadmapReviews": {
        "provider": "directory",
        "authority": "report",
        "mutability": "read-write",
        "owner": "roadmap-review",
        "allowedWriters": ["roadmap-review", "roadmap-status"],
        "validation": "exists",
        "classification": "active",
        "origin": "generated",
        "label": "Roadmap reviews (directory)",
    },
    "outsideAudits": {
        "provider": "directory",
        "authority": "evidence",
        "mutability": "append-only",
        "owner": "3rd-party-audit",
        "allowedWriters": ["3rd-party-audit"],
        "validation": "exists",
        "classification": "active",
        "origin": "authored",
        "label": "Outside audits (directory)",
    },
    "reference": {
        "provider": "directory",
        "authority": "reference",
        "mutability": "read-write",
        "owner": "",
        "allowedWriters": [],
        "validation": "exists",
        "classification": "active",
        "origin": "authored",
        "label": "Reference (directory)",
    },
    "governance": {
        "provider": "directory",
        "authority": "reference",
        "mutability": "read-write",
        "validation": "exists",
        "classification": "active",
        "origin": "authored",
        "label": "Governance documents (directory)",
    },
    "operational": {
        "provider": "directory",
        "authority": "reference",
        "mutability": "read-write",
        "validation": "exists",
        "classification": "active",
        "origin": "authored",
        "label": "Operational documents (directory)",
    },
    "temp": {
        "provider": "directory",
        "authority": "reference",
        "mutability": "read-write",
        "validation": "exists",
        "classification": "active",
        "origin": "authored",
        "label": "Temp (directory)",
    },
    "workflowReference": {
        "provider": "markdown",
        "authority": "reference",
        "mutability": "read-write",
        "validation": "markdown",
        "classification": "active",
        "origin": "authored",
        "label": "Workflow reference",
    },
    "sprintQueue": {
        "provider": "xlsx",
        "authority": "report",
        "mutability": "generated",
        "owner": "roadmap-review",
        "allowedWriters": ["roadmap-review"],
        "validation": "xlsx",
        "classification": "active",
        "origin": "generated",
        "generatedFrom": "workRegister",
        "generatedBy": "build_register_report",
        "label": "Sprint queue workbook (generated report)",
    },
    "sprintCatalog": {
        # Legacy compatibility export. NOT authoritative by default (item 6/25):
        # a project that wants the CSV to be the live register registers it as
        # `workRegister` instead.
        "provider": "csv",
        "authority": "mirror",
        "mutability": "generated",
        "owner": "roadmap-review",
        "allowedWriters": ["roadmap-review"],
        "validation": "csv-headers",
        "classification": "active",
        "origin": "generated",
        "generatedFrom": "workRegister",
        "label": "Sprint catalog (compatibility export)",
    },
}

#: Roles created by ``create`` on a brand-new workspace, in readme order.
CREATE_ROLE_ORDER = (
    "roadmap",
    "workRegister",
    "terminalLedger",
    "lessons",
    "closeOuts",
    "issues",
    "roadmapReviews",
    "outsideAudits",
    "reference",
    "governance",
    "operational",
    "temp",
    "workflowReference",
)

#: v1 manifest keys that were *structural* rather than document roles.
V1_STRUCTURAL_KEYS = frozenset(
    {"governance", "operational", "temp", "outsideAudits", "reference", "scripts",
     "governanceReadme", "roadmapReviews", "closeOuts", "issues"}
)


def default_role(name: str) -> dict:
    """The declared default metadata for a known role, or a conservative
    unknown-role skeleton. Never guesses authority from the name (item 6)."""
    base = DEFAULT_ROLES.get(name)
    if base is None:
        return {
            "provider": "none",
            "authority": "unknown",
            "mutability": "read-only",
            "validation": "exists",
            "classification": "unknown",
            "origin": "unknown",
        }
    return dict(base)
