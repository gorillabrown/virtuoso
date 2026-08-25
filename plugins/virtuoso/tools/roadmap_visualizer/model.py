from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkspaceContext:
    """Where the cockpit reads from — always the registry, never a convention."""

    root: Path
    manifest: Path
    roadmap: Path | None
    reports: Path
    work_register_role: str
    work_register_authority: str
    provider: dict
    compatibility_adapter: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RoadmapSnapshot:
    path: Path | None
    active_codes: list[str]
    completed_codes: list[str]
    full_spec_codes: list[str]
    headings: dict[str, str]
    frontmatter: dict[str, str]


@dataclass(frozen=True)
class HealthSummary:
    head_id: str
    head_title: str
    buffer_target: int
    buffer_filled: int
    counts: dict[str, int]
    drift_count: int
    drift_findings: list[str]
    recommendation: str


@dataclass(frozen=True)
class PlanningModel:
    workspace: WorkspaceContext
    roadmap: RoadmapSnapshot
    items: list[Any]
    metrics: dict
    health: HealthSummary
    provenance: dict


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value
