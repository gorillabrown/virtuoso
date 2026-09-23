"""Pace against a dated deadline (v1.8.1).

The rate a deadline requires — what remains in its scope, divided by the weeks
left — against the rate the project has delivered over a trailing window, in items
and in points, with a verdict.

Pure: no I/O and no clock. "As of" is the snapshot's own date, so a stale snapshot
yields pace as of that date, flagged stale, and the same inputs always give the same
answer.

Nothing is approximated. Every figure is a value or ``None`` with the inputs it
lacks named: an undatable completion, an unsized item, or a scope that matches no
work makes the figures that depend on it *not computable* — never zero, and an
empty scope is never "met".
"""
from __future__ import annotations

import datetime as _dt
import math
import re
from collections import Counter
from dataclasses import dataclass, field

from .. import policy as policy_mod
from ..deadlines import Deadline
from . import base
from .kpi import DEFAULT_EFFORT_SCALE

#: Worst first. A deadline's headline verdict is the worst verdict among the
#: units that could be computed.
VERDICTS = ("overdue", "behind", "on track", "ahead", "met")
NOT_COMPUTABLE = "not computable"
UNITS = ("items", "points")

#: Canonical fields a scope may select on; anything else is looked up among the
#: register's own columns, verbatim.
_SCOPE_FIELDS = ("id", "title", "lane", "group", "effort", "branch")

_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:$|[T ])")


def record_date(text) -> _dt.date | None:
    """The date at the start of a recorded timestamp: ``2026-09-22`` or
    ``2026-09-22T10:00:00Z``. Anything else is undatable."""
    match = _DATE_PREFIX_RE.match(str(text or "").strip())
    return policy_mod.iso_date(match.group(1)) if match else None


@dataclass(frozen=True)
class Completion:
    """One terminal record, as pace reads it."""

    item_id: str
    date: _dt.date | None
    raw_date: str
    result: str              # as recorded
    canonical: str           # through the project's status vocabulary
    record: str = ""         # the ledger record id, or the item id for a register


@dataclass
class CompletionSource:
    """Where completions come from — or, in ``missing``, why none can be read."""

    completions: list
    label: str
    missing: list = field(default_factory=list)


def from_ledger(records, statuses) -> list[Completion]:
    """Effective completions from terminal-ledger records.

    A correction replaces the record it names (the last correction wins) and is
    not itself a completion; a field the correction leaves blank keeps the
    original's value. That is what "append-only, corrected by a new record" means
    when it is read back.
    """
    effective: dict = {}
    order: list[str] = []
    for index, record in enumerate(records):
        if record.corrects:
            original = effective.get(record.corrects)
            if original is not None:
                effective[record.corrects] = _corrected(original, record)
            continue
        key = record.record_id or "#%d" % (index + 1)
        if key not in effective:
            order.append(key)
        effective[key] = {"item": record.item_id, "completed": record.completed,
                          "result": record.result}
    out = []
    for key in order:
        entry = effective[key]
        out.append(Completion(item_id=entry["item"], date=record_date(entry["completed"]),
                              raw_date=entry["completed"], result=entry["result"],
                              canonical=statuses.to_canonical(entry["result"]), record=key))
    return out


def _corrected(original: dict, correction) -> dict:
    return {"item": correction.item_id or original["item"],
            "completed": correction.completed or original["completed"],
            "result": correction.result or original["result"]}


def from_register(items) -> list[Completion]:
    """Completions from a register that keeps finished items and their dates."""
    return [Completion(item_id=i.id, date=record_date(i.completed), raw_date=i.completed,
                       result=i.raw_status or i.status, canonical=i.status, record=i.id)
            for i in items if i.is_terminal]


# --- the report ----------------------------------------------------------------


