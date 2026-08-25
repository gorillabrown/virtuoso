"""Previewable, transactional repair (items 7, 8, 9).

``repair`` never writes as a side effect of being asked what it would do.
:func:`plan` computes the *exact* bytes it would write and returns them; the
plan's public dict is what a preview prints and is byte-identical to the plan
the subsequent approved apply consumes (item 93).

:func:`apply_plan` is transactional:

1. the reconstructed manifest is parsed and validated **before any write** — on
   failure nothing is touched and the original registry and manifest are left
   intact (item 8);
2. every existing target is copied into a verified backup set first (item 9);
3. writes happen; a failure part-way restores from the backup set;
4. the written pair is re-loaded and re-validated; a failure restores.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

from . import backup as backup_mod, migrate, readme as readme_mod, registry as registry_mod
from . import schema, textio
from .errors import RepairError


@dataclass
class RepairAction:
    kind: str          # migrate-schema | adopt-readme-role | sync-readme-view |
                       # append-generated-region | create-registry-view |
                       # create-directory | manual
    role: str
    detail: str
    current: str = ""
    proposed: str = ""
    automatic: bool = True


@dataclass
class RepairPlan:
    root: str
    actions: list[RepairAction] = field(default_factory=list)
    files_affected: list[str] = field(default_factory=list)
    backup_root: str = backup_mod.BACKUP_DIRNAME.replace(os.sep, "/")
    manifest_text: str = ""
    readme_text: str = ""
    readme_action: str = ""
    #: findings that repair cannot fix on its own
    blocked: list[dict] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not any(a.automatic for a in self.actions)

    def as_dict(self) -> dict:
        """The preview payload. Deliberately excludes any timestamp so a preview
        and its subsequent apply compare equal (item 93)."""
        return {
            "actions": [asdict(a) for a in self.actions],
            "filesAffected": list(self.files_affected),
            "backupRoot": self.backup_root,
            "blocked": list(self.blocked),
        }

    def render(self) -> str:
        lines = ["Repair preview", "=============="]
        if not self.actions:
            lines.append("  nothing to repair")
        for action in self.actions:
            marker = "  *" if action.automatic else "  !"
            lines.append("%s [%s] %s" % (marker, action.kind, action.detail))
            if action.current or action.proposed:
                lines.append("      current:  %s" % (action.current or "(none)"))
                lines.append("      proposed: %s" % (action.proposed or "(none)"))
        lines.append("")
        lines.append("Files affected:")
        for path in self.files_affected or ["  (none)"]:
            lines.append("  - %s" % path if self.files_affected else path)
        lines.append("")
        lines.append("Backups will be written under: %s/" % self.backup_root)
        if self.blocked:
            lines.append("")
            lines.append("Not repairable automatically (fix these yourself):")
            for item in self.blocked:
                lines.append("  ! %s" % item.get("message", ""))
        return "\n".join(lines)


def plan(reg: registry_mod.Registry, *, plugin_version: str = "") -> RepairPlan:
    """Compute the repair plan for ``reg``. Pure: touches nothing on disk."""
    out = RepairPlan(root=reg.root)
    roles = {name: spec for name, spec in reg.roles.items()}

    raw = dict(reg.raw)
    extensions = dict(reg.extensions)

    # 1. schema migration -----------------------------------------------------
    if reg.manifest_present and migrate.needs_migration(reg.raw):
        out.actions.append(RepairAction(
            kind="migrate-schema", role="",
            detail="migrate registry schema v%s -> v%s (legacy roles stay unclassified)"
                   % (reg.schema_version, schema.SCHEMA_VERSION),
            current="schemaVersion %s" % reg.schema_version,
            proposed="schemaVersion %s" % schema.SCHEMA_VERSION))
        extensions.update(migrate.legacy_leftovers(reg.raw))

    # 2. reconstruct a lost manifest from the readme's machine block -----------
    view = reg.readme_view or readme_mod.parse(textio.read_text(reg.readme_path))
    if not reg.manifest_present and view.targets:
        for name, target in view.targets.items():
            if name in roles:
                continue
            roles[name] = _conservative_role(name, target)
            out.actions.append(RepairAction(
                kind="adopt-readme-role", role=name,
                detail="reconstruct role %r from the readme machine block (unclassified)" % name,
                current="(manifest absent)", proposed=target))
    else:
        # 3. readme-only roles ------------------------------------------------
        for name, target in view.targets.items():
            if name in roles:
                continue
            roles[name] = _conservative_role(name, target)
            out.actions.append(RepairAction(
                kind="adopt-readme-role", role=name,
                detail="adopt readme-only role %r into the manifest (unclassified until "
                       "you classify it)" % name,
                current="(readme only)", proposed=target))

    # 4. build the candidate manifest -----------------------------------------
    candidate = registry_mod.Registry(
        root=reg.root,
        schema_version=schema.SCHEMA_VERSION,
        plugin_compatibility=schema.PLUGIN_COMPATIBILITY,
        layout=reg.layout,
        adopted=reg.adopted,
        documentation_root=reg.documentation_root,
        roles=roles,
        policy=reg.policy,
        extensions=extensions,
        raw=raw,
    )
    candidate.compute_presence()
    out.manifest_text = candidate.manifest_json()

    current_manifest = textio.read_text(reg.manifest_path)
    if current_manifest is None or textio.normalized(current_manifest) != textio.normalized(out.manifest_text):
        out.files_affected.append(schema.MANIFEST_RELPATH)
        if current_manifest is not None and not any(a.kind == "migrate-schema" for a in out.actions):
            out.actions.append(RepairAction(
                kind="sync-manifest", role="",
                detail="rewrite %s with the repaired role table" % schema.MANIFEST_RELPATH))

    # 5. the readme view -------------------------------------------------------
    ordered = _ordered_roles(candidate)
    existing_readme = textio.read_text(reg.readme_path)
    new_readme, action = readme_mod.sync(existing_readme, ordered)
    out.readme_action = action
    if action == "unmanaged":
        # Never regenerate a user-authored registry from a template (item 5).
        # The only offer is an *additive* generated region appended at the end;
        # every existing byte is preserved.
        appended = existing_readme.rstrip("\n") + "\n\n## Registered roles (generated)\n\n" \
            + readme_mod.render_generated_region(ordered) + "\n"
        out.readme_text = appended
        out.readme_action = "append-generated-region"
        out.actions.append(RepairAction(
            kind="append-generated-region", role="",
            detail="%s carries no generated region; append one at the end. Every existing "
                   "byte is preserved — nothing above it is rewritten." % schema.README_RELPATH))
        out.files_affected.append(schema.README_RELPATH)
    else:
        out.readme_text = new_readme
        if existing_readme is None:
            out.actions.append(RepairAction(
                kind="create-registry-view", role="",
                detail="create %s as the human view of the manifest" % schema.README_RELPATH))
            out.files_affected.append(schema.README_RELPATH)
        elif textio.normalized(existing_readme) != textio.normalized(new_readme):
            out.actions.append(RepairAction(
                kind="sync-readme-view", role="",
                detail="refresh only the generated region of %s; user prose is preserved "
                       "byte-for-byte" % schema.README_RELPATH))
            out.files_affected.append(schema.README_RELPATH)

    # 6. what repair will not do ----------------------------------------------
    for finding in reg.findings:
        if finding.severity != "error":
            continue
        if finding.code in ("unsafe-path", "provider-mismatch", "bad-external-identifier",
                            "ambiguous-authority", "generator-source-missing", "dual-target",
                            "no-target", "plugin-incompatible"):
            out.blocked.append(finding.as_dict())
            out.actions.append(RepairAction(
                kind="manual", role=finding.role, detail=finding.message, automatic=False))

    return out


def _conservative_role(name: str, target: str) -> schema.RoleSpec:
    """A role adopted from the readme lands unclassified (item 21): not writable,
    not authoritative, until a human classifies it."""
    from . import identifiers
    if identifiers.looks_external(target):
        return schema.RoleSpec(name=name, external=target, provider="external",
                               authority="unknown", mutability="read-only",
                               validation="external", classification="unknown", origin="unknown")
    return schema.RoleSpec(name=name, path=target, provider="none", authority="unknown",
                           mutability="read-only", validation="exists",
                           classification="unknown", origin="unknown")


def _ordered_roles(reg: registry_mod.Registry) -> list[schema.RoleSpec]:
    """Known roles in their documented order, then project roles in registry order.
    Stable so a re-render never reorders a user's table."""
    known = [n for n in schema.CREATE_ROLE_ORDER if n in reg.roles]
    rest = [n for n in reg.roles if n not in known]
    return [reg.roles[n] for n in known + rest]


