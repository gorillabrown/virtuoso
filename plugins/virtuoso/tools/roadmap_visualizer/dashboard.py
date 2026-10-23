"""The board's Dashboard: KPI tiles with provenance, and slicers built from the data.

The tiles restate ``kpi.compute`` and ``summarize_health`` exactly; the page only
re-counts them for a filtered view. A slicer exists for Complete / Incomplete always,
and for any field holding two or more distinct values, never for a hard-coded list.
"""
from __future__ import annotations

from tools.governance.providers import base, kpi
from tools.governance.structure import _approved_index
from tools.roadmap_visualizer.board import UNASSIGNED, approved_structure

#: Mapped fields offered as slicers, in this order, when the data varies.
SLICER_FIELDS = (
    ("status", "Status"),
    ("workstream", "Workstream"),
    ("deliverable", "Deliverable"),
    ("written_status", "Written"),
    ("effort", "Effort"),
    ("group", "Group"),
)
#: An unmapped column becomes a slicer only when it reads like a category.
MAX_EXTRA_VALUES = 10
#: A deliverable longer than this is shortened on its slicer, as the workstream chart does.
FACET_WIDTH = 14
WRITTEN_ORDER = (base.FULL_SPEC, base.STUB)
WRITTEN_LABELS = {base.FULL_SPEC: "Full Spec", base.STUB: "Stub"}


def structure_index(structure) -> dict | None:
    """``{spelling: id}`` for an approved structure (``structure._approved_index``), or
    ``None`` without one."""
    return _approved_index(structure)[1] if structure else None


def facets(item, structured: bool = False, index: dict | None = None) -> dict:
    """The values a row is sliced by: canonical where a vocabulary exists. A deliverable
    is one only under an approved structure (``structured``). With that structure's
    ``index`` (:func:`structure_index`), a stored name reads as its id, so one workstream
    is one value; a value the structure does not know stays as stored."""
    workstream, deliverable = item.workstream, item.deliverable
    if index:
        spelled = (workstream or "").strip().lower()
        if not spelled.startswith("d:"):   # "d:" keys are deliverables
            workstream = index.get(spelled, workstream)
        deliverable = index.get("d:" + (deliverable or "").strip().lower(), deliverable)
    out = {
        "complete": "complete" if item.is_terminal else "incomplete",
        "status": item.status,
        "workstream": workstream,
        "written_status": item.written_status,
        "effort": item.effort,
        "group": item.group,
    }
    if structured and deliverable:          # absent, not blank: a page without is unchanged
        out["deliverable"] = deliverable
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
        "workstream": _names(project_policy.workstreams),
        # Workstreams read the pre-1.15.0 lanes too; deliverables exist only in a valid structure.
        "deliverable": _names(d for w in approved_structure(project_policy)
                              for d in w.get("deliverables") or []),
        # Not a slicer: the approved structure the workstream and deliverable values resolve by.
        "structure": approved_structure(project_policy),
    }


def _ordered(values: list[str], order: list[str], names: dict | None = None) -> list[str]:
    """Policy order first (matched without case, by a value or its ``names`` entry), then
    first appearance."""
    rank = {str(v).lower(): i for i, v in enumerate(order or [])}

    def key(v):
        return v.lower() if v.lower() in rank else str((names or {}).get(v, "")).lower()
    known = sorted((v for v in values if key(v) in rank), key=lambda v: rank[key(v)])
    return known + [v for v in values if key(v) not in rank]


def _structure_names(structure) -> dict:
    """``{key: {id: name}}`` for the workstream and deliverable slicers."""
    return {"workstream": {w.get("id"): w.get("name") or w.get("id") for w in structure},
            "deliverable": {d.get("id"): d.get("name") or d.get("id") for w in structure
                            for d in w.get("deliverables") or []}}


def slicers(items, columns, orders: dict, headers: dict | None = None, *,
            structured: bool = False) -> list[dict]:
    """The slicers the data supports, each with its values in display order.
    ``structured``: a structure is approved, so a blank workstream or deliverable is
    "Unassigned" rather than "(none)"."""
    out = [{"key": "complete", "label": "Complete / Incomplete",
            "values": ["complete", "incomplete"],
            "labels": {"complete": "Complete", "incomplete": "Incomplete"}}]
    structure = (orders.get("structure") or []) if structured else []
    named = _structure_names(structure)
    rows = [facets(item, structured, structure_index(structure)) for item in items]

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
            entry.setdefault("labels", {})[""] = (
                UNASSIGNED if structured and key in ("workstream", "deliverable") else "(none)")
        return entry

    for key, label in SLICER_FIELDS:
        values = distinct(key)
        if len(values) + has_blank(key) < 2:       # one value and blanks is still a choice
            continue
        names = named.get(key, {})
        entry = {"key": key, "label": (headers or {}).get(key) or label,
                 "values": _ordered(values, orders.get(key, []), names)}
        if key == "written_status":
            entry["labels"] = dict(WRITTEN_LABELS)
        shown = {v: str(names[v]) for v in values if v in names and names[v] != v}
        if shown:                           # an id is labelled by its name
            entry["labels"] = shown
        if key == "deliverable":
            long = {v: shown.get(v, v)[:FACET_WIDTH - 1] + "…" for v in values
                    if len(shown.get(v, v)) > FACET_WIDTH}
            if long:
                entry["labels"] = dict(entry.get("labels", {}), **long)
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