@dataclass
class PaceReport:
    deadline: Deadline
    as_of: _dt.date | None = None
    stale: bool = False
    days_remaining: int | None = None
    remaining: dict = field(default_factory=lambda: {"items": None, "points": None})
    blocked: dict = field(default_factory=dict)
    required: dict = field(default_factory=lambda: {"items": None, "points": None})
    trailing: dict = field(default_factory=dict)
    unit_verdicts: dict = field(default_factory=dict)
    verdict: str = NOT_COMPUTABLE
    basis: list = field(default_factory=list)
    reason: str = ""
    projected: dict = field(default_factory=lambda: {"items": None, "points": None})
    missing: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def weeks_remaining(self) -> float | None:
        return None if self.days_remaining is None else self.days_remaining / 7

    def as_dict(self) -> dict:
        return {
            "deadline": self.deadline.as_dict(),
            "asOf": self.as_of.isoformat() if self.as_of else None,
            "stale": self.stale,
            "daysRemaining": self.days_remaining,
            "weeksRemaining": _r(self.weeks_remaining, 2),
            "remaining": {u: _r(v, 2) for u, v in self.remaining.items()},
            "blocked": dict(self.blocked),
            "required": {u: _r(v, 2) for u, v in self.required.items()},
            "trailing": dict(self.trailing, **{u: _r(self.trailing.get(u), 2) for u in UNITS}),
            "verdict": self.verdict,
            "basis": list(self.basis),
            "unitVerdicts": dict(self.unit_verdicts),
            "reason": self.reason,
            "projectedFinish": dict(self.projected),
            "missingInputs": {k: list(v) for k, v in self.missing.items()},
            "findings": list(self.findings),
            "notes": list(self.notes),
        }

    def render(self) -> str:
        d = self.deadline
        lines = ["  %s  %s: due %s, owner %s" % (d.id, d.name, d.date.isoformat(), d.owner)]
        if self.as_of is not None and self.days_remaining is not None:
            lines.append("    as of %s (snapshot%s): %s"
                         % (self.as_of.isoformat(), ", STALE" if self.stale else "",
                            _days_text(self.days_remaining, self.weeks_remaining)))
        if self.remaining.get("items") is not None:
            points = self.remaining.get("points")
            lines.append("    scope:    %s: %d items, %s remain"
                         % (d.scope_text(), self.remaining["items"],
                            "%s points" % _n(points) if points is not None
                            else "points not computable"))
            if self.blocked.get("items"):
                share = self.blocked.get("shareOfPoints")
                lines.append("              blocked: %d items%s"
                             % (self.blocked["items"],
                                ", %s points (%s%% of remaining points)"
                                % (_n(self.blocked.get("points")), _n(share))
                                if share is not None else ""))
        rates = ["%s %s/week" % (_n(self.required[u], 2), u) for u in UNITS
                 if self.required.get(u) is not None]
        if rates:
            lines.append("    required: %s" % ", ".join(rates))
        if self.trailing.get("items") is not None:
            window = self.trailing.get("window", {})
            lines.append("    trailing: %s items/week over %s..%s, project-wide"
                         % (_n(self.trailing["items"], 2), window.get("from"), window.get("to")))
            lines.append("              %d completions%s%s"
                         % (self.trailing.get("completions", 0),
                            _tally(": ", self.trailing.get("byResult", {})),
                            _tally("; excluded: ", self.trailing.get("excluded", {}))))
            if self.trailing.get("points") is not None:
                lines.append("              %s points/week" % _n(self.trailing["points"], 2))
        for figure, inputs in self.missing.items():
            lines.append("    %s not computable (missing: %s)"
                         % (_FIGURE_LABELS.get(figure, figure), "; ".join(inputs)))
        verdict = self.verdict.upper()
        if self.basis:
            verdict += " on %s" % " and ".join(self.basis)
        lines.append("    verdict:  %s%s" % (verdict, (": " + self.reason) if self.reason else ""))
        for unit in UNITS:
            finish = self.projected.get(unit)
            if finish:
                late = (_dt.date.fromisoformat(finish) - d.date).days
                lines.append("    projected finish at the trailing %s rate: %s, %s"
                             % (unit[:-1], finish,
                                "%d days after the deadline" % late if late > 0
                                else "%d days before the deadline" % -late if late < 0
                                else "on the deadline"))
        for finding in self.findings:
            lines.append("    finding:  %s: %s" % (finding["code"], finding["message"]))
        for note in self.notes:
            lines.append("    note:     %s" % note)
        return "\n".join(lines)


#: How each figure that can be missing is named to a reader.
_FIGURE_LABELS = {
    "asOf": "the as-of date",
    "scope": "the scope",
    "remaining.points": "remaining points",
    "trailing": "the trailing rate",
    "trailing.points": "trailing points/week",
}


def _r(value, places):
    return None if value is None else round(value, places)


def _n(value, places=1) -> str:
    """A number as text: a count stays a whole number; anything else is rounded."""
    if value is None:
        return "—"
    if isinstance(value, int) and not isinstance(value, bool):
        return "%d" % value
    return "%.*f" % (places, value)


def _tally(prefix: str, counts: dict) -> str:
    if not counts:
        return ""
    return prefix + ", ".join("%s ×%d" % (word, n) for word, n in counts.items())


def _days_text(days: int, weeks: float) -> str:
    if days > 0:
        return "%d day%s, %.2f weeks remain" % (days, "" if days == 1 else "s", weeks)
    if days == 0:
        return "due today"
    return "passed %d day%s ago" % (-days, "" if days == -1 else "s")


