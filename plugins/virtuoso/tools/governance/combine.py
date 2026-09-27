"""Whether a set of roadmap items combines into one epic run (1.12.0).

An epic is not always one epic-scale item. The run that works is often several items
a roadmap review already specified and placed, none epic-scale alone, run together
unattended: serialized where they touch the same files, in parallel lanes where they
do not, under one Definition of Done. Deciding what combines is the valuable judgement,
and this module does the mechanical half of it. ``epic`` does the rest.

For a selection (item identifiers, or a lane and an optional sequence range) it
answers, from the live register and the specifications, with provenance:

* **membership** — each item is in the register, not terminal, not blocked, not already
  in flight, its specification written (``full-spec``), not an epic on its own
  (``Path: epic``), and not already named by an active epic charter;
* **prerequisites** — each is terminal already, or another item in the set;
* **files** — the files each specification's *Edit sites* and *Staging plan* name. Two
  items that share a file are serialized; an item whose files cannot be read is
  serialized with everything, because an unknown overlap is not a known absence;
* **order and lanes** — a serial order that honours every prerequisite and shared
  file, and the lanes: groups with no prerequisite and no file between them, which
  may run side by side;
* **size** — the item count and effort points, for the epic-scale verdict ``epic``
  states.

Everything here is read-only.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from . import lessons as lessons_mod, textio
from .providers import base
from .providers.kpi import DEFAULT_EFFORT_SCALE

# --- finding codes --------------------------------------------------------------------

ITEM_UNKNOWN = "combine-item-unknown"
ITEM_TERMINAL = "combine-item-terminal"
ITEM_BLOCKED = "combine-item-blocked"
ITEM_IN_FLIGHT = "combine-item-in-flight"
ITEM_STUB = "combine-item-stub"
ITEM_EPIC = "combine-item-epic"
ITEM_CHARTERED = "combine-item-chartered"
PREREQUISITE_OUTSIDE = "combine-prerequisite-outside"
CYCLE = "combine-cycle"
SINGLE = "combine-single"
SELECTION_EMPTY = "combine-selection-empty"
SNAPSHOT_STALE = "combine-snapshot-stale"
SPEC_UNLOCATED = "combine-spec-unlocated"
FILES_UNLISTED = "combine-files-unlisted"
LANE_UNMAPPED = "combine-lane-unmapped"
FINDING_CODES = (ITEM_UNKNOWN, ITEM_TERMINAL, ITEM_BLOCKED, ITEM_IN_FLIGHT, ITEM_STUB,
                 ITEM_EPIC, ITEM_CHARTERED, PREREQUISITE_OUTSIDE, CYCLE, SINGLE,
                 SELECTION_EMPTY, SNAPSHOT_STALE, SPEC_UNLOCATED, FILES_UNLISTED,
                 LANE_UNMAPPED)

#: The specification fields (the D.5.2 format) whose paths are the files an item touches.
FILE_FIELDS = ("edit sites", "staging plan")

_FIELD_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)[-*][ \t]+\*\*(?P<name>[^*]+?):\*\*[ \t]*"
                            r"(?P<value>.*)$")
_HEADING_RE = re.compile(r"^#{1,6}[ \t]")
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_BARE_PATH_RE = re.compile(r"(?<![\w./\\-])((?:[\w.-]+[/\\])+[\w.-]+)")
_EXTENSION_RE = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,7}$")


# --- reading a specification ------------------------------------------------------------

def field_text(lines: list[str], name: str) -> str | None:
    """The text of the ``- **Name:** …`` field in a specification's lines — its own
    line and every deeper-indented line under it — or ``None`` when absent."""
    wanted = name.strip().lower()
    for index, line in enumerate(lines):
        match = _FIELD_LINE_RE.match(line.rstrip("\r"))
        if not match or match.group("name").strip().lower() != wanted:
            continue
        indent = len(match.group("indent").expandtabs())
        out = [match.group("value")]
        for later in lines[index + 1:]:
            later = later.rstrip("\r")
            if _HEADING_RE.match(later):
                break
            if later.strip() and len(later) - len(later.lstrip()) <= indent:
                break
            out.append(later.strip())
        return "\n".join(out).strip()
    return None


def _clean_path(token: str) -> str:
    token = token.strip().strip("\"'").replace("\\", "/")
    token = re.split(r"::|#|:(?=\d|L\d)", token, maxsplit=1)[0]   # test ids, anchors, lines
    while token.startswith("./"):
        token = token[2:]
    return token.rstrip(".,;:)")


def paths_in(text: str) -> list[str]:
    """The file paths a field names: backticked tokens that look like a path (a slash,
    or a file extension), and bare tokens with a slash. Commands, identifiers and
    prose are not paths."""
    found: list[str] = []
    candidates = _BACKTICK_RE.findall(text or "")
    candidates += _BARE_PATH_RE.findall(_BACKTICK_RE.sub(" ", text or ""))
    for raw in candidates:
        if any(ch.isspace() for ch in raw.strip()):
            continue
        path = _clean_path(raw)
        if not path or "://" in raw:
            continue
        if "/" not in path and not _EXTENSION_RE.search(path):
            continue
        if path not in found:
            found.append(path)
    return found


def declares_epic_path(lines: list[str]) -> bool:
    """The specification's ``- **Path:** epic`` (references/execution-paths.md)."""
    value = field_text(lines, "path")
    return bool(value) and value.strip().lower().startswith("epic")


