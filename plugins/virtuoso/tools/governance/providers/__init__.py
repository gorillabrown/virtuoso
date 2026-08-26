"""Provider selection (items 22-25).

A ceremony asks for a *role*, not a file. This module maps the role's declared
provider type onto an implementation, decides read-only vs writable from the
role's authority, mutability, and ``allowedWriters``, and — for a project that
has not yet migrated — serves the legacy local CSV catalog through an explicit,
clearly-labelled **compatibility adapter** (item 102) that is read-only.
"""
from __future__ import annotations

import os

from .. import policy as policy_mod, schema
from ..errors import ProviderError
from . import base, kpi, ledger, mapping as mapping_mod, recovery  # noqa: F401  (re-exported)
from .csv_provider import CsvWorkRegister
from .external_provider import ExternalWorkRegister, PendingMutation  # noqa: F401
from .markdown_provider import MarkdownWorkRegister
from .snapshot_provider import SnapshotWorkRegister, write_snapshot  # noqa: F401
from .xlsx_provider import XlsxWorkRegister

WORK_REGISTER_ROLE = "workRegister"
LEGACY_CATALOG_ROLE = "sprintCatalog"
TERMINAL_LEDGER_ROLE = "terminalLedger"

_LOCAL_PROVIDERS = {
    "csv": CsvWorkRegister,
    "markdown": MarkdownWorkRegister,
    "xlsx": XlsxWorkRegister,
    "snapshot": SnapshotWorkRegister,
}


class Selection:
    """A resolved provider plus the provenance of how it was chosen."""

    def __init__(self, provider, role_name: str, authority: str, notes: list[str],
                 compatibility: bool = False) -> None:
        self.provider = provider
        self.role_name = role_name
        self.authority = authority
        self.notes = notes
        self.compatibility = compatibility

    def as_dict(self) -> dict:
        data = dict(self.provider.describe())
        data.update({"role": self.role_name, "authority": self.authority,
                     "compatibilityAdapter": self.compatibility, "notes": list(self.notes)})
        return data


def _resolve_path(reg, spec) -> str:
    return os.path.join(reg.root, *spec.path.split("/"))


def _make_local(spec, source: str, mapping, read_only: bool):
    factory = _LOCAL_PROVIDERS.get(spec.provider)
    if factory is None:
        raise ProviderError(
            "role %r declares provider %r, which has no local implementation "
            "(available: %s)" % (spec.name, spec.provider, ", ".join(sorted(_LOCAL_PROVIDERS))),
            detail={"role": spec.name, "provider": spec.provider})
    if factory is SnapshotWorkRegister:
        return SnapshotWorkRegister(source=source, mapping=mapping)
    return factory(source=source, mapping=mapping, read_only=read_only)


def _snapshot_for(reg, policy) -> SnapshotWorkRegister | None:
    name = policy.get("workRegister.snapshot", "")
    if not name:
        return None
    spec = reg.roles.get(name)
    if spec is None or spec.is_external:
        return None
    return SnapshotWorkRegister(
        source=_resolve_path(reg, spec),
        mapping=mapping_mod.Mapping.from_policy(policy.section("workRegister")),
        stale_after_hours=float(policy.get("workRegister.staleAfterHours", 24) or 24),
    )


def for_role(reg, role_name: str, *, actor: str = "") -> Selection:
    """Build the provider serving ``role_name``.

    ``actor`` is the ceremony asking. A provider is writable only when the role's
    ``allowedWriters`` names that actor *and* the role's authority and mutability
    permit writes; otherwise it is served read-only and says so.
    """
    policy = policy_mod.load(reg.policy)
    spec = reg.roles.get(role_name)
    if spec is None:
        raise ProviderError(
            "role %r is not registered. Register it in %s (path or external identifier, "
            "provider, authority, mutability, allowedWriters) before running ceremonies "
            "that need it." % (role_name, schema.MANIFEST_RELPATH),
            detail={"role": role_name})

    mapping = mapping_mod.Mapping.from_policy(policy.section("workRegister"))
    writable = bool(actor) and spec.writable_by(actor)
    notes = []
    if not writable:
        notes.append("served read-only: %s"
                     % ("no actor supplied" if not actor
                        else "authority=%s mutability=%s allowedWriters=%s"
                             % (spec.authority, spec.mutability,
                                ", ".join(spec.allowed_writers) or "none")))

    if spec.is_external:
        provider = ExternalWorkRegister(
            source=spec.external, mapping=mapping, provider_kind=spec.provider,
            snapshot_provider=_snapshot_for(reg, policy), read_only=not writable,
            recovery_root=reg.root)
    else:
        provider = _make_local(spec, _resolve_path(reg, spec), mapping, not writable)

    return Selection(provider, role_name, spec.authority, notes)


