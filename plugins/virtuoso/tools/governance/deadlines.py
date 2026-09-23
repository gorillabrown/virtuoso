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
import os
from dataclasses import dataclass

from . import overlays as overlays_mod, policy as policy_mod, textio
from .registry import Finding

#: The finding codes this module reports. Never error severity: a deadline problem
#: is the project's to fix, and repair has nothing to propose for it.
UNANCHORED = "deadline-unanchored"
FINISH_LINE_MISSING = "deadline-finish-line-missing"
INVALID = "deadline-invalid"
FINDING_CODES = (UNANCHORED, FINISH_LINE_MISSING, INVALID)


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


def invalid_findings(problems: list[str]) -> list[Finding]:
    """One ``deadline-invalid`` finding per validation problem. ``policy-set``
    refuses an invalid entry outright, so these only report hand edits."""
    return [Finding(INVALID, "warning", problem, role="", identifier="") for problem in problems]


#: "The caller has not read the roadmap; read it here." Distinct from ``None``,
#: which is a read that found nothing.
UNREAD = object()


def anchor_findings(reg, deadlines: list[Deadline], *, roadmap_raw=UNREAD) -> list[Finding]:
    """The body half of each deadline: its ``finishLine`` must name a heading in the
    registered roadmap, matched as the pairing rule matches every body — a depth
    2-4 heading that starts with the text, in any case, outside fenced examples.

    A deadline naming no finish line is ``info``: pace is still computed over its
    scope, but nothing defines what done means. A finish line the roadmap does
    not define is a ``warning``.
    """
    findings: list[Finding] = []
    text, why_unreadable = None, ""
    if any(d.finish_line for d in deadlines):
        text, why_unreadable = _roadmap_text(reg, roadmap_raw)
    for d in deadlines:
        if not d.finish_line:
            findings.append(Finding(
                UNANCHORED, "info",
                "deadline %s names no finishLine: pace is computed over %s, but nothing "
                "defines what done means" % (d.id, d.scope_text()),
                role="roadmap", identifier=d.id))
        elif text is None:
            findings.append(Finding(
                FINISH_LINE_MISSING, "warning",
                "deadline %s names the finish line %r, but %s" % (d.id, d.finish_line,
                                                                    why_unreadable),
                role="roadmap", identifier=d.id))
        elif not overlays_mod.body_heading(d.finish_line).search(text):
            findings.append(Finding(
                FINISH_LINE_MISSING, "warning",
                "deadline %s names the finish line %r, and the registered roadmap has no "
                "heading that starts with it" % (d.id, d.finish_line),
                role="roadmap", identifier=d.id))
    return findings


def _roadmap_text(reg, raw=UNREAD) -> tuple[str | None, str]:
    """The roadmap's text outside fenced examples, or ``(None, why not)``.

    ``raw`` is the file's bytes when the caller has already read them — session
    start reads the roadmap once, for its integrity line and for this."""
    spec = reg.roles.get("roadmap")
    if spec is None:
        return None, "no roadmap role is registered"
    if spec.is_external:
        return None, "the registered roadmap is external and is not read here"
    if raw is UNREAD:
        raw = textio.read_bytes(os.path.join(reg.root, *spec.path.split("/")))
    raw = textio.decode(raw) if raw is not None else None
    if raw is None:
        return None, "the registered roadmap %s cannot be read" % spec.path
    return overlays_mod.without_fenced_blocks(raw), ""


# --- the session-start line ---------------------------------------------------


def today() -> _dt.date:
    """The local date the session line counts from. One function, so tests can
    pin it; the pace engine never calls it — pace is as of its snapshot."""
    return _dt.date.today()


def until(date: _dt.date, on: _dt.date) -> str:
    days = (date - on).days
    if days > 0:
        return "%d day%s" % (days, "" if days == 1 else "s")
    if days == 0:
        return "due today"
    return "passed %d day%s ago" % (-days, "" if days == -1 else "s")


def summary(usable: list[Deadline], problems: list[str], findings: list, on: _dt.date) -> str:
    """The state after ``deadlines: `` — dates and days only, never pace, because
    session start must not read a register that may be external."""
    if not usable:
        return ("invalid (%s)" % problems[0]) if problems else "none declared"
    if len(usable) == 1:
        d = usable[0]
        text = "%s %s (%s)" % (d.id, d.date.isoformat(), until(d.date, on))
    else:
        upcoming = [d for d in usable if d.date >= on]
        shown, word = (upcoming[0], "next") if upcoming else (usable[-1], "latest")
        text = "%d declared; %s %s %s (%s)" % (len(usable), word, shown.id,
                                               shown.date.isoformat(), until(shown.date, on))
    count = len(findings) + len(problems)
    if count:
        text += "; %d finding%s" % (count, "" if count == 1 else "s")
    return text


def status(reg, on: _dt.date | None = None, *, roadmap_raw=UNREAD) -> tuple[str, dict]:
    """``(line state, JSON detail)`` for a loaded registry."""
    on = on or today()
    usable, problems = declared(policy_mod.load(reg.policy))
    findings = anchor_findings(reg, usable, roadmap_raw=roadmap_raw)
    state = summary(usable, problems, findings, on)
    detail = {
        "state": state,
        "asOf": on.isoformat(),
        "declared": [dict(d.as_dict(), daysRemaining=(d.date - on).days) for d in usable],
        "findings": [f.as_dict() for f in findings + invalid_findings(problems)],
    }
    return state, detail