@dataclass
class SpecReading:
    source: str = ""          # where the specification was read, or "" when unlocated
    unlocated: str = ""       # why it could not be read
    files: list = field(default_factory=list)
    files_listed: bool = False
    epic_path: bool = False


def read_spec(reg, project_policy, item: base.WorkItem, roadmap_text: str | None,
              roadmap_label: str) -> SpecReading:
    """Locate ``item``'s specification the way the buffer figure does — inline in the
    roadmap under a heading naming the item, or at its ``spec_link`` when
    ``policy.roadmap.specStorage`` is ``files`` — and read its files and path."""
    storage = str(project_policy.get("roadmap.specStorage", "inline"))
    reading = SpecReading()
    lines: list[str] | None = None
    if storage == "external":
        reading.unlocated = "specifications are external (policy.roadmap.specStorage)"
    elif storage == "inline":
        if roadmap_text is None:
            reading.unlocated = "no readable roadmap holds the specifications"
        else:
            lines = lessons_mod.item_section(roadmap_text, item.id)
            if lines is None:
                reading.unlocated = "no heading in %s names %s" % (roadmap_label, item.id)
            else:
                reading.source = "%s#%s" % (roadmap_label, item.id)
    else:
        link = (item.spec_link or "").strip()
        if not link or "://" in link:
            reading.unlocated = ("the item carries no local spec_link"
                                 if not link else "its spec_link %s is not local" % link)
        else:
            text = textio.read_text(link if os.path.isabs(link) else os.path.join(reg.root, link))
            if text is None:
                reading.unlocated = "its spec_link %s cannot be read" % link
            else:
                lines = text.splitlines()
                reading.source = link
    if lines is None:
        return reading
    reading.epic_path = declares_epic_path(lines)
    for name in FILE_FIELDS:
        value = field_text(lines, name)
        if value is None:
            continue
        reading.files_listed = True
        for path in paths_in(value):
            if path not in reading.files:
                reading.files.append(path)
    return reading


# --- epic charters already under way -------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


def charter_items(text: str) -> tuple[list[str], str]:
    """``(items, status)`` a charter's frontmatter declares: ``item:`` and ``items:``."""
    match = _FRONTMATTER_RE.match(text or "")
    if not match:
        return [], ""
    items: list[str] = []
    status = ""
    in_block = False                       # under ``items:`` written as a YAML block list
    for line in match.group(1).splitlines():
        bullet = re.match(r"^[ \t]*-[ \t]+(.*)$", line)
        if in_block and bullet:
            tokens = [bullet.group(1).split("#", 1)[0].strip()]
            key = ""
        else:
            key, _, value = line.partition(":")
            value = value.split("#", 1)[0].strip()
            key = key.strip().lower()
            in_block = key == "items" and not value
            # ``item: [ITEM-ID]`` is an unfilled template; ``items: [A, B]`` is a list.
            if key == "item" and not value.startswith("["):
                tokens = [value]
            elif key == "items":
                tokens = re.split(r"[,\s]+", value.strip("[]"))
            else:
                tokens = []
        for token in tokens:
            token = token.strip().strip("\"'")
            if token and token != "ITEM-ID" and token not in items:
                items.append(token)
        if key == "status":
            status = value.lower()
    return items, status


