"""The roadmap board's model: one page with three tabs (Dashboard, Roadmap, Completed).

Pure functions over canonical work items, ledger records and comments. The page
never edits the register or the roadmap; everything here describes what they say.
"""
from __future__ import annotations

import re

from tools.governance.policy import workstream_problems
from tools.governance.providers import base
from tools.governance.structure import _approved_index

BOARD_ROLE = "board"
COMMENTS_ROLE = "boardComments"
DEFAULT_PATH = "roadmap-board.html"
COMMENTS_PATH = "roadmap-board.comments.json"

#: The Roadmap tab: live work only, one group per pipeline state, in this order.
#: Conveyor (``None``) holds every live status the others do not claim: queued, unknown.
PIPELINE_GROUPS = (
    ("in-flight", "In Flight", "amber", (base.IN_FLIGHT,)),
    ("conveyor", "Conveyor", "blue", None),
    ("blocked", "Blocked / Gated", "red", (base.BLOCKED,)),
)
#: With an approved structure: the group for work it does not place, shown last.
UNASSIGNED = "Unassigned"

#: Mapped columns in the reference board's order: canonical field, the label used
#: when the provider does not say which register header it read, and the rendering.
#: ``id`` appears only when the register keeps it apart from the item's name.
ROADMAP_COLUMNS = (
    ("sequence", "Seq", "number"),
    ("workstream", "Workstream", "label"),
    ("status", "Status", "label"),
    ("written_status", "Written", "label"),
    ("description", "Description", "text"),
    ("prerequisites", "Depends On", "deps"),
    ("id", "ID", "text"),
    ("branch", "Branch", "mono"),
    ("spec_link", "Spec", "link"),
    ("notes", "Notes", "text"),
    ("effort", "Effort", "label"),
    ("group", "Group", "chip"),
    ("started", "Started", "text"),
    ("completed", "Completed", "text"),
    ("evidence", "Evidence", "link"),
)

#: Keys a snapshot import adds to ``extra`` that are not register columns.
IMPORT_KEYS = frozenset({"providerId", "revision", "url"})

_DASH = r"\s*[—–-]\s*"


def _named(value: str, item_id: str) -> bool:
    """Whether ``value`` reads ``<id> — <something>``."""
    return bool(item_id) and re.match(re.escape(item_id) + _DASH + r"\S",
                                      str(value or "").strip()) is not None


def name_column(items) -> str:
    """The ``extra`` header that holds ``ID — Title`` for items with no title of
    their own (a register whose Item column carries both), or ``""``."""
    for item in items:
        if item.title.strip():
            continue
        for header, value in item.extra.items():
            if header not in IMPORT_KEYS and _named(value, item.id):
                return header
    return ""


def display_name(item, name_key: str = "") -> str:
    """``<ID> — <Title>``. A title that already reads that way is used as it is; an
    item with no title uses its name column, then its bare id."""
    title = item.title.strip()
    if title:
        return title if _named(title, item.id) else "%s — %s" % (item.id, title)
    value = str(item.extra.get(name_key, "") if name_key else "").strip()
    if not value:
        value = next((str(v).strip() for k, v in item.extra.items()
                      if k not in IMPORT_KEYS and _named(v, item.id)), "")
    return value or item.id


def copy_text(item, name_key: str = "", *, dispatch: bool = False) -> str:
    """What a row's copy button copies; ``dispatch`` (Shift-copy) adds the spec path
    and branch when the register knows them."""
    text = display_name(item, name_key)
    if dispatch:
        if item.spec_link:
            text += "\nSpec: %s" % item.spec_link
        if item.branch:
            text += "\nBranch: %s" % item.branch
    return text


def ordered(items) -> list:
    """Seq, then id; unsequenced items last."""
    return sorted(items, key=lambda i: (i.sequence is None, i.sequence or 0, i.id))


def extra_headers(items, name_key: str = "") -> list[str]:
    """Every register column the mapping left in ``extra``, in first-seen order."""
    out: list[str] = []
    for item in items:
        for header in item.extra:
            if header not in out and header not in IMPORT_KEYS and header != name_key:
                out.append(header)
    return out


def _numeric(values) -> bool:
    seen = False
    for value in values:
        text = str(value).replace(",", "").strip()
        if not text:
            continue
        try:
            float(text)
        except ValueError:
            return False
        seen = True
    return seen


