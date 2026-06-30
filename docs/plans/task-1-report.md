# Task 1 Report: Conventional-layout fallback in `load_workspace`

**Branch:** `fix/roadmap-visualizer-remediation`
**Commit:** `9d262b6`
**Files changed:** `tools/roadmap_visualizer/workspace.py`, `scripts/test_roadmap_visualizer.py`

---

## Summary

Task 1 ("Conventional-layout fallback in `load_workspace`") is complete. `load_workspace` now falls back to `Virtuoso/Roadmap.md` + `Virtuoso/sprint-queue.xlsx` when no `Virtuoso/workspace-layout.json` manifest is present, and raises `FileNotFoundError` with a message referencing both paths only when neither is available. Manifest precedence is preserved.

---

## Step-by-step Evidence

### Step 1: Test replacement

Replaced `test_workspace_loader_requires_manifest` with two new functions in `scripts/test_roadmap_visualizer.py`:
- `test_workspace_loader_errors_when_no_manifest_and_no_conventional_layout` — asserts the error message mentions both `Virtuoso/workspace-layout.json` and `Virtuoso/Roadmap.md`.
- `test_workspace_loader_falls_back_to_conventional_layout` — creates only the conventional files and asserts `paths.roadmap`, `paths.sprint_queue`, and `paths.reports` resolve correctly.

### Step 2: Failing run (TDD red)

```
FAILED scripts/test_roadmap_visualizer.py::test_workspace_loader_errors_when_no_manifest_and_no_conventional_layout
  AssertionError: assert 'Virtuoso/Roadmap.md' in 'Virtuoso/workspace-layout.json is required for manifest-based workspace loading'

FAILED scripts/test_roadmap_visualizer.py::test_workspace_loader_falls_back_to_conventional_layout
  FileNotFoundError: Virtuoso/workspace-layout.json is required for manifest-based workspace loading
```

Both failed as expected.

### Step 3: Implementation

Replaced the body of `load_workspace` in `tools/roadmap_visualizer/workspace.py`:
- Inverted the guard: now enters the manifest branch only when `manifest.is_file()` is true.
- Added a conventional-fallback branch: if `Virtuoso/Roadmap.md` and `Virtuoso/sprint-queue.xlsx` both exist, returns `WorkspacePaths` pointing to them with `manifest` still set to the (non-existent) manifest path.
- The `raise FileNotFoundError` now mentions both `Virtuoso/workspace-layout.json` and `Virtuoso/Roadmap.md` in its message.
- `_resolve` helper left unchanged.

### Step 4: Passing run (TDD green) — 3 tests

```
PASSED scripts/test_roadmap_visualizer.py::test_workspace_loader_errors_when_no_manifest_and_no_conventional_layout
PASSED scripts/test_roadmap_visualizer.py::test_workspace_loader_falls_back_to_conventional_layout
PASSED scripts/test_roadmap_visualizer.py::test_workspace_loader_resolves_manifest_paths
3 passed
```

### Step 5: End-to-end test added

Appended `test_generator_writes_report_without_manifest` to `scripts/test_roadmap_visualizer.py`. Creates `Virtuoso/Roadmap.md` + `Virtuoso/sprint-queue.xlsx` under `tmp_path` (no manifest), calls `generate(tmp_path)`, and asserts the HTML cockpit is written with `Planning Health Cockpit` and `SK-001` present.

### Step 6: End-to-end test passes

```
PASSED scripts/test_roadmap_visualizer.py::test_generator_writes_report_without_manifest
1 passed
```

### Step 7: Full targeted suite

```
13 passed in 0.61s
```

(Original 11 tests + 2 new Task 1 tests — the existing `test_workspace_loader_requires_manifest` was replaced by 2 new tests, and `test_generator_writes_report_without_manifest` was added, netting +2 from the original 11.)

### Commit

```
git add tools/roadmap_visualizer/workspace.py scripts/test_roadmap_visualizer.py
git commit -m "fix(visualizer): fall back to conventional Virtuoso layout when no manifest (BC-1)"
[fix/roadmap-visualizer-remediation 9d262b6]
```

---

## Concerns

None. All steps completed cleanly. No unrelated files were staged.