def active_charters(directory: str) -> dict[str, str]:
    """``{item id: packet directory name}`` for every charter under ``directory`` whose
    status is not ``complete`` or ``aborted``."""
    claimed: dict[str, str] = {}
    if not directory or not os.path.isdir(directory):
        return claimed
    for name in sorted(os.listdir(directory)):
        charter = os.path.join(directory, name, "charter.md")
        text = textio.read_text(charter) if os.path.isfile(charter) else None
        if text is None:
            continue
        items, status = charter_items(text)
        if status in ("complete", "aborted"):
            continue
        for item in items:
            claimed.setdefault(item, name)
    return claimed


# --- the combination ---------------------------------------------------------------------

@dataclass
class Member:
    item: base.WorkItem
    position: int
    spec: SpecReading = field(default_factory=SpecReading)

    @property
    def files_known(self) -> bool:
        return bool(self.spec.source) and self.spec.files_listed and bool(self.spec.files)

    def as_dict(self) -> dict:
        item = self.item
        return {"id": item.id, "title": item.title, "sequence": item.sequence,
                "status": item.status, "specification": item.written_status or "unknown",
                "lane": item.lane, "group": item.group, "effort": item.effort,
                "prerequisites": list(item.prerequisites), "spec": self.spec.source,
                "specUnlocated": self.spec.unlocated, "files": list(self.spec.files),
                "filesKnown": self.files_known}


@dataclass
class Combination:
    selection: dict
    members: list = field(default_factory=list)
    order: list = field(default_factory=list)
    lanes: list = field(default_factory=list)
    edges: list = field(default_factory=list)       # {"before", "after", "why"}
    findings: list = field(default_factory=list)
    effort: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    def add(self, code: str, severity: str, message: str, item: str = "") -> None:
        finding = {"code": code, "severity": severity, "message": message}
        if item:
            finding["item"] = item
        self.findings.append(finding)

    @property
    def combinable(self) -> bool:
        return not any(f["severity"] == "error" for f in self.findings)

    def as_dict(self) -> dict:
        return {"combinable": self.combinable, "selection": dict(self.selection),
                "items": [m.as_dict() for m in self.members], "order": list(self.order),
                "lanes": [list(lane) for lane in self.lanes], "edges": list(self.edges),
                "effort": dict(self.effort), "findings": list(self.findings),
                "provenance": dict(self.provenance)}


def select(snapshot: base.Snapshot, *, items=(), lane: str = "", first=None,
           last=None) -> tuple[list, list[str], list[str]]:
    """``(work items, unknown ids, notes)`` for a selection by identifier, or by lane and
    an inclusive sequence range. A lane selection takes the active items only."""
    by_id = {item.id: item for item in snapshot.items}
    if items:
        chosen, unknown = [], []
        for item_id in items:
            if item_id in by_id:
                if by_id[item_id] not in chosen:
                    chosen.append(by_id[item_id])
            elif item_id not in unknown:
                unknown.append(item_id)
        return chosen, unknown, []
    wanted = lane.strip().lower()
    chosen = [i for i in snapshot.items if not i.is_terminal
              and (i.lane or "").strip().lower() == wanted
              and (first is None or (i.sequence is not None and i.sequence >= first))
              and (last is None or (i.sequence is not None and i.sequence <= last))]
    chosen.sort(key=lambda i: (i.sequence is None, i.sequence or 0, i.id))
    notes = []
    if "lane" not in snapshot.fields and not any(i.lane for i in snapshot.items):
        notes.append("the register serves no lane field (policy.workRegister.fieldMappings.lane)")
    return chosen, [], notes


def _same_file(a: str, b: str) -> bool:
    x, y = a.rstrip("/"), b.rstrip("/")
    if x == y or x.endswith("/" + y) or y.endswith("/" + x):
        return True
    return (a.endswith("/") and y.startswith(a)) or (b.endswith("/") and x.startswith(b))


