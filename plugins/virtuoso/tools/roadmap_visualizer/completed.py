"""The board's Completed tab: the register's terminal items joined with the ledger.

A completed item with no ledger record, and a ledger record with no terminal item,
each still get a row, marked *unreconciled*: the page shows a mismatch, never hides
it. A correcting record replaces the one it names; the row keeps the history. A
damaged record is skipped and listed (readers skip, writers stay strict).
"""
from __future__ import annotations

import re

from tools.governance import learning
from tools.governance.providers import base

from . import board

COMPLETED_GROUPS = (
    ("completed", "Completed", "green", (base.COMPLETED,)),
    ("retired", "Retired", "grey", (base.DISSOLVED, base.SUPERSEDED)),
)

#: The Completed tab's columns, in the design's order. ``optional`` columns appear
#: only when the register carries the field (or, for supersession, when a row names one).
COMPLETED_COLUMNS = (
    ("result", "Result", "label", False),
    ("completedOn", "Completed", "text", False),
    ("closeout", "Close-out", "link", False),
    ("branch", "Branch", "mono", True),
    ("workstream", "Workstream", "label", True),
    ("group", "Group", "chip", True),
    ("loe", "LOE", "label", False),
    ("estimateActual", "Est. → Actual", "estimate", False),
    ("supersededBy", "Superseded by", "ref", True),
    ("notes", "Notes", "text", True),
)

_FIELDS = ("item", "completed", "result", "evidence", "estimate", "actual", "effort")
#: "superseded by <id>": the id is whatever token follows, trailing punctuation dropped.
_SUPERSEDED_RE = re.compile(r"superseded\s+by\W*([A-Za-z0-9][\w.-]*[A-Za-z0-9]|[A-Za-z0-9])",
                            re.I)


def _version(record) -> dict:
    return {"record": record.record_id, "item": record.item_id,
            "completed": record.completed, "result": record.result,
            "evidence": record.evidence, "estimate": record.effort_estimate,
            "actual": record.effort_actual, "effort": record.effort}


def effective_records(records) -> tuple[list[dict], list[str]]:
    """Ledger records with corrections applied, in ledger order. A correction's
    non-blank fields replace the original's; ``history`` lists every version."""
    effective: dict = {}
    order: list[str] = []
    problems: list[str] = []
    #: A correction's own id -> the original it amends, so a correction of a
    #: correction lands on the same original.
    alias: dict = {}
    for index, record in enumerate(records):
        label = record.record_id or "row %d" % (index + 1)
        if record.corrects:
            target = alias.get(record.corrects, record.corrects)
            entry = effective.get(target)
            if entry is not None and record.record_id:
                alias[record.record_id] = target
            if entry is None:
                problems.append("ledger record %s corrects %s, which is not in the ledger; "
                                "skipped" % (label, record.corrects))
                continue
            version = _version(record)
            for name in _FIELDS:
                if version[name]:
                    entry[name] = version[name]
            entry["corrected"] = True
            entry["history"].append(version)
            continue
        if not record.item_id or not record.completed:
            problems.append("ledger record %s has no %s; skipped"
                            % (label, "item" if not record.item_id else "completion date"))
            continue
        key = record.record_id or "#%d" % (index + 1)
        if key not in effective:
            order.append(key)
        effective[key] = dict(_version(record), record=key, corrected=False,
                              history=[_version(record)])
    return [effective[key] for key in order], problems


def over_estimate(estimate: str, actual: str) -> bool:
    """Whether the actual duration exceeds the estimate; ``False`` unless both parse."""
    planned, spent = learning.hours(estimate), learning.hours(actual)
    return planned is not None and spent is not None and spent > planned


def superseded_by(item) -> str:
    """The id a retired item names as its replacement, in its notes or any column."""
    for text in [item.notes, *(str(v) for v in item.extra.values())]:
        match = _SUPERSEDED_RE.search(str(text or ""))
        if match:
            return match.group(1)
    for header, value in item.extra.items():
        if header.strip().lower() == "superseded by" and str(value).strip():
            return str(value).strip()
    return ""


