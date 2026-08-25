"""Derived metrics, with provenance and honest gaps (items 29, 30).

Every metric states which provider produced it, when the snapshot was taken, and
which fields it read. A metric whose inputs are missing is returned as
``not computable`` together with the exact inputs that were missing — it is never
approximated, and never quietly dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import base

#: A generic t-shirt scale used when a project declares none. It is a *default*,
#: not a requirement: set ``policy.roadmap.effortScale`` to your own.
DEFAULT_EFFORT_SCALE = {
    "xs": 0.5, "xs-s": 0.75, "s": 1, "s-m": 2, "m": 3, "m-l": 5, "l": 8, "xl": 20,
}


@dataclass
class Metric:
    name: str
    value: object = None
    computable: bool = True
    missing_inputs: list[str] = field(default_factory=list)
    unit: str = ""

    def as_dict(self) -> dict:
        if self.computable:
            data = {"name": self.name, "value": self.value}
            if self.unit:
                data["unit"] = self.unit
            return data
        return {"name": self.name, "value": None, "computable": False,
                "missingInputs": list(self.missing_inputs),
                "note": "not computable"}


@dataclass
class MetricSet:
    metrics: list[Metric]
    provenance: dict

    def as_dict(self) -> dict:
        return {
            "metrics": [m.as_dict() for m in self.metrics],
            "provenance": self.provenance,
        }

    def get(self, name: str) -> Metric | None:
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def render(self) -> str:
        lines = []
        for metric in self.metrics:
            if metric.computable:
                lines.append("  %-28s %s%s" % (metric.name, metric.value,
                                               (" " + metric.unit) if metric.unit else ""))
            else:
                lines.append("  %-28s not computable (missing: %s)"
                             % (metric.name, ", ".join(metric.missing_inputs)))
        provenance = self.provenance
        lines.append("")
        lines.append("  source: %s via %s, snapshot %s%s"
                     % (provenance.get("source"), provenance.get("provider"),
                        provenance.get("takenAt"),
                        "  [STALE: %s]" % provenance.get("staleReason")
                        if provenance.get("stale") else ""))
        return "\n".join(lines)


def compute(snapshot: base.Snapshot, *, effort_scale: dict | None = None,
            dispatch_buffer: int = 5) -> MetricSet:
    scale = {str(k).lower(): v for k, v in (effort_scale or DEFAULT_EFFORT_SCALE).items()}
    items = snapshot.items
    fields = set(snapshot.fields)
    metrics: list[Metric] = []

    counts = {status: 0 for status in base.CANONICAL_STATUSES}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1

    metrics.append(Metric("total-items", len(items), unit="items"))
    for status in base.CANONICAL_STATUSES:
        metrics.append(Metric("count-%s" % status, counts.get(status, 0), unit="items"))

    if "status" not in fields:
        metrics.append(Metric("percent-complete-by-count", computable=False,
                              missing_inputs=["status"]))
    elif not items:
        metrics.append(Metric("percent-complete-by-count", computable=False,
                              missing_inputs=["work items"]))
    else:
        done = sum(counts.get(s, 0) for s in base.TERMINAL_STATUSES)
        metrics.append(Metric("percent-complete-by-count", round(100.0 * done / len(items), 1),
                              unit="%"))

    # -- effort-weighted progress ------------------------------------------
    missing_effort = [i.id for i in items if not i.effort]
    unscaled = sorted({i.effort for i in items if i.effort and i.effort.lower() not in scale})
    if "effort" not in fields:
        for name in ("total-effort", "completed-effort", "percent-complete-by-effort"):
            metrics.append(Metric(name, computable=False, missing_inputs=["effort"]))
    elif missing_effort or unscaled:
        missing = []
        if missing_effort:
            missing.append("effort for %d item(s): %s"
                           % (len(missing_effort), ", ".join(missing_effort[:5])
                              + ("…" if len(missing_effort) > 5 else "")))
        if unscaled:
            missing.append("effort scale entries for: %s" % ", ".join(unscaled))
        for name in ("total-effort", "completed-effort", "percent-complete-by-effort"):
            metrics.append(Metric(name, computable=False, missing_inputs=missing))
    else:
        total = sum(scale[i.effort.lower()] for i in items)
        done = sum(scale[i.effort.lower()] for i in items if i.is_terminal)
        metrics.append(Metric("total-effort", round(total, 2), unit="points"))
        metrics.append(Metric("completed-effort", round(done, 2), unit="points"))
        metrics.append(Metric(
            "percent-complete-by-effort",
            round(100.0 * done / total, 1) if total else 0.0, unit="%"))

    # -- dispatch buffer ----------------------------------------------------
    if dispatch_buffer <= 0:
        metrics.append(Metric("dispatch-buffer-target", 0, unit="items"))
        metrics.append(Metric("dispatch-buffer-filled", 0, unit="items"))
    elif "written_status" not in fields:
        metrics.append(Metric("dispatch-buffer-target", dispatch_buffer, unit="items"))
        metrics.append(Metric("dispatch-buffer-filled", computable=False,
                              missing_inputs=["written_status"]))
    else:
        active = [i for i in items if not i.is_terminal]
        active.sort(key=lambda i: (i.sequence is None, i.sequence or 0, i.id))
        head = active[:dispatch_buffer]
        filled = sum(1 for i in head if i.written_status == base.FULL_SPEC)
        metrics.append(Metric("dispatch-buffer-target", dispatch_buffer, unit="items"))
        metrics.append(Metric("dispatch-buffer-filled", filled, unit="items"))

    return MetricSet(metrics=metrics, provenance=snapshot.provenance())
