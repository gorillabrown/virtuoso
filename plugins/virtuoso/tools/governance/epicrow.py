"""The epic row: one row on the belt for an epic run.

A combination charter (``epic`` Step 1b) runs several roadmap items as one run. Left as
they are, those items stay on the belt one by one, and ``next-dispatch`` would offer each
as a dispatch of its own while the epic runs them. The epic row is the fix: one row in the
work register that stands for the whole run, with its members nested under it.

* The **epic row** carries the packet's identifier (``EPIC-<SLUG>``), the charter's title,
  the earliest member's sequence slot, the prerequisites the members wait on outside the
  set, a written specification (the packet), and a link to the charter.
* Each **member** is nested under the epic row (its ``member_of`` field, the register's
  own parent / sub-item link). It stays a work item: its status still answers its
  dependants' prerequisites, and the close-out closes it with its own record. It is never
  the head of the belt; the epic row is.

A ``Path: epic`` item needs no epic row: its own row already stands for the run.

This module only plans. ``virtuoso_registry epic-row`` previews the plan, and with
``--apply`` writes it to a local register or emits the host handshake for an external one.
"""
from __future__ import annotations

import os

from . import combine as combine_mod
from .providers import base

KIND_ITEM = "item"
KIND_COMBINATION = "combination"


def find_charter(directory: str, packet: str) -> dict | None:
    """The charter whose packet directory or identifier is ``packet``."""
    wanted = (packet or "").strip().rstrip("/\\")
    wanted = os.path.basename(wanted) or wanted
    for charter in combine_mod.charters(directory):
        if wanted in (charter["packet"], charter["id"]):
            return charter
    return None


def _common(values: list[str]) -> str:
    distinct = {v for v in values if v}
    return distinct.pop() if len(distinct) == 1 and all(values) else ""


def plan(charter: dict, snap: base.Snapshot, *, root: str) -> dict:
    """What putting this run on the belt takes: the epic row to create (or that it exists)
    and the members to nest, with every reason not to, as ``problems``."""
    result = {"packet": charter["packet"], "epicRow": charter["id"], "kind": KIND_ITEM,
              "create": None, "exists": False, "nest": [], "nested": [], "problems": []}
    problems = result["problems"]
    if charter["status"] in ("complete", "aborted"):
        problems.append("the charter is %s: a finished run is not put on the belt"
                        % charter["status"])
    if not charter["id"]:
        problems.append("the charter declares no id: fill its frontmatter `id:` first")
        return result
    by_id = {item.id: item for item in snap.items}

    if not combine_mod.is_combination(charter):
        row = by_id.get(charter["id"])
        result["exists"] = row is not None
        if row is None:
            problems.append("%s is not in the work register" % charter["id"])
        elif row.is_terminal:
            problems.append("%s is already %s" % (charter["id"], row.status))
        return result

    result["kind"] = KIND_COMBINATION
    members = charter["items"]
    if len(members) < 2:
        problems.append("a combination names at least two items; this charter names %d"
                        % len(members))
    found = []
    for member_id in members:
        item = by_id.get(member_id)
        if item is None:
            problems.append("member %s is not in the work register" % member_id)
            continue
        if item.is_terminal:
            problems.append("member %s is already %s" % (member_id, item.status))
        if item.member_of and item.member_of != charter["id"]:
            problems.append("member %s is already nested under %s"
                            % (member_id, item.member_of))
        found.append(item)
        if item.member_of == charter["id"]:
            result["nested"].append(member_id)
        else:
            result["nest"].append({"item": member_id, "revision": item.revision})

    existing = by_id.get(charter["id"])
    if existing is not None:
        result["exists"] = True
        if existing.is_terminal:
            problems.append("epic row %s is already %s" % (charter["id"], existing.status))
        return result

    outside: list[str] = []
    for item in found:
        for prerequisite in item.prerequisites:
            if prerequisite and prerequisite not in members and prerequisite not in outside:
                outside.append(prerequisite)
    sequences = [item.sequence for item in found if item.sequence is not None]
    charter_path = os.path.relpath(charter["path"], root).replace(os.sep, "/")
    fields = {
        "id": charter["id"],
        "title": charter["title"] or charter["id"],
        "status": base.QUEUED,
        "written_status": base.FULL_SPEC,
        "sequence": min(sequences) if sequences else None,
        "prerequisites": outside,
        "spec_link": charter_path,
        "description": "Epic run of %d items, nested under this row: %s. Packet: %s."
                       % (len(members), ", ".join(members), charter_path),
        "workstream": _common([item.workstream for item in found]),
        "group": _common([item.group for item in found]),
    }
    served = set(snap.fields) | {"id", "title", "status"}
    result["create"] = {k: v for k, v in fields.items()
                        if k in served and v not in (None, "", [])}
    result["dropped"] = sorted(k for k, v in fields.items()
                               if k not in served and v not in (None, "", []))
    return result
