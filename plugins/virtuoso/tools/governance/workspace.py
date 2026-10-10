"""Building a registry for ``create`` and ``adopt``.

Conventional paths appear in exactly two places in this plugin: here, and in
:mod:`discovery`. Everywhere else a path comes from the registry (item 87).

``create`` scaffolds a new workspace from the documented defaults. ``adopt``
registers what a project already has, in place — it never moves, duplicates, or
seeds anything, and it registers a role only where the project actually keeps it
(or, for directory roles it cannot find, anchors the declaration next to the
project's governance home and marks it absent so the user can retarget it).
"""
from __future__ import annotations

import os

from . import (backup as backup_mod, discovery, policy as policy_mod, registry as registry_mod,
               repostate, schema)
from .providers import recovery as recovery_mod

DOC_SUBDIRS = {
    "governance": "1 governance",
    "operational": "2 operational",
    "temp": "3 temp",
    "outsideAudits": "4 Outside Audits",
    "reference": "5 Reference",
}

DEFAULT_DOC_ROOT = "Project Documentation"

#: Conventional filenames used only when initializing a brand-new workspace.
CREATE_FILENAMES = {
    "roadmap": "Roadmap.md",
    "workRegister": "work-register.csv",
    "terminalLedger": "CompletedWork.Ledger.md",
    "lessons": "Retrospective.Lessons.md",
    "findings": "Findings.md",
    "workflowReference": "WORKFLOW_REFERENCE.md",
}


def _posix(*parts: str) -> str:
    return "/".join(p for p in parts if p)


def _drop_empty_writers(meta: dict) -> None:
    """Remove a defaults-supplied ``allowedWriters: []`` before scaffolding a role.

    ``RoleSpec`` preserves an ``allowedWriters`` key the manifest actually carried,
    including an empty one, so a project that writes "nobody may write this" keeps
    saying it. That preservation is about a *project's* file. A freshly scaffolded
    manifest expresses the same thing by omission, exactly as it does for an empty
    ``owner``, and making `create` start emitting a new key would change its output
    bytes for no gain — the release pipeline compares those bytes across versions.
    """
    if not meta.get("allowedWriters"):
        meta.pop("allowedWriters", None)


def create_registry(root: str, *, doc_root: str = "", layout: str = "plugin-only") -> registry_mod.Registry:
    """The registry a brand-new workspace starts from. All authority is declared."""
    docs = doc_root or DEFAULT_DOC_ROOT
    governance = _posix(docs, DOC_SUBDIRS["governance"])
    operational = _posix(docs, DOC_SUBDIRS["operational"])

    targets = {
        "roadmap": _posix(governance, CREATE_FILENAMES["roadmap"]),
        "workRegister": _posix(operational, CREATE_FILENAMES["workRegister"]),
        "terminalLedger": _posix(governance, CREATE_FILENAMES["terminalLedger"]),
        "lessons": _posix(governance, CREATE_FILENAMES["lessons"]),
        "findings": _posix(governance, CREATE_FILENAMES["findings"]),
        "closeOuts": _posix(operational, "Close-Outs"),
        "issues": _posix(operational, "Issues"),
        "roadmapReviews": _posix(operational, "roadmap-reviews"),
        "outsideAudits": _posix(docs, DOC_SUBDIRS["outsideAudits"]),
        "reference": _posix(docs, DOC_SUBDIRS["reference"]),
        "governance": governance,
        "operational": operational,
        "temp": _posix(docs, DOC_SUBDIRS["temp"]),
        "workflowReference": _posix(docs, DOC_SUBDIRS["reference"],
                                    CREATE_FILENAMES["workflowReference"]),
    }

    roles: dict[str, schema.RoleSpec] = {}
    for name in schema.CREATE_ROLE_ORDER:
        meta = schema.default_role(name)
        meta.pop("generatedFrom", None)
        meta.pop("generatedBy", None)
        _drop_empty_writers(meta)
        roles[name] = schema.RoleSpec.from_manifest(name, dict(meta, path=targets[name]))

    reg = registry_mod.Registry(
        root=os.path.abspath(root),
        schema_version=schema.SCHEMA_VERSION,
        plugin_compatibility=schema.PLUGIN_COMPATIBILITY,
        layout=layout,
        adopted=False,
        documentation_root=docs,
        roles=roles,
        policy={},
    )
    reg.compute_presence()
    return reg


