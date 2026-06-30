# Task 2 Report: Flag Dashboard-cache staleness in health

**Branch:** fix/roadmap-visualizer-remediation
**Commit:** 67fbefb

---

## Step 1: Wrote the failing staleness test

Appended `test_health_summary_flags_dashboard_cache_staleness` to `scripts/test_roadmap_visualizer.py`.

## Step 2: Confirmed test fails

```
FAILED scripts/test_roadmap_visualizer.py::test_health_summary_flags_dashboard_cache_staleness
E       TypeError: summarize_health() takes 2 positional arguments but 3 were given
```

Fails as expected — `summarize_health()` had no `dashboard` parameter.

## Step 3: Implemented changes to `health.py`

- Added `_dashboard_staleness(dashboard, counts)` helper above `summarize_health`.
- Updated `_recommendation` signature to 5 args (added `staleness_count`); staleness branch returns recalc prompt; drift branch now routes to `/roadmap-review` instead of `/reconcile`.
- Updated `summarize_health` to accept `dashboard: dict | None = None`, compute staleness findings, merge them with drift findings into `all_findings`, and pass correct args to `_recommendation`.

## Step 4: Confirmed staleness test passes

```
scripts/test_roadmap_visualizer.py::test_health_summary_flags_dashboard_cache_staleness PASSED
1 passed in 0.49s
```

## Step 5: Updated existing `/reconcile` assertion

Changed `test_health_summary_treats_roadmap_as_source_of_truth` final assertion from:
```python
assert health.recommendation == "Run /reconcile: roadmap and sprint queue are out of sync."
```
to:
```python
assert health.recommendation == "Run /roadmap-review to reconcile: roadmap and sprint queue are out of sync."
```

## Step 6: Wired dashboard through `generate.py`

Changed `build_model` in `generate.py`:
```python
health = summarize_health(roadmap, rows)
```
to:
```python
health = summarize_health(roadmap, rows, dashboard)
```

## Step 7: Full test suite run

```
14 passed in 0.63s
```

All 14 tests pass (11 original + 3 added across Tasks 1-2).

## Step 8: Commit

```
[fix/roadmap-visualizer-remediation 67fbefb] feat(visualizer): flag stale Excel Dashboard cache as drift; route drift to /roadmap-review (BC-2)
 3 files changed, 290 insertions(+), 1 deletion(-)
 create mode 100644 tools/roadmap_visualizer/generate.py
 create mode 100644 tools/roadmap_visualizer/health.py
```

Staged only the 3 explicit files: `tools/roadmap_visualizer/health.py`, `tools/roadmap_visualizer/generate.py`, `scripts/test_roadmap_visualizer.py`.
