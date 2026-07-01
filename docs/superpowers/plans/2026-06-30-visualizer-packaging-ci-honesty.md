# Roadmap-Visualizer Packaging & CI-Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the roadmap-visualizer importable and runnable from any working directory, document a command that actually works, and put the full test suite in CI so the green check is honest.

**Architecture:** The `tools.roadmap_visualizer` package lives at `plugins/virtuoso/tools/roadmap_visualizer/` but `tools/` has no `__init__.py`, so it imports as a namespace package only when `plugins/virtuoso/` is the current directory or on `PYTHONPATH`. Three small, independent changes remove that cwd dependency: a `conftest.py` that pins the import root for tests, a thin launcher script that pins it for the CLI, and a CI edit that runs every test file instead of two hand-picked ones. No production logic in the visualizer changes — this is a packaging/wiring fix.

**Tech Stack:** Python 3.12, `pytest`, `openpyxl`, GitHub Actions.

## Background — why this is needed (verified, not assumed)

- From the **repo root**, `python -m pytest plugins/virtuoso/` → **14 failed, 11 passed** with `ModuleNotFoundError: No module named 'tools'`. From `plugins/virtuoso/` → **25 passed**. The code is correct; the import root is unpinned.
- `.github/workflows/ci.yml` line 22 runs exactly **two** of the **five** test files (`test_recalc.py`, `test_virtuoso_preflight.py`). The 14-test roadmap-visualizer suite — the v1.1.5 flagship feature — is **not gated**. CI is green while most tests never run.
- The README documents `python -m tools.roadmap_visualizer.generate --root .` from "a project root". Run from either repo root it fails: `No module named tools.roadmap_visualizer.generate`.
- `generate.py` uses **relative imports** (`from .health import ...`), so it cannot be run as a bare script (`python generate.py`) — only as a `-m` module with `tools/` on the path, or via a launcher that pins the path first.

All three fixes below were prototyped and verified end-to-end before this plan was written.

## Working directory

All paths are relative to the **Virtuoso plugin repo root** (the `virtuoso.dev` working copy at `C:\Users\estra\Projects\Virtuoso\virtuoso.dev`). Run every command from that repo root unless a step says otherwise.

## Global Constraints

- **Python 3.12** is the CI runtime; `openpyxl` and `pytest` are the only pip deps (`pip install --upgrade pip openpyxl pytest`).
- **No `C:\Users…` absolute paths** anywhere in tracked files — `scripts/validate.py` fails the build if any appear.
- **No `${CLAUDE_PLUGIN_ROOT}/` path-uses in skill bodies** — `scripts/validate.py` enforces this (not relevant to these files, but do not introduce it).
- **Manifest versions stay in sync** — `scripts/bump_version.py --check` must stay green. These tasks touch no versioned manifest, so do **not** change any version string. A release/version bump (e.g. to v1.1.6) is a separate task, out of scope here.
- **Structural validator must stay green** — `python plugins/virtuoso/scripts/validate.py` exits 0 after every task.

---

### Task 1: Pin the test import root with a `conftest.py`

Make `tools.roadmap_visualizer` importable for the test suite regardless of the directory pytest is invoked from.

**Files:**
- Create: `plugins/virtuoso/conftest.py`
- Test: the existing suite under `plugins/virtuoso/` (run from the repo root)

**Interfaces:**
- Consumes: nothing.
- Produces: a `sys.path` entry (`plugins/virtuoso/`) that makes the `tools` namespace package importable for every test collected under `plugins/virtuoso/`. Tasks 2 and 3 rely on this being in place so their tests pass from the repo-root cwd that CI uses.

- [ ] **Step 1: Reproduce the failure (this is the failing test)**

Run from the repo root:

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: FAIL — `14 failed, 11 passed`, errors read `ModuleNotFoundError: No module named 'tools'` from `test_roadmap_visualizer.py`.

- [ ] **Step 2: Create the conftest**

Create `plugins/virtuoso/conftest.py` with exactly this content:

```python
"""Pin the import root so `tools.roadmap_visualizer` resolves regardless of the
directory pytest is invoked from. `tools/` is a namespace package (no __init__.py),
so its parent (this file's directory) must be on sys.path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
```

- [ ] **Step 3: Run the full suite from the repo root to verify it passes**

Run from the repo root:

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: PASS — `35 passed` (the conftest also fixes collection of the other ungated suites).

- [ ] **Step 4: Confirm the validator still passes**

Run:

```bash
python plugins/virtuoso/scripts/validate.py
```

Expected: `All checks passed.` (exit 0).

- [ ] **Step 5: Commit**

