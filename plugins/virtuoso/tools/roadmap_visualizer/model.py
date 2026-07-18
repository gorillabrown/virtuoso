from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    manifest: Path
    roadmap: Path
    sprint_queue: Path
    reports: Path


@dataclass(frozen=True)
class SprintRow:
    seq: int | None
    code: str
    phase: str
    stage: str
    title: str
    loe: str
    dependencies: list[str]
    implementation_status: str
    written_status: str
    branch: str
    date_started: str
    date_completed: str
    close_out_file: str
    description: str
    notes: str


@dataclass(frozen=True)
class RoadmapSnapshot:
    path: Path
    active_codes: list[str]
    completed_codes: list[str]
    full_spec_codes: list[str]
    headings: dict[str, str]
    frontmatter: dict[str, str]


@dataclass(frozen=True)
class HealthSummary:
    head_code: str
    full_spec_buffer: int
    queued_count: int
    in_flight_count: int
    blocked_count: int
    completed_count: int
    drift_count: int
    drift_findings: list[str]
    recommendation: str


@dataclass(frozen=True)
class PlanningModel:
    workspace: WorkspacePaths
    roadmap: RoadmapSnapshot
    sprints: list[SprintRow]
    dashboard: dict[str, Any]
    health: HealthSummary


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value
