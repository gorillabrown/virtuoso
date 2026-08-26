#!/usr/bin/env python3
"""Registry and work-register operations for ceremonies.

Query subcommands create nothing and heal nothing as a side effect (item 86).
The commands that write say so explicitly: `snapshot`, `closeout --prepare`,
`mutation-plan` (opens durable recovery before a host connector write), and
`mutation-confirm` (records the connector result and resolves recovery only on
success).

Subcommands:
  roles                     list every registered role and how it resolves
  resolve <role>            print one role's absolute path or external identifier
  provider [--role R]       describe the provider serving a role, and its capabilities
  items [--all]             list work items from the work register
  next                      the next eligible work item
  kpis                      derived metrics, each with its provenance
  closeout --item ID --date D   resolve close-out artifact paths (read-only)
  repo [--expect PATHS]     read-only repository state and readiness finding
  deps                      check the project's declared runtime dependencies
  protected                 hash every protected file (immutable-hash verification)
  snapshot --out PATH       capture a timestamped snapshot of the work register
  recovery                  list unresolved partial-failure recovery records
  mutation-plan             emit a revision-aware host connector instruction
  mutation-confirm          durably record the host connector result

Exit codes: 0 ok; 3 the query could not be answered (unregistered role, missing
provider, malformed configuration) — always with a message naming the fix.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.governance import (  # noqa: E402
    policy as policy_mod, providers, registry as registry_mod, schema, textio,
)
from tools.governance.errors import CapabilityError, GovernanceError, RoleNotRegistered  # noqa: E402
from tools.governance import dependencies, integrity, repostate  # noqa: E402
from tools.governance.providers import kpi, recovery, snapshot_provider  # noqa: E402

EXIT_OK = 0
EXIT_UNANSWERABLE = 3


def _load(root: str) -> registry_mod.Registry:
    return registry_mod.load(root)


def _emit(payload, as_json: bool, renderer=None) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif renderer is not None:
        print(renderer())
    else:
        print(payload)
    return EXIT_OK


def cmd_roles(args) -> int:
    reg = _load(args.root)
    rows = providers.describe_all(reg, actor=args.actor)
    if args.as_json:
        return _emit({"roles": rows, "schemaVersion": reg.schema_version}, True)
    width = max((len(r["role"]) for r in rows), default=4)
    for row in rows:
        print("%-*s  %-10s %-10s %-11s %-9s %s"
              % (width, row["role"], row["provider"], row["authority"],
                 row["mutability"], row["presence"], row["target"]))
    return EXIT_OK


def cmd_resolve(args) -> int:
    reg = _load(args.root)
    print(reg.resolve(args.role))
    return EXIT_OK


def cmd_provider(args) -> int:
    reg = _load(args.root)
    selection = (providers.work_register(reg, actor=args.actor) if args.role == "workRegister"
                 else providers.for_role(reg, args.role, actor=args.actor))
    return _emit(selection.as_dict(), args.as_json,
                 lambda: json.dumps(selection.as_dict(), indent=2, ensure_ascii=False))


def cmd_items(args) -> int:
    reg = _load(args.root)
    selection = providers.work_register(reg, actor=args.actor)
    snap = selection.provider.snapshot()
    items = snap.items if args.all else [i for i in snap.items if not i.is_terminal]
    payload = {"items": [i.as_dict() for i in items], "provenance": snap.provenance(),
               "selection": selection.as_dict()}
    if args.as_json:
        return _emit(payload, True)
    for item in items:
        print("%-4s %-12s %-10s %-9s %s"
              % (item.sequence if item.sequence is not None else "-", item.id,
                 item.status, item.written_status or "-", item.title))
    if snap.stale:
        print("\n[STALE] %s" % snap.stale_reason)
    print("\nsource: %s via %s, snapshot %s"
          % (snap.source, snap.provider, snap.taken_at))
    return EXIT_OK


def cmd_next(args) -> int:
    reg = _load(args.root)
    selection = providers.work_register(reg, actor=args.actor)
    item = selection.provider.next_eligible()
    snap = selection.provider.snapshot()
    payload = {"item": item.as_dict() if item else None, "provenance": snap.provenance(),
               "selection": selection.as_dict()}
    if args.as_json:
        return _emit(payload, True)
    if item is None:
        print("no eligible item: every active item is blocked or waiting on a prerequisite")
        return EXIT_OK
    print("%s — %s" % (item.title or "(untitled)", item.id))
    print("  sequence:      %s" % (item.sequence if item.sequence is not None else "unsequenced"))
    print("  status:        %s (%s)" % (item.status, item.raw_status or "—"))
    print("  specification: %s" % (item.written_status or "unknown"))
    print("  prerequisites: %s" % (", ".join(item.prerequisites) or "none"))
    print("  effort:        %s" % (item.effort or "unrecorded"))
    print("\nsource: %s via %s, snapshot %s" % (snap.source, snap.provider, snap.taken_at))
    return EXIT_OK


def cmd_kpis(args) -> int:
    reg = _load(args.root)
    project_policy = policy_mod.load(reg.policy)
    selection = providers.work_register(reg, actor=args.actor)
    snap = selection.provider.snapshot()
    metrics = kpi.compute(
        snap,
        effort_scale=project_policy.get("roadmap.effortScale"),
        dispatch_buffer=project_policy.dispatch_buffer,
    )
    return _emit(metrics.as_dict(), args.as_json, metrics.render)


def cmd_closeout(args) -> int:
    """Resolve close-out artifact paths.

    Read-only unless --prepare is given (item 86), and *fails loudly* on a present-
    but-invalid registry rather than falling back to a conventional Close-Outs
    directory (item 85).
    """
    reg = _load(args.root)
    if not reg.manifest_present:
        print("no governance registry at %s/%s. Close-out locations are resolved through "
              "the registry — run virtuoso_preflight.py --mode adopt or --mode create "
              "--authorize first." % (args.root, schema.MANIFEST_RELPATH), file=sys.stderr)
        return EXIT_UNANSWERABLE
    blocking = [f for f in reg.findings if f.severity == "error"]
    if blocking:
        print("the governance registry is present but invalid; refusing to guess a close-out "
              "location. Run virtuoso_preflight.py --mode repair to preview a fix.\n  "
              + "\n  ".join(f.message for f in blocking), file=sys.stderr)
        return EXIT_UNANSWERABLE

    project_policy = policy_mod.load(reg.policy)
    closeout_dir = reg.resolve("closeOuts")   # RoleNotRegistered surfaces as exit 3
    lessons = ""
    try:
        lessons = reg.resolve("lessons")
    except RoleNotRegistered:
        pass
    try:
        ledger_path = reg.resolve("terminalLedger")
    except RoleNotRegistered:
        ledger_path = ""

    template = str(project_policy.get("issues.filenameTemplate", "Issue.{item-id}.{date}.md"))
    report = os.path.join(closeout_dir, "CloseOut.%s.%s.md" % (args.item, args.date))
    payload = {
        "closeOutDirectory": closeout_dir,
        "closeOutReport": report,
        "lessons": lessons,
        "terminalLedger": ledger_path,
        "nextLessonId": _next_lesson_id(lessons, args.lesson_prefix),
        "issueFilenameTemplate": template,
        "prepared": False,
    }
    if args.prepare:
        os.makedirs(closeout_dir, exist_ok=True)
        payload["prepared"] = True
    if args.as_json:
        return _emit(payload, True)
    for key, value in payload.items():
        print("%s=%s" % (key, value))
    return EXIT_OK


def _next_lesson_id(lessons: str, prefix: str) -> str:
    """The next lesson identifier. A missing or unregistered lessons document yields
    the first identifier; nothing is created here."""
    text = textio.read_text(lessons) if lessons else None
    numbers = [int(n) for n in re.findall(r"%s-(\d+)" % re.escape(prefix), text or "")]
    return "%s-%03d" % (prefix, (max(numbers) + 1) if numbers else 1)


def cmd_snapshot(args) -> int:
    reg = _load(args.root)
    selection = providers.work_register(reg, actor=args.actor)
    snap = selection.provider.snapshot()
    target = args.out if os.path.isabs(args.out) else os.path.join(args.root, args.out)
    snapshot_provider.write_snapshot(target, snap)
    print("snapshot written: %s (%d item(s), taken %s)"
          % (target, len(snap.items), snap.taken_at))
    return EXIT_OK


def cmd_deps(args) -> int:
    """Check the project's declared runtime dependencies (item 79)."""
    reg = _load(args.root)
    declared = policy_mod.load(reg.policy).section("dependencies")
    results = [r.as_dict() for r in dependencies.check(declared)]
    if args.as_json:
        return _emit({"dependencies": results}, True)
    if not results:
        print("no runtime dependencies declared")
        return EXIT_OK
    for row in results:
        print("%-14s %-10s %-10s %s"
              % (row["name"], row["required"] or "any", row["installed"] or "-",
                 "ok" if row["ok"] else row["reason"]))
    return EXIT_OK if all(r["ok"] for r in results) else EXIT_UNANSWERABLE


