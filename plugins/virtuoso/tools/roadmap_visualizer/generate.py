from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.governance import (  # noqa: E402
    policy as policy_mod, providers, registry as registry_mod, repair, schema, textio,
)
from tools.governance.errors import GovernanceError, RoleNotRegistered  # noqa: E402
from tools.governance.providers import base, kpi, mapping as mapping_mod  # noqa: E402

from . import board as board_mod, comments as comments_mod  # noqa: E402
from . import completed as completed_mod, dashboard as dashboard_mod, freshness  # noqa: E402
from .board_render import render_board  # noqa: E402
from .health import summarize_health  # noqa: E402
from .model import RoadmapSnapshot, to_jsonable  # noqa: E402
from .roadmap import parse_roadmap  # noqa: E402
from .workspace import load_workspace  # noqa: E402


@dataclass
class Reading:
    """One read of the workspace. The board is built from it."""

    context: object
    reg: object
    policy: object
    snapshot: base.Snapshot
    roadmap: RoadmapSnapshot
    metrics: object
    health: object


def read(root: Path | str) -> Reading:
    context, selection = load_workspace(root)
    reg = registry_mod.load(str(context.root))
    project_policy = policy_mod.load(reg.policy)

    snapshot = selection.provider.snapshot()
    roadmap = (parse_roadmap(context.roadmap) if context.roadmap and context.roadmap.is_file()
               else RoadmapSnapshot(path=None, active_codes=[], completed_codes=[],
                                    full_spec_codes=[], headings={}, frontmatter={}))
    metrics = kpi.compute(
        snapshot,
        effort_scale=project_policy.get("roadmap.effortScale"),
        dispatch_buffer=project_policy.dispatch_buffer,
    )
    metrics.pace, metrics.invalid_deadlines = providers.pace_for(reg, snapshot)
    health = summarize_health(roadmap, snapshot, buffer_target=project_policy.dispatch_buffer,
                              pace=[report.as_dict() for report in metrics.pace])
    return Reading(context, reg, project_policy, snapshot, roadmap, metrics, health)


# --- the board ---------------------------------------------------------------------


def _registered_board(reg) -> Path | None:
    try:
        return Path(reg.resolve(board_mod.BOARD_ROLE))
    except RoleNotRegistered:
        return None


def _ledger(reg) -> tuple[list, bool, list[str]]:
    """``(records, a ledger is read, problems)`` — read-only, so no actor."""
    spec = reg.roles.get("terminalLedger")
    if spec is None:
        return [], False, ["no terminal ledger is registered: the Completed tab shows the "
                           "register's terminal items only"]
    if spec.is_external:
        return [], False, ["the terminal ledger is external (%s) and is not read here: the "
                           "Completed tab shows the register's terminal items only"
                           % spec.external]
    try:
        return providers.terminal_ledger(reg).records(), True, []
    except GovernanceError as exc:
        return [], False, ["the terminal ledger could not be read: %s" % exc]


def _comments(reg) -> tuple[dict, list[str], str]:
    spec = reg.roles.get(board_mod.COMMENTS_ROLE)
    if spec is None or spec.is_external or not spec.path:
        return {}, [], board_mod.COMMENTS_PATH
    found, problems = comments_mod.read_comments(reg.resolve(board_mod.COMMENTS_ROLE))
    return found, problems, spec.path


