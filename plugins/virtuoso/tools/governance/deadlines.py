"""Deadlines: the declared half (v1.8.1).

A deadline is a *value* — ``policy.roadmap.deadlines.<id>``, written by
``policy-set`` — paired with a *body*: the roadmap heading that defines the finish
line it dates. This module turns the declaration into :class:`Deadline` objects,
checks the pairing, and states the session-start line. Pace against a deadline is
``providers/pace.py``.

One authority: the date lives in the manifest and nowhere else. Every surface that
shows it — ``kpis``, the cockpit, the session-start line, a review — reads it from
here, so there is one place to move it and no copy to drift.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from . import policy as policy_mod


@dataclass(frozen=True)
class Deadline:
    id: str
    date: _dt.date
    owner: str
    label: str = ""
    finish_line: str = ""
    scope_field: str = ""
    scope_values: tuple = ()
    recorded: str = ""

    @property
    def name(self) -> str:
        return self.label or self.id

    def scope_text(self) -> str:
        if not self.scope_field:
            return "every item in the register"
        return "%s in {%s}" % (self.scope_field, ", ".join(self.scope_values))

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.name,
            "date": self.date.isoformat(),
            "owner": self.owner,
            "finishLine": self.finish_line,
            "scope": self.scope_text(),
            "recorded": self.recorded,
        }


def declared(project_policy: policy_mod.Policy) -> tuple[list[Deadline], list[str]]:
    """The usable deadlines, sorted by date then id, and the problems of any that are not.

    An invalid entry is reported and left out whole — never half-used, because a
    deadline with a readable date and an unreadable scope would be paced over the
    wrong work while looking configured.
    """
    raw = project_policy.get("roadmap.deadlines", {})
    problems = policy_mod.deadline_problems(raw)
    if not isinstance(raw, dict):
        return [], problems
    usable: list[Deadline] = []
    for key, entry in raw.items():
        if policy_mod.deadline_problems({key: entry}):
            continue
        scope = entry.get("scope") or {}
        usable.append(Deadline(
            id=key,
            date=policy_mod.iso_date(entry["date"]),
            owner=entry["owner"].strip(),
            label=str(entry.get("label", "") or "").strip(),
            finish_line=str(entry.get("finishLine", "") or "").strip(),
            scope_field=str(scope.get("field", "") or "").strip(),
            scope_values=tuple(v.strip() for v in scope.get("values", []) or []),
            recorded=str(entry.get("recorded", "") or ""),
        ))
    usable.sort(key=lambda d: (d.date, d.id))
    return usable, problems
