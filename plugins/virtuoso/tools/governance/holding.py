"""The holding bay: ad hoc plans waiting for the next roadmap review.

Work that arrives between roadmap reviews enters through ``storyboard`` (alignment)
and ``write-plan`` (a dispatch-ready plan). Neither ceremony touches the roadmap or
the live work register — that is ``roadmap-review``'s job — so what they produce waits
in the registered ``holdingBay`` role: one Markdown file per piece of work, named
``<yyyy-mm-dd>-<slug>.md``.

    # Held Plan — Retry failed exports
    <!-- virtuoso-held-plan v1 -->
    - **Entry:** 2026-09-24-export-retry
    - **Size:** single item
    - **Origin:** storyboard 2026-09-24 — a customer escalation; cannot wait

    ## Trail
    | Date | State | By | Note |
    |---|---|---|---|
    | 2026-09-24 | storyboarded | storyboard | aligned; skeleton approved |
    | 2026-09-24 | planned | write-plan | HB-3 passed the rubric |

    ## Storyboard
    ### Alignment record
    ### Alignment verdict
    Aligned — 2026-09-24 ...

    ## Plan
    #### HB-3 — Retry failed exports
    ...

The **trail** is the entry's history, one row per state change, appended through
``virtuoso_registry holding --record`` and never edited; its last row is the current
state. A state is recorded only by the ceremony that owns that step, and only when
the entry carries what that state promises — an *Aligned* verdict before it is
``storyboarded``, a plan before it is ``planned``. Every entry that is not
``absorbed`` or ``withdrawn`` is open, and the next roadmap review reconciles every
open entry that is not in flight: it absorbs it into the roadmap, or withdraws it.

Items inside a held plan carry provisional identifiers (``HB-<n>``, never reused)
until the review absorbs them and the register assigns their real ones.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from . import overlays as overlays_mod

MARKER = "<!-- virtuoso-held-plan v1 -->"
ID_PREFIX = "HB"

UNRECORDED = "unrecorded"
STORYBOARDED = "storyboarded"
PLANNED = "planned"
IN_FLIGHT = "in-flight"
EXECUTED = "executed"
ABSORBED = "absorbed"
WITHDRAWN = "withdrawn"

#: Every state a trail row may record, in lifecycle order.
STATES = (STORYBOARDED, PLANNED, IN_FLIGHT, EXECUTED, ABSORBED, WITHDRAWN)
#: States that end an entry's life in the bay.
CLOSED_STATES = (ABSORBED, WITHDRAWN)

#: The legal next states. A state may repeat where a revision is meaningful: a
#: storyboard re-approved after a change, a plan rewritten after a re-audit.
TRANSITIONS = {
    UNRECORDED: (STORYBOARDED,),
    STORYBOARDED: (STORYBOARDED, PLANNED, ABSORBED, WITHDRAWN),
    PLANNED: (STORYBOARDED, PLANNED, IN_FLIGHT, ABSORBED, WITHDRAWN),
    IN_FLIGHT: (PLANNED, EXECUTED),
    EXECUTED: (ABSORBED,),
    ABSORBED: (),
    WITHDRAWN: (),
}

#: Which ceremony records which state. ``write-plan`` may re-open alignment
#: (``storyboarded``) because anything that changes what was agreed goes back there.
RECORDED_BY = {
    STORYBOARDED: ("storyboard", "write-plan"),
    PLANNED: ("write-plan",),
    IN_FLIGHT: ("write-plan",),
    EXECUTED: ("pointer-closeout",),
    ABSORBED: ("roadmap-review",),
    WITHDRAWN: ("storyboard", "write-plan", "roadmap-review"),
}

#: States whose trail row must say something: where the evidence is, what the
#: review turned the entry into, or why it was dropped.
NOTE_REQUIRED = (EXECUTED, ABSORBED, WITHDRAWN)

SINGLE_ITEM = "single item"
ITEM_SET = "item set"
EPIC_SCALE = "epic-scale"
SIZES = (SINGLE_ITEM, ITEM_SET, EPIC_SCALE)

#: Finding codes for ``--check`` and ``--record``.
MARKER_MISSING = "held-marker-missing"
NAME_INVALID = "held-name-invalid"
ENTRY_MISMATCH = "held-entry-mismatch"
SIZE_INVALID = "held-size-invalid"
TRAIL_MISSING = "held-trail-missing"
UNRECORDED_ENTRY = "held-unrecorded"
STATE_UNKNOWN = "held-state-unknown"
TRANSITION_ILLEGAL = "held-transition-illegal"
RECORDER_WRONG = "held-recorder-wrong"
DATE_INVALID = "held-date-invalid"
NOTE_MISSING = "held-note-missing"
NOT_ALIGNED = "held-not-aligned"
PLAN_MISSING = "held-plan-missing"
EPIC_PLANNED = "held-epic-planned"
FINDING_CODES = (MARKER_MISSING, NAME_INVALID, ENTRY_MISMATCH, SIZE_INVALID, TRAIL_MISSING,
                 UNRECORDED_ENTRY, STATE_UNKNOWN, TRANSITION_ILLEGAL, RECORDER_WRONG,
                 DATE_INVALID, NOTE_MISSING, NOT_ALIGNED, PLAN_MISSING, EPIC_PLANNED)

_NAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.+?)[ \t]*$")
_FIELD_RE = re.compile(r"^[-*][ \t]+\*\*(?P<name>[^*]+?):\*\*[ \t]*(?P<value>.*)$")
_ITEM_RE = re.compile(r"(?<![\w-])%s-(\d+)(?![\w-])" % ID_PREFIX)
_SEPARATOR_RE = re.compile(r"^\|?[ \t]*:?-{2,}:?[ \t]*(\|[ \t]*:?-{2,}:?[ \t]*)*\|?[ \t]*$")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def _blank(text: str) -> str:
    """``text`` with fenced blocks and HTML comments blanked, every offset kept: a
    fenced example or a template's guidance comment is never structure."""
    body = overlays_mod.without_fenced_blocks(text or "")
    return _COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), body)