def cmd_protected(args) -> int:
    """Hash every protected file (item 62). Read-only."""
    reg = _load(args.root)
    snap = integrity.snapshot(reg)
    if args.as_json:
        return _emit(snap.as_dict(), True)
    if not snap.hashes:
        print("no protected files")
        return EXIT_OK
    for role, members in sorted(snap.roles.items()):
        print("%s:" % role)
        for rel in members:
            print("  %s  %s" % (snap.hashes.get(rel, "unreadable")[:16], rel))
    for rel in snap.unreadable:
        print("  UNREADABLE  %s" % rel)
    return EXIT_OK


def cmd_repo(args) -> int:
    """Read-only repository state and the repository-readiness finding."""
    reg = _load(args.root)
    project_policy = policy_mod.load(reg.policy)
    state = repostate.inspect(args.root, project_policy.section("git"))
    expected = [p for p in (args.expect or "").split(",") if p.strip()]
    finding = repostate.readiness(state, expected, project_policy.section("git"))
    payload = {"state": state.as_dict(), "readiness": finding,
               "policy": project_policy.section("git")}
    if args.as_json:
        return _emit(payload, True)
    if not state.is_repository:
        print("not a git repository: %s" % args.root)
        return EXIT_OK
    print("repository:     %s" % args.root)
    print("remote:         %s (%s)" % (state.remote or "none", state.remote_source))
    print("default branch: %s (%s)" % (state.default_branch or "unknown",
                                       state.default_branch_source))
    print("current branch: %s" % (state.current_branch or "(detached HEAD)"))
    print("worktrees:      %d%s" % (len(state.worktrees),
                                    "" if state.is_primary_worktree else " (not the primary tree)"))
    if state.ahead is not None:
        print("ahead/behind:   %d/%d" % (state.ahead, state.behind or 0))
    print("scoped dirty:   %s" % (", ".join(finding["scopedDirty"]) or "none"))
    print("unrelated dirty:%s" % (" " + ", ".join(finding["unrelatedDirty"])
                                  if finding["unrelatedDirty"] else " none (left untouched)"))
    print("readiness:      %s" % finding["result"])
    for problem in finding["problems"]:
        print("  - %s" % problem)
    return EXIT_OK


