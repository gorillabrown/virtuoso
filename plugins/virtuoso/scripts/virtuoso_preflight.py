#!/usr/bin/env python3
"""Virtuoso preflight — validate, adopt, create, or repair a project's governance registry.

Four separate operations, each with one job (redesign item 3):

  check    read-only validation and discovery. **Zero project writes**, always.
           `detect` is a retained alias so existing hooks keep working.
  adopt    register an already-established project in place. Never rewrites the
           project's own documents; against an already-registered project it is
           exactly `check` — adoption never silently heals (item 4).
  create   initialize a new workspace. Requires --authorize (item 3).
  repair   preview proposed repairs; apply them only with --apply (items 7, 8).

Every invocation prints the two machine-readable contract lines, quiet or not:

    virtuoso-status: <status>
    writes: <N>

`--json` additionally emits the full structured result (item 11): status, mode,
writes, files written, findings, and the resolved role table. The complete list
of statuses is published in tools/governance/result.py and covered by
scripts/test_status_contract.py (item 10).

Usage:
    python virtuoso_preflight.py --root <dir> [--mode check|adopt|create|repair]
        [--authorize] [--apply] [--json] [--quiet] [--strict]
    python virtuoso_preflight.py --check-document <path>
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.governance import (  # noqa: E402
    backup as backup_mod, discovery, install, policy as policy_mod, providers,
    registry as registry_mod, repair as repair_mod, result as result_mod, schema,
    textio, workspace,
)
from tools.governance.errors import GovernanceError  # noqa: E402

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: A document larger than this earns a WARN from the integrity guard — an
#: archive-forward document that has stopped being archived. Project policy may
#: override it via `policy.roadmap.oversizeBytes`.
DEFAULT_OVERSIZE_BYTES = 512 * 1024


def plugin_version() -> str:
    import json
    try:
        with open(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"),
                  encoding="utf-8") as handle:
            return str(json.load(handle).get("version", ""))
    except (OSError, ValueError):
        return ""


def _say(quiet: bool, message: str) -> None:
    if not quiet:
        print(message)


def _record_install() -> None:
    """Record this version's install root and refresh the launchers.

    Both live under the user's home, never inside a project, so this is not a
    project write and never affects the `writes:` count. The record is keyed by
    plugin version, so two installed versions cannot overwrite each other's
    discovery state (item 12).
    """
    install.record(PLUGIN_ROOT, plugin_version())
    install.ensure_launchers()


def _roles_payload(reg: registry_mod.Registry) -> list[dict]:
    return providers.describe_all(reg)


def _findings_payload(reg: registry_mod.Registry) -> list[dict]:
    return [f.as_dict() for f in reg.findings]


def _status_for(reg: registry_mod.Registry) -> str:
    if any(f.severity == "error" for f in reg.findings):
        return result_mod.REPAIR_NEEDED
    if any(f.severity == "warning" for f in reg.findings):
        return result_mod.WARNING
    return result_mod.READY


def _is_registered(root: str) -> bool:
    return os.path.isfile(os.path.join(root, *schema.MANIFEST_RELPATH.split("/"))) or \
        os.path.isfile(os.path.join(root, *schema.MARKER_RELPATH.split("/")))


# --- modes -------------------------------------------------------------------


def run_check(root: str, mode: str = "check") -> result_mod.Result:
    """Read-only. Performs discovery and validation with zero project writes."""
    if _is_registered(root):
        reg = registry_mod.load(root, plugin_version=plugin_version())
        status = _status_for(reg)
        message = {
            result_mod.READY: "registry is valid; nothing to do.",
            result_mod.WARNING: "registry is usable; %d non-blocking finding(s)."
                                % sum(1 for f in reg.findings if f.severity == "warning"),
            result_mod.REPAIR_NEEDED: "registry has %d error-severity finding(s); run "
                                      "`--mode repair` to preview a fix."
                                      % sum(1 for f in reg.findings if f.severity == "error"),
        }[status]
        return result_mod.Result(
            status=status, mode=mode, root=root, message=message,
            findings=_findings_payload(reg), roles=_roles_payload(reg),
            schema_version=reg.schema_version, plugin_version=plugin_version())

    if discovery.is_adoptable(root):
        found = discovery.find_roadmap(root)
        return result_mod.Result(
            status=result_mod.ADOPTABLE, mode=mode, root=root,
            message="an established governance tree exists here (roadmap: %s) but is not "
                    "registered. Run `--mode adopt` to register it in place — nothing is "
                    "moved, duplicated, or rewritten." % found.relative,
            plugin_version=plugin_version())

    return result_mod.Result(
        status=result_mod.NONE, mode=mode, root=root,
        message="no governance registry here and nothing to adopt. Run `--mode create "
                "--authorize` to initialize a workspace.",
        plugin_version=plugin_version())


def run_adopt(root: str) -> result_mod.Result:
    """Register an established project. Against an already-registered project this
    is exactly `check` — an adoption command never invokes repair (item 4)."""
    if _is_registered(root):
        outcome = run_check(root, mode="adopt")
        if outcome.status in (result_mod.WARNING, result_mod.REPAIR_NEEDED):
            outcome.message += (" This project is already registered; `adopt` did not heal "
                                "it. Run `--mode repair` to preview a fix.")
        return outcome

    if not discovery.is_adoptable(root):
        return result_mod.Result(
            status=result_mod.NONE, mode="adopt", root=root,
            message="no live roadmap found here, so there is nothing to adopt. Run "
                    "`--mode create --authorize` to initialize a workspace.",
            plugin_version=plugin_version())

    reg, notes = workspace.adopt_registry(root)
    written = _write_marker(root)
    written += repair_mod.write_registry(reg)
    reloaded = registry_mod.load(root, plugin_version=plugin_version())
    return result_mod.Result(
        status=result_mod.ADOPTED, mode="adopt", root=root,
        message="adopted in place. Nothing was moved, duplicated, or rewritten.\n  "
                + "\n  ".join(notes),
        writes=len(written), files_written=written,
        findings=_findings_payload(reloaded), roles=_roles_payload(reloaded),
        schema_version=reloaded.schema_version, plugin_version=plugin_version())


def run_create(root: str, *, authorized: bool, layout: str = "plugin-only") -> result_mod.Result:
    """Initialize a new workspace. Explicit authorization required (item 3)."""
    if not authorized:
        return result_mod.Result(
            status=result_mod.FAILED, mode="create", root=root,
            message="`create` writes new files into this project, so it requires explicit "
                    "authorization. Re-run with --authorize (or use `--mode check` to see "
                    "what is here without writing anything).",
            error={"code": "authorization-required", "message": "--authorize not supplied"},
            plugin_version=plugin_version())

    if _is_registered(root):
        return result_mod.Result(
            status=result_mod.FAILED, mode="create", root=root,
            message="this project already carries a governance registry; `create` will not "
                    "overwrite it. Use `--mode check`, or `--mode repair` to preview a fix.",
            error={"code": "already-registered", "message": schema.MANIFEST_RELPATH},
            plugin_version=plugin_version())

    reg = workspace.create_registry(root, layout=layout)
    written: list[str] = []
    for directory in workspace.scaffold_paths(reg):
        os.makedirs(directory, exist_ok=True)
    for relative, content in workspace.seed_contents(reg).items():
        target = os.path.join(root, *relative.split("/"))
        if os.path.exists(target):
            continue                       # never overwrite user content
        if textio.write_if_changed(target, content):
            written.append(relative)
    written += _write_marker(root)
    written += repair_mod.write_registry(reg)

    reloaded = registry_mod.load(root, plugin_version=plugin_version())
    return result_mod.Result(
        status=result_mod.CREATED, mode="create", root=root,
        message="initialized a new workspace with %d file(s)." % len(written),
        writes=len(written), files_written=written,
        findings=_findings_payload(reloaded), roles=_roles_payload(reloaded),
        schema_version=reloaded.schema_version, plugin_version=plugin_version())


def run_repair(root: str, *, apply: bool) -> result_mod.Result:
    """Preview repairs; apply them only when asked. Applying is transactional."""
    if not _is_registered(root):
        return run_check(root, mode="repair")

    reg = registry_mod.load(root, plugin_version=plugin_version())
    plan = repair_mod.plan(reg, plugin_version=plugin_version())

    if not apply:
        status = result_mod.REPAIR_PREVIEW if plan.actions else _status_for(reg)
        return result_mod.Result(
            status=status, mode="repair", root=root,
            message=plan.render(), plan=plan.as_dict(),
            findings=_findings_payload(reg), roles=_roles_payload(reg),
            schema_version=reg.schema_version, plugin_version=plugin_version())

    if plan.empty:
        outcome = run_check(root, mode="repair")
        outcome.plan = plan.as_dict()
        return outcome

    written, backup_set = repair_mod.apply_plan(reg, plan, plugin_version=plugin_version())
    backup_mod.prune(root, keep=int(policy_mod.load(reg.policy).get("sweep.backupRetention", 10)))
    reloaded = registry_mod.load(root, plugin_version=plugin_version())
    return result_mod.Result(
        status=result_mod.REPAIRED, mode="repair", root=root,
        message="applied %d change(s); originals backed up under %s"
                % (len(written), backup_set.relative_directory),
        writes=len(written), files_written=written,
        plan=plan.as_dict(), backup=backup_set.as_dict(),
        findings=_findings_payload(reloaded), roles=_roles_payload(reloaded),
        schema_version=reloaded.schema_version, plugin_version=plugin_version())


def _write_marker(root: str) -> list[str]:
    target = os.path.join(root, *schema.MARKER_RELPATH.split("/"))
    if textio.write_if_changed(target, "virtuoso-workspace\n"):
        return [schema.MARKER_RELPATH]
    return []


# --- document integrity guard -------------------------------------------------


def check_document(path: str, *, oversize_bytes: int = DEFAULT_OVERSIZE_BYTES) -> int:
    """Integrity guard for a document about to be rewritten.
    Exit codes: 0 ok, 2 warn (empty / oversize), 3 fail (missing / corrupt)."""
    if not path or not os.path.isfile(path):
        print("document-integrity: fail (missing: %s)" % path)
        return 3
    raw = textio.read_bytes(path)
    if raw is None:
        print("document-integrity: fail (unreadable: %s)" % path)
        return 3

    failures, warnings = [], []
    if b"\x00" in raw:
        failures.append("null-bytes")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        failures.append("not-utf-8")
    if not raw.strip():
        warnings.append("empty")
    if len(raw) > oversize_bytes:
        warnings.append("oversize:%d-bytes(>%d)" % (len(raw), oversize_bytes))

    if failures:
        print("document-integrity: fail (%s) size=%d"
              % (", ".join(failures + warnings), len(raw)))
        return 3
    if warnings:
        print("document-integrity: warn (%s) size=%d" % (", ".join(warnings), len(raw)))
        return 2
    print("document-integrity: ok size=%d" % len(raw))
    return 0


# --- entry point --------------------------------------------------------------


def preflight(root: str, mode: str = "check", *, quiet: bool = False,
              authorized: bool = False, apply: bool = False,
              layout: str = "plugin-only") -> result_mod.Result:
    root = os.path.abspath(root)
    _record_install()
    try:
        if mode in ("check", "detect"):
            outcome = run_check(root, mode=mode)
        elif mode == "adopt":
            outcome = run_adopt(root)
        elif mode == "create":
            outcome = run_create(root, authorized=authorized, layout=layout)
        elif mode == "repair":
            outcome = run_repair(root, apply=apply)
        else:
            raise ValueError("unknown mode %r (one of %s)" % (mode, ", ".join(result_mod.MODES)))
    except GovernanceError as exc:
        outcome = result_mod.Result(
            status=result_mod.FAILED, mode=mode, root=root, message=str(exc),
            error=exc.as_dict(), plugin_version=plugin_version())
    outcome.assert_contract()
    return outcome


def emit(outcome: result_mod.Result, *, quiet: bool, as_json: bool) -> None:
    # The two contract lines are EXEMPT from --quiet: they are what hooks and
    # tools parse, and the SessionStart hook runs quiet.
    for line in outcome.contract_lines():
        print(line)
    if as_json:
        print(outcome.to_json())
        return
    if outcome.message:
        _say(quiet, "virtuoso: " + outcome.message)
    if outcome.files_written:
        _say(quiet, "virtuoso: wrote %d file(s):" % len(outcome.files_written))
        for path in outcome.files_written:
            _say(quiet, "  + " + path)
    for finding in outcome.findings:
        if finding.get("severity") in ("error", "warning"):
            _say(quiet, "  [%s] %s" % (finding["severity"], finding["message"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--mode", choices=list(result_mod.MODES), default="check")
    parser.add_argument("--layout", default="plugin-only")
    parser.add_argument("--authorize", action="store_true",
                        help="authorize `create` to write new files into the project")
    parser.add_argument("--apply", action="store_true",
                        help="apply an approved repair (without it, repair only previews)")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="emit the full structured result")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero when the registry needs repair (for CI)")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--check-document", dest="check_document", default=None,
                        help="integrity-check one document and exit (0 ok / 2 warn / 3 fail)")
    parser.add_argument("--check-roadmap", dest="check_document", default=None,
                        help=argparse.SUPPRESS)   # retained alias
    args = parser.parse_args(argv)

    if args.check_document is not None:
        return check_document(args.check_document)

    outcome = preflight(args.root, args.mode, quiet=args.quiet, authorized=args.authorize,
                        apply=args.apply, layout=args.layout)
    emit(outcome, quiet=args.quiet, as_json=args.as_json)
    return outcome.strict_exit_code() if args.strict else outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())