def work_register(reg, *, actor: str = "") -> Selection:
    """The live work register, or the labelled compatibility adapter (item 102).

    Precedence:

    1. a registered ``workRegister`` role — whatever its provider;
    2. otherwise, a registered legacy ``sprintCatalog``, served **read-only**
       through the compatibility adapter with a note saying so;
    3. otherwise, a :class:`ProviderError` naming exactly what to register.

    Nothing here promotes a role to live authority on its own (item 6).
    """
    if WORK_REGISTER_ROLE in reg.roles:
        return for_role(reg, WORK_REGISTER_ROLE, actor=actor)

    legacy = reg.roles.get(LEGACY_CATALOG_ROLE)
    if legacy is not None and not legacy.is_external:
        policy = policy_mod.load(reg.policy)
        mapping = mapping_mod.Mapping.from_policy(policy.section("workRegister"))
        provider = _make_local(legacy, _resolve_path(reg, legacy), mapping, True)
        return Selection(
            provider, LEGACY_CATALOG_ROLE, legacy.authority,
            ["compatibility adapter: no `workRegister` role is registered, so the legacy "
             "`sprintCatalog` is being READ as the work register. It is not authoritative "
             "and cannot be written. Register a `workRegister` role to enable mutations."],
            compatibility=True)

    raise ProviderError(
        "no work register is registered. Add a `workRegister` role to %s — a local CSV or "
        "Markdown file, a spreadsheet, a connector-backed task manager, an issue tracker, a "
        "database, or a read-only snapshot." % schema.MANIFEST_RELPATH,
        detail={"role": WORK_REGISTER_ROLE})


def terminal_ledger(reg, *, actor: str = "") -> ledger.TerminalLedger:
    """The append-only terminal ledger, with its writers taken from policy."""
    policy = policy_mod.load(reg.policy)
    spec = reg.roles.get(TERMINAL_LEDGER_ROLE)
    if spec is None:
        raise ProviderError(
            "no `terminalLedger` role is registered. Close-out cannot append a terminal "
            "record until one is (item 24: the live register and the terminal ledger are "
            "different roles).", detail={"role": TERMINAL_LEDGER_ROLE})
    if spec.is_external:
        raise ProviderError(
            "terminal ledger %s is external; append its record with the host's connector and "
            "record the outcome via the recovery log" % spec.external,
            detail={"role": TERMINAL_LEDGER_ROLE, "external": spec.external})
    fmt = str(policy.get("terminalLedger.format", "markdown"))
    if spec.provider in ledger.FORMATS:
        fmt = spec.provider
    return ledger.TerminalLedger(
        _resolve_path(reg, spec), fmt=fmt,
        writers=[str(w) for w in policy.get("terminalLedger.writers", []) or []],
        correction_writers=[str(w) for w in
                            policy.get("terminalLedger.correctionWriters", []) or []],
    )


def describe_all(reg, *, actor: str = "") -> list[dict]:
    """A machine-readable description of every role and how it would be served."""
    out = []
    for name, spec in reg.roles.items():
        entry = {
            "role": name,
            "target": spec.target,
            "provider": spec.provider,
            "authority": spec.authority,
            "mutability": spec.mutability,
            "classification": spec.classification,
            "origin": spec.origin,
            "presence": spec.presence,
            "allowedWriters": list(spec.allowed_writers),
            "writable": bool(actor) and spec.writable_by(actor),
        }
        if spec.generated_from:
            entry["generatedFrom"] = spec.generated_from
        if spec.generated_by:
            entry["generatedBy"] = spec.generated_by
        out.append(entry)
    return out