```bash
git add plugins/virtuoso/conftest.py
git commit -m "test: pin import root via conftest so tools.* resolves from any cwd"
```

---

### Task 2: Run the full test suite in CI

Replace the two hand-picked test files in CI with the whole suite, so the flagship visualizer tests (and the other ungated suites) actually gate merges.

**Files:**
- Modify: `.github/workflows/ci.yml:22`

**Interfaces:**
- Consumes: the `plugins/virtuoso/conftest.py` from Task 1 (without it, the CI run fails from the repo-root cwd).
- Produces: a CI "Tests" step that runs all five test files.

- [ ] **Step 1: Simulate the new CI command locally (the test)**

The CI job checks out the repo and runs from the repo root on Ubuntu/Python 3.12. Run the proposed command from the repo root:

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: PASS — `35 passed`. (If this fails with `ModuleNotFoundError`, Task 1 is not in place — stop and finish Task 1 first.)

- [ ] **Step 2: Edit the CI Tests step**

In `.github/workflows/ci.yml`, replace the `Tests` step. Change this exact line:

```yaml
      - name: Tests
        run: python -m pytest plugins/virtuoso/skills/roadmap-review/scripts/test_recalc.py plugins/virtuoso/scripts/test_virtuoso_preflight.py -q
```

to:

```yaml
      - name: Tests
        run: python -m pytest plugins/virtuoso/ -q
```

- [ ] **Step 3: Re-run the exact CI command to confirm green**

Run from the repo root:

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: PASS — `35 passed`.

- [ ] **Step 4: Sanity-check the other CI steps are unaffected**

Run the other two CI steps locally:

```bash
python plugins/virtuoso/scripts/validate.py
python plugins/virtuoso/scripts/bump_version.py --check
```

Expected: validator prints `All checks passed.`; version check prints `All declared files in sync at 1.1.5`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run the full plugin test suite, not two hand-picked files"
```

---

### Task 3: Add a cwd-independent CLI launcher and fix the README command

Give the visualizer a single entry point that resolves its own imports, then point the README at a command that actually works.

**Files:**
- Create: `plugins/virtuoso/scripts/generate_cockpit.py`
- Create: `plugins/virtuoso/scripts/test_generate_cockpit.py`
- Modify: `README.md:109-111` (the ` ```bash ` command block under "Roadmap planning cockpit")

**Interfaces:**
- Consumes: `tools.roadmap_visualizer.generate.main(argv: list[str] | None = None) -> int` — the existing argparse entry point in `plugins/virtuoso/tools/roadmap_visualizer/generate.py`. It accepts `--root` (default `.`) and `--output` (default `""`), and prints `planning cockpit written: <path>`.
- Produces: a runnable script `plugins/virtuoso/scripts/generate_cockpit.py` that works from any cwd.

- [ ] **Step 1: Write the failing test**

Create `plugins/virtuoso/scripts/test_generate_cockpit.py` with exactly this content:

```python
"""The launcher must run from any working directory, including the repo root,
where `tools.roadmap_visualizer` is otherwise not importable."""
import subprocess
import sys
from pathlib import Path

# scripts -> virtuoso -> plugins -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = REPO_ROOT / "plugins" / "virtuoso" / "scripts" / "generate_cockpit.py"


def test_launcher_help_runs_from_repo_root():
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "planning cockpit" in result.stdout.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run from the repo root:

```bash
python -m pytest plugins/virtuoso/scripts/test_generate_cockpit.py -v
```

Expected: FAIL — non-zero return code because `generate_cockpit.py` does not exist yet (`can't open file ... No such file or directory`).

- [ ] **Step 3: Create the launcher**

Create `plugins/virtuoso/scripts/generate_cockpit.py` with exactly this content:

```python
"""cwd-independent launcher for the roadmap planning cockpit.

`tools/` is a namespace package under this script's parent (plugins/virtuoso/),
so we put that directory on sys.path before importing. This lets the tool run
from any working directory — `python plugins/virtuoso/scripts/generate_cockpit.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.roadmap_visualizer.generate import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run from the repo root:

```bash
python -m pytest plugins/virtuoso/scripts/test_generate_cockpit.py -v
```

Expected: PASS.

- [ ] **Step 5: Update the README command**

In `README.md`, under the "## Roadmap planning cockpit" section, replace this exact block:

```bash
python -m tools.roadmap_visualizer.generate --root .
```

with:

```bash
# Runs from any directory; --root points at the project whose Roadmap.md +
# sprint-queue.xlsx you want to visualize (defaults to the current directory).
python plugins/virtuoso/scripts/generate_cockpit.py --root .
```

