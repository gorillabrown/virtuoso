import csv
import json
from pathlib import Path

import pytest


CATALOG_HEADERS = [
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
]


def write_catalog_csv(path, rows):
    """Write a sprint-catalog.csv with the 15-column schema (no computed columns)."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CATALOG_HEADERS)
        for row in rows:
            writer.writerow(row)


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


def test_workspace_loader_errors_when_no_manifest_and_no_conventional_layout(tmp_path):
    from tools.roadmap_visualizer.workspace import load_workspace

    try:
        load_workspace(tmp_path)
    except FileNotFoundError as exc:
        message = str(exc)
    else:
        raise AssertionError("load_workspace should error when nothing is found")

    assert "Virtuoso/workspace-layout.json" in message
    assert "Virtuoso/Roadmap.md" in message


def test_workspace_loader_falls_back_to_conventional_layout(tmp_path):
    from tools.roadmap_visualizer.workspace import load_workspace

    roadmap = tmp_path / "Virtuoso" / "Roadmap.md"
    queue = tmp_path / "Virtuoso" / "sprint-queue.xlsx"
    roadmap.parent.mkdir(parents=True)
    roadmap.write_text("# Project Roadmap\n", encoding="utf-8")
    queue.write_bytes(b"")  # presence is enough for path resolution

    paths = load_workspace(tmp_path)

    assert paths.roadmap == roadmap
    assert paths.sprint_queue == queue
    assert paths.reports == tmp_path / "Virtuoso" / "reports"


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


def test_catalog_parser_reads_rows_from_csv(tmp_path):
    from tools.roadmap_visualizer.workbook import read_catalog

    catalog = tmp_path / "sprint-catalog.csv"
    write_catalog_csv(
        catalog,
        [
            [
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
            ]
        ],
    )

    rows, dashboard = read_catalog(catalog)

    assert len(rows) == 1
    assert rows[0].code == "SK-001"
    assert rows[0].seq == 1
    assert rows[0].dependencies == ["SK-000", "SK-BASE"]
    assert rows[0].implementation_status == "Queued"
    assert rows[0].written_status == "Full Spec"
    assert dashboard == {}


def test_catalog_parser_accepts_sprint_queue_path_and_reads_sibling_csv(tmp_path):
    """read_catalog is fed workspace.sprint_queue (the xlsx path); it must resolve
    the sibling sprint-catalog.csv rather than opening the workbook."""
    from tools.roadmap_visualizer.workbook import read_catalog

    queue = tmp_path / "sprint-queue.xlsx"
    write_catalog_csv(
        tmp_path / "sprint-catalog.csv",
        [
            [
                1,
                "SK-001",
                "Phase 1",
                "Stage 1",
                "First sprint",
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
            ]
        ],
    )

    rows, dashboard = read_catalog(queue)

    assert len(rows) == 1
    assert rows[0].code == "SK-001"
    assert dashboard == {}


def test_catalog_parser_skips_rows_without_sprint_code(tmp_path):
    from tools.roadmap_visualizer.workbook import read_catalog

    catalog = tmp_path / "sprint-catalog.csv"
    write_catalog_csv(
        catalog,
        [
            ["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            [
                2,
                "SK-002",
                "Phase 1",
                "Stage 1",
                "Second sprint",
                "S",
                "",
                "Queued",
                "Stub",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ],
    )

    rows, _ = read_catalog(catalog)

    assert [row.code for row in rows] == ["SK-002"]


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
sprint_catalog_doc: sprint-catalog.csv
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
        ),
        SprintRow(
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
        ),
    ]

    health = summarize_health(roadmap, rows)

    assert health.head_code == "SK-001"
    assert health.full_spec_buffer == 0
    assert health.queued_count == 1
    assert health.blocked_count == 1
    assert health.drift_count == 3
    assert "Missing from sprint queue: SK-001" in health.drift_findings
    assert "Queue row not present in roadmap active section: SK-003" in health.drift_findings
    assert "Unknown dependency referenced by SK-003: SK-999" in health.drift_findings
    assert health.recommendation == "Run /roadmap-review to reconcile: roadmap and sprint queue are out of sync."


def test_health_summary_proceeds_when_queue_has_aligned_full_spec_sprint():
    from pathlib import Path

    from tools.roadmap_visualizer.health import summarize_health
    from tools.roadmap_visualizer.model import RoadmapSnapshot, SprintRow

    roadmap = RoadmapSnapshot(
        path=Path("Roadmap.md"),
        active_codes=["SK-001"],
        completed_codes=[],
        full_spec_codes=["SK-001"],
        headings={"SK-001": "Build visualizer"},
        frontmatter={},
    )
    rows = [
        SprintRow(
            seq=1,
            code="SK-001",
            phase="Phase 1",
            stage="Stage 1",
            title="Build visualizer",
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
        )
    ]

    health = summarize_health(roadmap, rows)

    assert health.drift_count == 0
    assert health.full_spec_buffer == 1
    assert health.queued_count == 1
    assert health.recommendation == "Proceed: queue is aligned."


def test_health_summary_flags_status_drift_from_queue_mirror():
    from pathlib import Path

    from tools.roadmap_visualizer.health import summarize_health
    from tools.roadmap_visualizer.model import RoadmapSnapshot, SprintRow

    roadmap = RoadmapSnapshot(
        path=Path("Roadmap.md"),
        active_codes=["SK-001"],
        completed_codes=["SK-000"],
        full_spec_codes=["SK-001"],
        headings={"SK-001": "Build visualizer", "SK-000": "Bootstrap"},
        frontmatter={},
    )
    rows = [
        SprintRow(
            seq=1,
            code="SK-001",
            phase="Phase 1",
            stage="Stage 1",
            title="Build visualizer",
            loe="M",
            dependencies=[],
            implementation_status="Completed",
            written_status="Full Spec",
            branch="",
            date_started="",
            date_completed="",
            close_out_file="",
            description="",
            notes="",
        ),
        SprintRow(
            seq=2,
            code="SK-000",
            phase="Phase 0",
            stage="Stage 1",
            title="Bootstrap",
            loe="S",
            dependencies=[],
            implementation_status="Queued",
            written_status="Full Spec",
            branch="",
            date_started="",
            date_completed="",
            close_out_file="",
            description="",
            notes="",
        ),
    ]

    health = summarize_health(roadmap, rows)

    assert health.head_code == "SK-001"
    assert (
        "Roadmap-active sprint marked done in queue: SK-001"
        in health.drift_findings
    )
    assert (
        "Roadmap-completed sprint still active in queue: SK-000"
        in health.drift_findings
    )


def test_generator_refuses_to_overwrite_manifest_source_file(tmp_path):
    import hashlib

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
    write_catalog_csv(
        queue.with_name("sprint-catalog.csv"),
        [
            [
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
            ]
        ],
    )
    original_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="Refusing to overwrite workspace source file"):
        generate(tmp_path, output="Virtuoso/workspace-layout.json")

    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == original_hash


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
    write_catalog_csv(
        queue.with_name("sprint-catalog.csv"),
        [
            [
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


def test_generator_writes_report_without_manifest(tmp_path):
    from tools.roadmap_visualizer.generate import generate

    roadmap = tmp_path / "Virtuoso" / "Roadmap.md"
    queue = tmp_path / "Virtuoso" / "sprint-queue.xlsx"
    roadmap.parent.mkdir(parents=True)
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
    queue.write_bytes(b"")  # presence is enough for workspace path resolution
    write_catalog_csv(
        queue.with_name("sprint-catalog.csv"),
        [
            [1, "SK-001", "Phase 1", "Stage 1", "Build visualizer", "M", "", "Queued", "Full Spec", "", "", "", "", "", ""],
        ],
    )

    output = generate(tmp_path)

    assert output == tmp_path / "Virtuoso" / "reports" / "planning-cockpit.html"
    assert output.is_file()
    html = output.read_text(encoding="utf-8")
    assert "Planning Health Cockpit" in html
    assert "SK-001" in html


def test_health_summary_dashboard_staleness_is_skipped_when_no_dashboard():
    """The catalog CSV carries no cached KPIs, so summarize_health's dashboard-staleness
    check is inert by default (no dashboard argument, matching read_catalog's `{}`)."""
    from pathlib import Path

    from tools.roadmap_visualizer.health import summarize_health
    from tools.roadmap_visualizer.model import RoadmapSnapshot, SprintRow

    roadmap = RoadmapSnapshot(
        path=Path("Roadmap.md"),
        active_codes=["SK-001"],
        completed_codes=[],
        full_spec_codes=["SK-001"],
        headings={"SK-001": "Build visualizer"},
        frontmatter={},
    )
    rows = [
        SprintRow(
            seq=1, code="SK-001", phase="Phase 1", stage="Stage 1",
            title="Build visualizer", loe="M", dependencies=[],
            implementation_status="Queued", written_status="Full Spec",
            branch="", date_started="", date_completed="", close_out_file="",
            description="", notes="",
        )
    ]

    health = summarize_health(roadmap, rows, {})

    assert health.drift_count == 0
    assert health.recommendation == "Proceed: queue is aligned."
