"""Effort as hours or as a size word (v1.17.3).

A register may size an item two ways: a size word on the project's effort scale
(``effort``: XS … XL) and an hours estimate (``effort_hours``: a number, or a select
whose labels are numbers). ``policy.roadmap.effortBasis`` says which one governs the
figures:

* ``size`` — points, from the size word through ``policy.roadmap.effortScale``.
* ``hours`` — hours. An item with an hours figure counts it; an item with only a size
  word counts its scale value *read as hours*, which makes the figure ``inferred``; an
  item with neither is named, and the figure is not computable.
* ``auto`` (the default) — ``hours`` when the register serves an hours field, else
  ``size``.

Pure: no I/O. Every sum says how many items each source sized, so a figure can state
its basis and its kind (``measured`` when every item was read directly, ``inferred``
when any came through the scale).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

HOURS, SIZE, AUTO = "hours", "size", "auto"
BASES = (HOURS, SIZE, AUTO)

#: The unit a basis reports in.
UNIT = {HOURS: "hours", SIZE: "points"}

#: The canonical register field that holds the hours figure.
HOURS_FIELD = "effort_hours"

_HOURS_RE = re.compile(r"^(\d+(?:\.\d+)?|\.\d+)\s*(?:h|hr|hrs|hour|hours)?$", re.IGNORECASE)


def parse_hours(text) -> float | None:
    """Hours in ``1.5``, ``40``, ``2h``, ``2 hours``; ``None`` for blank or anything else."""
    if isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return float(text) if text >= 0 else None
    match = _HOURS_RE.match(str(text or "").strip())
    return float(match.group(1)) if match else None


def resolve(basis, fields) -> str:
    """The basis that governs: ``hours`` or ``size``. ``auto`` (or anything unset) picks
    ``hours`` when the register serves an hours field."""
    basis = str(basis or AUTO).strip().lower()
    if basis in (HOURS, SIZE):
        return basis
    return HOURS if HOURS_FIELD in set(fields or ()) else SIZE


def normalize_scale(scale: dict | None, default: dict) -> dict:
    return {str(k).lower(): v for k, v in (scale or default).items()}


@dataclass
class Sum:
    """A sum of effort over some items, or why it cannot be computed."""

    basis: str
    value: float | None = None
    missing: list = field(default_factory=list)
    #: How many items each source sized: ``hours`` (read as hours), ``scale`` (a size
    #: word through the scale), ``ledger`` (the terminal ledger's own record).
    sources: dict = field(default_factory=dict)

    @property
    def unit(self) -> str:
        return UNIT[self.basis]

    @property
    def computable(self) -> bool:
        return self.value is not None

    @property
    def kind(self) -> str:
        from .kpi import INFERRED, MEASURED
        return INFERRED if self.basis == HOURS and self.sources.get("scale") else MEASURED

    def describe(self) -> str:
        """The basis in one line: which source sized how many items."""
        if self.basis == SIZE:
            return "size words through policy.roadmap.effortScale (%d item(s))" % \
                sum(self.sources.values())
        parts = []
        if self.sources.get("ledger"):
            parts.append("%d from the terminal ledger's hours" % self.sources["ledger"])
        if self.sources.get("hours"):
            parts.append("%d from the register's hours" % self.sources["hours"])
        if self.sources.get("scale"):
            parts.append("%d size word(s) through policy.roadmap.effortScale, read as hours"
                         % self.sources["scale"])
        return "hours: " + ("; ".join(parts) if parts else "no items")

    def provenance(self) -> dict:
        return {"unit": self.unit, "basis": self.basis, "kind": self.kind,
                "sources": dict(self.sources), "describe": self.describe()}


def _some(names, limit: int = 5) -> str:
    names = list(names)
    return ", ".join(names[:limit]) + ("…" if len(names) > limit else "")


def total(items, *, basis: str, scale: dict, fields, ledger_hours=None) -> Sum:
    """The effort of ``items`` on ``basis`` (``hours`` or ``size``).

    Each item needs ``id``, ``effort`` (size word) and ``effort_hours`` attributes.
    ``fields`` are the canonical fields the source serves; an item may carry its own
    ``from_ledger`` attribute (True when its hours or size came from the ledger).
    """
    items = list(items)
    fields = set(fields or ())
    result = Sum(basis=basis)
    if basis == SIZE:
        if "effort" not in fields:
            result.missing = ["effort (the register has no effort field)"]
            return result
        unsized = [i.id for i in items if not i.effort]
        unscaled = sorted({i.effort for i in items if i.effort and i.effort.lower() not in scale})
        if unsized:
            result.missing.append("effort for %d item(s): %s" % (len(unsized), _some(unsized)))
        if unscaled:
            result.missing.append("effort scale entries for: %s" % ", ".join(unscaled))
        if result.missing:
            return result
        result.value = float(sum(scale[i.effort.lower()] for i in items))
        result.sources = {"scale": len(items)}
        return result

    if HOURS_FIELD not in fields and "effort" not in fields:
        result.missing = ["effort_hours (the register has no hours or effort field)"]
        return result
    value = 0.0
    sources = {"ledger": 0, "hours": 0, "scale": 0}
    unreadable, unsized, unscaled = [], [], set()
    for item in items:
        raw_hours = str(getattr(item, "effort_hours", "") or "").strip()
        hours = parse_hours(raw_hours) if raw_hours else None
        if hours is not None:
            value += hours
            sources["ledger" if getattr(item, "from_ledger", False) else "hours"] += 1
        elif raw_hours:
            unreadable.append("%s (%r)" % (item.id, raw_hours))
        elif item.effort and item.effort.lower() in scale:
            value += scale[item.effort.lower()]
            sources["scale"] += 1
        elif item.effort:
            unscaled.add(item.effort)
        else:
            unsized.append(item.id)
    if unreadable:
        result.missing.append("a readable hours figure for %d item(s): %s"
                              % (len(unreadable), _some(unreadable)))
    if unsized:
        result.missing.append("hours or a size word for %d item(s): %s"
                              % (len(unsized), _some(unsized)))
    if unscaled:
        result.missing.append("effort scale entries for: %s" % ", ".join(sorted(unscaled)))
    result.sources = {k: v for k, v in sources.items() if v}
    if result.missing:
        return result
    result.value = round(value, 4)
    return result


def over_limit(items, limit) -> list:
    """``[(id, hours)]`` of items whose hours exceed ``limit``: candidates to split."""
    if not limit:
        return []
    found = []
    for item in items:
        hours = parse_hours(getattr(item, "effort_hours", ""))
        if hours is not None and hours > float(limit):
            found.append((item.id, hours))
    return found
