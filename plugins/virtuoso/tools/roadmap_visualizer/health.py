"""Drift between the roadmap document and the live work register.

Works on canonical statuses from the provider layer, so a project using its own
vocabulary ("Doing Now", "Shipped") is analyzed exactly like one using the
defaults. Nothing here reads a generated workbook cache.
"""
from __future__ import annotations

from tools.governance.providers import base

from .model import HealthSummary, RoadmapSnapshot


def _ordered(items):
    return sorted(items, key=lambda i: (i.sequence is None, i.sequence or 0, i.id))


def _drift_findings(roadmap: RoadmapSnapshot, items) -> list[str]:
    ordered = _ordered(items)
    by_id = {item.id: item for item in ordered}
    register_ids = set(by_id)
    active_codes = set(roadmap.active_codes)
    completed_codes = set(roadmap.completed_codes)
    known = active_codes | completed_codes | register_ids

    findings: list[str] = []
    for code in roadmap.active_codes:
        if code not in register_ids:
            findings.append("In the roadmap's active section but not in the work register: %s"
                            % code)
            continue
        if by_id[code].is_terminal:
            findings.append("Roadmap-active item is terminal in the work register: %s" % code)

    for code in roadmap.completed_codes:
        item = by_id.get(code)
        if item is not None and not item.is_terminal:
            findings.append("Roadmap-completed item is still active in the work register: %s"
                            % code)

    if roadmap.path is not None:
        for item in ordered:
            if item.id not in active_codes and item.id not in completed_codes \
                    and not item.is_terminal:
                findings.append("Work-register item absent from the roadmap: %s" % item.id)

    roadmap_common = [c for c in roadmap.active_codes if c in register_ids]
    register_common = [i.id for i in ordered if i.id in active_codes]
    if roadmap_common and roadmap_common != register_common:
        findings.append("Sequence differs: roadmap=%s; register=%s"
                        % (", ".join(roadmap_common), ", ".join(register_common)))

    for item in ordered:
        for prerequisite in item.prerequisites:
            if prerequisite and prerequisite not in known:
                findings.append("Unknown prerequisite referenced by %s: %s"
                                % (item.id, prerequisite))
    return findings


def _recommendation(drift: int, buffer_filled: int, buffer_target: int,
                    counts: dict, stale: bool) -> str:
    if stale:
        return ("The work register was read from a stale snapshot. Refresh it before acting "
                "on these numbers.")
    if drift:
        return "Run the roadmap-review ceremony: the roadmap and the work register disagree."
    if counts.get(base.QUEUED, 0) == 0 and counts.get(base.BLOCKED, 0):
        return "Run the roadmap-status ceremony: everything active is blocked."
    if buffer_target and buffer_filled < buffer_target:
        return ("Run the roadmap-review ceremony: the dispatch buffer holds %d of %d "
                "specified items." % (buffer_filled, buffer_target))
    return "Proceed: the roadmap and the work register agree."


def summarize_health(roadmap: RoadmapSnapshot, snapshot: base.Snapshot,
                     *, buffer_target: int = 5) -> HealthSummary:
    ordered = _ordered(snapshot.items)
    counts = {status: 0 for status in base.CANONICAL_STATUSES}
    for item in ordered:
        counts[item.status] = counts.get(item.status, 0) + 1

    active = [item for item in ordered if not item.is_terminal]
    head = active[0] if active else None
    buffer_filled = sum(1 for item in active[:buffer_target]
                        if item.written_status == base.FULL_SPEC) if buffer_target else 0

    findings = _drift_findings(roadmap, ordered)
    return HealthSummary(
        head_id=head.id if head else "",
        head_title=head.title if head else "",
        buffer_target=buffer_target,
        buffer_filled=buffer_filled,
        counts=counts,
        drift_count=len(findings),
        drift_findings=findings,
        recommendation=_recommendation(len(findings), buffer_filled, buffer_target,
                                       counts, snapshot.stale),
    )