@dataclass
class TrailRow:
    date: str
    state: str
    by: str
    note: str
    line: int                    # index of the row in the document's lines

    def as_dict(self) -> dict:
        return {"date": self.date, "state": self.state, "by": self.by, "note": self.note}


@dataclass
class Entry:
    """One held plan, parsed. ``problems`` are the structural findings; an entry with
    problems still lists, so a broken file is reported rather than skipped."""
    id: str
    path: str = ""
    title: str = ""
    entry_field: str = ""
    size: str = ""
    raw_size: str = ""
    origin: str = ""
    has_marker: bool = False
    trail: list = field(default_factory=list)
    trail_found: bool = False
    trail_end: int = -1          # index of the last line of the trail table
    aligned: bool = False
    has_alignment_record: bool = False
    has_plan: bool = False
    items: list = field(default_factory=list)          # provisional ids in the plan
    problems: list = field(default_factory=list)

    @property
    def state(self) -> str:
        return self.trail[-1].state if self.trail else UNRECORDED

    @property
    def since(self) -> str:
        return self.trail[-1].date if self.trail else ""

    @property
    def open(self) -> bool:
        return self.state not in CLOSED_STATES

    def as_dict(self) -> dict:
        return {"id": self.id, "path": self.path, "title": self.title, "size": self.size,
                "origin": self.origin, "state": self.state, "since": self.since,
                "open": self.open, "items": list(self.items),
                "trail": [row.as_dict() for row in self.trail],
                "problems": list(self.problems)}


def _problem(code: str, message: str) -> dict:
    return {"code": code, "severity": "error", "message": message}


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def _normalize_size(value: str) -> str:
    low = value.strip().lower()
    for size in SIZES:
        if low.startswith(size):
            return size
    return ""