def cmd_recovery(args) -> int:
    records = recovery.outstanding(os.path.abspath(args.root))
    if args.as_json:
        return _emit({"outstanding": records}, True)
    if not records:
        print("no outstanding recovery records")
        return EXIT_OK
    for record in records:
        print("%s  %s/%s" % (
            record.get("id"), record.get("operation"),
            record.get("item_id") or record.get("itemId")))
        for step in record.get("remaining_steps", []):
            print("    remaining: %s" % step)
    return EXIT_OK


def _json_object(raw: str, label: str) -> dict:
    try:
        value = json.loads(raw or "{}")
    except ValueError as exc:
        raise GovernanceError("%s must be valid JSON: %s" % (label, exc)) from exc
    if not isinstance(value, dict):
        raise GovernanceError("%s must be a JSON object" % label)
    return value


def _external_mutation_provider(args):
    if not args.actor:
        raise CapabilityError("an explicit ceremony actor is required for external mutations")
    selection = providers.work_register(_load(args.root), actor=args.actor)
    provider = selection.provider
    if not hasattr(provider, "plan_mutation"):
        raise CapabilityError(
            "provider %r performs local mutations and does not use host mutation plans"
            % provider.name)
    return provider


def cmd_mutation_plan(args) -> int:
    """Create a revision-aware instruction and durable recovery record."""
    provider = _external_mutation_provider(args)
    plan = provider.plan_mutation(
        args.operation, args.item, _json_object(args.fields_json, "--fields-json"),
        revision=args.revision, idempotency_key=args.idempotency_key)
    return _emit(plan.as_dict(), args.as_json,
                 lambda: json.dumps(plan.as_dict(), indent=2, ensure_ascii=False))


