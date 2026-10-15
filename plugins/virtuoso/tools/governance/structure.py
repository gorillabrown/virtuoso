"""Workstreams and deliverables proposed from the active work (1.15.0).

A roadmap review asks the owner to approve how the active work splits into workstreams
(work that can run side by side) and the deliverables inside each. This module does the
mechanical half: it reads the active items and their specifications and proposes. The
review names each candidate, writes its purpose, and asks; nothing is written before the
owner approves, and then only by ``structure --apply``.

* **A first proposal** (no approved structure): a workstream is a group joined by strong
  links — a prerequisite, or two items sharing more than half their files. A weaker
  overlap does not join two workstreams; it is reported as a *crossing* between them, a
  plan-time hint only (run-time ordering stays ``combine``'s). Inside a workstream, the
  deliverables are the groups joined by prerequisites or an existing grouping: the
  register's ``group``, or a roadmap table row naming two or more of the items (a chunk).
  An item with no listed files and no prerequisite is its own workstream, flagged
  ``noSignal`` — never merged by default.
* **A later proposal** (an approved structure in ``policy.roadmap.workstreams``): only a
  place for each active item the register does not assign, the deliverable it shares most
  with and why; a split for a deliverable over :data:`SPLIT_ABOVE` items; a merge for two
  deliverables sharing more than half their files.

Everything here is read-only and deterministic: every list is ordered by register
sequence, then id.
"""
from __future__ import annotations

import re

from . import combine
from .providers import base

#: A deliverable with more active items than this is proposed for a split.
SPLIT_ABOVE = 8
#: The register fields an applied structure writes.
FIELDS = ("workstream", "deliverable")


def _rank(item: base.WorkItem):
    return (item.sequence is None, item.sequence or 0, item.id)


def active_members(snapshot: base.Snapshot, read=None) -> list:
    """The active items as :class:`combine.Member`, each with its specification read."""
    items = sorted((i for i in snapshot.items if not i.is_terminal), key=_rank)
    members = [combine.Member(item, n) for n, item in enumerate(items)]
    if read is not None:
        for member in members:
            member.spec = read(member.item)
    return members


def shares_most(shared: list, a: list, b: list) -> bool:
    """More than half of the two file lists, together, is shared."""
    union = len(a) + len(b) - len(shared)
    return bool(shared) and len(shared) * 2 > union


def _files_between(a, b) -> list:
    return combine.shared_files(a, b) if a.files_known and b.files_known else []


def _prerequisite(a, b) -> str:
    if a.item.id in b.item.prerequisites:
        return "%s before %s" % (a.item.id, b.item.id)
    if b.item.id in a.item.prerequisites:
        return "%s before %s" % (b.item.id, a.item.id)
    return ""


def roadmap_groups(text: str | None, ids) -> dict:
    """``{item id: grouping name}`` from roadmap table rows naming two or more of ``ids``
    (a chunk table's ``| E9 — name | A, B, C |``); the first such row wins."""
    groups: dict = {}
    for line in (text or "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.lstrip().startswith("|") or len(cells) < 2:
            continue
        named = [i for i in ids if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(i),
                                             " ".join(cells[1:]))]
        if len(named) >= 2:
            for item_id in named:
                groups.setdefault(item_id, cells[0])
    return groups


def _components(members: list, joined) -> list:
    """Groups of ``members`` connected by ``joined(a, b)``, in member order."""
    position = {m.item.id: n for n, m in enumerate(members)}
    parent = {m.item.id: m.item.id for m in members}

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(members):
        for b in members[i + 1:]:
            if joined(a, b):
                ra, rb = sorted((root(a.item.id), root(b.item.id)), key=position.get)
                parent[rb] = ra                          # the earlier item stays the root
    out: dict = {}
    for m in members:
        out.setdefault(root(m.item.id), []).append(m)
    return list(out.values())


def _signals(group: list, grouping: dict) -> list[str]:
    signals: list[str] = []
    for i, a in enumerate(group):
        for b in group[i + 1:]:
            link = _prerequisite(a, b)
            if link:
                signals.append("prerequisite: " + link)
            shared = _files_between(a, b)
            if shared:
                signals.append("shared files (%s, %s): %s"
                               % (a.item.id, b.item.id, ", ".join(shared)))
    names = sorted({grouping[m.item.id] for m in group if grouping.get(m.item.id)})
    signals += ["grouping: %s" % n for n in names]
    return signals


