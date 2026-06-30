# Roadmap Sprint Queue Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only static HTML planning cockpit that visualizes a manifest-based Virtuoso roadmap and sprint queue.

**Architecture:** A Python CLI reads `Virtuoso/workspace-layout.json`, parses the canonical `Roadmap.md`, reads `sprint-queue.xlsx` with `openpyxl`, computes health and drift findings, and writes one self-contained HTML report. The roadmap is the source of truth; the workbook is a structured mirror, and disagreement is surfaced as drift.

**Tech Stack:** Python standard library, `openpyxl`, vanilla HTML/CSS/JS, existing `pytest` test style.

---

## File Structure

- Create `tools/roadmap_visualizer/__init__.py`: package marker and public version.
- Create `tools/roadmap_visualizer/model.py`: dataclasses plus JSON serialization helpers.
- Create `tools/roadmap_visualizer/workspace.py`: manifest-first workspace path loading.
- Create `tools/roadmap_visualizer/workbook.py`: workbook catalog/dashboard parsing.
- Create `tools/roadmap_visualizer/roadmap.py`: markdown roadmap parsing.
- Create `tools/roadmap_visualizer/health.py`: drift detection, KPIs, planning recommendation.
- Create `tools/roadmap_visualizer/render.py`: self-contained HTML renderer.
- Create `tools/roadmap_visualizer/generate.py`: CLI entry point.
- Create `scripts/test_roadmap_visualizer.py`: unit and end-to-end tests.
- Modify `README.md`: add a short visualizer usage section after the workspace section.

The generator is intentionally read-only. It creates only the requested output HTML and the containing reports directory. It never edits `Roadmap.md`, `sprint-queue.xlsx`, or `workspace-layout.json`.

---

### Task 1: Package Skeleton and Shared Model

**Files:**
- Create: `tools/roadmap_visualizer/__init__.py`
- Create: `tools/roadmap_visualizer/model.py`
- Test: `scripts/test_roadmap_visualizer.py`

- [ ] **Step 1: Write the failing import/model test**

Add this file:

```python
import json
from pathlib import Path

from openpyxl import Workbook


def test_model_jsonable_handles_paths_and_nested_dataclasses():
    from tools.roadmap_visualizer.model import (
        HealthSummary,
        PlanningModel,
        RoadmapSnapshot,
        SprintRow,
        WorkspacePaths,
        to_jsonable,
    )

    root = Path("C:/project")
    model = PlanningModel(
        workspace=WorkspacePaths(
            root=root,
            manifest=root / "Virtuoso" / "workspace-layout.json",
            roadmap=root / "Project Documentation" / "1 governance" / "Roadmap.md",
            sprint_queue=root / "Project Documentation" / "2 operational" / "sprint-queue.xlsx",
            reports=root / "Virtuoso" / "reports",
        ),
        roadmap=RoadmapSnapshot(
            path=root / "Project Documentation" / "1 governance" / "Roadmap.md",
            active_codes=["SK-001"],
            completed_codes=[],
            full_spec_codes=["SK-001"],
            headings={"SK-001": "First sprint"},
            frontmatter={"roadmap_doc": "Roadmap.md"},
        ),
        sprints=[
            SprintRow(
                priority="1",
                seq=1,
                code="SK-001",
                phase="Phase 1",
                stage="Stage 1",
                title="First sprint",
                loe="M",
                dependencies=[],
                implementation_status="Queued",
                written_status="Full Spec",
                branch="",
                date_started="",
                date_completed="",
                close_out_file="",
                description="",
                notes="",
                done=False,
                sort_key="1",
            )
        ],
        dashboard={"total": 1},
        health=HealthSummary(
            head_code="SK-001",
            full_spec_buffer=1,
            queued_count=1,
            in_flight_count=0,
            blocked_count=0,
            completed_count=0,
            drift_count=0,
            drift_findings=[],
            recommendation="Proceed: queue is aligned.",
        ),
    )

    payload = to_jsonable(model)
    assert payload["workspace"]["root"].endswith("project")
    assert payload["roadmap"]["active_codes"] == ["SK-001"]
    assert payload["sprints"][0]["code"] == "SK-001"
    assert json.dumps(payload)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_model_jsonable_handles_paths_and_nested_dataclasses -q
```

Expected: fail with `ModuleNotFoundError: No module named 'tools'` or an import error for `tools.roadmap_visualizer.model`.

- [ ] **Step 3: Add the package marker**

Create `tools/roadmap_visualizer/__init__.py`:

```python
"""Static planning cockpit generator for Virtuoso roadmap workspaces."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Add the shared model dataclasses**

Create `tools/roadmap_visualizer/model.py`:

```python
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
    priority: str
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
    done: bool
    sort_key: str


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
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_model_jsonable_handles_paths_and_nested_dataclasses -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit**

```powershell
git add tools/roadmap_visualizer/__init__.py tools/roadmap_visualizer/model.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): add planning model"
```

---

### Task 2: Manifest-First Workspace Loader

**Files:**
- Create: `tools/roadmap_visualizer/workspace.py`
- Modify: `scripts/test_roadmap_visualizer.py`

- [ ] **Step 1: Write failing workspace loader tests**