def adopt_registry(root: str) -> tuple[registry_mod.Registry, list[str]]:
    """Register an established project in place.

    Returns ``(registry, notes)`` where ``notes`` explains, per role, exactly what
    was registered and why — adoption is never silent about what it decided.
    """
    root = os.path.abspath(root)
    notes: list[str] = []
    roles: dict[str, schema.RoleSpec] = {}

    roadmap = discovery.find_roadmap(root)
    if roadmap is None:
        raise ValueError("no live roadmap found under %s; nothing to adopt" % root)
    home = os.path.dirname(roadmap.path)
    home_rel = os.path.relpath(home, root).replace("\\", "/")
    if home_rel == ".":
        home_rel = ""

    def register(name: str, target: str, note: str, **overrides) -> None:
        meta = schema.default_role(name)
        meta.pop("generatedFrom", None)
        meta.pop("generatedBy", None)
        _drop_empty_writers(meta)
        meta.update(overrides)
        roles[name] = schema.RoleSpec.from_manifest(name, dict(meta, path=target))
        notes.append("%s -> %s (%s)" % (name, target, note))

    register("roadmap", roadmap.relative, roadmap.reason)

    register_found = discovery.find_work_register(root)
    if register_found:
        # Discovered, but NOT promoted to live authority on the plugin's say-so
        # (item 6): adoption registers it as an unclassified candidate and says so.
        roles["workRegister"] = schema.RoleSpec(
            name="workRegister", path=register_found.relative, provider="csv",
            authority="unknown", mutability="read-only", validation="csv-headers",
            classification="unknown", origin="unknown",
            label="Work register (candidate — classify before writes)")
        notes.append(
            "workRegister -> %s (%s; registered UNCLASSIFIED — set authority/mutability/"
            "allowedWriters to enable writes)" % (register_found.relative, register_found.reason))
    else:
        notes.append("workRegister -> (not registered: no local work register discovered; "
                     "register one — file, spreadsheet, tracker, or database — before "
                     "running work-register ceremonies)")

    workbook = discovery.find_workbook(root)
    if workbook:
        roles["sprintQueue"] = schema.RoleSpec(
            name="sprintQueue", path=workbook.relative, provider="xlsx",
            authority="report", mutability="generated", validation="xlsx",
            classification="active", origin="generated",
            label="Sprint queue workbook (generated report)")
        notes.append("sprintQueue -> %s (%s; presentation output, never read as truth)"
                     % (workbook.relative, workbook.reason))

    lessons = discovery.find_lessons(root, near=home)
    if lessons:
        register("lessons", lessons.relative, lessons.reason)
    else:
        register("lessons", _posix(home_rel, CREATE_FILENAMES["lessons"]),
                 "anchored beside the roadmap; not present yet")

    for name, base in (
        ("closeOuts", "Close-Outs"),
        ("issues", "Issues"),
        ("roadmapReviews", "roadmap-reviews"),
    ):
        target = _posix(home_rel, base)
        existing = os.path.isdir(os.path.join(root, *target.split("/")))
        register(name, target,
                 "existing directory" if existing else "anchored beside the roadmap; "
                 "not present yet")

    terminal = _posix(home_rel, CREATE_FILENAMES["terminalLedger"])
    if os.path.isfile(os.path.join(root, *terminal.split("/"))):
        register("terminalLedger", terminal, "existing terminal ledger")
    else:
        notes.append("terminalLedger -> (not registered: register an append-only terminal "
                     "ledger to enable transactional close-out)")

    reg = registry_mod.Registry(
        root=root,
        schema_version=schema.SCHEMA_VERSION,
        plugin_compatibility=schema.PLUGIN_COMPATIBILITY,
        layout="plugin-only",
        adopted=True,
        documentation_root=home_rel or ".",
        roles=roles,
        policy={},
    )
    reg.compute_presence()
    return reg, notes


#: A file name no project keeps, used to ask git whether a directory's contents are
#: ignored without the directory having to exist.
_IGNORE_PROBE = ".virtuoso-ignore-probe"

LOCAL_ONLY_HEADER = "# Virtuoso: machine-local state (repair backups, sweep quarantine, temp)"


def local_only_paths(reg: registry_mod.Registry) -> list[str]:
    """Directories whose contents stay on this machine: repair backups, the sweep's
    quarantine, and the registered ``temp`` role. Recovery records are the opposite:
    they are the idempotency trail for external writes and are versioned, so a fresh
    clone or a cloud session never repeats a write that already happened."""
    quarantine = policy_mod.load(reg.policy).get("sweep.quarantineDirectory",
                                                 "Virtuoso/.quarantine")
    paths = [_posix(*backup_mod.BACKUP_DIRNAME.split(os.sep)), quarantine]
    temp = reg.roles.get("temp")
    if temp and temp.path and not temp.is_external and temp.path.strip("/") not in ("", "."):
        paths.append(temp.path)
    return [p.replace("\\", "/").strip("/") for p in paths]


def gitignore_lines(reg: registry_mod.Registry) -> list[str]:
    return ["/%s/" % path for path in local_only_paths(reg)]


