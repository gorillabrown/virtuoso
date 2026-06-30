# Roadmap Visualizer Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two load-bearing gaps the adversarial review found in the `roadmap_visualizer` close-out — it cannot run on a real plugin workspace (it hard-requires a manifest nothing creates), and it reads the Excel Dashboard cells but never uses them to catch cache staleness.

**Architecture:** The tool is a small pure-Python package (`tools/roadmap_visualizer/`) that loads a workspace, parses `Roadmap.md` + the `sprint-queue.xlsx` Catalog, computes health/drift, and renders a self-contained HTML cockpit. This plan (a) makes `load_workspace` fall back to the conventional `Virtuoso/` layout when no `workspace-layout.json` manifest is present, and (b) adds a Dashboard-cache staleness check to `summarize_health` so the cockpit flags when the Excel Dashboard disagrees with the freshly-computed catalog counts.

**Tech Stack:** Python 3.12, `openpyxl`, `pytest`. Frozen dataclasses (`tools/roadmap_visualizer/model.py`). No new dependencies.

## Global Constraints

- Run all commands from the repo root: `C:/Users/estra/Projects/Virtuoso/virtuoso.dev`.
- TDD: write the failing test first, watch it fail, implement, watch it pass.
- Test file is `scripts/test_roadmap_visualizer.py`; reuse its existing `make_workbook(path, rows)` helper and `CATALOG_HEADERS` for workbook fixtures.
- `HealthSummary` is a **frozen** dataclass — this plan adds **no** new fields to it (staleness findings fold into the existing `drift_findings`/`drift_count`), so no model change and no fixture churn.
- The repo has many unrelated dirty/untracked files. **Only ever `git add` explicit sprint paths** — never `git add .`/`-A`.
- Targeted test run: `python -m pytest scripts/test_roadmap_visualizer.py -q`. Full suite: `python -m pytest -q`. Validator: `python scripts/validate.py`.
- Design decision (recorded): the `workspace-layout.json` manifest stays the authoritative path source **when present** (it supports non-standard layouts like `Project Documentation/…`); absence now means "use the conventional plugin layout," not "fail."

---

## File Structure

- **Modify** `tools/roadmap_visualizer/workspace.py` — add conventional-layout fallback to `load_workspace`; keep manifest precedence.
- **Modify** `tools/roadmap_visualizer/health.py` — `summarize_health` gains an optional `dashboard` arg; add `_dashboard_staleness`; `_recommendation` gains a staleness branch and drops the unbuilt `/reconcile` reference in favor of `/roadmap-review`.
- **Modify** `tools/roadmap_visualizer/generate.py` — pass the parsed `dashboard` dict into `summarize_health`.
- **Modify** `scripts/test_roadmap_visualizer.py` — update the manifest-required test to a no-manifest-error test; add fallback + end-to-end-without-manifest tests; update the recommendation assertion; add a Dashboard-staleness test.

