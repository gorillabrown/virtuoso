"""The board's Dashboard: KPI tiles with provenance, and slicers built from the data.

The tiles restate ``kpi.compute`` and ``summarize_health`` exactly; the page only
re-counts them for a filtered view. A slicer exists for Complete / Incomplete always,
and for any field holding two or more distinct values, never for a hard-coded list.
"""
from __future__ import annotations

from tools.governance.providers import base, kpi

#: Mapped fields offered as slicers, in this order, when the data varies.
SLICER_FIELDS = (
    ("status", "Status"),
    ("lane", "Lane"),
    ("written_status", "Written"),
    ("effort", "Effort"),
    ("group", "Group"),
)
#: An unmapped column becomes a slicer only when it reads like a category.
MAX_EXTRA_VALUES = 10
WRITTEN_ORDER = (base.FULL_SPEC, base.STUB)
WRITTEN_LABELS = {base.FULL_SPEC: "Full Spec", base.STUB: "Stub"}


def facets(item) -> dict:
    """The values a row is sliced by: canonical where a vocabulary exists."""
    out = {
        "complete": "complete" if item.is_terminal else "incomplete",
        "status": item.status,
        "lane": item.lane,
        "written_status": item.written_status,
        "effort": item.effort,
        "group": item.group,
    }
    for header, value in item.extra.items():
        out["extra:" + header] = "" if value is None else str(value).strip()
    return out


def _names(values) -> list[str]:
    out = []
    for value in values or []:
        name = (value.get("name") or value.get("id")) if isinstance(value, dict) else value
        if name not in (None, ""):
            out.append(str(name))
    return out


def policy_orders(project_policy) -> dict:
    """``{field: [values in the order policy declares]}``."""
    scale = project_policy.get("roadmap.effortScale") or kpi.DEFAULT_EFFORT_SCALE
    return {
        "status": list(base.CANONICAL_STATUSES),
        "written_status": list(WRITTEN_ORDER),
        "effort": [str(k) for k in scale],
        "lane": _names(project_policy.get("roadmap.lanes")),
    }


def _ordered(values: list[str], order: list[str]) -> list[str]:
    """Policy order first (matched without case), then first appearance."""
    rank = {str(v).lower(): i for i, v in enumerate(order or [])}
    known = sorted((v for v in values if v.lower() in rank), key=lambda v: rank[v.lower()])
    return known + [v for v in values if v.lower() not in rank]


def slicers(items, columns, orders: dict, headers: dict | None = None) -> list[dict]:
    """The slicers the data supports, each with its values in display order."""
    out = [{"key": "complete", "label": "Complete / Incomplete",
            "values": ["complete", "incomplete"],
            "labels": {"complete": "Complete", "incomplete": "Incomplete"}}]
    rows = [facets(item) for item in items]

    def distinct(key):
        seen: list[str] = []
        for row in rows:
            value = row.get(key, "")
            if value not in ("", None) and value not in seen:
                seen.append(value)
        return seen

    def has_blank(key):
        return any(row.get(key) in ("", None) for row in rows)

    def blanks(key, entry):
        """Rows with no value stay selectable, as "(none)"."""
        if has_blank(key):
            entry["values"].append("")
            entry.setdefault("labels", {})[""] = "(none)"
        return entry

    for key, label in SLICER_FIELDS:
        values = distinct(key)
        if len(values) + has_blank(key) < 2:       # one value and blanks is still a choice
            continue
        entry = {"key": key, "label": (headers or {}).get(key) or label,
                 "values": _ordered(values, orders.get(key, []))}
        if key == "written_status":
            entry["labels"] = dict(WRITTEN_LABELS)
        out.append(blanks(key, entry))
    for column in columns:
        if not column["key"].startswith("extra:"):
            continue
        values = distinct(column["key"])
        if 2 <= len(values) <= MAX_EXTRA_VALUES and len(values) < len(rows):
            out.append(blanks(column["key"],
                              {"key": column["key"], "label": column["header"], "values": values}))
    return out


def _metric(metrics: dict, name: str) -> dict:
    return next((m for m in metrics.get("metrics", []) if m.get("name") == name), {})


def tiles(metrics: dict, health, provenance: dict) -> list[dict]:
    """The KPI tiles, each citing the figure it restates and the snapshot it is from."""
    cite = "%s · %s · snapshot %s" % (provenance.get("provider", "?"),
                                      provenance.get("source", "?"),
                                      provenance.get("takenAt", "?"))

    def tile(key, label, value, origin, detail="", missing=None):
        entry = {"key": key, "label": label, "value": value, "detail": detail,
                 "source": "%s · %s" % (origin, cite)}
        if missing:
            entry["missing"] = list(missing)
        return entry

    total = _metric(metrics, "total-items").get("value", 0) or 0
    done = sum(_metric(metrics, "count-%s" % s).get("value", 0) or 0
               for s in sorted(base.TERMINAL_STATUSES))
    percent = _metric(metrics, "percent-complete-by-count")
    pace = (metrics.get("pace") or [None])[0]
    deadline = (pace or {}).get("deadline") or {}
    return [
        tile("total", "Total", total, "kpi.compute total-items"),
        tile("complete", "Complete", done,
             "kpi.compute count-completed + count-dissolved + count-superseded"),
        tile("incomplete", "Incomplete", total - done, "kpi.compute total-items − complete"),
        tile("percent", "% Complete", percent.get("value"),
             "kpi.compute percent-complete-by-count", missing=percent.get("missingInputs")),
        tile("buffer", "Dispatch buffer", "%s / %s" % (health.buffer_filled,
                                                      health.buffer_target),
             "summarize_health buffer_filled / buffer_target", "ready vs target"),
        tile("blocked", "Blocked", _metric(metrics, "count-blocked").get("value", 0),
             "kpi.compute count-blocked"),
        tile("pace", "Pace", pace["verdict"] if pace else "no deadline",
             "pace_for (earliest declared deadline)",
             "%s · due %s" % (deadline.get("label", ""), deadline.get("date", ""))
             if pace else ""),
    ]