def _completed_row(item, entry, statuses, name_key, unreconciled: str) -> dict:
    row = board.row(item, name_key)
    entry = entry or {}
    result = entry.get("result") or item.raw_status or item.status
    canonical = statuses.to_canonical(result) if entry else item.status
    if canonical == base.UNKNOWN and item.status != base.UNKNOWN:
        canonical = item.status          # a result word no vocabulary maps: trust the register
    estimate, actual = entry.get("estimate", ""), entry.get("actual", "")
    values = row["values"]
    values.update({
        "result": result,
        "completedOn": entry.get("completed") or item.completed,
        "closeout": entry.get("evidence") or item.evidence,
        "loe": entry.get("effort") or item.effort,
        "estimateActual": ("%s → %s" % (estimate or "?", actual or "?")
                           if estimate or actual else ""),
        "supersededBy": superseded_by(item),
    })
    row.update({
        "result": canonical,
        "retired": canonical in (base.DISSOLVED, base.SUPERSEDED),
        "over": over_estimate(estimate, actual),
        "record": entry.get("record", ""),
        "corrected": bool(entry.get("corrected")),
        "earlier": entry.get("earlier", 0),
        "history": entry.get("history", []),
        "unreconciled": unreconciled,
        "warn": "",                     # a ledger-only row has no register status to doubt
    })
    return row


def completed_rows(items, records, statuses, name_key: str = "", *,
                   ledger: bool = True) -> tuple[list[dict], list[str]]:
    """Every terminal item and every ledger record, newest completion first.

    ``ledger=False`` (no ledger registered): rows come from the register alone and
    nothing is marked unreconciled, because there is nothing to reconcile against.
    """
    entries, problems = effective_records(records if ledger else [])
    by_item: dict = {}
    for entry in entries:
        by_item.setdefault(entry["item"], []).append(entry)
    register = {item.id: item for item in items}

    def latest(found):
        """The newest completion; earlier ones join its history, never vanish."""
        found = sorted(found, key=lambda e: e["completed"])
        if not found:
            return None
        newest = dict(found[-1])
        earlier = [version for entry in found[:-1] for version in entry["history"]]
        newest["history"] = earlier + newest["history"]
        newest["earlier"] = len(found) - 1
        return newest

    rows = []
    for item in items:
        if not item.is_terminal:
            continue
        found = by_item.pop(item.id, [])
        reason = "" if found or not ledger else "no ledger record for this item"
        rows.append(_completed_row(item, latest(found), statuses, name_key, reason))
    for item_id, found in by_item.items():
        item = register.get(item_id)
        reason = ("the register has no item %s" % item_id if item is None else
                  "the register shows %s as %s" % (item_id, item.raw_status or item.status))
        rows.append(_completed_row(item or base.WorkItem(id=item_id), latest(found), statuses,
                                   name_key, reason))
    rows.sort(key=lambda r: r["id"])
    rows.sort(key=lambda r: str(r["values"]["completedOn"] or ""), reverse=True)
    return rows, problems


def completed_groups(rows) -> list[dict]:
    """Completed, then Retired; a row whose result is not terminal stays in Completed
    (it is unreconciled and says so)."""
    out = []
    for key, title, rail, _statuses in COMPLETED_GROUPS:
        ids = [r["id"] for r in rows if r["retired"] == (key == "retired")]
        if ids:
            out.append({"key": key, "title": title, "rail": rail, "ids": ids})
    return out


def completed_columns(fields, headers: dict, rows, items, name_key: str = "") -> list[dict]:
    carried = set(fields or [])
    out = []
    for key, label, kind, optional in COMPLETED_COLUMNS:
        if optional and key == "supersededBy":
            if not any(r["values"].get("supersededBy") for r in rows):
                continue
        elif optional and key not in carried:
            continue
        header = (headers or {}).get(key) or label
        if key == "loe":
            header = (headers or {}).get("effort") or label
        out.append({"key": key, "header": header, "kind": kind})
    terminal = [i for i in items if i.is_terminal]
    for header in board.extra_headers(terminal, name_key):
        out.append({"key": "extra:" + header, "header": header, "kind": "text"})
    return out