Append to `scripts/test_roadmap_visualizer.py`:

```python
def test_workspace_loader_requires_manifest(tmp_path):
    from tools.roadmap_visualizer.workspace import load_workspace

    try:
        load_workspace(tmp_path)
    except FileNotFoundError as exc:
        message = str(exc)
    else:
        raise AssertionError("load_workspace should require Virtuoso/workspace-layout.json")

    assert "Virtuoso/workspace-layout.json" in message
    assert "manifest-based workspace" in message


def test_workspace_loader_resolves_manifest_paths(tmp_path):
    import json

    from tools.roadmap_visualizer.workspace import load_workspace

    manifest = tmp_path / "Virtuoso" / "workspace-layout.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "layout": "plugin-only",
                "paths": {
                    "roadmap": "Project Documentation/1 governance/Roadmap.md",
                    "sprintQueue": "Project Documentation/2 operational/sprint-queue.xlsx",
                },
            }
        ),
        encoding="utf-8",
    )

    paths = load_workspace(tmp_path)

    assert paths.root == tmp_path
    assert paths.manifest == manifest
    assert paths.roadmap == tmp_path / "Project Documentation" / "1 governance" / "Roadmap.md"
    assert paths.sprint_queue == tmp_path / "Project Documentation" / "2 operational" / "sprint-queue.xlsx"
    assert paths.reports == tmp_path / "Virtuoso" / "reports"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_workspace_loader_requires_manifest scripts/test_roadmap_visualizer.py::test_workspace_loader_resolves_manifest_paths -q
```

Expected: fail with import error for `tools.roadmap_visualizer.workspace`.

- [ ] **Step 3: Implement the workspace loader**

Create `tools/roadmap_visualizer/workspace.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from .model import WorkspacePaths


def _resolve(root: Path, rel: str) -> Path:
    path = Path(rel)
    if path.is_absolute():
        return path
    return root / path


def load_workspace(root: Path | str) -> WorkspacePaths:
    root_path = Path(root).resolve()
    manifest = root_path / "Virtuoso" / "workspace-layout.json"
    if not manifest.is_file():
        raise FileNotFoundError(
            "Missing Virtuoso/workspace-layout.json. "
            "The roadmap visualizer requires a manifest-based workspace; "
            "run virtuoso-init with a manifest-capable version before generating the cockpit."
        )

    data = json.loads(manifest.read_text(encoding="utf-8"))
    paths = data.get("paths", {})
    roadmap_rel = paths.get("roadmap")
    queue_rel = paths.get("sprintQueue")
    missing = [name for name, value in (("paths.roadmap", roadmap_rel), ("paths.sprintQueue", queue_rel)) if not value]
    if missing:
        raise ValueError("Invalid workspace-layout.json; missing " + ", ".join(missing))

    return WorkspacePaths(
        root=root_path,
        manifest=manifest,
        roadmap=_resolve(root_path, roadmap_rel),
        sprint_queue=_resolve(root_path, queue_rel),
        reports=root_path / "Virtuoso" / "reports",
    )
```

- [ ] **Step 4: Run the workspace tests**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_workspace_loader_requires_manifest scripts/test_roadmap_visualizer.py::test_workspace_loader_resolves_manifest_paths -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```powershell
git add tools/roadmap_visualizer/workspace.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): load manifest workspace paths"
```

---

### Task 3: Workbook Parser

**Files:**
- Create: `tools/roadmap_visualizer/workbook.py`
- Modify: `scripts/test_roadmap_visualizer.py`

- [ ] **Step 1: Add workbook test helpers and parser test**

Append to `scripts/test_roadmap_visualizer.py`:

```python
CATALOG_HEADERS = [
    "Priority",
    "Seq",
    "Sprint Code",
    "Phase",
    "Stage",
    "Title",
    "LOE",
    "Dependencies",
    "Implementation Status",
    "Written Status",
    "Branch",
    "Date Started",
    "Date Completed",
    "Close-Out File",
    "Description",
    "Notes",
    "Done?",
    "PhaseRank",
    "SizeRank",
    "SortKey",
]


def make_workbook(path, rows):
    wb = Workbook()
    dashboard = wb.active
    dashboard.title = "Dashboard"
    dashboard["B11"] = len(rows)
    dashboard["B12"] = sum(1 for row in rows if str(row[8]).startswith("Completed"))
    dashboard["B13"] = sum(1 for row in rows if row[8] == "Blocked")
    dashboard["B14"] = sum(1 for row in rows if row[8] == "Queued")
    dashboard["B15"] = sum(1 for row in rows if row[8] == "In Flight")
    dashboard["B21"] = 3
    dashboard["B22"] = 0
    dashboard["B23"] = 3
    dashboard["B24"] = 0
    catalog = wb.create_sheet("DATA.sprint-catalog")
    catalog.append(CATALOG_HEADERS)
    for row in rows:
        catalog.append(row)
    wb.save(path)


def test_workbook_parser_reads_catalog_rows_and_dashboard(tmp_path):
    from tools.roadmap_visualizer.workbook import read_workbook

    queue = tmp_path / "sprint-queue.xlsx"
    make_workbook(
        queue,
        [
            [
                "1",
                1,
                "SK-001",
                "Phase 1",
                "Stage 1",
                "First sprint",
                "M",
                "SK-000, SK-BASE",
                "Queued",
                "Full Spec",
                "",
                "",
                "",
                "",
                "A sprint ready for dispatch.",
                "",
                False,
                1,
                4,
                1,
            ]
        ],
    )

    rows, dashboard = read_workbook(queue)

    assert len(rows) == 1
    assert rows[0].code == "SK-001"
    assert rows[0].seq == 1
    assert rows[0].dependencies == ["SK-000", "SK-BASE"]
    assert rows[0].implementation_status == "Queued"
    assert rows[0].written_status == "Full Spec"
    assert dashboard["total"] == 1
    assert dashboard["queued"] == 1
```