def ignore_findings(reg: registry_mod.Registry) -> list[registry_mod.Finding]:
    """Warnings for plugin state git treats the wrong way. Read-only; outside a git
    repository, or without git, there is nothing to say."""
    local = local_only_paths(reg)
    recovery_dir = _posix(*recovery_mod.RECOVERY_DIR.split(os.sep))
    probes = ["%s/%s" % (path, _IGNORE_PROBE) for path in local + [recovery_dir]]
    code, out = repostate._run(reg.root, "-c", "core.quotePath=false", "check-ignore",
                               *probes)
    if code not in (0, 1):
        return []
    ignored = set(out.splitlines())
    findings = []
    missing = ["/%s/" % path for path, probe in zip(local, probes) if probe not in ignored]
    if missing:
        findings.append(registry_mod.Finding(
            code="local-state-not-ignored", severity="warning",
            message="machine-local state is not git-ignored (%s), so every close-out "
                    "reports its contents. Add to .gitignore:\n"
                    "    %s\n    %s" % (", ".join(missing), LOCAL_ONLY_HEADER,
                                        "\n    ".join(missing))))
    if probes[-1] in ignored:
        findings.append(registry_mod.Finding(
            code="recovery-records-ignored", severity="warning",
            message="git ignores %s/, but recovery records are the idempotency trail "
                    "for external writes: a clone without them can repeat a write that "
                    "already happened. Remove the ignore rule and commit them."
                    % recovery_dir))
    return findings


def scaffold_paths(reg: registry_mod.Registry) -> list[str]:
    """Directories a ``create`` run lays down, in registry order."""
    out = []
    for spec in reg.roles.values():
        if spec.is_directory and spec.path:
            out.append(os.path.join(reg.root, *spec.path.split("/")))
    return out


def seed_contents(reg: registry_mod.Registry) -> dict[str, str]:
    """Template content for roles a ``create`` run seeds. Seeding is a create-only
    act: ``adopt`` and ``repair`` never write template content over a project."""
    buffer = policy_mod.load(reg.policy).dispatch_buffer
    seeds: dict[str, str] = {}
    roadmap = reg.roles.get("roadmap")
    if roadmap:
        seeds[roadmap.path] = ROADMAP_SEED.replace("{buffer}", str(buffer))
    ledger = reg.roles.get("terminalLedger")
    if ledger:
        seeds[ledger.path] = TERMINAL_LEDGER_SEED
    lessons = reg.roles.get("lessons")
    if lessons:
        seeds[lessons.path] = LESSONS_SEED
    findings = reg.roles.get("findings")
    if findings:
        seeds[findings.path] = FINDINGS_SEED
    work = reg.roles.get("workRegister")
    if work and work.provider == "csv":
        seeds[work.path] = WORK_REGISTER_SEED
    return seeds


ROADMAP_SEED = """# Project Roadmap

**Last updated:** (seeded by virtuoso create)

## How This Document Is Maintained

Archive-forward: the active section holds dispatch-ready specifications for the next
{buffer} items, stubs beyond, and one line per completed item in the Completed Work
Summary. Full content migrates to a dated archive at close-out. The dispatch buffer,
the hierarchy, and where specifications are stored are all project policy — see
`policy.roadmap` in `Virtuoso/workspace-layout.json`.

## Finish Line — Target

(define via the roadmap-review ceremony)

## Completed Work Summary

| Item | Session | Result | Close-Out |
|------|---------|--------|-----------|

## Active & Remaining Work

### Standing Rules All Items Inherit

## Notes
"""

TERMINAL_LEDGER_SEED = """# Completed Work — Terminal Ledger

Append-only. Every record is final: corrections are appended as new records that
reference the record they correct. Nothing here is reordered, rewritten, or deleted.

Estimate and Actual are the effort the item was estimated at and what it took, as
durations (90m, 1.5h); effort calibration in `kpis` learns from them. Effort is the
item's size word on the effort scale (xs … xl), not a duration; pace reads trailing
points from it.

| Record | Item | Completed | Result | Evidence | Corrects | Estimate | Actual | Effort |
|--------|------|-----------|--------|----------|----------|----------|--------|--------|
"""

LESSONS_SEED = """# Retrospective — Lessons Learned

(append numbered lesson entries here)
"""

FINDINGS_SEED = """# Findings

Append-only. One entry per finding — from a governance sweep, an adversarial review,
or an agent — under `### F-NNN — title (source, YYYY-MM-DD)` with **Source:**,
**Severity:**, **Where:**, **Finding:** and **Disposition:** (`open` when recorded).
A disposition changes only by appending a record under the same id. The roadmap
review reads the open ones.
"""

WORK_REGISTER_SEED = (
    "id,title,sequence,status,written_status,prerequisites,effort,lane,group,"
    "spec_link,branch,started,completed,evidence,description,notes\n"
)
