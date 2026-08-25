"""Conservative migration from the v1 registry to schema v2 (items 21, 101, 102).

Two rules govern every decision here:

* **Unknown stays unknown.** A legacy key the plugin does not recognize becomes a
  role with ``authority="unknown"`` and ``mutability="read-only"``. It is neither
  writable nor authoritative until a human classifies it.
* **A compatibility file is never promoted.** v1's ``sprintCatalog`` was
  documented as "the source of truth"; v2 does not carry that claim forward. It
  migrates as a ``mirror`` and the migration emits an explicit instruction to
  register a ``workRegister`` role if the CSV really is the live register.

Nothing here writes. It produces roles plus findings; applying them is
:mod:`repair`'s job, behind a preview and an approval.
"""
from __future__ import annotations

from . import schema
from .registry import Finding

#: v1 ``paths`` keys that map straight onto a v2 role of the same name.
_V1_DIRECT = (
    "roadmap", "lessons", "closeOuts", "issues", "roadmapReviews",
    "outsideAudits", "reference", "governance", "operational", "temp",
    "workflowReference", "sprintQueue", "sprintCatalog",
)

#: v1 keys that were plugin-internal locations, not governance documents. Their
#: values are preserved under ``x-legacy-v1`` so migration stays non-destructive,
#: but they do not become roles.
_V1_INTERNAL = ("scripts", "governanceReadme")


def roles_from_v1(data: dict) -> tuple[dict[str, schema.RoleSpec], list[Finding]]:
    """Translate a v1 manifest's ``paths`` mapping into v2 roles."""
    roles: dict[str, schema.RoleSpec] = {}
    findings: list[Finding] = []

    paths = data.get("paths")
    if not isinstance(paths, dict):
        return roles, findings

    for key, value in paths.items():
        if not isinstance(value, str) or not value.strip():
            continue
        if key in _V1_INTERNAL:
            continue
        if key in _V1_DIRECT:
            meta = schema.default_role(key)
            if key == "sprintCatalog":
                # v1 called this "the source of truth". v2 will not carry that
                # forward, and will not carry write access forward either: until a
                # human classifies it (or registers a real workRegister), it is a
                # read-only compatibility mirror with no writers.
                meta.update({"authority": "mirror", "mutability": "read-only",
                             "allowedWriters": []})
            # A derived-artifact relationship only survives migration when its
            # source role migrates too; a dangling generatedFrom would be a
            # validation error the project never authored.
            if meta.get("generatedFrom") not in paths:
                meta.pop("generatedFrom", None)
                meta.pop("generatedBy", None)
            roles[key] = schema.RoleSpec.from_manifest(key, dict(meta, path=value))
            continue
        # Unknown legacy role — stays unknown (item 21).
        roles[key] = schema.RoleSpec(
            name=key,
            path=value,
            provider="none",
            authority="unknown",
            mutability="read-only",
            validation="exists",
            classification="unknown",
            origin="unknown",
        )
        findings.append(Finding(
            "unclassified-legacy-role", "warning",
            "legacy role %r migrated as unclassified (not writable, not authoritative). "
            "Set its authority, mutability, provider, and allowedWriters in %s to activate it."
            % (key, schema.MANIFEST_RELPATH), role=key))

    if "sprintCatalog" in roles and "workRegister" not in roles:
        findings.append(Finding(
            "compatibility-catalog", "warning",
            "the legacy sprintCatalog migrated as a READ-ONLY compatibility mirror, not the "
            "live work register, and carries no writers. Ceremonies can still READ it through "
            "the compatibility adapter; mutations require an explicit `workRegister` role. "
            "Register one (provider csv/markdown/xlsx/connector/issue-tracker/database), or "
            "classify this role deliberately, to enable writes.",
            role="sprintCatalog"))

    if "terminalLedger" not in roles:
        findings.append(Finding(
            "no-terminal-ledger", "info",
            "no terminalLedger role is registered. Close-out ceremonies need an append-only "
            "terminal record; register one to enable transactional close-out."))

    return roles, findings


def legacy_leftovers(data: dict) -> dict:
    """The v1 keys that do not become roles, preserved verbatim for round-tripping."""
    paths = data.get("paths")
    if not isinstance(paths, dict):
        return {}
    kept = {k: v for k, v in paths.items() if k in _V1_INTERNAL and isinstance(v, str)}
    return {"x-legacy-v1": {"paths": kept}} if kept else {}


def needs_migration(data: dict) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    try:
        version = int(data.get("schemaVersion", 1))
    except (TypeError, ValueError):
        return True
    return version < schema.SCHEMA_VERSION