- [ ] **Step 2: Run the workbook parser test to verify it fails**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_workbook_parser_reads_catalog_rows_and_dashboard -q
```

Expected: fail with import error for `tools.roadmap_visualizer.workbook`.

- [ ] **Step 3: Implement workbook parsing**

Create `tools/roadmap_visualizer/workbook.py`:

```python
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .model import SprintRow


DASHBOARD_CELLS = {
    "total": "B11",
    "completed": "B12",
    "blocked": "B13",
    "queued": "B14",
    "in_flight": "B15",
    "dissolved": "B16",
    "superseded": "B17",
    "percent_count_complete": "B18",
    "remaining_points": "B21",
    "completed_points": "B22",
    "total_points": "B23",
    "percent_points_complete": "B24",
    "sprints_remaining": "B25",
    "average_points": "B26",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.date().isoformat() if isinstance(value, dt.datetime) else value.isoformat()
    return str(value).strip()


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _clean(value).lower() in {"true", "yes", "y", "1", "done"}


def _dependencies(value: Any) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,;\n]+", text) if part.strip()]


def _find_catalog(wb):
    for name in wb.sheetnames:
        if name.strip().lower() in {"data.sprint-catalog", "catalog", "sprint catalog"}:
            return wb[name]
    for ws in wb.worksheets:
        headers = [_clean(cell.value) for cell in ws[1]]
        if "Sprint Code" in headers:
            return ws
    raise KeyError("No sprint catalog sheet with a 'Sprint Code' header")


def _row_value(row: tuple[Any, ...], index: dict[str, int], name: str) -> Any:
    i = index.get(name)
    if i is None or i >= len(row):
        return None
    return row[i]


def read_workbook(path: Path | str) -> tuple[list[SprintRow], dict[str, Any]]:
    workbook_path = Path(path)
    wb = load_workbook(workbook_path, read_only=True, data_only=True)
    catalog = _find_catalog(wb)
    headers = [_clean(cell.value) for cell in catalog[1]]
    index = {name: i for i, name in enumerate(headers) if name}

    rows: list[SprintRow] = []
    for values in catalog.iter_rows(min_row=2, values_only=True):
        code = _clean(_row_value(values, index, "Sprint Code"))
        if not code:
            continue
        rows.append(
            SprintRow(
                priority=_clean(_row_value(values, index, "Priority")),
                seq=_as_int(_row_value(values, index, "Seq")),
                code=code,
                phase=_clean(_row_value(values, index, "Phase")),
                stage=_clean(_row_value(values, index, "Stage")),
                title=_clean(_row_value(values, index, "Title")),
                loe=_clean(_row_value(values, index, "LOE")),
                dependencies=_dependencies(_row_value(values, index, "Dependencies")),
                implementation_status=_clean(_row_value(values, index, "Implementation Status")),
                written_status=_clean(_row_value(values, index, "Written Status")),
                branch=_clean(_row_value(values, index, "Branch")),
                date_started=_clean(_row_value(values, index, "Date Started")),
                date_completed=_clean(_row_value(values, index, "Date Completed")),
                close_out_file=_clean(_row_value(values, index, "Close-Out File")),
                description=_clean(_row_value(values, index, "Description")),
                notes=_clean(_row_value(values, index, "Notes")),
                done=_as_bool(_row_value(values, index, "Done?")),
                sort_key=_clean(_row_value(values, index, "SortKey")),
            )
        )

    dashboard_ws = wb["Dashboard"] if "Dashboard" in wb.sheetnames else None
    dashboard: dict[str, Any] = {}
    if dashboard_ws is not None:
        for name, cell in DASHBOARD_CELLS.items():
            dashboard[name] = dashboard_ws[cell].value

    return rows, dashboard
```

- [ ] **Step 4: Run the workbook parser test**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_workbook_parser_reads_catalog_rows_and_dashboard -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add tools/roadmap_visualizer/workbook.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): parse sprint queue workbook"
```

---

### Task 4: Roadmap Parser

**Files:**
- Create: `tools/roadmap_visualizer/roadmap.py`
- Modify: `scripts/test_roadmap_visualizer.py`

- [ ] **Step 1: Write roadmap parser tests**

Append to `scripts/test_roadmap_visualizer.py`:

```python
def test_roadmap_parser_extracts_active_completed_and_full_spec_codes(tmp_path):
    from tools.roadmap_visualizer.roadmap import parse_roadmap

    roadmap = tmp_path / "Roadmap.md"
    roadmap.write_text(
        """# Project Roadmap

## Completed Work Summary
| Sprint | Session | Result | Close-Out |
|--------|---------|--------|-----------|
| SK-000 | 2026-06-01 | Complete | Close-Outs/SK-000.md |

## Active & Remaining Sprint Skeletons

### Phase 1

#### SK-001 - Build parser
Full Spec:
Build the parser, wire tests, and verify workbook reading.

Acceptance Criteria:
- Parser reads the workbook.

#### SK-002 - Stub follow-up
One-line stub only.

## Notes

<!-- Frontmatter:
roadmap_doc: Roadmap.md
sprint_queue_doc: sprint-queue.xlsx
-->
""",
        encoding="utf-8",
    )

    result = parse_roadmap(roadmap)

    assert result.active_codes == ["SK-001", "SK-002"]
    assert result.completed_codes == ["SK-000"]
    assert result.full_spec_codes == ["SK-001"]
    assert result.headings["SK-001"] == "Build parser"
    assert result.frontmatter["roadmap_doc"] == "Roadmap.md"
```

- [ ] **Step 2: Run the roadmap parser test to verify it fails**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_roadmap_parser_extracts_active_completed_and_full_spec_codes -q
```

Expected: fail with import error for `tools.roadmap_visualizer.roadmap`.

- [ ] **Step 3: Implement roadmap parsing**

Create `tools/roadmap_visualizer/roadmap.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

from .model import RoadmapSnapshot


SPRINT_CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+\b")
HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
FRONTMATTER_RE = re.compile(r"<!--\s*Frontmatter:\s*(.*?)-->", re.DOTALL | re.IGNORECASE)


def _section(text: str, start_heading: str, stop_heading_level: str = "## ") -> str:
    marker = start_heading.lower()
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == marker:
            start = i + 1
            break
    if start is None:
        return ""
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith(stop_heading_level) and line.strip().lower() != marker:
            break
        out.append(line)
    return "\n".join(out)