def apply_plan(reg: registry_mod.Registry, repair_plan: RepairPlan, *,
               plugin_version: str = "", now=None) -> tuple[list[str], backup_mod.BackupSet]:
    """Apply an approved plan transactionally. Returns ``(files_written, backup_set)``."""
    # -- 1. validate the reconstruction BEFORE any write ----------------------
    try:
        candidate_data = json.loads(repair_plan.manifest_text)
    except ValueError as exc:
        raise RepairError("repaired manifest is not valid JSON; nothing was written: %s" % exc)
    candidate = registry_mod.from_dict(reg.root, candidate_data, plugin_version=plugin_version)
    errors = [f.as_dict() for f in candidate.findings if f.severity == "error"]
    if errors:
        raise RepairError(
            "repaired registry failed validation; the original registry and manifest are "
            "untouched", detail={"findings": errors})

    # -- 2. back up every existing target ------------------------------------
    backup_set = backup_mod.open_set(reg.root, "repair", now=now)
    for rel in repair_plan.files_affected:
        backup_set.add(os.path.join(reg.root, *rel.split("/")), "repair")
    backup_set.write_manifest()
    problems = backup_mod.verify(backup_set)
    if problems:
        raise RepairError("backup verification failed; nothing was written",
                          detail={"problems": problems})

    # -- 3. write ------------------------------------------------------------
    written: list[str] = []
    try:
        if schema.MANIFEST_RELPATH in repair_plan.files_affected:
            if textio.write_if_changed(reg.manifest_path, repair_plan.manifest_text):
                written.append(schema.MANIFEST_RELPATH)
        if schema.README_RELPATH in repair_plan.files_affected:
            if textio.write_if_changed(reg.readme_path, repair_plan.readme_text):
                written.append(schema.README_RELPATH)
        # -- 4. verify what landed -------------------------------------------
        reloaded = registry_mod.load(reg.root, plugin_version=plugin_version)
        post_errors = [f.as_dict() for f in reloaded.findings if f.severity == "error"]
        if post_errors:
            raise RepairError("post-write validation failed", detail={"findings": post_errors})
    except Exception as exc:  # noqa: BLE001 - any failure rolls the pair back
        backup_mod.restore(backup_set)
        raise RepairError(
            "repair failed and was rolled back from %s: %s"
            % (backup_set.relative_directory, exc),
            detail={"backup": backup_set.relative_directory}) from exc

    return written, backup_set


def write_registry(reg: registry_mod.Registry, *, create_readme: bool = True) -> list[str]:
    """Write the manifest and synchronize the readme view for a registry the caller
    just built (``create`` / ``adopt``). Returns project-relative paths written.

    Refuses to touch a readme that carries no generated region — that is a
    user-authored document and only an approved repair may append to it (item 5).
    """
    reg.compute_presence()   # the readme's State column must reflect disk as of now
    written: list[str] = []
    if textio.write_if_changed(reg.manifest_path, reg.manifest_json()):
        written.append(schema.MANIFEST_RELPATH)
    if not create_readme:
        return written
    ordered = _ordered_roles(reg)
    existing = textio.read_text(reg.readme_path)
    new_text, action = readme_mod.sync(existing, ordered)
    if action == "unmanaged":
        return written
    if textio.write_if_changed(reg.readme_path, new_text):
        written.append(schema.README_RELPATH)
    return written