def roadmap_columns(fields, headers: dict, items, name_key: str = "") -> list[dict]:
    """The Roadmap tab's columns: mapped fields the register carries, under its own
    header, in the reference order; then every unmapped column, never dropped."""
    carried = set(fields or [])
    out = []
    for key, label, kind in ROADMAP_COLUMNS:
        if key == "id" and not name_key:
            continue
        if key != "id" and key not in carried:
            continue
        out.append({"key": key, "header": (headers or {}).get(key) or label, "kind": kind})
    for header in extra_headers(items, name_key):
        values = [item.extra.get(header, "") for item in items]
        out.append({"key": "extra:" + header, "header": header,
                    "kind": "number" if _numeric(values) else "text"})
    return out


def cell_values(item) -> dict:
    """The row's display value for every column key, as the register spells it."""
    values = {
        "sequence": item.sequence,
        "status": item.raw_status or item.status,
        "written_status": item.raw_written_status or item.written_status,
        "prerequisites": list(item.prerequisites),
    }
    for key in ("id", "workstream", "description", "branch", "spec_link", "notes", "effort",
                "group", "started", "completed", "evidence"):
        values[key] = getattr(item, key)
    for header, value in item.extra.items():
        values["extra:" + header] = "" if value is None else str(value)
    return values


def row(item, name_key: str = "") -> dict:
    return {
        "id": item.id,
        "name": display_name(item, name_key),
        "copy": copy_text(item, name_key),
        "copyDispatch": copy_text(item, name_key, dispatch=True),
        "status": item.status,
        "written": item.written_status,
        "terminal": item.is_terminal,
        "warn": "status unknown: %r" % (item.raw_status or "") if item.status == base.UNKNOWN
                else "",
        "values": cell_values(item),
    }


def live(items) -> list:
    """The Roadmap tab's rows: every item that is not terminal, in Seq order. Terminal
    items belong to the Completed tab. Every grouping the page offers starts here."""
    return ordered(i for i in items if not i.is_terminal)


def roadmap_groups(items) -> list[dict]:
    """Live work grouped In Flight → Conveyor → Blocked / Gated; an empty group is
    not shown."""
    rows = live(items)
    claimed = {s for *_, statuses in PIPELINE_GROUPS if statuses for s in statuses}
    out = []
    for key, title, rail, statuses in PIPELINE_GROUPS:
        ids = [i.id for i in rows
               if (i.status in statuses if statuses else i.status not in claimed)]
        if ids:
            out.append({"key": key, "title": title, "rail": rail, "ids": ids})
    return out


def approved_structure(project_policy) -> list:
    """The approved workstreams, ``roadmap.workstreams``, or ``[]``. The pre-1.15.0
    ``roadmap.lanes`` is not a structure: a project with only lanes renders as before.
    A structure policy validation refuses is not used either; preflight names its problems."""
    value = project_policy.section("roadmap").get("workstreams")
    return value if isinstance(value, list) and not workstream_problems(value) else []


def structure_groups(items, workstreams) -> list[dict]:
    """Live work grouped by workstream, then deliverable, in policy order. An item with a
    workstream but no deliverable it owns follows that workstream's deliverables; one the
    structure does not place goes under "Unassigned", last. An empty group is not shown."""
    owner, spelling = _approved_index(workstreams)
    placed: dict = {}
    for i in live(items):
        d = spelling.get("d:" + (i.deliverable or "").strip().lower())
        w = spelling.get((i.workstream or "").strip().lower())
        key = (owner[d], d) if d and (not w or owner[d] == w) else (w, None) if w else None
        placed.setdefault(key, []).append(i.id)
    out = []
    for w in workstreams:
        name = w.get("name") or w.get("id")
        for d in list(w.get("deliverables") or []) + [None]:
            ids = placed.get((w.get("id"), d.get("id") if d else None))
            if ids:
                out.append({"key": "ws:%s/%s" % (w.get("id"), d.get("id") if d else ""),
                            "title": "%s › %s" % (name, d.get("name") or d.get("id"))
                            if d else name, "rail": "blue", "ids": ids})
    if placed.get(None):
        out.append({"key": "unassigned", "title": UNASSIGNED, "rail": "grey",
                    "ids": placed[None]})
    return out