def build_board(reading: Reading, sources: list | None = None) -> dict:
    """The board's model. ``sources`` are the source files' times taken *before*
    ``reading`` was read: a file written during the read then reads as stale."""
    snapshot = reading.snapshot
    items = board_mod.ordered(snapshot.items)
    name_key = board_mod.name_column(items)
    register_policy = reading.policy.section("workRegister")
    statuses = mapping_mod.Mapping.from_policy(register_policy).statuses
    # A column's header is the register's own: the one the provider read, else the one
    # the project mapped (a snapshot import records no headers), else a generic label.
    configured = register_policy.get("fieldMappings")
    headers = dict({k: v for k, v in configured.items() if isinstance(v, str)}
                   if isinstance(configured, dict) else {}, **snapshot.headers)
    columns = board_mod.roadmap_columns(snapshot.fields, headers, items, name_key)
    rows = [dict(board_mod.row(item, name_key), facets=dashboard_mod.facets(item))
            for item in items]

    records, has_ledger, ledger_problems = _ledger(reading.reg)
    done, record_problems = completed_mod.completed_rows(items, records, statuses, name_key,
                                                         ledger=has_ledger)
    register = {item.id: item for item in items}
    for row in done:
        # A ledger-only row is sliced by what the ledger says it became.
        row["facets"] = dashboard_mod.facets(register.get(row["id"])
                                             or base.WorkItem(id=row["id"], status=row["result"]))
    comments, comment_problems, comments_file = _comments(reading.reg)
    return to_jsonable({
        "version": 1,
        "project": reading.context.root.name,
        "root": reading.context.root,
        "generatedAt": base.utc_now(),
        "provenance": snapshot.provenance(),
        "register": {"role": reading.context.work_register_role,
                     "authority": reading.context.work_register_authority,
                     "compatibilityAdapter": reading.context.compatibility_adapter},
        "sources": sources if sources is not None else freshness.source_times(reading.reg),
        "columns": columns,
        "rows": rows,
        "roadmap": {"groups": board_mod.roadmap_groups(items),
                    "live": [item.id for item in board_mod.live(items)]},
        "completed": {
            "columns": completed_mod.completed_columns(snapshot.fields, headers, done,
                                                       items, name_key),
            "rows": done,
            "groups": completed_mod.completed_groups(done),
            "problems": ledger_problems + record_problems,
        },
        "dashboard": {
            "tiles": dashboard_mod.tiles(reading.metrics.as_dict(), reading.health,
                                         snapshot.provenance()),
            "slicers": dashboard_mod.slicers(items, columns,
                                             dashboard_mod.policy_orders(reading.policy),
                                             headers),
        },
        "comments": comments,
        "commentsFile": comments_file,
        "commentProblems": comment_problems,
        "metrics": reading.metrics.as_dict(),
        "health": reading.health,
    })