# --- the computation -----------------------------------------------------------


def compute(deadline: Deadline, snapshot: base.Snapshot, source: CompletionSource, *,
            effort_scale: dict | None = None, trailing_weeks: int = 4,
            tolerance: float = 0.1) -> PaceReport:
    report = PaceReport(deadline=deadline, stale=snapshot.stale)
    scale = {str(k).lower(): v for k, v in (effort_scale or DEFAULT_EFFORT_SCALE).items()}
    if snapshot.stale:
        report.notes.append("the snapshot is stale (%s); pace is as of its own date"
                            % (snapshot.stale_reason or "past its freshness window"))

    # 1. as of
    report.as_of = record_date(snapshot.taken_at)
    if report.as_of is None:
        report.missing["asOf"] = ["a readable snapshot time (the snapshot says %r)"
                                  % snapshot.taken_at]
        report.reason = _missing_reason(report.missing)
        return report
    report.days_remaining = (deadline.date - report.as_of).days

    # 2. scope
    in_scope, why_not = _select(snapshot, deadline)
    if why_not:
        report.missing["scope"] = why_not
        report.reason = _missing_reason(report.missing)
        return report

    # 3-4. remaining and blocked
    remaining = [i for i in in_scope if not i.is_terminal]
    blocked = [i for i in remaining if i.status == base.BLOCKED]
    report.remaining["items"] = len(remaining)
    points, points_missing = _points(remaining, scale, "effort" in snapshot.fields)
    report.remaining["points"] = points
    if points_missing:
        report.missing["remaining.points"] = points_missing
    blocked_points = _points(blocked, scale, "effort" in snapshot.fields)[0] \
        if points is not None else None
    report.blocked = {
        "items": len(blocked),
        "points": _r(blocked_points, 2),
        "shareOfPoints": _r(100.0 * blocked_points / points, 1)
        if blocked_points is not None and points else None,
        "shareOfItems": _r(100.0 * len(blocked) / len(remaining), 1) if remaining else None,
    }

    # 5. required
    weeks = report.days_remaining / 7
    if remaining and report.days_remaining > 0:
        report.required["items"] = len(remaining) / weeks
        if points is not None:
            report.required["points"] = points / weeks

    # 6-8. trailing
    _trailing(report, source, snapshot, scale, trailing_weeks)

    # 9. verdict
    if not remaining:
        report.verdict, report.reason = "met", "nothing in scope remains"
        return report
    for unit in UNITS:
        required, trailing = report.required.get(unit), report.trailing.get(unit)
        if required is not None and trailing is not None:
            report.unit_verdicts[unit] = unit_verdict(required, trailing, tolerance)
    _project(report)
    if report.days_remaining <= 0:
        report.verdict = "overdue"
        report.reason = "%s with %d item%s remaining" % (
            "due today" if report.days_remaining == 0
            else "the date passed %d day%s ago" % (-report.days_remaining,
                                                  "" if report.days_remaining == -1 else "s"),
            len(remaining), "" if len(remaining) == 1 else "s")
        return report
    if not report.unit_verdicts:
        report.reason = _missing_reason(report.missing)
        return report
    worst = min(report.unit_verdicts.values(), key=VERDICTS.index)
    report.verdict = worst
    report.basis = [u for u in UNITS if report.unit_verdicts.get(u) == worst]
    report.reason = "; ".join(
        "trailing %s %s/week is %d%% of the %s required"
        % (_n(report.trailing[u], 2), u, round(100 * report.trailing[u] / report.required[u]),
           _n(report.required[u], 2))
        for u in report.basis)
    return report


def unit_verdict(required: float, trailing: float, tolerance: float) -> str:
    if trailing > required * (1 + tolerance):
        return "ahead"
    if trailing >= required * (1 - tolerance):
        return "on track"
    return "behind"


def compute_all(deadlines, snapshot, source, *, effort_scale=None, trailing_weeks=4,
                tolerance=0.1) -> list[PaceReport]:
    reports = [compute(d, snapshot, source, effort_scale=effort_scale,
                       trailing_weeks=trailing_weeks, tolerance=tolerance)
               for d in sorted(deadlines, key=lambda d: (d.date, d.id))]
    if len(reports) > 1:
        for report in reports:
            report.notes.append("the trailing rate is shared capacity: every declared "
                                "deadline draws on the same delivery")
    return reports


def _missing_reason(missing: dict) -> str:
    return "missing: " + "; ".join("; ".join(v) for v in missing.values())