Out of scope (review's lower-severity items; recommend a separate pass): broadening `_refuse_protected_output` beyond the 3 source files (G5, Low), and whether the visualizer should ultimately *consume* `recalc.py`'s computation instead of re-deriving KPIs (architecture decision).

---

### Task 1: Conventional-layout fallback in `load_workspace` (closes BC-1)

**Files:**
- Modify: `tools/roadmap_visualizer/workspace.py`
- Test: `scripts/test_roadmap_visualizer.py`

**Interfaces:**
- Consumes: `WorkspacePaths` from `tools/roadmap_visualizer/model.py` (fields: `root, manifest, roadmap, sprint_queue, reports`).
- Produces: `load_workspace(root) -> WorkspacePaths` — uses the manifest when `Virtuoso/workspace-layout.json` exists; else falls back to `Virtuoso/Roadmap.md` + `Virtuoso/sprint-queue.xlsx`; raises `FileNotFoundError` only when neither is available.

- [ ] **Step 1: Replace the manifest-required test and add the fallback test**

In `scripts/test_roadmap_visualizer.py`, **replace** the entire `test_workspace_loader_requires_manifest` function with the two functions below:

```python
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
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m pytest scripts/test_roadmap_visualizer.py -k "conventional_layout or no_manifest" -v`
Expected: `test_workspace_loader_falls_back_to_conventional_layout` FAILS with `FileNotFoundError` (current code hard-requires the manifest); the error-message test may also fail on the new `Virtuoso/Roadmap.md` assertion.

- [ ] **Step 3: Add the fallback to `load_workspace`**

Replace the body of `load_workspace` in `tools/roadmap_visualizer/workspace.py` with:

```python
def load_workspace(root: Path | str) -> WorkspacePaths:
    root_path = Path(root).resolve()
    manifest = root_path / "Virtuoso" / "workspace-layout.json"

    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        paths = data.get("paths") if isinstance(data, dict) else None
        roadmap = paths.get("roadmap") if isinstance(paths, dict) else None
        sprint_queue = paths.get("sprintQueue") if isinstance(paths, dict) else None
        missing_fields = []
        if not roadmap:
            missing_fields.append("paths.roadmap")
        if not sprint_queue:
            missing_fields.append("paths.sprintQueue")
        if missing_fields:
            raise ValueError(
                f"workspace manifest missing required fields: {', '.join(missing_fields)}"
            )
        return WorkspacePaths(
            root=root_path,
            manifest=manifest,
            roadmap=_resolve(root_path, roadmap),
            sprint_queue=_resolve(root_path, sprint_queue),
            reports=root_path / "Virtuoso" / "reports",
        )

    # No manifest: fall back to the conventional plugin layout.
    conventional_roadmap = root_path / "Virtuoso" / "Roadmap.md"
    conventional_queue = root_path / "Virtuoso" / "sprint-queue.xlsx"
    if conventional_roadmap.is_file() and conventional_queue.is_file():
        return WorkspacePaths(
            root=root_path,
            manifest=manifest,
            roadmap=conventional_roadmap,
            sprint_queue=conventional_queue,
            reports=root_path / "Virtuoso" / "reports",
        )

    raise FileNotFoundError(
        "No Virtuoso/workspace-layout.json manifest, and no conventional "
        "Virtuoso/Roadmap.md + Virtuoso/sprint-queue.xlsx were found under "
        f"{root_path}. Provide a manifest or use the conventional layout."
    )
```

Leave the `_resolve` helper unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest scripts/test_roadmap_visualizer.py -k "conventional_layout or no_manifest or resolves_manifest" -v`
Expected: all 3 PASS (fallback works; error path works; manifest precedence still works).

- [ ] **Step 5: Add an end-to-end no-manifest generate test**

Append to `scripts/test_roadmap_visualizer.py`:

```python
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
    make_workbook(
        queue,
        [
            [
                "1", 1, "SK-001", "Phase 1", "Stage 1", "Build visualizer", "M", "",
                "Queued", "Full Spec", "", "", "", "", "", "", False, 1, 4, 1,
            ]
        ],
    )

    output = generate(tmp_path)

    assert output == tmp_path / "Virtuoso" / "reports" / "planning-cockpit.html"
    assert output.is_file()
    html = output.read_text(encoding="utf-8")
    assert "Planning Health Cockpit" in html
    assert "SK-001" in html
```

- [ ] **Step 6: Run it to verify the full pipeline works without a manifest**

Run: `python -m pytest scripts/test_roadmap_visualizer.py::test_generator_writes_report_without_manifest -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/roadmap_visualizer/workspace.py scripts/test_roadmap_visualizer.py
git commit -m "fix(visualizer): fall back to conventional Virtuoso layout when no manifest (BC-1)"
```

---

### Task 2: Flag Dashboard-cache staleness in health (closes BC-2)

**Files:**
- Modify: `tools/roadmap_visualizer/health.py`
- Modify: `tools/roadmap_visualizer/generate.py`
- Test: `scripts/test_roadmap_visualizer.py`

**Interfaces:**
- Consumes: the `dashboard: dict[str, Any]` returned by `read_workbook` (keys include `total, completed, blocked, queued, in_flight` from `workbook.DASHBOARD_CELLS`); `RoadmapSnapshot`, `SprintRow`, `HealthSummary` from `model.py`.
- Produces: `summarize_health(roadmap, rows, dashboard=None) -> HealthSummary`. When `dashboard` is provided and a cached count disagrees with the computed count, a `"Dashboard cache stale: …"` string is appended to `drift_findings` (and counted in `drift_count`); the recommendation becomes a recalc prompt. `dashboard=None` preserves current behavior.

- [ ] **Step 1: Write the failing staleness test**

Append to `scripts/test_roadmap_visualizer.py`:

```python
def test_health_summary_flags_dashboard_cache_staleness():
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
            priority="1", seq=1, code="SK-001", phase="Phase 1", stage="Stage 1",
            title="Build visualizer", loe="M", dependencies=[],
            implementation_status="Queued", written_status="Full Spec",
            branch="", date_started="", date_completed="", close_out_file="",
            description="", notes="", done=False, sort_key="1",
        )
    ]
    # Catalog has 1 queued; the cached Dashboard says 5 -> stale.
    dashboard = {"total": 1, "queued": 5, "in_flight": 0, "blocked": 0, "completed": 0}

    health = summarize_health(roadmap, rows, dashboard)

    assert any(
        finding.startswith("Dashboard cache stale: queued")
        for finding in health.drift_findings
    )
    assert health.drift_count >= 1
    assert health.recommendation == "Run recalc.py: the sprint-queue Dashboard cache is stale."
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest scripts/test_roadmap_visualizer.py::test_health_summary_flags_dashboard_cache_staleness -v`
Expected: FAIL — `summarize_health()` currently takes 2 positional args (TypeError) and has no staleness logic.

- [ ] **Step 3: Add staleness reconciliation to `health.py`**

In `tools/roadmap_visualizer/health.py`, add this helper above `summarize_health`:

```python
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
        if cached_int != counts[key]:
            findings.append(
                f"Dashboard cache stale: {label} shows {cached_int} but catalog has "
                f"{counts[key]} - run recalc.py"
            )
    return findings