def cmd_mutation_confirm(args) -> int:
    """Record the host connector result; only success resolves recovery."""
    provider = _external_mutation_provider(args)
    if not hasattr(provider, "confirm"):
        raise CapabilityError("provider %r cannot confirm host mutations" % provider.name)
    plan = providers.PendingMutation(
        operation=args.operation,
        register=provider.source,
        item_id=args.item,
        idempotency_key=args.idempotency_key,
        recovery_id=args.recovery_id,
    )
    outcome = provider.confirm(
        plan, succeeded=args.succeeded, actual_revision=args.actual_revision,
        detail=_json_object(args.detail_json, "--detail-json"))
    return _emit(outcome, args.as_json,
                 lambda: json.dumps(outcome, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    # The global flags are attached to every subparser via `parents` so they work
    # both before and after the subcommand. They default to SUPPRESS so a
    # subparser that does NOT see the flag leaves the value the top-level parser
    # already captured — the usual `parents` trap is the subparser silently
    # re-defaulting `--root` back to the working directory.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS)
    common.add_argument("--actor", default=argparse.SUPPRESS,
                        help="the ceremony asking (gates writability)")
    common.add_argument("--json", dest="as_json", action="store_true",
                        default=argparse.SUPPRESS)

    # NOTE: do not call parser.set_defaults() for these — set_defaults mutates the
    # shared Action objects `parents` handed to every subparser, which would turn
    # their SUPPRESS defaults back into concrete ones and reintroduce the clobber.
    # Defaults are applied in main() instead.
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0], parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("roles", parents=[common]).set_defaults(func=cmd_roles)

    resolve = sub.add_parser("resolve", parents=[common])
    resolve.add_argument("role")
    resolve.set_defaults(func=cmd_resolve)

    provider = sub.add_parser("provider", parents=[common])
    provider.add_argument("--role", default="workRegister")
    provider.set_defaults(func=cmd_provider)

    items = sub.add_parser("items", parents=[common])
    items.add_argument("--all", action="store_true", help="include terminal items")
    items.set_defaults(func=cmd_items)

    sub.add_parser("next", parents=[common]).set_defaults(func=cmd_next)
    sub.add_parser("kpis", parents=[common]).set_defaults(func=cmd_kpis)

    closeout = sub.add_parser("closeout", parents=[common])
    closeout.add_argument("--item", required=True)
    closeout.add_argument("--date", required=True)
    closeout.add_argument("--lesson-prefix", default="SRL")
    closeout.add_argument("--prepare", action="store_true",
                          help="create the close-out directory (a write; off by default)")
    closeout.set_defaults(func=cmd_closeout)

    snapshot = sub.add_parser("snapshot", parents=[common])
    snapshot.add_argument("--out", default="Virtuoso/work-register.snapshot.json")
    snapshot.set_defaults(func=cmd_snapshot)

    repo = sub.add_parser("repo", parents=[common])
    repo.add_argument("--expect", default="",
                      help="comma-separated paths this work is expected to touch")
    repo.set_defaults(func=cmd_repo)

    sub.add_parser("deps", parents=[common]).set_defaults(func=cmd_deps)
    sub.add_parser("protected", parents=[common]).set_defaults(func=cmd_protected)
    sub.add_parser("recovery", parents=[common]).set_defaults(func=cmd_recovery)

    mutation_plan = sub.add_parser("mutation-plan", parents=[common])
    mutation_plan.add_argument(
        "--operation", required=True,
        choices=("set-status", "store-spec-link", "record-completion"))
    mutation_plan.add_argument("--item", required=True)
    mutation_plan.add_argument("--fields-json", required=True)
    mutation_plan.add_argument("--revision", default="")
    mutation_plan.add_argument("--idempotency-key", default="")
    mutation_plan.set_defaults(func=cmd_mutation_plan)

    mutation_confirm = sub.add_parser("mutation-confirm", parents=[common])
    mutation_confirm.add_argument(
        "--operation", required=True,
        choices=("set-status", "store-spec-link", "record-completion"))
    mutation_confirm.add_argument("--item", required=True)
    mutation_confirm.add_argument("--idempotency-key", required=True)
    mutation_confirm.add_argument("--recovery-id", required=True)
    mutation_confirm.add_argument("--actual-revision", default="")
    mutation_confirm.add_argument("--detail-json", default="{}")
    confirmation = mutation_confirm.add_mutually_exclusive_group(required=True)
    confirmation.add_argument(
        "--succeeded", dest="succeeded", action="store_true",
        help="the host connector mutation succeeded")
    confirmation.add_argument(
        "--failed", dest="succeeded", action="store_false",
        help="the host connector mutation failed; leave recovery outstanding")
    mutation_confirm.set_defaults(func=cmd_mutation_confirm)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # SUPPRESS leaves the attribute absent when the flag was not given anywhere.
    args.root = os.path.abspath(getattr(args, "root", None) or os.getcwd())
    args.actor = getattr(args, "actor", "")
    args.as_json = getattr(args, "as_json", False)
    try:
        return args.func(args)
    except GovernanceError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_UNANSWERABLE
    except (FileNotFoundError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_UNANSWERABLE


if __name__ == "__main__":
    sys.exit(main())