> **Decision point (surface to the user, do not guess):** This documents the
> command for someone running from the cloned Virtuoso repo. For an **end user of
> the installed plugin**, `plugins/virtuoso/scripts/...` is not on their project
> path, and no skill currently invokes the visualizer. Wiring the launcher
> through the recorded `~/.virtuoso/plugin-root` for installed use is a separate
> design question (flagged in the adversarial review's Remaining Uncertainty) and
> is **out of scope** for this plan. If the user confirms the audience is
> installed-plugin end users, open a follow-up plan.

- [ ] **Step 6: Verify the documented command end-to-end (optional, needs a workspace)**

If a `Virtuoso/` workspace with `Roadmap.md` + `sprint-queue.xlsx` exists in the repo, run from the repo root:

```bash
python plugins/virtuoso/scripts/generate_cockpit.py --root .
```

Expected: `planning cockpit written: ...Virtuoso\reports\planning-cockpit.html` (exit 0). If no workspace exists, skip — Step 4's test already proves the launcher resolves its imports.

- [ ] **Step 7: Confirm the full suite and validator still pass**

```bash
python -m pytest plugins/virtuoso/ -q
python plugins/virtuoso/scripts/validate.py
```

Expected: `36 passed` (the new launcher test adds one); validator `All checks passed.`

- [ ] **Step 8: Commit**

```bash
git add plugins/virtuoso/scripts/generate_cockpit.py plugins/virtuoso/scripts/test_generate_cockpit.py README.md
git commit -m "feat: cwd-independent cockpit launcher + correct README command"
```

---

### Task 4: Keep the build artifact out of the tree

`plugins/virtuoso/skills.zip` is a build artifact currently sitting untracked in the working copy. Ignore it so it never gets committed by accident. (`__pycache__/`, `*.pyc`, and `.pytest_cache/` are already ignored.)

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other repo code depends on.

- [ ] **Step 1: Confirm the artifact is currently untracked (the failing state)**

Run from the repo root:

```bash
git status --short
```

Expected: the output includes `?? plugins/virtuoso/skills.zip`.

- [ ] **Step 2: Add the ignore rule**

Append this line to `.gitignore` (after the existing `desktop.ini` line):

```gitignore
skills.zip
```

- [ ] **Step 3: Verify the artifact is now ignored**

Run from the repo root:

```bash
git status --short
git check-ignore plugins/virtuoso/skills.zip
```

Expected: `git status --short` no longer lists `skills.zip`; `git check-ignore` prints `plugins/virtuoso/skills.zip`.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore the skills.zip build artifact"
```

---

## Self-Review

**1. Spec coverage** (the adversarial review's Phase 1 = R1, R2, R3):
- R1 (visualizer importable regardless of cwd; README command works) → Task 1 (tests) + Task 3 (launcher + README). ✅
- R2 (add the ungated test files to CI) → Task 2. ✅
- R3 (clean-room / keep dev artifacts out so the published layout is what's tested) → Task 1 makes tests pass from the repo-root cwd CI uses; Task 4 stops the artifact leaking in. The broader clean-room CI job is noted below as a deliberate follow-up, not silently dropped. ✅ (partial — see below)
- **Out of scope, by design** (Scope Check — independent subsystems get their own plans): R4 eval harness (Phase 3), R5 `build_sprint_queue.py` orphan + validator orphan-check (Phase 2 drift), R6 self-dogfooding, R7 skill-size split. The installed-plugin invocation path is a flagged design question, not a defect to fix here.

**2. Placeholder scan:** No `TBD`/`TODO`/"handle edge cases"/"similar to Task N". Every code step shows complete, verified content. ✅

**3. Type consistency:** The launcher and its test reference only `main()` from `generate.py`, whose real signature (`main(argv: list[str] | None = None) -> int`) was read from source. `parents[1]` (launcher → `plugins/virtuoso/`) and `parents[3]` (test → repo root) were both verified against the actual tree depth. ✅

**Deliberate residual (not a gap):** A dedicated "run the documented command against the *published* layout" clean-room CI job (full R3) would harden against future dev/publish divergence, but it depends on confirming the installed-plugin invocation (the flagged design question). It is intentionally deferred to the same follow-up. Tasks 1–4 already remove the *current* cwd-based mask, which is the load-bearing part.

## Notes for the executor

- These four tasks are independent except that **Task 2 depends on Task 1** (CI fails without the conftest). Recommended order: 1 → 2 → 3 → 4.
- If you commit per the project's Git Workflow where the planner authors but does not certify commits, treat the `git commit` steps as "stage + propose"; otherwise commit directly.
- Do not bump any version string. A v1.1.6 release (notes + `bump_version.py` bump) is a separate task.