def parse(text: str, entry_id: str, path: str = "") -> Entry:
    """Parse one held plan. Fenced blocks and HTML comments are never structure."""
    entry = Entry(id=entry_id, path=path)
    body = _blank(text)
    entry.has_marker = MARKER in (text or "")
    lines = body.splitlines()

    section = ""          # the current depth-2 section, lowercased
    subsection = ""       # the current depth-3 heading inside it, lowercased
    verdict_seen = False
    in_trail_table = False
    for index, raw in enumerate(lines):
        line = raw.rstrip("\r")
        heading = _HEADING_RE.match(line)
        if heading:
            depth, text_ = len(heading.group("hashes")), heading.group("text").strip()
            in_trail_table = False
            if depth == 1 and not entry.title:
                title = re.sub(r"^held plan[ \t]*[—–:-][ \t]*", "", text_, flags=re.IGNORECASE)
                entry.title = title.strip()
            elif depth == 2:
                section, subsection = text_.lower(), ""
                if section.startswith("trail"):
                    entry.trail_found = True
                elif section.startswith("plan"):
                    entry.has_plan = True
            elif depth == 3:
                subsection = text_.lower()
                if section.startswith("storyboard") and subsection.startswith("alignment record"):
                    entry.has_alignment_record = True
            if section.startswith("plan") and depth >= 3:
                for match in _ITEM_RE.finditer(text_):
                    item = "%s-%s" % (ID_PREFIX, match.group(1))
                    if item not in entry.items:
                        entry.items.append(item)
            continue

        stripped = line.strip()
        if not section:
            field_match = _FIELD_RE.match(stripped)
            if field_match:
                name = field_match.group("name").strip().lower()
                value = field_match.group("value").strip()
                if name == "entry":
                    entry.entry_field = value
                elif name == "size":
                    entry.raw_size, entry.size = value, _normalize_size(value)
                elif name == "origin":
                    entry.origin = value
            continue

        if section.startswith("trail"):
            if stripped.startswith("|"):
                if not in_trail_table:
                    in_trail_table = True          # the header row
                    entry.trail_end = index
                    continue
                entry.trail_end = index
                if _SEPARATOR_RE.match(stripped):
                    continue
                cells = _cells(stripped) + ["", "", "", ""]
                entry.trail.append(TrailRow(date=cells[0], state=cells[1].lower(),
                                            by=cells[2], note=cells[3], line=index))
            elif stripped:
                in_trail_table = False
            continue

        if (section.startswith("storyboard") and subsection.startswith("alignment verdict")
                and not verdict_seen and stripped):
            verdict_seen = True
            low = stripped.lstrip("*_ ").lower()
            entry.aligned = low.startswith("aligned")
    return entry


def validate(entry: Entry) -> list[dict]:
    """Every structural finding for ``entry`` in its current state."""
    problems = []
    if not entry.has_marker:
        problems.append(_problem(MARKER_MISSING, "no `%s` marker: this is not a held plan the "
                                                 "plugin can read" % MARKER))
    if not _NAME_RE.match(entry.id):
        problems.append(_problem(NAME_INVALID, "%r is not named <yyyy-mm-dd>-<slug>" % entry.id))
    if entry.entry_field and entry.entry_field != entry.id:
        problems.append(_problem(ENTRY_MISMATCH, "the Entry field says %r but the file is %r"
                                                 % (entry.entry_field, entry.id)))
    if not entry.size:
        problems.append(_problem(SIZE_INVALID, "Size %r is not one of: %s"
                                               % (entry.raw_size, ", ".join(SIZES))))
    if not entry.trail_found:
        problems.append(_problem(TRAIL_MISSING, "no `## Trail` section"))
    elif not entry.trail:
        problems.append(_problem(UNRECORDED_ENTRY, "the trail has no row: record the entry "
                                                   "with `holding --record` before it counts"))

    previous = UNRECORDED
    for row in entry.trail:
        if not _DATE_RE.match(row.date):
            problems.append(_problem(DATE_INVALID, "trail date %r is not YYYY-MM-DD" % row.date))
        if row.state not in STATES:
            problems.append(_problem(STATE_UNKNOWN, "trail state %r is not one of: %s"
                                                    % (row.state, ", ".join(STATES))))
            previous = row.state
            continue
        if previous in TRANSITIONS and row.state not in TRANSITIONS[previous]:
            problems.append(_problem(TRANSITION_ILLEGAL, "%s → %s is not a legal move"
                                                         % (previous, row.state)))
        if row.by not in RECORDED_BY[row.state]:
            problems.append(_problem(RECORDER_WRONG, "%s was recorded by %r; only %s may record it"
                                                     % (row.state, row.by,
                                                        " or ".join(RECORDED_BY[row.state]))))
        if row.state in NOTE_REQUIRED and not row.note:
            problems.append(_problem(NOTE_MISSING, "the %s row carries no note" % row.state))
        previous = row.state

    problems.extend(content_problems(entry, entry.state))
    return problems