def shared_files(a: Member, b: Member) -> list[str]:
    shared = []
    for x in a.spec.files:
        for y in b.spec.files:
            if _same_file(x, y):
                longer = x if len(x) >= len(y) else y
                if longer not in shared:
                    shared.append(longer)
    return shared


def _reaches(graph: dict, start: str, goal: str) -> bool:
    seen, stack = set(), [start]
    while stack:
        node = stack.pop()
        if node == goal:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    return False


def _effort(members: list, scale: dict | None) -> dict:
    table = {str(k).lower(): v for k, v in (scale or DEFAULT_EFFORT_SCALE).items()}
    unsized = [m.item.id for m in members if not m.item.effort]
    unscaled = sorted({m.item.effort for m in members
                       if m.item.effort and m.item.effort.lower() not in table})
    if unsized or unscaled:
        missing = []
        if unsized:
            missing.append("effort for %s" % ", ".join(unsized))
        if unscaled:
            missing.append("effort scale entries for %s (policy.roadmap.effortScale)"
                           % ", ".join(unscaled))
        return {"computable": False, "missingInputs": missing}
    return {"computable": True, "points": float(sum(table[m.item.effort.lower()]
                                                    for m in members)),
            "scale": "policy.roadmap.effortScale" if scale else "the default t-shirt scale"}


def check(snapshot: base.Snapshot, chosen: list, *, unknown=(), selection: dict | None = None,
          notes=(), read=None, charters: dict | None = None,
          effort_scale: dict | None = None) -> Combination:
    """Check whether ``chosen`` combines into one epic run.

    ``read`` reads an item's specification (:func:`read_spec`, bound); ``charters`` is
    :func:`active_charters`. Errors make the combination not combinable; warnings are
    facts the charter must carry (an item whose files are unknown runs serially).
    """
    combo = Combination(selection=dict(selection or {}), provenance=snapshot.provenance())
    for note in notes:
        combo.add(LANE_UNMAPPED, "warning", note)
    if snapshot.stale:
        combo.add(SNAPSHOT_STALE, "error",
                  "the register snapshot is stale (%s); refresh it before combining — a "
                  "combination checked against old status charters old status"
                  % (snapshot.stale_reason or "no timestamp"))
    for item_id in unknown:
        combo.add(ITEM_UNKNOWN, "error", "%s is not in the work register" % item_id, item_id)
    if not chosen and not unknown:
        combo.add(SELECTION_EMPTY, "error", "the selection names no active item")
    by_id = {item.id: item for item in snapshot.items}
    charters = charters or {}
    members = [Member(item, index) for index, item in enumerate(chosen)]
    for member in members:
        item = member.item
        name = "%s (%s)" % (item.title or "untitled", item.id)
        if item.is_terminal:
            combo.add(ITEM_TERMINAL, "error", "%s is already %s" % (name, item.status), item.id)
        elif item.status == base.BLOCKED:
            combo.add(ITEM_BLOCKED, "error", "%s is blocked (%s)" % (name, item.raw_status
                                                                    or item.status), item.id)
        elif item.status == base.IN_FLIGHT:
            combo.add(ITEM_IN_FLIGHT, "error", "%s is already in flight; finish or stop that "
                      "dispatch before it joins a run" % name, item.id)
        if not item.is_terminal and item.written_status != base.FULL_SPEC:
            combo.add(ITEM_STUB, "error", "%s has no written specification (%s); a roadmap "
                      "review specifies it first" % (name, item.written_status or "unknown"),
                      item.id)
        if item.id in charters:
            combo.add(ITEM_CHARTERED, "error", "%s is already in the epic packet %s"
                      % (name, charters[item.id]), item.id)
        if read is not None:
            member.spec = read(item)
        if member.spec.epic_path:
            combo.add(ITEM_EPIC, "error", "%s declares Path: epic; it is chartered on its own "
                      "(/epic %s)" % (name, item.id), item.id)
        if not member.spec.source:
            combo.add(SPEC_UNLOCATED, "warning", "%s: specification not read — %s; its files "
                      "are unknown, so it runs serially with every other item"
                      % (name, member.spec.unlocated or "no reader"), item.id)
        elif not member.files_known:
            combo.add(FILES_UNLISTED, "warning", "%s: its specification names no file under "
                      "Edit sites or Staging plan; it runs serially with every other item"
                      % name, item.id)
    combo.members = members
    ids = [m.item.id for m in members]
    in_set = set(ids)
    for member in members:
        outside = []
        for prerequisite in member.item.prerequisites:
            if prerequisite in in_set:
                continue
            known = by_id.get(prerequisite)
            if known is not None and known.is_terminal:
                continue
            outside.append("%s (%s)" % (prerequisite, known.status if known else
                                        "not in the register"))
        if outside:
            combo.add(PREREQUISITE_OUTSIDE, "error",
                      "%s waits on %s, which is neither done nor in this combination"
                      % (member.item.id, ", ".join(outside)), member.item.id)
    if len(members) == 1 and not unknown:
        combo.add(SINGLE, "error",
                  "one item is not a combination: /next-pointer dispatches it, or a roadmap "
                  "review marks it Path: epic when it is epic-scale on its own")

    _order(combo, members, effort_scale)
    return combo


