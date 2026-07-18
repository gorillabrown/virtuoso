from __future__ import annotations

from .model import HealthSummary, RoadmapSnapshot, SprintRow


DONE_STATUSES = {"Dissolved", "Superseded"}


def _is_completed(status: str) -> bool:
    return status.startswith("Completed")


def _is_done(status: str) -> bool:
    return _is_completed(status) or status in DONE_STATUSES


def _queue_rows(rows: list[SprintRow]) -> list[SprintRow]:
    return sorted(
        rows,
        key=lambda row: (
            row.seq is None,
            row.seq or 999999,
            row.code,
        ),
    )


def _drift_findings(roadmap: RoadmapSnapshot, rows: list[SprintRow]) -> list[str]:
    ordered_rows = _queue_rows(rows)
    rows_by_code = {row.code: row for row in ordered_rows}
    queue_codes = {row.code for row in ordered_rows}
    active_codes = set(roadmap.active_codes)
    completed_codes = set(roadmap.completed_codes)
    known_codes = active_codes | completed_codes | queue_codes

    findings: list[str] = []

    for code in roadmap.active_codes:
        if code not in queue_codes:
            findings.append(f"Missing from sprint queue: {code}")
            continue
        row = rows_by_code[code]
        if _is_done(row.implementation_status):
            findings.append(f"Roadmap-active sprint marked done in queue: {code}")

    for code in roadmap.completed_codes:
        row = rows_by_code.get(code)
        if row is not None and not _is_done(row.implementation_status):
            findings.append(f"Roadmap-completed sprint still active in queue: {code}")

    for row in ordered_rows:
        if row.code not in active_codes and row.code not in completed_codes:
            findings.append(
                f"Queue row not present in roadmap active section: {row.code}"
            )

    roadmap_common = [code for code in roadmap.active_codes if code in queue_codes]
    queue_common = [row.code for row in ordered_rows if row.code in active_codes]
    if roadmap_common and roadmap_common != queue_common:
        findings.append(
            "Queue order differs from roadmap order: "
            f"roadmap={', '.join(roadmap_common)}; queue={', '.join(queue_common)}"
        )

    for row in ordered_rows:
        for dependency in row.dependencies:
            if dependency not in known_codes:
                findings.append(
                    f"Unknown dependency referenced by {row.code}: {dependency}"
                )

    return findings


def _dashboard_staleness(dashboard: dict | None, counts: dict[str, int]) -> list[str]:
    if not dashboard:
        return []
    labels = {
        "total": "total",
        "queued": "queued",
        "in_flight": "in flight",
        "blocked": "blocked",
        "completed": "completed",
    }
    findings: list[str] = []
    for key, label in labels.items():
        cached = dashboard.get(key)
        if cached is None:
            continue
        try:
            cached_int = int(cached)
        except (TypeError, ValueError):
            continue
        live = counts.get(key)
        if live is None:
            continue
        if cached_int != live:
            findings.append(
                f"Dashboard cache stale: {label} shows {cached_int} but catalog has "
                f"{live} - run recalc.py"
            )
    return findings


def _recommendation(
    drift_count: int,
    staleness_count: int,
    full_spec_buffer: int,
    queued_count: int,
    blocked_count: int,
) -> str:
    if staleness_count:
        return "Run recalc.py: the sprint-queue Dashboard cache is stale."
    if drift_count:
        return "Run /roadmap-review to reconcile: roadmap and sprint queue are out of sync."
    if queued_count == 0 and blocked_count:
        return "Run /roadmap-status: queue has blockers and no queued sprint."
    if full_spec_buffer > 0:
        return "Proceed: queue is aligned."
    if full_spec_buffer < 5:
        return "Run /roadmap-review: full-spec buffer is below 5."
    return "Proceed: queue is aligned."


def summarize_health(
    roadmap: RoadmapSnapshot,
    rows: list[SprintRow],
    dashboard: dict | None = None,
) -> HealthSummary:
    ordered_rows = _queue_rows(rows)

    queued_count = sum(
        1 for row in ordered_rows if row.implementation_status == "Queued"
    )
    in_flight_count = sum(
        1 for row in ordered_rows if row.implementation_status == "In Flight"
    )
    blocked_count = sum(
        1 for row in ordered_rows if row.implementation_status == "Blocked"
    )
    completed_count = sum(
        1 for row in ordered_rows if _is_completed(row.implementation_status)
    )
    full_spec_buffer = sum(
        1
        for row in ordered_rows
        if row.implementation_status == "Queued" and row.written_status == "Full Spec"
    )

    head_code = roadmap.active_codes[0] if roadmap.active_codes else ""
    if not head_code and ordered_rows:
        head_code = ordered_rows[0].code

    drift_findings = _drift_findings(roadmap, ordered_rows)
    staleness_findings = _dashboard_staleness(
        dashboard,
        {
            "total": len(ordered_rows),
            "queued": queued_count,
            "in_flight": in_flight_count,
            "blocked": blocked_count,
            "completed": completed_count,
        },
    )
    all_findings = drift_findings + staleness_findings

    return HealthSummary(
        head_code=head_code,
        full_spec_buffer=full_spec_buffer,
        queued_count=queued_count,
        in_flight_count=in_flight_count,
        blocked_count=blocked_count,
        completed_count=completed_count,
        drift_count=len(all_findings),
        drift_findings=all_findings,
        recommendation=_recommendation(
            len(drift_findings),
            len(staleness_findings),
            full_spec_buffer,
            queued_count,
            blocked_count,
        ),
    )