```

Change the `_recommendation` signature and body to:

```python
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
```

Change `summarize_health` to accept `dashboard` and wire in staleness. Replace its signature and its final block:

```python
def summarize_health(
    roadmap: RoadmapSnapshot,
    rows: list[SprintRow],
    dashboard: dict | None = None,
) -> HealthSummary:
    ordered_rows = _queue_rows(rows)
    rows_by_code = {row.code: row for row in ordered_rows}

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
```

(`rows_by_code` is retained as in the original; leave the rest of the file unchanged.)

- [ ] **Step 4: Run the staleness test to verify it passes**

Run: `python -m pytest scripts/test_roadmap_visualizer.py::test_health_summary_flags_dashboard_cache_staleness -v`
Expected: PASS.

- [ ] **Step 5: Update the existing recommendation assertion (the `/reconcile` text changed)**

In `scripts/test_roadmap_visualizer.py`, inside `test_health_summary_treats_roadmap_as_source_of_truth`, change the final assertion from:

```python
    assert health.recommendation == "Run /reconcile: roadmap and sprint queue are out of sync."
```
to:
```python
    assert health.recommendation == "Run /roadmap-review to reconcile: roadmap and sprint queue are out of sync."
```

- [ ] **Step 6: Wire the dashboard through `generate.py`**

In `tools/roadmap_visualizer/generate.py`, in `build_model`, change:

```python
    health = summarize_health(roadmap, rows)
```
to:
```python
    health = summarize_health(roadmap, rows, dashboard)