def _order(combo: Combination, members: list, effort_scale) -> None:
    """Order the members and group them into lanes, recording why each edge exists."""
    ids = [m.item.id for m in members]
    by_id = {m.item.id: m for m in members}
    graph: dict[str, set] = {i: set() for i in ids}      # before -> {after}
    for member in members:
        for prerequisite in member.item.prerequisites:
            if prerequisite in by_id and prerequisite != member.item.id:
                graph[prerequisite].add(member.item.id)
                combo.edges.append({"before": prerequisite, "after": member.item.id,
                                    "why": "prerequisite"})

    def rank(member):
        return (member.item.sequence is None, member.item.sequence or 0, member.position)

    for i, a in enumerate(members):
        for b in members[i + 1:]:
            if a.files_known and b.files_known:
                shared = shared_files(a, b)
                if not shared:
                    continue
                why = "shared files: %s" % ", ".join(shared)
            else:
                unknown = [m.item.id for m in (a, b) if not m.files_known]
                why = "files unknown for %s" % ", ".join(unknown)
            if _reaches(graph, a.item.id, b.item.id) or _reaches(graph, b.item.id, a.item.id):
                first, then = ((a, b) if _reaches(graph, a.item.id, b.item.id) else (b, a))
                combo.edges.append({"before": first.item.id, "after": then.item.id,
                                    "why": why + " (already ordered)"})
                continue
            first, then = (a, b) if rank(a) <= rank(b) else (b, a)
            graph[first.item.id].add(then.item.id)
            combo.edges.append({"before": first.item.id, "after": then.item.id, "why": why})

    # A topological order, ties broken by register sequence, then selection order.
    incoming = {i: 0 for i in ids}
    for before, afters in graph.items():
        for after in afters:
            incoming[after] += 1
    ready = sorted((by_id[i] for i in ids if incoming[i] == 0), key=rank)
    order: list[str] = []
    while ready:
        member = ready.pop(0)
        order.append(member.item.id)
        for after in graph[member.item.id]:
            incoming[after] -= 1
            if incoming[after] == 0:
                ready.append(by_id[after])
        ready.sort(key=rank)
    if len(order) < len(ids):
        stuck = [i for i in ids if i not in order]
        combo.add(CYCLE, "error", "the prerequisites of %s form a cycle; no serial order "
                  "honours them" % ", ".join(stuck))
        order.extend(sorted(stuck, key=lambda i: rank(by_id[i])))
    combo.order = order

    # Lanes: the groups with no edge between them.
    neighbours: dict[str, set] = {i: set() for i in ids}
    for before, afters in graph.items():
        for after in afters:
            neighbours[before].add(after)
            neighbours[after].add(before)
    placed: set = set()
    for item_id in order:
        if item_id in placed:
            continue
        lane, stack = set(), [item_id]
        while stack:
            node = stack.pop()
            if node in lane:
                continue
            lane.add(node)
            stack.extend(neighbours[node])
        placed |= lane
        combo.lanes.append([i for i in order if i in lane])
    combo.effort = _effort(members, effort_scale)