def content_problems(entry: Entry, state: str) -> list[dict]:
    """What ``entry`` must carry to stand in ``state``."""
    problems = []
    if state in (UNRECORDED, WITHDRAWN) or state not in STATES:
        return problems
    if not entry.has_alignment_record or not entry.aligned:
        problems.append(_problem(NOT_ALIGNED, "no `## Storyboard` alignment record with an "
                                              "\"Aligned\" verdict: nothing is held until the "
                                              "user and the agent agree on it"))
    if state in (PLANNED, IN_FLIGHT, EXECUTED):
        if entry.size == EPIC_SCALE:
            problems.append(_problem(EPIC_PLANNED, "an epic-scale entry is never planned here: "
                                                   "it waits for roadmap review, then /epic"))
        if not entry.has_plan or not entry.items:
            problems.append(_problem(PLAN_MISSING, "no `## Plan` section with an %s-<n> item "
                                                   "heading" % ID_PREFIX))
    return problems


# --- the directory -----------------------------------------------------------


def entry_paths(directory: str) -> list[str]:
    """Every held-plan file directly under ``directory``, sorted by name. A missing
    directory holds nothing."""
    if not os.path.isdir(directory):
        return []
    return sorted(os.path.join(directory, name) for name in os.listdir(directory)
                  if name.endswith(".md") and not name.startswith((".", "_"))
                  and name.lower() != "readme.md"
                  and os.path.isfile(os.path.join(directory, name)))


def load(path: str, text: str, root: str = "") -> Entry:
    entry_id = os.path.splitext(os.path.basename(path))[0]
    shown = os.path.relpath(path, root).replace(os.sep, "/") if root else path
    entry = parse(text, entry_id, shown)
    entry.problems = validate(entry)
    return entry


def next_id(texts) -> str:
    """The next provisional item identifier. Identifiers are never reused, so every
    entry counts — absorbed and withdrawn ones too."""
    highest = 0
    for text in texts:
        for match in _ITEM_RE.finditer(text or ""):
            highest = max(highest, int(match.group(1)))
    return "%s-%d" % (ID_PREFIX, highest + 1)


def record_problems(entry: Entry, state: str, actor: str, note: str, date: str) -> list[dict]:
    """Why ``actor`` may not append a ``state`` row to ``entry`` now — empty when it may."""
    state = state.strip().lower()
    if state not in STATES:
        return [_problem(STATE_UNKNOWN, "%r is not one of: %s" % (state, ", ".join(STATES)))]
    problems = []
    blocking = [p for p in entry.problems
                if p["code"] not in (UNRECORDED_ENTRY, NOT_ALIGNED, PLAN_MISSING, EPIC_PLANNED)]
    problems.extend(blocking)
    if state not in TRANSITIONS.get(entry.state, ()):
        problems.append(_problem(TRANSITION_ILLEGAL, "%s → %s is not a legal move (from %s: %s)"
                                                     % (entry.state, state, entry.state,
                                                        ", ".join(TRANSITIONS.get(entry.state, ()))
                                                        or "nothing — the entry is closed")))
    if actor not in RECORDED_BY[state]:
        problems.append(_problem(RECORDER_WRONG, "%s may not record %s; only %s may"
                                                 % (actor, state, " or ".join(RECORDED_BY[state]))))
    if state in NOTE_REQUIRED and not note.strip():
        problems.append(_problem(NOTE_MISSING, "recording %s needs --note" % state))
    if not _DATE_RE.match(date):
        problems.append(_problem(DATE_INVALID, "%r is not YYYY-MM-DD" % date))
    if "|" in note or "\n" in note:
        problems.append(_problem(NOTE_MISSING, "a note is one line without `|`"))
    problems.extend(content_problems(entry, state))
    return problems


def append_row(text: str, entry: Entry, row: str) -> str:
    """``text`` with ``row`` appended to the trail table, in the file's own line
    endings. Refuses a document whose trail table cannot be found."""
    if entry.trail_end < 0:
        raise ValueError("no trail table to append to")
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    # The parsed line index counts lines of the blanked body, which keeps every
    # line position, so it addresses the raw document too.
    lines.insert(entry.trail_end + 1, row)
    return eol.join(lines)


def trail_row(date: str, state: str, by: str, note: str) -> str:
    return "| %s | %s | %s | %s |" % (date, state, by, note.strip())
