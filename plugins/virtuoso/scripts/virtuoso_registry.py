#!/usr/bin/env python3
"""Registry and work-register operations for ceremonies.

Query subcommands create nothing and heal nothing as a side effect (item 86).
The commands that write say so explicitly: `snapshot`, `closeout --prepare`,
`create-item` (appends a new item to a LOCAL register), `mutation-plan` (opens
durable recovery before a host connector write), and `mutation-confirm` (records
the connector result and resolves recovery only on success).

Subcommands:
  roles                     list every registered role and how it resolves
  resolve <role>            print one role's absolute path or external identifier
  overlays [--for PATH]     the project's overlays for shipped skills, agents, references
           [--scaffold]     print an overlay skeleton to stdout (writes nothing)
  policy-set <key> --value-json V   set one policy value (preview; --apply writes)
  provider [--role R]       describe the provider serving a role, and its capabilities
  items [--all]             list work items from the work register
  next                      the next eligible work item
  kpis                      derived metrics, each with its provenance, and pace
                            against every declared deadline
  closeout --item ID --date D   resolve close-out artifact paths (read-only)
  lessons [--open]          the registered lessons and their status (read-only)
          --check PATH      check a spec's Lessons applied (rubric U9), or with
                            --closeout a close-out's Lessons section
          --hygiene         what to merge, retire, tidy or repair (governance-sweep)
          --candidates      lessons that have earned promotion or revision
          --record-status ID --status S   append a status record (--apply writes)
  repo [--expect PATHS]     read-only repository state and readiness finding
  deps                      check the project's declared runtime dependencies
  protected                 hash every protected file (immutable-hash verification)
  snapshot --out PATH       capture a timestamped snapshot of the work register
  recovery                  list unresolved partial-failure recovery records
  record-completion         append the terminal record and close the item in a LOCAL
                            register, in order, then verify (preview; --apply writes)
  create-item               bring a new item into a LOCAL register (a write)
  mutation-plan             emit a revision-aware host connector instruction
                            (operations: set-status, store-spec-link,
                            record-completion, create-item)
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
    backup as backup_mod, learning as learning_mod, lessons as lessons_mod,
    overlays as overlays_mod,
    policy as policy_mod, providers,
    registry as registry_mod, repair as repair_mod, schema, textio,
)
from tools.governance.errors import CapabilityError, GovernanceError, RoleNotRegistered  # noqa: E402
from tools.governance import dependencies, integrity, repostate  # noqa: E402
from tools.governance.providers import (  # noqa: E402
    base as provider_base, kpi, ledger as ledger_mod, recovery, snapshot_provider,
)

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXIT_OK = 0
EXIT_UNANSWERABLE = 3

#: The planned mutations an external register accepts through the handshake.
MUTATION_OPERATIONS = ("set-status", "store-spec-link", "record-completion", "create-item")


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


def _write_bytes_to_stdout(content: str) -> None:
    """Write ``content`` to stdout as UTF-8, whatever the console's encoding is.

    The documented workflow is ``... --scaffold --for <path> > <path>``, so this
    stdout is a file the plugin will later read back. A Windows console defaults
    to a legacy code page, and the text layer would then encode the scaffold's
    own punctuation into bytes no reader can decode -- the operator saves a
    correct overlay and is told the section does not exist.
    """
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:              # a replaced stdout (capture); text is all there is
        sys.stdout.write(content)
        return
    sys.stdout.flush()
    buffer.write(content.encode("utf-8"))
    buffer.flush()


def cmd_overlays(args) -> int:
    """Resolve the project's overlays for shipped skills and agents. Read-only.

    Always answers. An unregistered role, an absent directory, and no matching file
    are three different messages and all of them are a result — printing nothing
    would be indistinguishable from "everything is applied".
    """
    reg = _load(args.root)
    status = overlays_mod.audit(reg, PLUGIN_ROOT)

    if args.scaffold:
        if args.for_path:
            mirror = overlays_mod.mirror_path(args.for_path)
            # Prefer the seeded skeleton when the audit already knows what this file
            # is missing, so --for and the full plan never disagree about one path.
            seeded = dict(overlays_mod.scaffold_plan(reg, status))
            content = (seeded.get(mirror) or overlays_mod.scaffold(reg, mirror)) if mirror else ""
            if not content:
                print("--for %r is not a shipped file that may carry an overlay"
                      % args.for_path, file=sys.stderr)
                return EXIT_UNANSWERABLE
            # Exactly the file's content, so `... > <path>` is the whole write.
            _write_bytes_to_stdout(content)
            return EXIT_OK
        plan = overlays_mod.scaffold_plan(reg, status)
        if not plan:
            print("nothing to scaffold (%s)" % status.line())
            print("Every declared identifier already has a body. Use --for <path> to "
                  "scaffold an overlay for a specific shipped file.")
            return EXIT_OK
        root = status.root or "<overlays>"
        for mirror, content in plan:
            # Named, not written: re-run with --for <mirror> and redirect.
            print("# ==== %s ====" % os.path.join(root, *mirror.split("/")))
            _write_bytes_to_stdout(content)
            print()
        return EXIT_OK

    if args.for_path:
        mirror = overlays_mod.mirror_path(args.for_path)
        if not mirror:
            print("--for %r is not a usable mirror path: give a path relative to the plugin "
                  "root, such as skills/<skill>/SKILL.md or agents/<Agent>.md"
                  % args.for_path, file=sys.stderr)
            return EXIT_UNANSWERABLE
        overlay = overlays_mod.find(reg, PLUGIN_ROOT, mirror)
        payload = {"mirror": mirror, "overlay": overlay.as_dict() if overlay else None,
                   "safetyFloor": list(overlays_mod.SAFETY_FLOOR), "line": status.line()}
        if args.as_json:
            return _emit(payload, True)
        if overlay is None:
            print("no overlay for %s (%s)" % (mirror, status.line()))
            return EXIT_OK
        print(overlay.path)
        return EXIT_OK

    if args.as_json:
        return _emit(status.as_dict(), True)

    print(status.line())
    for overlay in status.overlays:
        print("  %-10s %s" % ("applies" if overlay.mirrors_shipped_file else "inert",
                              overlay.mirror))
    for finding in status.findings:
        print("  [%s] %s" % (finding.severity, finding.message))
    if status.applied:
        print("\nan overlay may not loosen these shared-contract rules: %s"
              % ", ".join(overlays_mod.SAFETY_FLOOR))
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
        spec_ready=_spec_ready(reg, project_policy),
    )
    metrics.pace, metrics.invalid_deadlines = providers.pace_for(reg, snap)
    metrics.learning, metrics.learning_provenance = _learning_metrics(reg, project_policy)
    return _emit(metrics.as_dict(), args.as_json, metrics.render)


def _spec_ready(reg, project_policy):
    """A judge of whether an item's specification passes U9, for the buffer figure —
    or the reason no judge is possible here."""
    prefix = project_policy.lesson_prefix
    try:
        lessons_path = reg.resolve("lessons")
    except RoleNotRegistered:
        return "a registered lessons role (U9 checks specifications against it)"
    recorded = lessons_mod.parse(textio.read_text(lessons_path) or "", prefix)
    storage = str(project_policy.get("roadmap.specStorage", "inline"))
    if storage == "external":
        return "specifications in a readable store (policy.roadmap.specStorage is external)"
    if storage == "inline":
        try:
            roadmap = textio.read_text(reg.resolve("roadmap")) or ""
        except RoleNotRegistered:
            return "a registered roadmap holding the specifications"

        def judge(item):
            result = lessons_mod.check(roadmap, recorded, prefix, item=item.id)
            if any(f["code"] == lessons_mod.ITEM_MISSING for f in result.findings):
                return None
            return result.passed
        return judge

    def judge_file(item):
        link = (item.spec_link or "").strip()
        if not link or "://" in link:
            return None
        text = textio.read_text(link if os.path.isabs(link) else os.path.join(reg.root, link))
        return None if text is None else lessons_mod.check(text, recorded, prefix).passed
    return judge_file


def _learning_metrics(reg, project_policy):
    """The loop-health figures and where they came from. No lessons role: each
    figure is not computable, naming the role."""
    prefix = project_policy.lesson_prefix
    try:
        path = reg.resolve("lessons")
    except RoleNotRegistered:
        from tools.governance.providers.kpi import Metric
        return ([Metric(name, computable=False, missing_inputs=["a registered lessons role"])
                 for name in LEARNING_METRICS], {})
    recorded = lessons_mod.parse(textio.read_text(path) or "", prefix)
    outcomes, closeouts = _lesson_outcomes(reg, prefix)
    figures = learning_mod.metrics(recorded, outcomes)
    provenance = {"lessons": os.path.relpath(path, reg.root).replace(os.sep, "/"),
                  "closeOuts": closeouts, "closeOutsRead": outcomes.closeouts,
                  "asOf": _today().isoformat()}
    figures.append(_effort_calibration(reg, provenance))
    return figures, provenance


def _effort_calibration(reg, provenance):
    try:
        book = providers.terminal_ledger(reg)
    except GovernanceError:
        return kpi.Metric("effort-calibration", computable=False,
                          missing_inputs=["a local terminal ledger"])
    provenance["ledger"] = os.path.relpath(book.path, reg.root).replace(os.sep, "/")
    return learning_mod.effort_calibration(book.records())


LEARNING_METRICS = ("live-count", "lesson-yield", "held-rate", "promotion-rate",
                    "time-to-apply", "repeated-trap-rate")


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
        "nextLessonId": _next_lesson_id(lessons, args.lesson_prefix
                                        or project_policy.lesson_prefix),
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


EXIT_CHECK_FAILED = 1


def _today():
    import datetime as _dt
    return _dt.date.today()


def _lesson_outcomes(reg, prefix):
    """``(Outcomes, closeOuts path or "")`` — every close-out report the registry
    holds, read for what it says about lessons. No closeOuts role: no outcomes."""
    try:
        directory = reg.resolve("closeOuts")
    except RoleNotRegistered:
        return learning_mod.Outcomes(), ""
    return (learning_mod.load_outcomes(directory, prefix),
            os.path.relpath(directory, reg.root).replace(os.sep, "/"))


def _record_lesson_status(args, reg, path, source, recorded, text) -> int:
    """Append one status record — the only way a lesson is promoted, retired or
    superseded. Previews unless ``--apply``; refuses an actor the role does not
    allow, an unknown or closed lesson, and a status that says nothing."""
    actor = getattr(args, "actor", "") or ""
    if not actor:
        raise GovernanceError("--record-status needs --actor: the ceremony recording it")
    if not reg.writable("lessons", actor):
        raise GovernanceError("%s may not write the lessons role (allowedWriters in %s)"
                              % (actor, schema.MANIFEST_RELPATH))
    problem = learning_mod.status_problem(recorded, args.record_status, args.status)
    if problem:
        raise GovernanceError(problem)
    record = learning_mod.status_record(args.record_status, args.status,
                                        args.item or actor, args.date or _today().isoformat())
    if not args.apply:
        print("preview — append to %s (run again with --apply):\n\n%s" % (source, record))
        return EXIT_OK
    raw = textio.read_bytes(path) or b""
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        raise GovernanceError("%s is not UTF-8 text; convert it before appending" % source)
    eol = "\r\n" if b"\r\n" in raw else "\n"
    lead = "" if not raw or raw.endswith(b"\n") else eol
    with open(path, "ab") as handle:
        handle.write((lead + eol + record.replace("\n", eol)).encode("utf-8"))
    after = {l.id: l for l in lessons_mod.parse(textio.read_text(path) or "",
                                                policy_mod.load(reg.policy).lesson_prefix)}
    recorded_now = after.get(args.record_status)
    if recorded_now is None or recorded_now.status != args.status.strip():
        raise GovernanceError("the record was appended but does not read back as the "
                              "current status of %s; inspect %s" % (args.record_status, source))
    print("recorded %s: %s (%s)" % (args.record_status, recorded_now.status, source))
    return EXIT_OK


def cmd_lessons(args) -> int:
    """The learning loop's read side. Lists the registered lessons with their current
    status, or checks a specification (rubric U9) or a close-out against them.

    Read-only. Exit 0 when the listing or the check passes, 1 when a check fails,
    3 when there is no lessons role to read.
    """
    reg = _load(args.root)
    project_policy = policy_mod.load(reg.policy)
    prefix = project_policy.lesson_prefix
    try:
        path = reg.resolve("lessons")
    except RoleNotRegistered:
        raise GovernanceError(
            "no `lessons` role is registered, so there is nowhere a lesson is recorded and "
            "nothing a specification can apply. Register one in %s (virtuoso-init "
            "creates it)." % schema.MANIFEST_RELPATH)
    text = textio.read_text(path)
    source = os.path.relpath(path, args.root).replace(os.sep, "/")
    notes = [] if text is not None else [
        "the registered lessons document %s does not exist yet" % source]
    recorded = lessons_mod.parse(text or "", prefix)

    if args.check:
        target = args.check if os.path.isabs(args.check) else os.path.join(args.root, args.check)
        document = textio.read_text(target)
        if document is None:
            raise GovernanceError("%s cannot be read" % args.check)
        result = lessons_mod.check(document, recorded, prefix, item=args.item,
                                   closeout=args.closeout,
                                   standing_rules=project_policy.get("standingRules.ids") or ())
        payload = dict(result.as_dict(), document=args.check, lessons=source, prefix=prefix,
                       notes=notes)
        if args.as_json:
            _emit(payload, True)
        else:
            what = ("close-out lessons" if args.closeout
                    else "U9 lessons applied%s" % (" (%s)" % args.item if args.item else ""))
            print("%s: %s" % (what, "PASS" if result.passed else "FAIL"))
            if result.cited:
                print("  cited: %s" % ", ".join(result.cited))
            for finding in result.findings:
                print("  [%s] %s: %s" % (finding["severity"], finding["code"],
                                         finding["message"]))
            for note in notes:
                print("  note: %s" % note)
            print("  lessons: %s (prefix %s)" % (source, prefix))
        return EXIT_OK if result.passed else EXIT_CHECK_FAILED

    if args.record_status:
        return _record_lesson_status(args, reg, path, source, recorded, text)
    if args.hygiene or args.candidates:
        outcomes, closeouts = _lesson_outcomes(reg, prefix)
        if args.hygiene:
            report = learning_mod.hygiene(
                recorded, outcomes, today=_today(),
                stale_after_days=int(project_policy.get("lessons.staleAfterDays", 180) or 0))
            payload = dict(report, source=source, closeOuts=closeouts,
                           closeOutsRead=outcomes.closeouts, notes=notes)
            if args.as_json:
                return _emit(payload, True)
            print("lessons hygiene: %s (%d lessons, %d close-outs read)"
                  % (source, len(recorded), outcomes.closeouts))
            for group in report["duplicates"]:
                print("  merge    keep %s; supersede %s — %s" % (
                    group["keep"], ", ".join(group["supersede"]), group["why"]))
            for entry in report["stale"]:
                print("  retire   %s — recorded %s (%d days), never applied in a close-out"
                      % (entry["id"], entry["recorded"], entry["ageDays"]))
            for entry in report["incomplete"]:
                print("  tidy     %s — missing %s" % (entry["id"], ", ".join(entry["missing"])))
            for entry in report["malformed"]:
                print("  repair   %s — %s" % (entry["id"], entry["why"]))
            if not any(report[k] for k in ("duplicates", "stale", "incomplete", "malformed")):
                print("  clean — nothing to merge, retire, tidy or repair")
            return EXIT_OK
        found = learning_mod.candidates(recorded, outcomes)
        payload = {"candidates": found, "source": source, "closeOuts": closeouts,
                   "closeOutsRead": outcomes.closeouts, "notes": notes}
        if args.as_json:
            return _emit(payload, True)
        print("promotion candidates: %d (%d close-outs read)" % (len(found), outcomes.closeouts))
        for entry in found:
            print("  %-9s %-16s %s" % (entry["id"], entry["action"], entry["why"]))
        return EXIT_OK

    shown = [lesson for lesson in recorded if lesson.live or not args.open]
    live = sum(1 for lesson in recorded if lesson.live)
    payload = {"lessons": [lesson.as_dict() for lesson in shown], "source": source,
               "prefix": prefix, "live": live, "closed": len(recorded) - live, "notes": notes}
    if args.as_json:
        return _emit(payload, True)
    print("%d lesson(s) in %s: %d live, %d closed%s"
          % (len(recorded), source, live, len(recorded) - live,
             " (showing live only)" if args.open else ""))
    for lesson in shown:
        print("  %-9s %-6s %s" % (lesson.id, "live" if lesson.live else "closed", lesson.title))
        if lesson.applies_to:
            print("            applies to: %s" % lesson.applies_to)
        if not lesson.live or lesson.status != lessons_mod.DEFAULT_STATUS:
            print("            status: %s" % lesson.status)
    for note in notes:
        print("note: %s" % note)
    return EXIT_OK


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


CROSSING_STEPS = ("append-terminal-record", "close-in-register", "verify-results")


def cmd_record_completion(args) -> int:
    """The close-out crossing's two record-keeping writes, in order, for a local
    register and ledger: append the terminal record, then close the item in the
    live register — then verify both from their sources.

    Previews without ``--apply``. Idempotent: a record already in the ledger for this
    item, or an item already completed, is reported and not repeated. A register
    write that fails after the ledger append leaves a recovery record naming the
    steps that remain. An external register or ledger is refused: those go through
    the mutation handshake the host's connector executes.
    """
    actor = getattr(args, "actor", "") or ""
    if not actor:
        raise CapabilityError("record-completion needs --actor: the ceremony closing the item")
    reg = _load(args.root)
    selection = providers.work_register(reg, actor=actor)
    provider = selection.provider
    if hasattr(provider, "plan_mutation"):
        raise CapabilityError(
            "the live register %r is external: close the item with `mutation-plan "
            "--operation record-completion`, the host's connector, and `mutation-confirm`"
            % provider.name)
    book = providers.terminal_ledger(reg)          # refuses an external ledger by name
    item = provider.get(args.item)
    if item is None:
        raise GovernanceError("%s is not in the live register (%s)" % (args.item, provider.source))
    prior = [r for r in book.records() if r.item_id == args.item and not r.corrects]
    record = ledger_mod.LedgerRecord(record_id=book.next_record_id(), item_id=args.item,
                                     completed=args.date, result=args.result,
                                     evidence=args.evidence, effort_estimate=args.estimate,
                                     effort_actual=args.actual)
    completed_already = item.status == provider_base.COMPLETED
    plan = {"item": args.item, "actor": actor, "register": provider.source,
            "ledger": os.path.relpath(book.path, reg.root).replace(os.sep, "/"),
            "ledgerRecord": prior[0].as_dict() if prior else record.as_dict(),
            "appendRecord": not prior, "closeInRegister": not completed_already,
            "revision": args.revision or item.revision}
    if not args.apply:
        return _emit(dict(plan, applied=False), args.as_json, lambda: "\n".join([
            "preview — record-completion %s (run again with --apply):" % args.item,
            "  1. terminal ledger %s: %s" % (plan["ledger"], (
                "append %s (%s, %s, %s)" % (record.record_id, args.date, args.result,
                                             args.evidence))
                if not prior else "already holds %s — nothing to append" % prior[0].record_id),
            "  2. live register %s: %s" % (plan["register"], (
                "record completion at revision %s" % plan["revision"])
                if not completed_already else "item already completed — nothing to change"),
            "  3. verify both from their sources"]))

    done: list[str] = []
    if not prior:
        book.append(record, actor=actor)
    done.append("append-terminal-record")
    if not completed_already:
        try:
            provider.record_completion(args.item, completed=args.date, evidence=args.evidence,
                                       revision=args.revision or item.revision)
        except GovernanceError as exc:
            opened = recovery.open_record(
                args.root, operation="record-completion", item_id=args.item,
                completed_steps=list(done),
                remaining_steps=list(CROSSING_STEPS[len(done):]),
                detail={"register": provider.source, "ledger": plan["ledger"],
                        "error": str(exc)})
            raise GovernanceError(
                "the terminal record is appended but the register refused the completion "
                "(%s). Recovery record %s names what remains; resolve it before re-running."
                % (exc, opened.id))
    done.append("close-in-register")
    after = provider.get(args.item)
    in_ledger = [r for r in book.records() if r.item_id == args.item and not r.corrects]
    if not in_ledger or after is None or after.status != provider_base.COMPLETED:
        opened = recovery.open_record(
            args.root, operation="record-completion", item_id=args.item,
            completed_steps=list(done), remaining_steps=["verify-results"],
            detail={"register": provider.source, "ledger": plan["ledger"]})
        raise GovernanceError("the writes did not read back (ledger: %s, register status: %s); "
                              "recovery record %s" % (bool(in_ledger),
                                                      after.status if after else "missing",
                                                      opened.id))
    done.append("verify-results")
    result = dict(plan, applied=True, steps=done, ledgerRecord=in_ledger[0].as_dict())
    return _emit(result, args.as_json, lambda: "recorded %s: ledger %s, register %s (%s)"
                 % (args.item, in_ledger[0].record_id, after.status, ", ".join(done)))


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
        detail=_json_object(args.detail_json, "--detail-json"),
        provider_item_id=args.provider_id)
    return _emit(outcome, args.as_json,
                 lambda: json.dumps(outcome, indent=2, ensure_ascii=False))


def cmd_create_item(args) -> int:
    """Bring a new item into a LOCAL work register. This is a write.

    An external register is never created into from here: it goes through the
    host handshake (`mutation-plan --operation create-item`, execute with the
    host's connector, `mutation-confirm`), so the refusal names that path.
    """
    if not args.actor:
        raise CapabilityError("an explicit ceremony actor is required to create a work item")
    selection = providers.work_register(_load(args.root), actor=args.actor)
    provider = selection.provider
    fields = _json_object(args.fields_json, "--fields-json")
    fields.setdefault("id", args.item)
    if str(fields.get("id") or "").strip() != args.item:
        raise CapabilityError("--item %r and fields.id %r disagree" % (args.item, fields.get("id")))
    if hasattr(provider, "plan_mutation"):
        raise CapabilityError(
            "external register %s is created into through the host handshake: run "
            "`mutation-plan --operation create-item --item %s --fields-json ...`, execute the "
            "instruction with the host's connector, then `mutation-confirm`."
            % (provider.source, args.item),
            detail={"register": provider.source, "operation": "create-item"})
    provider.require(provider_base.CREATE_ITEM)
    existed = provider.get(args.item) is not None
    item = provider.create_item(fields)
    payload = {"created": not existed, "item": item.as_dict(),
               "register": provider.source, "provider": provider.name}
    if args.as_json:
        return _emit(payload, True)
    print("%s %s in %s" % ("created" if payload["created"] else "already present:",
                           item.id, provider.source))
    print("  title:         %s" % (item.title or "(untitled)"))
    print("  status:        %s (%s)" % (item.status, item.raw_status or "—"))
    print("  specification: %s" % (item.written_status or "unknown"))
    return EXIT_OK


def _json_value(raw: str, label: str):
    """Any JSON value. A policy value may be a list, string, number, or object, so
    this deliberately does not require an object the way ``_json_object`` does."""
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise GovernanceError("%s must be valid JSON: %s" % (label, exc)) from exc


#: A key the raw policy block does not carry at all, as distinct from one set to null.
_ABSENT = object()


def _raw_policy_value(raw: dict | None, path: str):
    cursor = raw or {}
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return _ABSENT
        cursor = cursor[part]
    return cursor


def cmd_policy_set(args) -> int:
    """Set one policy value in the manifest. Previews by default; ``--apply`` writes.

    Policy is the machine-readable half of a project rule. Until now the only way
    to set one was to hand-edit the manifest — which every ceremony is forbidden to
    do, and which skips validation, the backup, and the rollback. This routes it
    through the same transaction repair uses, so the ceremony that documents a
    previewed, backed-up write actually performs one.
    """
    if not args.actor:
        raise CapabilityError(
            "an explicit ceremony actor is required to set a policy value, for example "
            "--actor project-profile")
    reg = _load(args.root)
    if [f for f in reg.findings if f.severity == "error"]:
        raise GovernanceError(
            "this registry reports errors; run `virtuoso_preflight.py --mode repair` first. "
            "Writing policy onto an invalid registry buries the invalidity under a change "
            "that looks successful.")
    if not policy_mod.is_documented(args.key):
        raise GovernanceError(
            "policy.%s is not a documented key, so no ceremony reads it. Project-owned "
            "configuration belongs under an `x-` extension key." % args.key)

    value = _json_value(args.value_json, "--value-json")
    before = policy_mod.load(reg.policy).get(args.key)
    # `null` on a project-named entry (a deadline) withdraws it. Anywhere else it
    # is a value like any other, and the type gate judges it.
    withdrawing = value is None and policy_mod.open_child(args.key)
    if withdrawing:
        if before is None:
            raise GovernanceError("policy.%s is not declared, so there is nothing to withdraw. "
                                  "Nothing was written." % args.key)
        candidate = policy_mod.withdraw(reg.policy, args.key)
    else:
        mismatch = policy_mod.type_problem(args.key, value)
        if mismatch:
            raise GovernanceError("%s Nothing was written." % mismatch)
        candidate = policy_mod.assign(reg.policy, args.key, value)
    problems = policy_mod.load(candidate).validate()
    if problems:
        raise GovernanceError("the resulting policy is not valid; nothing was written:\n  %s"
                              % "\n  ".join(problems))

    reg.policy = candidate
    plan = repair_mod.policy_plan(reg, args.key, before, value, withdraw=withdrawing)

    if not args.apply:
        payload = {"key": args.key, "current": before, "proposed": value,
                   "applied": False, "plan": plan.as_dict()}
        if args.as_json:
            return _emit(payload, True)
        print(plan.render())
        print("Nothing was written. Re-run with --apply to write it.")
        return EXIT_OK

    written, backup_set = repair_mod.apply_plan(reg, plan, label="policy-set",
                                                actor=args.actor)
    # Read the value back from disk. apply_plan re-validates what it wrote, but
    # "valid" is not "what was asked for", and a ceremony that is about to cite
    # this value — a deadline most of all — should know it landed. The raw block
    # is compared, not the merged policy: merging would fold defaults into a
    # partial mapping and report a correct write as a wrong one.
    landed = _raw_policy_value(registry_mod.load(args.root).policy, args.key)
    expected = _ABSENT if withdrawing else value
    if landed != expected:
        raise GovernanceError(
            "policy.%s was written, but the manifest on disk now reads %s instead of %s. "
            "The previous manifest is backed up in %s."
            % (args.key, "(absent)" if landed is _ABSENT else json.dumps(landed, ensure_ascii=False),
               "(absent)" if expected is _ABSENT else json.dumps(expected, ensure_ascii=False),
               backup_set.relative_directory))
    backup_mod.prune(args.root, keep=int(
        policy_mod.load(reg.policy).get("sweep.backupRetention", 10)))
    payload = {"key": args.key, "current": before, "proposed": value, "applied": True,
               "withdrawn": withdrawing, "verified": True,
               "filesWritten": written, "backup": backup_set.as_dict()}
    if args.as_json:
        return _emit(payload, True)
    print("policy.%s %s" % (args.key, "withdrawn" if withdrawing else "set"))
    print("  was:    %s" % json.dumps(before, ensure_ascii=False))
    print("  now:    %s" % ("(withdrawn)" if withdrawing
                            else json.dumps(value, ensure_ascii=False)))
    print("  wrote:  %s" % (", ".join(written) or "(already that value)"))
    print("  backup: %s" % backup_set.relative_directory)
    print("  verified: read back from disk")
    return EXIT_OK


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

    overlays = sub.add_parser("overlays", parents=[common])
    overlays.add_argument("--for", dest="for_path", default="",
                          help="a shipped file's plugin-relative path, e.g. agents/<Agent>.md")
    overlays.add_argument("--scaffold", action="store_true",
                          help="print an overlay skeleton (writes nothing; redirect it "
                               "yourself). With --for, prints that one file's content.")
    overlays.set_defaults(func=cmd_overlays)

    policy_set = sub.add_parser("policy-set", parents=[common])
    policy_set.add_argument("key", help="dotted policy key, e.g. rubric.extensions")
    policy_set.add_argument("--value-json", required=True,
                            help='the new value as JSON, e.g. \'["db-migration"]\'')
    policy_set.add_argument("--apply", action="store_true",
                            help="write it; without this the change is previewed only")
    policy_set.set_defaults(func=cmd_policy_set)

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
    closeout.add_argument("--lesson-prefix", default="",
                          help="override policy.lessons.idPrefix (default SRL)")
    closeout.add_argument("--prepare", action="store_true",
                          help="create the close-out directory (a write; off by default)")
    closeout.set_defaults(func=cmd_closeout)

    lessons = sub.add_parser("lessons", parents=[common])
    lessons.add_argument("--open", action="store_true", help="live lessons only")
    lessons.add_argument("--check", default="", metavar="PATH",
                         help="check a specification (rubric U9) or, with --closeout, a "
                              "close-out report")
    lessons.add_argument("--item", default="",
                         help="the item: locates an inline specification, or names the "
                              "item a close-out closes")
    lessons.add_argument("--closeout", action="store_true",
                         help="check a close-out's Lessons section instead of a "
                              "specification's Lessons applied")
    lessons.add_argument("--hygiene", action="store_true",
                         help="what to merge, retire, tidy or repair (governance-sweep)")
    lessons.add_argument("--candidates", action="store_true",
                         help="lessons that have earned promotion or revision (roadmap-review)")
    lessons.add_argument("--record-status", default="", metavar="ID",
                         help="append a status record for ID (with --status, --actor)")
    lessons.add_argument("--status", default="",
                         help="the status to record: Promoted -> <rule> / Retired — <why> / "
                              "Superseded -> <ID> / Observation")
    lessons.add_argument("--date", default="", help="the record's date (default: today)")
    lessons.add_argument("--apply", action="store_true",
                         help="append the record (without it, --record-status previews)")
    lessons.set_defaults(func=cmd_lessons)

    completion = sub.add_parser("record-completion", parents=[common])
    completion.add_argument("--item", required=True)
    completion.add_argument("--date", required=True, help="YYYY-MM-DD the item completed")
    completion.add_argument("--result", required=True, help="the ledger's result word")
    completion.add_argument("--evidence", default="", help="the close-out artifact")
    completion.add_argument("--estimate", default="",
                            help="the effort the specification estimated, as a duration (90m, 1.5h)")
    completion.add_argument("--actual", default="",
                            help="the effort it took, as a duration (the close-out's runtime)")
    completion.add_argument("--revision", default="",
                            help="the revision read in Wave 1 (default: the current one)")
    completion.add_argument("--apply", action="store_true",
                            help="perform the writes (without it, previews)")
    completion.set_defaults(func=cmd_record_completion)

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

    create_item = sub.add_parser("create-item", parents=[common])
    create_item.add_argument("--item", required=True)
    create_item.add_argument("--fields-json", required=True,
                             help="canonical field names; extra keys are project columns")
    create_item.set_defaults(func=cmd_create_item)

    mutation_plan = sub.add_parser("mutation-plan", parents=[common])
    mutation_plan.add_argument("--operation", required=True, choices=MUTATION_OPERATIONS)
    mutation_plan.add_argument("--item", required=True)
    mutation_plan.add_argument("--fields-json", required=True)
    mutation_plan.add_argument("--revision", default="")
    mutation_plan.add_argument("--idempotency-key", default="")
    mutation_plan.set_defaults(func=cmd_mutation_plan)

    mutation_confirm = sub.add_parser("mutation-confirm", parents=[common])
    mutation_confirm.add_argument("--operation", required=True, choices=MUTATION_OPERATIONS)
    mutation_confirm.add_argument("--item", required=True)
    mutation_confirm.add_argument("--idempotency-key", required=True)
    mutation_confirm.add_argument("--recovery-id", required=True)
    mutation_confirm.add_argument("--actual-revision", default="")
    mutation_confirm.add_argument("--provider-id", default="",
                                  help="the identifier the external system assigned (creations)")
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