def _select(snapshot: base.Snapshot, deadline: Deadline):
    items = list(snapshot.items)
    if not items:
        return [], ["the register has no work items"]
    if not deadline.scope_field:
        return items, []
    wanted = {v.strip().lower() for v in deadline.scope_values}
    name = deadline.scope_field
    if name in _SCOPE_FIELDS:
        def value_of(item):
            return getattr(item, name)
    else:
        lowered = name.lower()

        def value_of(item):
            for key, value in (item.extra or {}).items():
                if str(key).strip().lower() == lowered:
                    return value
            return None
        if all(value_of(i) is None for i in items):
            return [], ["no work item carries a %r field (canonical fields are %s; anything "
                        "else must be a column the register exposes)"
                        % (name, ", ".join(_SCOPE_FIELDS))]
    chosen = [i for i in items if str(value_of(i) or "").strip().lower() in wanted]
    if not chosen:
        return [], ["no work item carries %s" % deadline.scope_text()]
    return chosen, []


def _points(items, scale: dict, effort_known: bool):
    """(points, missing inputs) for ``items``; points is None when not computable."""
    if not effort_known:
        return None, ["effort (the register has no effort field)"]
    unsized = [i.id for i in items if not i.effort]
    unscaled = sorted({i.effort for i in items if i.effort and i.effort.lower() not in scale})
    missing = []
    if unsized:
        missing.append("effort for %d item(s): %s" % (len(unsized), _some(unsized)))
    if unscaled:
        missing.append("effort scale entries for: %s" % ", ".join(unscaled))
    if missing:
        return None, missing
    return float(sum(scale[i.effort.lower()] for i in items)), []


def _some(names, limit: int = 5) -> str:
    names = list(names)
    return ", ".join(names[:limit]) + ("…" if len(names) > limit else "")


def _trailing(report: PaceReport, source: CompletionSource, snapshot, scale, weeks: int):
    as_of = report.as_of
    start = as_of - _dt.timedelta(days=7 * weeks)          # exclusive
    report.trailing = {"items": None, "points": None, "projectWide": True,
                       "window": {"from": (start + _dt.timedelta(days=1)).isoformat(),
                                  "to": as_of.isoformat(), "weeks": weeks},
                       "completions": 0, "byResult": {}, "excluded": {},
                       "source": source.label}
    if source.missing:
        report.missing["trailing"] = list(source.missing)
        return
    completions = source.completions
    undatable = [c for c in completions if c.date is None and c.canonical == base.COMPLETED]
    if undatable:
        report.missing["trailing"] = [
            "a readable completion date (YYYY-MM-DD) on %d completed record(s): %s — append a "
            "correction that dates it" % (len(undatable),
                                          _some("%s (%r)" % (c.record, c.raw_date)
                                                for c in undatable))]
        return
    in_window = [c for c in completions if c.date is not None and start < c.date <= as_of]
    counted: dict = {}
    by_result: Counter = Counter()
    excluded: Counter = Counter()
    for c in in_window:
        if c.canonical == base.COMPLETED:
            if c.item_id not in counted:
                counted[c.item_id] = c
                by_result[c.result] += 1
        else:
            excluded[c.result] += 1
    report.trailing.update(completions=len(counted), byResult=dict(by_result),
                           excluded=dict(excluded))
    report.trailing["items"] = len(counted) / weeks
    dated = [c.date for c in completions if c.date is not None]
    if dated and min(dated) > start + _dt.timedelta(days=1):
        report.notes.append("the completion record begins %s, after the window opens; the "
                            "trailing rate may understate delivery from before it"
                            % min(dated).isoformat())

    by_id = {i.id: i for i in snapshot.items}
    absent = [item for item in counted if item not in by_id]
    if absent:
        report.missing["trailing.points"] = [
            "effort for %d completed item(s) absent from the register: %s"
            % (len(absent), _some(absent))]
        return
    points, missing = _points([by_id[item] for item in counted], scale,
                              "effort" in snapshot.fields)
    if missing:
        report.missing["trailing.points"] = missing
        return
    report.trailing["points"] = points / weeks


def _project(report: PaceReport) -> None:
    for unit in UNITS:
        rate, left = report.trailing.get(unit), report.remaining.get(unit)
        if rate is None or left is None:
            continue
        if rate <= 0:
            if "no completions in the trailing window; no projection" not in report.notes:
                report.notes.append("no completions in the trailing window; no projection")
            continue
        days = math.ceil(7 * left / rate)
        report.projected[unit] = (report.as_of + _dt.timedelta(days=days)).isoformat()
