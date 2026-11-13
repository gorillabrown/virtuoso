"""Milestones: the named stages a dispatch or an epic passes through, each with its steps.

A **specification** carries a ``##### Milestones`` table beside its ``##### Task list``: each
milestone names the task rows that make it up, so a step is a task row and a milestone is a
group of them. An **epic charter** carries a ``## Milestones`` table whose steps are outcome
checkpoints. Both parse to the milestone list ``progress --begin`` records (rubric U11).

    ##### Milestones
    | Milestone | Rows | Done when |
    |---|---|---|
    | Registry and CLI | 1-3 | the command registers, flags and ends a run |

    ## Milestones
    | Milestone | Steps | Done when |
    |---|---|---|
    | Discovery | map the layout; confirm the assumptions | the layout is written down |
"""
from __future__ import annotations

import re

from .errors import GovernanceError

_SEPARATOR = re.compile(r"[\s|:-]+")
_BLANK = ("", "-", "—", "–", "n/a")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table(body: list[str]) -> list[dict]:
    """The first table in a section as rows keyed by header, or ``[]`` where there is none."""
    lines = []
    for line in body:
        if line.strip().startswith("|"):
            lines.append(line)
        elif lines:
            break
    if len(lines) < 2:
        return []
    header = _cells(lines[0])
    rows = [line for line in lines[1:] if not _SEPARATOR.fullmatch(line.strip())]
    return [dict(zip(header, _cells(line))) for line in rows]


def _section(text: str, item: str, wanted: str):
    from . import lessons as lessons_mod, overlays as overlays_mod
    if item:
        lines = lessons_mod.item_section(text, item)
        if lines is None:
            raise GovernanceError("no heading in the document names %s" % item)
    else:
        lines = overlays_mod.without_fenced_blocks(text or "").splitlines()
    return lessons_mod._find_section(lines, (wanted,))


def _row_numbers(cell: str) -> list[int]:
    """``1-3, 5`` (a hyphen or an en dash makes a range) as ``[1, 2, 3, 5]``."""
    out = []
    for part in re.split(r"[,;]", cell.replace("–", "-").replace("—", "-")):
        part = part.strip().lower().removeprefix("rows").removeprefix("row").strip()
        if not part:
            continue
        span = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if span:
            low, high = int(span.group(1)), int(span.group(2))
            if high < low:
                raise GovernanceError("rows %r run backwards" % part)
            out.extend(range(low, high + 1))
        elif part.isdigit():
            out.append(int(part))
        else:
            raise GovernanceError("rows %r is not a row number or a range such as 1-3" % part)
    return out


def from_spec(text: str, item: str = "") -> list[dict]:
    """The milestones of a specification, their steps the task rows each names. Refuses,
    naming what is missing or wrong: no Task list or Milestones table, a milestone with no
    rows, a row that does not exist, a row in two milestones or in none, no *Done when*."""
    tasks_body = _section(text, item, "task list")
    if tasks_body is None:
        raise GovernanceError("no \"Task list\" section%s: milestones group its rows"
                              % (" for %s" % item if item else ""))
    tasks = {}
    for row in _table(tasks_body):
        number, title = row.get("#", ""), row.get("Task", "")
        if number.isdigit() and title:
            tasks[int(number)] = title
    if not tasks:
        raise GovernanceError("the Task list holds no rows with a # and a Task")
    body = _section(text, item, "milestones")
    if body is None:
        raise GovernanceError("no \"Milestones\" section%s (rubric U11)"
                              % (" for %s" % item if item else ""))
    table = _table(body)
    if not table:
        raise GovernanceError("the Milestones section holds no table rows")
    out, owner = [], {}
    for index, row in enumerate(table, start=1):
        name, done_when = row.get("Milestone", ""), row.get("Done when", "")
        if not name or name.lower() in _BLANK:
            raise GovernanceError("milestone %d has no name" % index)
        if "Rows" not in row:
            raise GovernanceError("the Milestones table has no Rows column")
        if done_when.lower() in _BLANK:
            raise GovernanceError("milestone %r has no Done when" % name)
        rows = sorted(set(_row_numbers(row["Rows"])))
        if not rows:
            raise GovernanceError("milestone %r names no rows" % name)
        for number in rows:
            if number not in tasks:
                raise GovernanceError("milestone %r names row %d, which the Task list does not "
                                      "have" % (name, number))
            if number in owner:
                raise GovernanceError("row %d is in both %r and %r; a row belongs to one "
                                      "milestone" % (number, owner[number], name))
            owner[number] = name
        out.append({"id": "M%d" % index, "name": name, "doneWhen": done_when,
                    "steps": [{"id": str(n), "name": tasks[n]} for n in rows]})
    loose = sorted(set(tasks) - set(owner))
    if loose:
        raise GovernanceError("Task list row%s %s %s in no milestone"
                              % ("s" if len(loose) > 1 else "", ", ".join(map(str, loose)),
                                 "are" if len(loose) > 1 else "is"))
    return out


def from_charter(text: str) -> list[dict]:
    """The milestones of an epic charter: a ``Milestones`` table whose *Steps* column lists
    outcome checkpoints separated by semicolons. Refuses, naming what is missing or wrong."""
    body = _section(text, "", "milestones")
    if body is None:
        raise GovernanceError("no \"Milestones\" section in the charter (rubric U11)")
    table = _table(body)
    if not table:
        raise GovernanceError("the Milestones section holds no table rows")
    out = []
    for index, row in enumerate(table, start=1):
        name, done_when = row.get("Milestone", ""), row.get("Done when", "")
        if not name or name.lower() in _BLANK:
            raise GovernanceError("milestone %d has no name" % index)
        if "Steps" not in row:
            raise GovernanceError("the Milestones table has no Steps column")
        if done_when.lower() in _BLANK:
            raise GovernanceError("milestone %r has no Done when" % name)
        steps = [s.strip() for s in row["Steps"].split(";") if s.strip()]
        if not steps:
            raise GovernanceError("milestone %r lists no steps" % name)
        out.append({"id": "M%d" % index, "name": name, "doneWhen": done_when,
                    "steps": [{"id": "%d.%d" % (index, n), "name": s}
                              for n, s in enumerate(steps, start=1)]})
    return out