def _frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.search(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip('"')
    return out


def _completed_codes(text: str) -> list[str]:
    completed = _section(text, "## Completed Work Summary")
    codes: list[str] = []
    for line in completed.splitlines():
        if not line.strip().startswith("|"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if not parts:
            continue
        match = SPRINT_CODE_RE.search(parts[0])
        if match and match.group(0) not in codes:
            codes.append(match.group(0))
    return codes


def _active_blocks(text: str) -> tuple[list[str], dict[str, str], list[str]]:
    active = _section(text, "## Active & Remaining Sprint Skeletons")
    headings: dict[str, str] = {}
    codes: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    current_code = ""
    current_lines: list[str] = []

    for line in active.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            match = SPRINT_CODE_RE.search(heading.group(2))
            if match:
                if current_code:
                    blocks.append((current_code, current_lines))
                current_code = match.group(0)
                current_lines = []
                if current_code not in codes:
                    codes.append(current_code)
                title = heading.group(2).replace(current_code, "", 1).strip(" -:")
                headings[current_code] = title or current_code
                continue
        if current_code:
            current_lines.append(line)
    if current_code:
        blocks.append((current_code, current_lines))

    full_spec_codes: list[str] = []
    for code, block_lines in blocks:
        block = "\n".join(block_lines).lower()
        has_full_spec = "full spec" in block or "acceptance criteria" in block or "implementation plan" in block
        if has_full_spec:
            full_spec_codes.append(code)

    return codes, headings, full_spec_codes


def parse_roadmap(path: Path | str) -> RoadmapSnapshot:
    roadmap_path = Path(path)
    text = roadmap_path.read_text(encoding="utf-8")
    active_codes, headings, full_spec_codes = _active_blocks(text)
    return RoadmapSnapshot(
        path=roadmap_path,
        active_codes=active_codes,
        completed_codes=_completed_codes(text),
        full_spec_codes=full_spec_codes,
        headings=headings,
        frontmatter=_frontmatter(text),
    )
```

- [ ] **Step 4: Run the roadmap parser test**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_roadmap_parser_extracts_active_completed_and_full_spec_codes -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add tools/roadmap_visualizer/roadmap.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): parse canonical roadmap"
```

---

### Task 5: Health Summary, Drift Detection, and Recommendation

**Files:**
- Create: `tools/roadmap_visualizer/health.py`
- Modify: `scripts/test_roadmap_visualizer.py`

- [ ] **Step 1: Write health/drift tests**

Append to `scripts/test_roadmap_visualizer.py`:

```python
def test_health_summary_treats_roadmap_as_source_of_truth():
    from pathlib import Path

    from tools.roadmap_visualizer.health import summarize_health
    from tools.roadmap_visualizer.model import RoadmapSnapshot, SprintRow

    roadmap = RoadmapSnapshot(
        path=Path("Roadmap.md"),
        active_codes=["SK-001", "SK-002"],
        completed_codes=["SK-000"],
        full_spec_codes=["SK-001"],
        headings={"SK-001": "Build parser", "SK-002": "Stub"},
        frontmatter={},
    )
    rows = [
        SprintRow(
            priority="1",
            seq=1,
            code="SK-002",
            phase="Phase 1",
            stage="Stage 1",
            title="Stub",
            loe="S",
            dependencies=[],
            implementation_status="Queued",
            written_status="Stub",
            branch="",
            date_started="",
            date_completed="",
            close_out_file="",
            description="",
            notes="",
            done=False,
            sort_key="1",
        ),
        SprintRow(
            priority="2",
            seq=2,
            code="SK-003",
            phase="Phase 1",
            stage="Stage 2",
            title="Queue-only sprint",
            loe="M",
            dependencies=["SK-999"],
            implementation_status="Blocked",
            written_status="Full Spec",
            branch="",
            date_started="",
            date_completed="",
            close_out_file="",
            description="",
            notes="",
            done=False,
            sort_key="2",
        ),
    ]

    health = summarize_health(roadmap, rows)

    assert health.head_code == "SK-001"
    assert health.full_spec_buffer == 1
    assert health.queued_count == 1
    assert health.blocked_count == 1
    assert health.drift_count == 3
    assert "Missing from sprint queue: SK-001" in health.drift_findings
    assert "Queue row not present in roadmap active section: SK-003" in health.drift_findings
    assert "Unknown dependency referenced by SK-003: SK-999" in health.drift_findings
    assert health.recommendation == "Run /reconcile: roadmap and sprint queue are out of sync."
```

- [ ] **Step 2: Run the health test to verify it fails**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_health_summary_treats_roadmap_as_source_of_truth -q
```

Expected: fail with import error for `tools.roadmap_visualizer.health`.

- [ ] **Step 3: Implement health and drift logic**

Create `tools/roadmap_visualizer/health.py`:

```python
from __future__ import annotations

from .model import HealthSummary, RoadmapSnapshot, SprintRow


DONE_STATUSES = {"Dissolved", "Superseded"}


def _is_completed(status: str) -> bool:
    return status.startswith("Completed")


def _is_done(status: str) -> bool:
    return _is_completed(status) or status in DONE_STATUSES


def _queue_rows(rows: list[SprintRow]) -> list[SprintRow]:
    return sorted(rows, key=lambda row: (row.seq is None, row.seq or 999999, row.priority, row.code))


def _drift_findings(roadmap: RoadmapSnapshot, rows: list[SprintRow]) -> list[str]:
    findings: list[str] = []
    queue_codes = [row.code for row in _queue_rows(rows)]
    queue_code_set = set(queue_codes)
    roadmap_code_set = set(roadmap.active_codes)
    known_codes = roadmap_code_set | set(roadmap.completed_codes) | queue_code_set

    for code in roadmap.active_codes:
        if code not in queue_code_set:
            findings.append(f"Missing from sprint queue: {code}")

    for code in queue_codes:
        if code not in roadmap_code_set and code not in set(roadmap.completed_codes):
            findings.append(f"Queue row not present in roadmap active section: {code}")

    common_roadmap_order = [code for code in roadmap.active_codes if code in queue_code_set]
    common_queue_order = [code for code in queue_codes if code in roadmap_code_set]
    if common_roadmap_order and common_queue_order and common_roadmap_order != common_queue_order:
        findings.append(
            "Queue order differs from roadmap order: "
            + "roadmap="
            + ", ".join(common_roadmap_order)
            + "; queue="
            + ", ".join(common_queue_order)
        )

    for row in rows:
        for dependency in row.dependencies:
            if dependency not in known_codes:
                findings.append(f"Unknown dependency referenced by {row.code}: {dependency}")

    return findings


def _recommendation(drift_count: int, full_spec_buffer: int, queued_count: int, blocked_count: int) -> str:
    if drift_count:
        return "Run /reconcile: roadmap and sprint queue are out of sync."
    if full_spec_buffer < 5:
        return "Run /roadmap-review: full-spec buffer is below 5."
    if queued_count == 0 and blocked_count:
        return "Run /roadmap-status: queue has blockers and no queued sprint."
    return "Proceed: queue is aligned."


def summarize_health(roadmap: RoadmapSnapshot, rows: list[SprintRow]) -> HealthSummary:
    queue = _queue_rows(rows)
    queued_count = sum(1 for row in rows if row.implementation_status == "Queued")
    in_flight_count = sum(1 for row in rows if row.implementation_status == "In Flight")
    blocked_count = sum(1 for row in rows if row.implementation_status == "Blocked")
    completed_count = sum(1 for row in rows if _is_completed(row.implementation_status))
    full_spec_buffer = sum(
        1
        for row in rows
        if row.implementation_status == "Queued" and row.written_status == "Full Spec"
    )

    active_queue_codes = {row.code for row in queue if not _is_done(row.implementation_status)}
    head_code = ""
    for code in roadmap.active_codes:
        if code in active_queue_codes or code not in {row.code for row in queue}:
            head_code = code
            break
    if not head_code and queue:
        head_code = queue[0].code

    findings = _drift_findings(roadmap, rows)

    return HealthSummary(
        head_code=head_code,
        full_spec_buffer=full_spec_buffer,
        queued_count=queued_count,
        in_flight_count=in_flight_count,
        blocked_count=blocked_count,
        completed_count=completed_count,
        drift_count=len(findings),
        drift_findings=findings,
        recommendation=_recommendation(len(findings), full_spec_buffer, queued_count, blocked_count),
    )
```

- [ ] **Step 4: Run the health test**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_health_summary_treats_roadmap_as_source_of_truth -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add tools/roadmap_visualizer/health.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): summarize planning health"
```

---

### Task 6: Self-Contained HTML Renderer

**Files:**
- Create: `tools/roadmap_visualizer/render.py`
- Modify: `scripts/test_roadmap_visualizer.py`

- [ ] **Step 1: Write renderer test**

Append to `scripts/test_roadmap_visualizer.py`:

```python
def test_renderer_outputs_self_contained_cockpit_html():
    from pathlib import Path

    from tools.roadmap_visualizer.model import (
        HealthSummary,
        PlanningModel,
        RoadmapSnapshot,
        WorkspacePaths,
    )
    from tools.roadmap_visualizer.render import render_html

    root = Path("C:/project")
    model = PlanningModel(
        workspace=WorkspacePaths(
            root=root,
            manifest=root / "Virtuoso" / "workspace-layout.json",
            roadmap=root / "Roadmap.md",
            sprint_queue=root / "sprint-queue.xlsx",
            reports=root / "Virtuoso" / "reports",
        ),
        roadmap=RoadmapSnapshot(
            path=root / "Roadmap.md",
            active_codes=["SK-001"],
            completed_codes=[],
            full_spec_codes=["SK-001"],
            headings={"SK-001": "First sprint"},
            frontmatter={},
        ),
        sprints=[],
        dashboard={"total": 1},
        health=HealthSummary(
            head_code="SK-001",
            full_spec_buffer=1,
            queued_count=1,
            in_flight_count=0,
            blocked_count=0,
            completed_count=0,
            drift_count=0,
            drift_findings=[],
            recommendation="Proceed: queue is aligned.",
        ),
    )

    html = render_html(model)

    assert "<!doctype html>" in html
    assert "Planning Health Cockpit" in html
    assert "Conveyor" in html
    assert "Dependencies" in html
    assert "const MODEL =" in html
    assert "SK-001" in html
    assert "<script src=" not in html
    assert "<link rel=" not in html
```

- [ ] **Step 2: Run renderer test to verify it fails**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_renderer_outputs_self_contained_cockpit_html -q
```

Expected: fail with import error for `tools.roadmap_visualizer.render`.

- [ ] **Step 3: Implement renderer**

Create `tools/roadmap_visualizer/render.py`:

```python
from __future__ import annotations

import html
import json

from .model import PlanningModel, to_jsonable


def render_html(model: PlanningModel) -> str:
    payload = json.dumps(to_jsonable(model), ensure_ascii=True)
    title = "Planning Health Cockpit"
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    :root {{
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --line: #d0d5dd;
      --accent: #2563eb;
      --warn: #b42318;
      --ok: #047857;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 14px;
      line-height: 1.4;
    }}
    header {{
      padding: 20px 28px 12px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{ margin: 0 0 4px; font-size: 24px; letter-spacing: 0; }}
    .subtle {{ color: var(--muted); }}
    main {{ padding: 20px 28px 32px; }}
    .tabs {{ display: flex; gap: 8px; margin-bottom: 16px; }}
    .tabs button {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
    }}
    .tabs button.active {{ border-color: var(--accent); color: var(--accent); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric {{ font-size: 28px; font-weight: 700; }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .recommendation {{ border-left: 4px solid var(--accent); }}
    .warning {{ border-left: 4px solid var(--warn); }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .hidden {{ display: none; }}
    .status {{ font-weight: 600; }}
  </style>
</head>
<body>
  <header>
    <h1>{escaped_title}</h1>
    <div class="subtle" id="workspace"></div>
  </header>
  <main>
    <nav class="tabs" aria-label="Views">
      <button class="active" data-view="cockpit">Cockpit</button>
      <button data-view="conveyor">Conveyor</button>
      <button data-view="dependencies">Dependencies</button>
    </nav>
    <section id="cockpit"></section>
    <section id="conveyor" class="hidden"></section>
    <section id="dependencies" class="hidden"></section>
  </main>
  <script>
    const MODEL = {payload};

    function text(value) {{
      return value === null || value === undefined || value === "" ? "-" : String(value);
    }}

    function metric(label, value) {{
      return `<div class="card"><div class="label">${{label}}</div><div class="metric">${{text(value)}}</div></div>`;
    }}

    function renderCockpit() {{
      const h = MODEL.health;
      const warnings = h.drift_findings.map(item => `<li>${{item}}</li>`).join("");
      document.getElementById("cockpit").innerHTML = `
        <div class="grid">
          ${{metric("Head sprint", h.head_code)}}
          ${{metric("Full-spec buffer", h.full_spec_buffer)}}
          ${{metric("Queued", h.queued_count)}}
          ${{metric("In flight", h.in_flight_count)}}
          ${{metric("Blocked", h.blocked_count)}}
          ${{metric("Drift findings", h.drift_count)}}
        </div>
        <div class="card recommendation" style="margin-top:12px">
          <div class="label">Next planning action</div>
          <div>${{h.recommendation}}</div>
        </div>
        <div class="card warning" style="margin-top:12px">
          <div class="label">Roadmap / queue drift</div>
          <ul>${{warnings || "<li>No drift detected.</li>"}}</ul>
        </div>`;
    }}

    function renderConveyor() {{
      const rows = MODEL.sprints;
      const body = rows.map(row => `
        <tr>
          <td>${{text(row.seq)}}</td>
          <td><strong>${{row.code}}</strong><br>${{row.title}}</td>
          <td>${{row.phase}}<br><span class="subtle">${{row.stage}}</span></td>
          <td>${{row.loe}}</td>
          <td class="status">${{row.implementation_status}}</td>
          <td>${{row.written_status}}</td>
        </tr>`).join("");
      document.getElementById("conveyor").innerHTML = `
        <table>
          <thead><tr><th>Seq</th><th>Sprint</th><th>Phase</th><th>LOE</th><th>Status</th><th>Spec</th></tr></thead>
          <tbody>${{body}}</tbody>
        </table>`;
    }}

    function renderDependencies() {{
      const rows = MODEL.sprints.filter(row => row.dependencies.length);
      const body = rows.map(row => `
        <tr>
          <td><strong>${{row.code}}</strong><br>${{row.title}}</td>
          <td>${{row.dependencies.join(", ")}}</td>
          <td>${{row.implementation_status}}</td>
        </tr>`).join("");
      document.getElementById("dependencies").innerHTML = `
        <table>
          <thead><tr><th>Sprint</th><th>Dependencies</th><th>Status</th></tr></thead>
          <tbody>${{body || `<tr><td colspan="3">No dependencies recorded.</td></tr>`}}</tbody>
        </table>`;
    }}

    function switchView(name) {{
      for (const section of ["cockpit", "conveyor", "dependencies"]) {{
        document.getElementById(section).classList.toggle("hidden", section !== name);
      }}
      for (const button of document.querySelectorAll(".tabs button")) {{
        button.classList.toggle("active", button.dataset.view === name);
      }}
    }}

    document.getElementById("workspace").textContent = MODEL.workspace.root;
    renderCockpit();
    renderConveyor();
    renderDependencies();
    document.querySelector(".tabs").addEventListener("click", event => {{
      const button = event.target.closest("button[data-view]");
      if (button) switchView(button.dataset.view);
    }});
  </script>
</body>
</html>
"""
```

- [ ] **Step 4: Run renderer test**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_renderer_outputs_self_contained_cockpit_html -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add tools/roadmap_visualizer/render.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): render static cockpit html"
```

---

### Task 7: Generator CLI and End-to-End Test

**Files:**
- Create: `tools/roadmap_visualizer/generate.py`
- Modify: `scripts/test_roadmap_visualizer.py`

- [ ] **Step 1: Write end-to-end generator test**

Append to `scripts/test_roadmap_visualizer.py`:

```python
def test_generator_writes_report_from_manifest_workspace(tmp_path):
    import json

    from tools.roadmap_visualizer.generate import generate

    roadmap = tmp_path / "Project Documentation" / "1 governance" / "Roadmap.md"
    queue = tmp_path / "Project Documentation" / "2 operational" / "sprint-queue.xlsx"
    manifest = tmp_path / "Virtuoso" / "workspace-layout.json"
    roadmap.parent.mkdir(parents=True)
    queue.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "layout": "plugin-only",
                "paths": {
                    "roadmap": "Project Documentation/1 governance/Roadmap.md",
                    "sprintQueue": "Project Documentation/2 operational/sprint-queue.xlsx",
                },
            }
        ),
        encoding="utf-8",
    )
    roadmap.write_text(
        """# Project Roadmap

## Completed Work Summary
| Sprint | Session | Result | Close-Out |
|--------|---------|--------|-----------|

## Active & Remaining Sprint Skeletons

#### SK-001 - Build visualizer
Full Spec:
Build the static visualizer.

## Notes
""",
        encoding="utf-8",
    )
    make_workbook(
        queue,
        [
            [
                "1",
                1,
                "SK-001",
                "Phase 1",
                "Stage 1",
                "Build visualizer",
                "M",
                "",
                "Queued",
                "Full Spec",
                "",
                "",
                "",
                "",
                "",
                "",
                False,
                1,
                4,
                1,
            ]
        ],
    )

    output = generate(tmp_path)

    assert output == tmp_path / "Virtuoso" / "reports" / "planning-cockpit.html"
    assert output.is_file()
    html = output.read_text(encoding="utf-8")
    assert "Planning Health Cockpit" in html
    assert "SK-001" in html
    assert "Proceed: queue is aligned." in html
```

- [ ] **Step 2: Run end-to-end test to verify it fails**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_generator_writes_report_from_manifest_workspace -q
```

Expected: fail with import error for `tools.roadmap_visualizer.generate`.

- [ ] **Step 3: Implement generator CLI**

Create `tools/roadmap_visualizer/generate.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from .health import summarize_health
from .model import PlanningModel
from .render import render_html
from .roadmap import parse_roadmap
from .workbook import read_workbook
from .workspace import load_workspace


def build_model(root: Path | str) -> PlanningModel:
    workspace = load_workspace(root)
    roadmap = parse_roadmap(workspace.roadmap)
    rows, dashboard = read_workbook(workspace.sprint_queue)
    health = summarize_health(roadmap, rows)
    return PlanningModel(
        workspace=workspace,
        roadmap=roadmap,
        sprints=rows,
        dashboard=dashboard,
        health=health,
    )


def generate(root: Path | str, output: Path | str | None = None) -> Path:
    model = build_model(root)
    output_path = Path(output) if output else model.workspace.reports / "planning-cockpit.html"
    if not output_path.is_absolute():
        output_path = model.workspace.root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(model), encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a static Virtuoso planning cockpit.")
    parser.add_argument("--root", default=".", help="Project root containing Virtuoso/workspace-layout.json.")
    parser.add_argument("--output", default="", help="Output HTML path. Defaults to Virtuoso/reports/planning-cockpit.html.")
    args = parser.parse_args(argv)
    output = generate(Path(args.root), Path(args.output) if args.output else None)
    print(f"planning cockpit written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run end-to-end test**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py::test_generator_writes_report_from_manifest_workspace -q
```

Expected: `1 passed`.

- [ ] **Step 5: Run the CLI against a temp manifest workspace**

Use the test suite for isolated behavior:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py -q
```

Expected: all visualizer tests pass.

- [ ] **Step 6: Commit**

```powershell
git add tools/roadmap_visualizer/generate.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): generate planning cockpit report"
```

---

### Task 8: README Usage and Validation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add README usage text**

Add this section after the `Virtuoso/workspace-layout.json` paragraph in `README.md`:

```markdown
## Roadmap planning cockpit

Virtuoso includes a read-only static planning cockpit generator for manifest-based
workspaces. It treats `Roadmap.md` as the source of truth and `sprint-queue.xlsx` as a
structured mirror. If they disagree, the report surfaces drift instead of changing files.

Generate the report from a project root:

```bash
python -m tools.roadmap_visualizer.generate --root .
```

The default output is:

```text
Virtuoso/reports/planning-cockpit.html
```

The generator requires `Virtuoso/workspace-layout.json`. Legacy flat workspaces should be
upgraded with a manifest-capable `virtuoso-init` before using the cockpit.
```

- [ ] **Step 2: Run targeted tests**

Run:

```powershell
python -m pytest scripts/test_roadmap_visualizer.py -q
```

Expected: all visualizer tests pass.

- [ ] **Step 3: Run repository validation**

Run:

```powershell
python scripts/validate.py
```

Expected: `All checks passed.`

- [ ] **Step 4: Run the broader test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs: document roadmap planning cockpit"
```

---

### Task 9: Manual Smoke Test on a Real Manifest Workspace

**Files:**
- No source edits expected.
- Runtime output: `Virtuoso/reports/planning-cockpit.html` in the selected test project.

- [ ] **Step 1: Create or choose a manifest workspace**

Use a disposable project where `Virtuoso/workspace-layout.json` exists. If the current checkout still has only a legacy flat `Virtuoso/` workspace, do not run the visualizer against it as the acceptance workspace. Use a temp workspace produced by the manifest-capable preflight tests or run the updated `virtuoso-init` after the manifest-capable initializer is installed.

- [ ] **Step 2: Generate the report**

Run from the chosen project root:

```powershell
python -m tools.roadmap_visualizer.generate --root .
```

Expected output:

```text
planning cockpit written: <absolute path ending in Virtuoso\reports\planning-cockpit.html>
```

- [ ] **Step 3: Open and inspect the report**

Open `Virtuoso/reports/planning-cockpit.html` in a browser. Verify:

- The Cockpit tab shows head sprint, full-spec buffer, queued, in-flight, blocked, and drift counts.
- The next planning action appears in plain language.
- The Conveyor tab lists sprint rows from `DATA.sprint-catalog`.
- The Dependencies tab lists dependency relationships or an empty-state row.
- No network access is required by the report.

- [ ] **Step 4: Verify read-only behavior**

Run:

```powershell
git status --short
```

Expected: only `Virtuoso/reports/planning-cockpit.html` is new or modified in the selected project. `Roadmap.md`, `sprint-queue.xlsx`, and `Virtuoso/workspace-layout.json` are unchanged.

- [ ] **Step 5: Commit source changes in the plugin repo**

In the plugin repository:

```powershell
git add tools/roadmap_visualizer scripts/test_roadmap_visualizer.py README.md
git commit -m "feat: add roadmap planning cockpit generator"
```

---

## Self-Review Notes

- Spec coverage: The plan implements a read-only static HTML generator, manifest-first workspace loading, roadmap-as-source-of-truth drift detection, a Planning Health Cockpit, Conveyor view, Dependencies view, and no-server output.
- Omitted-detail scan: No task relies on unspecified behavior; code-bearing steps include concrete code.
- Type consistency: `WorkspacePaths`, `SprintRow`, `RoadmapSnapshot`, `HealthSummary`, and `PlanningModel` are defined before use and referenced consistently across parser, health, renderer, and generator tasks.