```

- [ ] **Step 7: Run the full visualizer test file to verify no regressions**

Run: `python -m pytest scripts/test_roadmap_visualizer.py -q`
Expected: all pass (the original 11 + the 3 added in Tasks 1–2 = 14 passed).

- [ ] **Step 8: Commit**

```bash
git add tools/roadmap_visualizer/health.py tools/roadmap_visualizer/generate.py scripts/test_roadmap_visualizer.py
git commit -m "feat(visualizer): flag stale Excel Dashboard cache as drift; route drift to /roadmap-review (BC-2)"
```

---

### Task 3: Verify against a real workspace, run the full suite, and commit the sprint

**Files:** none changed (verification + persistence).

**Interfaces:** consumes the CLI entry point `python -m tools.roadmap_visualizer.generate --root <dir>`.

- [ ] **Step 1: Real-workspace smoke (the check BC-1 was about)**

Create a conventional workspace and generate against it (no hand-made manifest):

```bash
python -c "import os,openpyxl; os.makedirs('tmp_ws/Virtuoso',exist_ok=True); open('tmp_ws/Virtuoso/Roadmap.md','w',encoding='utf-8').write('# Project Roadmap\n\n## Active & Remaining Sprint Skeletons\n\n#### SK-001 - Demo\nFull Spec:\nDemo.\n\n## Notes\n'); wb=openpyxl.Workbook(); d=wb.active; d.title='Dashboard'; d['B11']=1; d['B14']=1; c=wb.create_sheet('DATA.sprint-catalog'); c.append(['Priority','Seq','Sprint Code','Phase','Stage','Title','LOE','Dependencies','Implementation Status','Written Status','Branch','Date Started','Date Completed','Close-Out File','Description','Notes','Done?','PhaseRank','SizeRank','SortKey']); c.append(['1',1,'SK-001','Phase 1','Stage 1','Demo','M','','Queued','Full Spec','','','','','','',False,1,4,1]); wb.save('tmp_ws/Virtuoso/sprint-queue.xlsx')"
python -m tools.roadmap_visualizer.generate --root tmp_ws
```
Expected: prints `planning cockpit written: …tmp_ws/Virtuoso/reports/planning-cockpit.html` (no `FileNotFoundError`).

- [ ] **Step 2: Confirm the report is real and self-contained**

```bash
python -c "p='tmp_ws/Virtuoso/reports/planning-cockpit.html'; t=open(p,encoding='utf-8').read(); assert 'Planning Health Cockpit' in t and 'SK-001' in t; assert '<script src=' not in t and '<link rel=' not in t; print('OK self-contained, contains SK-001')"
```
Expected: `OK self-contained, contains SK-001`.

- [ ] **Step 3: Clean up the scratch workspace**

```bash
rm -rf tmp_ws
```

- [ ] **Step 4: Full suite + validator (the close-out's broader claims)**

Run: `python -m pytest -q`
Expected: all pass (`25 passed` — the prior 22 plus the 3 new visualizer tests).

Run: `python scripts/validate.py`
Expected: `All checks passed.`

- [ ] **Step 5: Commit the sprint by explicit path (do not stage unrelated dirty files)**

If on `main`/`master`, branch first:
```bash
git rev-parse --abbrev-ref HEAD
# if main/master:
git checkout -b fix/roadmap-visualizer-remediation
```
Then stage and commit only this sprint's files:
```bash
git add tools/roadmap_visualizer scripts/test_roadmap_visualizer.py README.md
git status --porcelain tools/roadmap_visualizer scripts/test_roadmap_visualizer.py README.md
git commit -m "chore(visualizer): roadmap visualizer remediation — manifest fallback + Dashboard staleness, verified"
```
Expected: `git status` shows only the intended files staged; the commit succeeds and anchors the close-out to a SHA.

---

## Self-Review

**1. Spec coverage (against the adversarial review's remediation):**
- BC-1 (manifest gap) → Task 1 (fallback + no-manifest end-to-end test). ✔
- BC-2 (KPI reconciliation) → Task 2 (Dashboard staleness flagged; recommendation → recalc). ✔ (Reframed per code: render shows computed numbers, so this adds a staleness signal rather than fixing a display bug.)
- G3 (`/reconcile` not built) → Task 2 Step 3/5 (recommendation now points to `/roadmap-review`). ✔
- R1 (real-workspace run) → Task 3 Steps 1–2. ✔
- R5 (commit, explicit paths) → Task 1/2/3 commits. ✔
- R7 (full suite) → Task 3 Step 4. ✔
- G5 (broaden protected-output) and the "consume recalc.py" architecture question → explicitly out of scope (noted under File Structure). ✔

**2. Placeholder scan:** No TBD/TODO/"handle edge cases"; every code and test step shows complete code; every run step states the exact command and expected output. ✔

**3. Type consistency:** `summarize_health(roadmap, rows, dashboard=None)` is used identically in `generate.py` (Task 2 Step 6) and the new test (Task 2 Step 1). `_recommendation(drift_count, staleness_count, full_spec_buffer, queued_count, blocked_count)` is defined and called with matching 5-arg order (Task 2 Step 3). `_dashboard_staleness(dashboard, counts)` keys (`total/queued/in_flight/blocked/completed`) match both the `counts` dict built in `summarize_health` and `workbook.DASHBOARD_CELLS`. `WorkspacePaths` field names match `model.py`. ✔

---

## Execution Handoff

**Plan complete and saved to `docs/plans/2026-06-30-roadmap-visualizer-remediation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?**