def crossings(members: list, key_of: dict) -> list:
    """Per pair of workstreams, the files and prerequisites that cross them."""
    found: dict = {}
    for i, a in enumerate(members):
        for b in members[i + 1:]:
            ka, kb = key_of.get(a.item.id), key_of.get(b.item.id)
            if not ka or not kb or ka == kb:
                continue
            pair = tuple(sorted((ka, kb)))
            entry = found.setdefault(pair, {"between": list(pair), "files": [],
                                            "prerequisites": []})
            for path in _files_between(a, b):
                if path not in entry["files"]:
                    entry["files"].append(path)
            link = _prerequisite(a, b)
            if link:
                entry["prerequisites"].append(link)
    out = [dict(e, files=sorted(e["files"])) for e in found.values()
           if e["files"] or e["prerequisites"]]
    return sorted(out, key=lambda e: e["between"])


def _group_of(item, grouping: dict) -> str:
    return (item.group or "").strip() or grouping.get(item.id, "")


def _unread(members: list) -> list:
    return [{"item": m.item.id, "why": m.spec.unlocated or "no reader"}
            for m in members if not m.spec.source]


def propose_first(members: list, grouping: dict) -> dict:
    """Candidate workstreams and deliverables, with crossings, for a project with no
    approved structure."""
    def strong(a, b):
        shared = _files_between(a, b)
        return bool(_prerequisite(a, b)) or shares_most(shared, a.spec.files, b.spec.files)

    def same_deliverable(a, b):
        ga = _group_of(a.item, grouping)
        return bool(_prerequisite(a, b)) or (bool(ga) and ga == _group_of(b.item, grouping))

    active_ids = {m.item.id for m in members}
    workstreams, key_of = [], {}
    for n, group in enumerate(_components(members, strong), start=1):
        key = "W%d" % n
        deliverables = []
        for d, part in enumerate(_components(group, same_deliverable), start=1):
            deliverables.append({"key": "%s.D%d" % (key, d),
                                 "items": [m.item.id for m in part],
                                 "signals": _signals(part, grouping)})
        no_signal = len(group) == 1 and not group[0].files_known and not any(
            p in active_ids for p in group[0].item.prerequisites)
        workstreams.append({"key": key, "items": [m.item.id for m in group],
                            "noSignal": no_signal, "signals": _signals(group, grouping),
                            "deliverables": deliverables})
        for m in group:
            key_of[m.item.id] = key
    return {"mode": "first", "workstreams": workstreams,
            "crossings": crossings(members, key_of), "unread": _unread(members)}


def _approved_index(approved: list) -> tuple[dict, dict]:
    """``({deliverable id: workstream id}, {spelling: id})``: ids and names, lowercased,
    both resolve, so a register holding either reads as assigned."""
    owner, spelling = {}, {}
    for w in approved:
        spelling[str(w.get("id", "")).lower()] = w.get("id")
        spelling[str(w.get("name") or "").lower()] = w.get("id")
        for d in w.get("deliverables") or []:
            owner[d.get("id")] = w.get("id")
            spelling["d:" + str(d.get("id", "")).lower()] = d.get("id")
            spelling["d:" + str(d.get("name") or "").lower()] = d.get("id")
    spelling.pop("", None)
    spelling.pop("d:", None)
    return owner, spelling