def generate_board(root: Path | str, output: Path | str | None = None) -> Path:
    """Write the board to ``output``, or to its registered path."""
    sources = freshness.source_times(registry_mod.load(str(Path(root).resolve())))
    reading = read(root)
    if output is None:
        output_path = _registered_board(reading.reg)
        if output_path is None:
            raise RoleNotRegistered(
                "no `board` role is registered; run generate_board --create (roadmap-review "
                "D.7) to register it at %s" % board_mod.DEFAULT_PATH,
                detail={"role": board_mod.BOARD_ROLE})
    else:
        output_path = _output_path(reading.context, output)
    _refuse_protected_output(reading, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model = build_board(reading, sources)
    output_path.write_text(render_board(model), encoding="utf-8", newline="\n")
    for problem in model["commentProblems"]:
        print("warning: board comments: %s" % problem, file=sys.stderr)
    return output_path


def refresh_board(root: Path | str) -> str:
    """Regenerate a registered board after a write; never raises. Returns the line a
    ceremony prints, or ``""`` when the project has no board."""
    try:
        if _registered_board(registry_mod.load(str(Path(root).resolve()))) is None:
            return ""
        return "board regenerated: %s" % generate_board(root)
    except Exception as exc:  # noqa: BLE001 - an advisory output never fails its caller
        return "board: not regenerated (%s)" % exc


def ensure_board(root: Path | str) -> list[str]:
    """roadmap-review D.7: register a missing board role, generate a missing page (and
    ignore it in git), regenerate an existing one. Returns the lines for D.8."""
    root_path = Path(root).resolve()
    reg = registry_mod.load(str(root_path))
    lines = []
    added = []
    for name, path in ((board_mod.BOARD_ROLE, board_mod.DEFAULT_PATH),
                       (board_mod.COMMENTS_ROLE, board_mod.COMMENTS_PATH)):
        if name not in reg.roles:
            reg.roles[name] = schema.RoleSpec.from_manifest(
                name, dict(schema.default_role(name), path=path))
            added.append(name)
    if added:
        repair.write_registry(reg)
        lines.append("board roles registered: %s" % ", ".join(added))
        reg = registry_mod.load(str(root_path))
    page = Path(reg.resolve(board_mod.BOARD_ROLE))
    existed = page.is_file()
    written = generate_board(root_path)
    if added:
        repair.write_registry(registry_mod.load(str(root_path)))   # the readme sees the page
    lines.append("board %s: %s" % ("regenerated" if existed else "created", written))
    if not existed:
        lines.append(ignore_page(root_path, reg.roles[board_mod.BOARD_ROLE].path))
    return lines


def _git(root: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def ignore_page(root: Path, relative: str) -> str:
    """Add the page's path to the project's ``.gitignore`` once: it is a build output
    with absolute paths and a timestamp in it. Skipped outside git or when ignored."""
    line = "/" + relative.replace("\\", "/").lstrip("/")
    try:
        if _git(root, "rev-parse", "--is-inside-work-tree").returncode != 0:
            return "gitignore: skipped (not a git repository)"
        if _git(root, "check-ignore", "-q", relative).returncode == 0:
            return "gitignore: skipped (%s is already ignored)" % relative
    except OSError:
        return "gitignore: skipped (git is not available)"
    gitignore = root / ".gitignore"
    existing = textio.read_text(str(gitignore)) or ""
    if line in existing.splitlines():
        return "gitignore: skipped (%s is already listed)" % line
    newline = "\r\n" if "\r\n" in existing else "\n"          # keep the file's own endings
    separator = "" if not existing or existing.endswith("\n") else newline
    with open(gitignore, "a", encoding="utf-8", newline="") as handle:
        handle.write("%s%s%s" % (separator, line, newline))
    return "gitignore: added %s" % line


# --- shared ----------------------------------------------------------------------


def _output_path(context, output: Path | str) -> Path:
    output_path = Path(output)
    if output_path.is_absolute():
        return output_path
    return context.root / output_path


def _refuse_protected_output(reading: Reading, output_path: Path) -> None:
    """A generated page may never be written over a source: the manifest, the
    provider's source, or any registered file that is not itself generated."""
    context = reading.context
    protected = {context.manifest.resolve()}
    if context.roadmap is not None:
        protected.add(context.roadmap.resolve())
    source = context.provider.get("source", "")
    if source and os.path.isabs(source):
        protected.add(Path(source).resolve())
    for name, spec in reading.reg.roles.items():
        if spec.path and not spec.is_external and spec.mutability != "generated":
            protected.add(Path(reading.reg.resolve(name)).resolve())
    if output_path.resolve() in protected:
        raise ValueError("refusing to overwrite a registered governance document: %s"
                         % output_path)


def board_main(argv: list[str] | None = None) -> int:
    textio.utf8_stdio()
    parser = argparse.ArgumentParser(description="Generate the Virtuoso roadmap board.")
    parser.add_argument("--root", default=".",
                        help="project root carrying Virtuoso/workspace-layout.json")
    parser.add_argument("--create", action="store_true",
                        help="roadmap-review D.7: register the board role if it is missing, "
                             "create the page if it is absent, and ignore it in git")
    parser.add_argument("--output", default="",
                        help="write here instead of the registered path")
    args = parser.parse_args(argv)
    try:
        if args.create:
            for line in ensure_board(args.root):
                print(line)
        else:
            print("board written: %s" % generate_board(args.root, args.output or None))
    except (RoleNotRegistered, ValueError, FileNotFoundError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(board_main())