def propose_later(members: list, approved: list, grouping: dict) -> dict:
    """Placement for each unassigned active item, and split and merge suggestions, against
    an approved structure read in the same run as the register."""
    owner, spelling = _approved_index(approved)
    placed: dict = {}                                  # deliverable id -> [Member]
    unassigned, stale = [], []
    for m in members:
        d = spelling.get("d:" + (m.item.deliverable or "").strip().lower())
        w = spelling.get((m.item.workstream or "").strip().lower())
        if d and (not w or owner[d] == w):
            placed.setdefault(d, []).append(m)
            continue
        if m.item.workstream or m.item.deliverable:
            stale.append({"item": m.item.id, "workstream": m.item.workstream,
                          "deliverable": m.item.deliverable})
        unassigned.append(m)
    order = [d.get("id") for w in approved for d in (w.get("deliverables") or [])]

    placements = []
    for m in unassigned:
        best, best_score, best_why = None, 0, []
        for d in order:
            why, score = [], 0
            for other in placed.get(d, []):
                shared = _files_between(m, other)
                link = _prerequisite(m, other)
                score += len(shared) + (2 if link else 0)
                if shared:
                    why.append("shares %s with %s" % (", ".join(shared), other.item.id))
                if link:
                    why.append("prerequisite: " + link)
            if score > best_score:
                best, best_score, best_why = d, score, why
        group = _group_of(m.item, grouping)
        placements.append({"item": m.item.id, "deliverable": best,
                           "workstream": owner.get(best) if best else None,
                           "why": best_why, "noSignal": best is None,
                           "grouping": group})

    def same_deliverable(a, b):
        ga = _group_of(a.item, grouping)
        return bool(_prerequisite(a, b)) or (bool(ga) and ga == _group_of(b.item, grouping))

    splits = []
    for d in order:
        group = placed.get(d, [])
        if len(group) > SPLIT_ABOVE:
            parts = _components(group, same_deliverable)
            splits.append({"deliverable": d, "items": [m.item.id for m in group],
                           "parts": [[m.item.id for m in p] for p in parts]
                           if len(parts) > 1 else []})

    def files(d):
        out = []
        for m in placed.get(d, []):
            if m.files_known:
                out += [f for f in m.spec.files if f not in out]
        return out

    merges = []
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            fa, fb = files(a), files(b)
            shared = [x for x in fa if any(combine._same_file(x, y) for y in fb)]
            if shares_most(shared, fa, fb):
                merges.append({"deliverables": [a, b], "files": sorted(shared)})

    key_of = {m.item.id: owner[d] for d, group in placed.items() for m in group}
    return {"mode": "later", "placements": placements, "stale": stale, "splits": splits,
            "merges": merges, "crossings": crossings(members, key_of),
            "unread": _unread(members)}


def propose(snapshot: base.Snapshot, approved: list, *, read=None,
            roadmap_text: str | None = None) -> dict:
    members = active_members(snapshot, read)
    grouping = roadmap_groups(roadmap_text, [m.item.id for m in members])
    result = (propose_later(members, approved, grouping) if approved
              else propose_first(members, grouping))
    result["provenance"] = snapshot.provenance()
    return result


# --- apply ------------------------------------------------------------------------------

def assignments(approved: dict, snapshot: base.Snapshot) -> tuple[list, list, list]:
    """``(writes, untouched, problems)`` for an approved file
    ``{"workstreams": [...], "assignments": {item: {"workstream", "deliverable"}}}``.

    A write is ``(item, workstream, deliverable)`` for an active item whose register
    values differ. A finished item is never touched; it is named in ``untouched``."""
    from .policy import workstream_problems
    workstreams = approved.get("workstreams") or []
    problems = list(workstream_problems(workstreams)) if isinstance(workstreams, list) \
        else ["workstreams is not a list"]
    owner, _ = _approved_index(workstreams if not problems else [])
    by_id = {i.id: i for i in snapshot.items}
    writes, untouched = [], []
    raw = approved.get("assignments") or {}
    if not isinstance(raw, dict):
        return [], [], problems + ["assignments is not an object of item ids"]
    for item_id in sorted(raw, key=lambda i: _rank(by_id[i]) if i in by_id else (True, 0, i)):
        entry = raw[item_id] or {}
        if not isinstance(entry, dict):
            problems.append("%s: an assignment is {\"workstream\", \"deliverable\"}" % item_id)
            continue
        w, d = str(entry.get("workstream") or ""), str(entry.get("deliverable") or "")
        item = by_id.get(item_id)
        if item is None:
            problems.append("%s is not in the work register" % item_id)
        elif d not in owner or owner[d] != w:
            problems.append("%s: deliverable %r is not under workstream %r in the approved "
                            "structure" % (item_id, d, w))
        elif item.is_terminal:
            untouched.append({"item": item_id, "why": "finished (%s)" % item.status})
        elif (item.workstream, item.deliverable) != (w, d):
            writes.append((item, w, d))
    return writes, untouched, problems
