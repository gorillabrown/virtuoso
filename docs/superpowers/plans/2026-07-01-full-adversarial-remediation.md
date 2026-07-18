# Virtuoso Adversarial-Review Full Remediation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Supersedes** `docs/superpowers/plans/2026-06-30-visualizer-packaging-ci-honesty.md` — that Phase-1-only plan is fully absorbed here as Tasks 1–5. Delete it after this plan is accepted to avoid a stale duplicate.

> **Scope note:** This is a single document covering all seven gaps (G1–G7) from the adversarial review, at the user's explicit request. This deliberately runs against the writing-plans Scope Check (which prefers one plan per independent subsystem). The tasks remain independently testable, but reviewers should gate them in the phase groups below rather than as one monolithic merge.

**Goal:** Close all seven gaps from the Virtuoso adversarial review — make the flagship visualizer work as documented and CI-honest (G1/G2/G5), guard against doc/tree drift (G4), put the four largest skills on a token diet (G7), have Virtuoso run its own close-out ceremony (G6), and stand up a real triggering-eval pilot (G3).

**Architecture:** Five phase groups, sequenced by dependency. Group A (Tasks 1–4) fixes the packaging seam: a `conftest.py` and a launcher pin the import root so the visualizer runs from any cwd, and CI runs the whole suite plus a clean-room smoke test. Group B (Task 5) encodes "removed means removed" in the validator and deletes the resurrected script. Group C (Tasks 6–9) extracts self-contained reference material from four large skills into per-skill `references/` files, leaving pointers — no behavior change. Group D (Task 10) uses `pointer-closeout`'s own templates to close out this remediation sprint. Group E (Task 11) adopts skill-creator's triggering-eval harness for one pilot skill.

**Tech Stack:** Python 3.12, `pytest`, `openpyxl`, GitHub Actions, the `claude` CLI (for the eval pilot only), Markdown skills.

## Working directory

All paths are relative to the **Virtuoso plugin repo root** — the `virtuoso.dev` working copy at `C:\Users\estra\Projects\Virtuoso\virtuoso.dev`. Run every command from that repo root unless a step says otherwise. (`virtuoso.app` is the clean published mirror; do not edit it — it re-syncs from the same remote.)

## Global Constraints

- **Python 3.12** is the CI runtime; deps are `pip install --upgrade pip openpyxl pytest`.
- **No `C:\Users…` absolute paths** in any tracked file — `scripts/validate.py` fails the build if any appear. Every path shown below is repo-relative or derived from `__file__`.
- **No `${CLAUDE_PLUGIN_ROOT}/` path-uses inside skill bodies** — `scripts/validate.py` enforces this (resolves only in hooks/MCP).
- **Manifest versions stay in sync** — `scripts/bump_version.py --check` must stay green (currently `1.1.5`). These tasks touch **no** versioned manifest; do not change any version string. A v1.1.6 release (notes + `bump_version.py` bump) is a separate task.
- **`scripts/validate.py` exits 0 after every task** (except transiently inside Task 5, where a new check goes red until the dead file is deleted).
- **Skill edits must not change behavior** — Group C only relocates reference prose behind pointers. The YAML frontmatter `name:` must stay equal to the folder name, and no control-flow section may be moved (only the candidates named below).

## File Structure

**Created:**
- `plugins/virtuoso/conftest.py` — pins the test import root (Task 1).
- `plugins/virtuoso/scripts/generate_cockpit.py` — cwd-independent visualizer launcher (Task 3).
- `plugins/virtuoso/scripts/test_generate_cockpit.py` — launcher smoke test (Task 3).
- Nine `references/*.md` files across four skills (Tasks 6–9), listed per task.
- `Virtuoso/Close-Outs/CloseOut.remediation-2026-07-01.2026-07-01.md` + an `SRL-001` entry appended to `Virtuoso/SpecRetro.Lessons_Learned.md` (Task 10).
- `plugins/virtuoso/evals/adversarial-review-triggers.json` + `plugins/virtuoso/evals/README.md` (Task 11).

**Modified:**
- `.github/workflows/ci.yml` — full test suite (Task 2) + launcher smoke step (Task 4).
- `README.md` — corrected visualizer command (Task 3).
- `.gitignore` — ignore `skills.zip` (Task 4).
- `plugins/virtuoso/scripts/validate.py` — resurrected-removed-file guard (Task 5).
- Four large `SKILL.md` files (Tasks 6–9) — sections replaced by pointers.

**Deleted:**
- `plugins/virtuoso/scripts/build_sprint_queue.py` — dead code, documented "Removed" in v1.1.0 (Task 5).

---

# GROUP A — Packaging & CI honesty (G1, G2, G5)

### Task 1: Pin the test import root with a `conftest.py`  *(G1)*

`tools/` has no `__init__.py`, so `tools.roadmap_visualizer` imports only when `plugins/virtuoso/` is on `sys.path`. This makes the test suite pass regardless of the cwd pytest is invoked from.

**Files:**
- Create: `plugins/virtuoso/conftest.py`

**Interfaces:**
- Produces: a `sys.path` entry (`plugins/virtuoso/`) making the `tools` namespace package importable for every test under `plugins/virtuoso/`. Tasks 2 and 4 depend on this so their CI runs (repo-root cwd) pass.

- [ ] **Step 1: Reproduce the failure (the failing test)**

Run from the repo root:

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: FAIL — `14 failed, 11 passed`, `ModuleNotFoundError: No module named 'tools'`.

- [ ] **Step 2: Create the conftest**

Create `plugins/virtuoso/conftest.py`:

```python
"""Pin the import root so `tools.roadmap_visualizer` resolves regardless of the
directory pytest is invoked from. `tools/` is a namespace package (no __init__.py),
so its parent (this file's directory) must be on sys.path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
```

- [ ] **Step 3: Verify it passes from the repo root**

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: PASS — `35 passed`.

- [ ] **Step 4: Validator still green**

```bash
python plugins/virtuoso/scripts/validate.py
```

Expected: `All checks passed.`

- [ ] **Step 5: Commit**

```bash
git add plugins/virtuoso/conftest.py
git commit -m "test: pin import root via conftest so tools.* resolves from any cwd"
```

---

### Task 2: Run the full test suite in CI  *(G2)*

CI runs only 2 of 5 test files; the 14-test visualizer suite is ungated. Run the whole suite.

**Files:**
- Modify: `.github/workflows/ci.yml` (the `Tests` step)

**Interfaces:**
- Consumes: `plugins/virtuoso/conftest.py` (Task 1). Without it this CI run fails from the repo-root cwd.

- [ ] **Step 1: Simulate the new CI command (the test)**

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: PASS — `35 passed`. (If it fails with `ModuleNotFoundError`, Task 1 is not in place — finish it first.)

- [ ] **Step 2: Edit the CI Tests step**

In `.github/workflows/ci.yml`, replace this exact line:

```yaml
      - name: Tests
        run: python -m pytest plugins/virtuoso/skills/roadmap-review/scripts/test_recalc.py plugins/virtuoso/scripts/test_virtuoso_preflight.py -q
```

with:

```yaml
      - name: Tests
        run: python -m pytest plugins/virtuoso/ -q
```

- [ ] **Step 3: Re-run the exact CI command**

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: PASS — `35 passed`.

- [ ] **Step 4: Confirm the other CI steps are unaffected**

```bash
python plugins/virtuoso/scripts/validate.py
python plugins/virtuoso/scripts/bump_version.py --check
```

Expected: validator `All checks passed.`; version check `All declared files in sync at 1.1.5`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run the full plugin test suite, not two hand-picked files"
```

---

### Task 3: Add a cwd-independent CLI launcher and fix the README  *(G1)*

`generate.py` uses relative imports, so it can't run as a bare script and the README's `python -m tools.roadmap_visualizer.generate` fails from any repo root. A launcher pins the path first.

**Files:**
- Create: `plugins/virtuoso/scripts/generate_cockpit.py`
- Create: `plugins/virtuoso/scripts/test_generate_cockpit.py`
- Modify: `README.md` (the ` ```bash ` block under "## Roadmap planning cockpit")

**Interfaces:**
- Consumes: `tools.roadmap_visualizer.generate.main(argv: list[str] | None = None) -> int` — existing argparse entry point (accepts `--root` default `.`, `--output` default `""`; prints `planning cockpit written: <path>`).
- Produces: a script runnable from any cwd.

- [ ] **Step 1: Write the failing test**

Create `plugins/virtuoso/scripts/test_generate_cockpit.py`:

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

- [ ] **Step 2: Run it to verify it fails**

```bash
python -m pytest plugins/virtuoso/scripts/test_generate_cockpit.py -v
```

Expected: FAIL — non-zero exit because `generate_cockpit.py` does not exist yet.

- [ ] **Step 3: Create the launcher**

Create `plugins/virtuoso/scripts/generate_cockpit.py`:

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

- [ ] **Step 4: Run it to verify it passes**

```bash
python -m pytest plugins/virtuoso/scripts/test_generate_cockpit.py -v
```

Expected: PASS.

- [ ] **Step 5: Fix the README command**

In `README.md`, under "## Roadmap planning cockpit", replace this exact block:

```bash
python -m tools.roadmap_visualizer.generate --root .
```

with:

```bash
# Runs from any directory; --root points at the project whose Roadmap.md +
# sprint-queue.xlsx you want to visualize (defaults to the current directory).
python plugins/virtuoso/scripts/generate_cockpit.py --root .
```

> **Decision point (surface to the user, do not guess):** This documents the command for someone running from the cloned Virtuoso repo. For an **end user of the installed plugin**, `plugins/virtuoso/scripts/...` is not on their project path, and no skill currently invokes the visualizer. Wiring the launcher through the recorded `~/.virtuoso/plugin-root` for installed use is a separate design question (the review's Remaining Uncertainty) and is **out of scope** here.

- [ ] **Step 6: Full suite + validator green**

```bash
python -m pytest plugins/virtuoso/ -q
python plugins/virtuoso/scripts/validate.py
```

Expected: `36 passed` (the launcher test adds one); validator `All checks passed.`

- [ ] **Step 7: Commit**

```bash
git add plugins/virtuoso/scripts/generate_cockpit.py plugins/virtuoso/scripts/test_generate_cockpit.py README.md
git commit -m "feat: cwd-independent cockpit launcher + correct README command"
```

---

### Task 4: Clean-room CI smoke + ignore the build artifact  *(G5)*

Two hygiene fixes that stop the "works on my machine" divergence: a CI step that runs the documented command from the repo-root (published) layout, and a `.gitignore` for the untracked `skills.zip` build artifact. (`__pycache__/`, `*.pyc`, `.pytest_cache/` are already ignored.)

**Files:**
- Modify: `.github/workflows/ci.yml` (add a step)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `plugins/virtuoso/scripts/generate_cockpit.py` (Task 3).

- [ ] **Step 1: Confirm the launcher smoke passes from the repo root (the test)**

```bash
python plugins/virtuoso/scripts/generate_cockpit.py --help
echo "exit=$?"
```

Expected: usage text printed, `exit=0`.

- [ ] **Step 2: Add the CI smoke step**

In `.github/workflows/ci.yml`, immediately after the `Tests` step, add:

```yaml
      - name: Cockpit launcher smoke (published-layout invocation)
        run: python plugins/virtuoso/scripts/generate_cockpit.py --help
```

- [ ] **Step 3: Confirm `skills.zip` is currently untracked**

```bash
git status --short
```

Expected: output includes `?? plugins/virtuoso/skills.zip`.

- [ ] **Step 4: Add the ignore rule**

Append to `.gitignore` (after the existing `desktop.ini` line):

```gitignore
skills.zip
```

- [ ] **Step 5: Verify it's ignored**

```bash
git status --short
git check-ignore plugins/virtuoso/skills.zip
```

Expected: `git status --short` no longer lists `skills.zip`; `git check-ignore` prints `plugins/virtuoso/skills.zip`.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml .gitignore
git commit -m "ci: clean-room launcher smoke; chore: gitignore skills.zip artifact"
```

---

# GROUP B — Drift guard (G4)

### Task 5: Delete the resurrected script and guard against it  *(G4)*

`plugins/virtuoso/scripts/build_sprint_queue.py` (324 lines) was documented "Removed" in RELEASE-NOTES v1.1.0 but re-added in commit `cdaca28`. It has no `.py`/`.json`/`.yml` importers or callers (verified). Delete it and add a validator guard so "removed" stays removed.

**Files:**
- Delete: `plugins/virtuoso/scripts/build_sprint_queue.py`
- Modify: `plugins/virtuoso/scripts/validate.py`

**Interfaces:**
- Produces: a new validator check `no resurrected removed-files` driven by a `removed_files` allowlist.

- [ ] **Step 1: Add the guard (this is the failing test — it goes red while the file exists)**

In `plugins/virtuoso/scripts/validate.py`, insert this block immediately before the line `    print("VALIDATION RESULTS")`:

```python
    # 7. Files declared "Removed" in RELEASE-NOTES must stay gone (drift guard).
    removed_files = ["scripts/build_sprint_queue.py"]
    resurrected = [r for r in removed_files if os.path.isfile(os.path.join(ROOT, r))]
    (ok if not resurrected else fail)(
        "no resurrected removed-files" if not resurrected
        else f"files declared removed but present: {resurrected}")

```

- [ ] **Step 2: Run the validator to see it fail**

```bash
python plugins/virtuoso/scripts/validate.py
```

Expected: FAIL — `[FAIL] files declared removed but present: ['scripts/build_sprint_queue.py']`, `1 failure(s)`.

- [ ] **Step 3: Delete the dead file**

```bash
git rm plugins/virtuoso/scripts/build_sprint_queue.py
```

- [ ] **Step 4: Run the validator to see it pass**

```bash
python plugins/virtuoso/scripts/validate.py
```

Expected: PASS — includes `[OK]   no resurrected removed-files`, `All checks passed.`

- [ ] **Step 5: Full suite still green**

```bash
python -m pytest plugins/virtuoso/ -q
```

Expected: `36 passed` (nothing imported the deleted file).

- [ ] **Step 6: Commit**

```bash
git add plugins/virtuoso/scripts/validate.py
git commit -m "fix: delete resurrected build_sprint_queue.py + guard removed files (G4)"
```

---

# GROUP C — Skill token diet (G7)

**How every Group C task works (read once):** For each named section, (1) create the skill's `references/` dir if absent; (2) **cut the section verbatim** — from its heading line through the line just before the next `---` or next `##`/`###` heading — into the new reference file; (3) **replace** the cut region in `SKILL.md` with the exact pointer blockquote given; (4) apply the small "repoint" edits that fix `below`/`earlier in this skill` wording; (5) verify. Locate sections by their **verbatim heading text** (line numbers are 1-based from the last read and may drift by a line or two). No section body is retyped here because the operation is a move — the source file defines the content precisely.

**Group C verification (run after each task):**
```bash
python plugins/virtuoso/scripts/validate.py            # frontmatter/name unchanged, no dangling refs
python -m pytest plugins/virtuoso/ -q                  # unaffected: 36 passed
grep -n "below\|earlier in this skill" plugins/virtuoso/skills/<skill>/SKILL.md   # no orphaned directional words left pointing at moved sections
```
Every reference file must begin with a top-of-file H1 naming it (e.g. `# Dispatch-Readiness Rubric`) followed by the moved content, so it reads standalone.

---

### Task 6: Split `next-pointer` (1039 lines)  *(G7)*

**Files:**
- Modify: `plugins/virtuoso/skills/next-pointer/SKILL.md`
- Create: `plugins/virtuoso/skills/next-pointer/references/dispatch-readiness-rubric.md`
- Create: `plugins/virtuoso/skills/next-pointer/references/git-reconciliation-protocol.md`

- [ ] **Step 1: Create the references dir**

```bash
mkdir -p plugins/virtuoso/skills/next-pointer/references
```

- [ ] **Step 2: Extract the Dispatch-Readiness Rubric**

Cut the section `## Dispatch-Readiness Rubric` (≈lines 214–341, heading through the last R11 bullet before the `---`) into `references/dispatch-readiness-rubric.md` (prefixed with `# Dispatch-Readiness Rubric`). Replace it in `SKILL.md` with exactly:

```markdown
## Dispatch-Readiness Rubric

Every full spec must pass an 11-check rubric (R1–R11) before /next-pointer prints the pointer. The full rubric — Edit Sites, Test Names, Constants, Done-When, Branch/Commit Hygiene, Calibration Cadence, Edge Cases, Prerequisites, No Deferred Decisions, Source Citations, and Git Reconciliation — lives in **[references/dispatch-readiness-rubric.md](references/dispatch-readiness-rubric.md)**. Read that file now and walk the checks in order when you reach Phase 2. Each item is either PASS, a closable gap (resolve via investigation in Phase 3), or a structural gap (halt + AskUserQuestion).
```

- [ ] **Step 3: Extract the Git Reconciliation Protocol**

Cut the section `## Git Reconciliation Protocol` (≈lines 384–455) into `references/git-reconciliation-protocol.md` (prefixed with `# Git Reconciliation Protocol`). Replace it in `SKILL.md` with exactly:

```markdown
## Git Reconciliation Protocol

The canonical, copy-pasteable git reconciliation recipe that every Sprint Pointer embeds — the downstream half of reconciliation the CLI implementer runs verbatim as step 0 — lives in **[references/git-reconciliation-protocol.md](references/git-reconciliation-protocol.md)**, together with its halt semantics and during-sprint commit-hygiene rules. Read that file when you reach Phase 4 (Compose and Print) and when Rubric R11 asks you to verify or insert the recipe. Substitute `<default>` (repo default branch) and `<branch-name>` (the R5 sprint branch) before emitting it into the pointer.
```

- [ ] **Step 4: Repoint the directional words**

In `SKILL.md`, fix these three references that used to say "below":
- In the Glossary line "…that has passed the Dispatch-Readiness Rubric below" → change "below" to "(see [references/dispatch-readiness-rubric.md](references/dispatch-readiness-rubric.md))".
- In principle 1 "…dispatch-ready by the rubric below" → same replacement.
- In the moved rubric's R11 text (now in the reference file), the phrase "see **Git Reconciliation Protocol** below" → change to "see [git-reconciliation-protocol.md](git-reconciliation-protocol.md)" (sibling link inside `references/`).

- [ ] **Step 5: Verify** — run the Group C verification block for `next-pointer`. Expected: validator `All checks passed.`; `36 passed`; grep shows no "below" still pointing at the two moved sections.

- [ ] **Step 6: Commit**

```bash
git add plugins/virtuoso/skills/next-pointer/
git commit -m "refactor(next-pointer): extract rubric + git-reconciliation to references/ (G7)"
```

---

### Task 7: Split `roadmap-review` (692 lines)  *(G7)*

**Files:**
- Modify: `plugins/virtuoso/skills/roadmap-review/SKILL.md`
- Create: `plugins/virtuoso/skills/roadmap-review/references/dispatch-readiness-rubric.md`
- Create: `plugins/virtuoso/skills/roadmap-review/references/roadmap-document-template.md`
- Create: `plugins/virtuoso/skills/roadmap-review/references/sprint-queue-structure.md`

> **Precision flag:** this rubric is the **R1–R10** variant (no git-reconciliation item) and is deliberately self-contained per this skill's own note (lines ~126–127). It is a **distinct file** from Task 6's R1–R11 rubric — do not share one file between the two skills.

- [ ] **Step 1: Create the references dir**

```bash
mkdir -p plugins/virtuoso/skills/roadmap-review/references
```

- [ ] **Step 2: Extract the Dispatch-Readiness Rubric (R1–R10)**

Cut `## Dispatch-Readiness Rubric` (≈lines 117–218) into `references/dispatch-readiness-rubric.md` (prefixed `# Dispatch-Readiness Rubric`). Replace in `SKILL.md` with exactly:

```markdown
## Dispatch-Readiness Rubric

Every full spec authored by Phase D.3 must pass a 10-check rubric (R1–R10) before it is saved inline in the roadmap, because the CLI implementer is a lower-capability model than Cowork. The full rubric — Edit Sites, Test Names, Constants, Done-When, Branch/Commit Hygiene, Calibration Cadence, Edge Cases, Prerequisites, No Deferred Decisions, and Source Citations — lives in **[references/dispatch-readiness-rubric.md](references/dispatch-readiness-rubric.md)**. Read that file and walk the checks in order when you reach Phase D.3.2. (This is intentionally a self-contained copy; `/next-pointer` keeps its own just-in-time re-verification version with an added git-reconciliation check.)
```

- [ ] **Step 3: Extract the Roadmap document template**

Cut `## Roadmap document template` (≈lines 592–651, including the fenced ```markdown template) into `references/roadmap-document-template.md` (prefixed `# Roadmap document template`). Replace in `SKILL.md` with exactly:

```markdown
## Roadmap document template

The canonical skeleton for a project roadmap document — the section order (How This Document Is Maintained, Finish Line, Completed Work Summary, Active & Remaining Sprint Skeletons with Standing Rules, full-spec and stub examples, Non-Blocking Follow-Up Queue, Notes) plus the frontmatter block — lives in **[references/roadmap-document-template.md](references/roadmap-document-template.md)**. Read and copy it when Phase 0 creates a roadmap or when you need the exact heading structure while placing specs.
```

- [ ] **Step 4: Extract the Sprint queue spreadsheet structure**

Cut `## Sprint queue spreadsheet structure` (≈lines 653–682) into `references/sprint-queue-structure.md` (prefixed `# Sprint queue spreadsheet structure`). Replace in `SKILL.md` with exactly:

```markdown
## Sprint queue spreadsheet structure

The `sprint-queue.xlsx` workbook has three sheets — **Dashboard** (formula-driven KPIs, Pipeline Status B11–B18, Effort & Progress B21–B26, Next Up queue, status doughnut), **DATA.sprint-catalog** (the `sprint_catalog` Excel table, 20 columns A–T, five formula-driven), and **Variables** (lookup tables that re-rank the conveyor belt). The full layout, cell ranges, LOE point weights, and the headless `recalc.py` refresh note live in **[references/sprint-queue-structure.md](references/sprint-queue-structure.md)**. Read it when computing KPIs (Phase B) or writing Catalog rows (Phase D.5.4).
```

- [ ] **Step 5: Repoint the directional words**

- Glossary line "…has passed the Dispatch-Readiness Rubric below." → replace "below" with "(see [references/dispatch-readiness-rubric.md](references/dispatch-readiness-rubric.md))".
- Phase D.3.2 line "Walk the rubric — **see the section earlier in this skill** — against the draft spec." → replace "see the section earlier in this skill" with "see [references/dispatch-readiness-rubric.md](references/dispatch-readiness-rubric.md)".

- [ ] **Step 6: Verify** — Group C verification block for `roadmap-review`. Expected: validator green; `36 passed`; no orphaned "below"/"earlier in this skill".

- [ ] **Step 7: Commit**

```bash
git add plugins/virtuoso/skills/roadmap-review/
git commit -m "refactor(roadmap-review): extract rubric + templates to references/ (G7)"
```

---

### Task 8: Split `mid-dispatch-decision` (864 lines)  *(G7)*

**Files:**
- Modify: `plugins/virtuoso/skills/mid-dispatch-decision/SKILL.md`
- Create: `plugins/virtuoso/skills/mid-dispatch-decision/references/decision-types.md`
- Create: `plugins/virtuoso/skills/mid-dispatch-decision/references/anti-patterns.md`

> `references/` already exists here (holds `example-sk01b.md`) — do not recreate it.

- [ ] **Step 1: Extract Decision Types**

Cut `## Decision Types` (≈lines 95–174) into `references/decision-types.md` (prefixed `# Decision Types`). Replace in `SKILL.md` with exactly:

```markdown
## Decision Types

There are seven decision types across three axes (same vs. new direction, continue vs. stop, plus a verification gate): **Type 1a** (Advance — Pre-Authorized), **1b** (Advance — Cowork-Originated), **2** (Advance with Narrowing), **3** (Pivot Advance), **3a** (Revise Routing/Effort), **4** (Pivot Stop), and **5** (Verify First). The full definition of each type and its CLI-block shape lives in **[references/decision-types.md](references/decision-types.md)**. Read that file before Step 3 (Decision Classification); the classification decision tree in Step 3 produces one of these seven verdicts, and Step 6a gives the pasteable CLI-block format per type.
```

- [ ] **Step 2: Extract the Anti-Patterns table**

Cut `## Anti-Patterns` (≈lines 835–854) into `references/anti-patterns.md` (prefixed `# Anti-Patterns`). Replace in `SKILL.md` with exactly:

```markdown
## Anti-Patterns

A quick-reference table of the common mid-dispatch failure modes and their corrections — rubber-stamping the pre-authorization, producing the CLI block before confirmation, vague CLI blocks, skipping the spec amendment, using inline-spec amendments for worktree-resident sprints, and more — lives in **[references/anti-patterns.md](references/anti-patterns.md)**. Skim it before finalizing a recommendation to make sure you haven't fallen into one.
```

- [ ] **Step 3: Repoint the directional word**

In the moved Decision Types content, Type 5's "When to use" line says "…at least one of the valid measurement suspicions (below) applies." Since the "Valid Measurement Suspicions" list is NOT extracted (it stays in Step 3 of `SKILL.md`), change "(below)" to "(see Step 3, Valid Measurement Suspicions)".

- [ ] **Step 4: Verify** — Group C verification block for `mid-dispatch-decision`. Expected: validator green; `36 passed`; no orphaned directional words.

- [ ] **Step 5: Commit**

```bash
git add plugins/virtuoso/skills/mid-dispatch-decision/
git commit -m "refactor(mid-dispatch-decision): extract decision-types + anti-patterns (G7)"
```

---

### Task 9: Split `virtuoso` (850 lines)  *(G7)*

**Files:**
- Modify: `plugins/virtuoso/skills/virtuoso/SKILL.md`
- Create: `plugins/virtuoso/skills/virtuoso/references/worktree-governance-staging.md`
- Create: `plugins/virtuoso/skills/virtuoso/references/rationalization-table.md`

> `references/` already exists here (holds `zeus.md`). **Cross-skill dependency:** `mid-dispatch-decision` cites `virtuoso skill §Rule 3` and `§Rule 5`. When extracting, **preserve the verbatim `### Rule 3` / `### Rule 5` headings inside the new reference file**, and name that file in the pointer so those cross-skill citations remain followable.

- [ ] **Step 1: Extract Worktree Governance Staging**

Cut `## Worktree Governance Staging` (≈lines 667–849, through end of file) into `references/worktree-governance-staging.md` (prefixed `# Worktree Governance Staging`, all `### Rule N` headings preserved verbatim). Replace in `SKILL.md` with exactly:

```markdown
## Worktree Governance Staging

Worktree-resident sprints must never edit main governance documents directly — doing so conflicts with concurrent Cowork-side edits on canonical main (visible rebase conflict, or silent revert). The full pattern that eliminates this conflict surface — Rule 1 (no direct edits), Rule 2 (all change-intent to a staging file), Rule 3 (staging-file structure + fold-in action types), Rule 4 (pointer-closeout processes it as Wave 2 Step 0), Rule 5 (mid-dispatch amendments use the staging file), Rule 6 (Cowork-side default), plus the in-flight-migration and "what this prevents" notes — lives in **[references/worktree-governance-staging.md](references/worktree-governance-staging.md)**. Read it at sprint start (Phase 1) whenever the sprint runs in a git worktree, and whenever a task in the plan would edit a main governance document. (The `mid-dispatch-decision` skill's §Rule 3 / §Rule 5 citations refer to that file.)
```

- [ ] **Step 2: Extract the Rationalization Table**

Cut `## The Rationalization Table` (≈lines 623–641) into `references/rationalization-table.md` (prefixed `# The Rationalization Table`). Replace in `SKILL.md` with exactly:

```markdown
## The Rationalization Table

Before skipping narration, skipping a plan reprint, or taking a shortcut, check the rationalization table — every tempting excuse ("this one's trivial," "reprinting is redundant," "the human can see the tool calls") paired with why it's wrong. It lives in **[references/rationalization-table.md](references/rationalization-table.md)**. Consult it at any step boundary where you're tempted to cut a corner.
```

- [ ] **Step 3: Verify** — Group C verification block for `virtuoso`. Additionally confirm the cross-skill refs still resolve:

```bash
grep -n "Rule 3\|Rule 5" plugins/virtuoso/skills/virtuoso/references/worktree-governance-staging.md
```

Expected: `### Rule 3` and `### Rule 5` headings present in the reference file; validator green; `36 passed`.

- [ ] **Step 4: Commit**

```bash
git add plugins/virtuoso/skills/virtuoso/
git commit -m "refactor(virtuoso): extract worktree-staging + rationalization-table (G7)"
```

> **Deferred (optional) extractions — do NOT do in this plan:** next-pointer 1C Edge cases (many control-flow entry points), mid-dispatch 2C Step 2 First-Principles (mid-workflow step), virtuoso 3C Phase 6 Close-Out (numbered phase). These are control-flow the model reads top-to-bottom; extracting them risks skipped steps. Revisit only if further token savings are needed.

---

# GROUP D — Dogfood the close-out ceremony (G6)

### Task 10: Produce the first real Close-Out Report + retrospective  *(G6)*

Virtuoso's own `Close-Outs/` is empty. Close out **this remediation sprint** (Tasks 1–9) using `pointer-closeout`'s own templates — the strongest possible dogfood: the governance tool governing its own fix.

**Files:**
- Create: `Virtuoso/Close-Outs/CloseOut.remediation-2026-07-01.2026-07-01.md`
- Modify/Create: `Virtuoso/SpecRetro.Lessons_Learned.md` (append an `SRL-001` entry)

> **State facts (from investigation):** the live `Virtuoso/` workspace is legacy-flat with **no `workspace-layout.json`**. The helper `prepare_closeout_files.py` resolves the close-out dir to `Virtuoso/Close-Outs/` and creates it if absent. The seed roadmap has an **empty queue**, so the retire/elevate + buffer-depletion sections are N/A for this first run — state that explicitly rather than inventing movement.

- [ ] **Step 1: Resolve the paths with the helper script**

```bash
python plugins/virtuoso/skills/pointer-closeout/scripts/prepare_closeout_files.py --project-root . --sprint-id "remediation-2026-07-01" --date "2026-07-01"
```

Expected: four `KEY=VALUE` lines — `CLOSEOUT_DIR=...Virtuoso/Close-Outs`, `CLOSEOUT_REPORT=...CloseOut.remediation-2026-07-01.2026-07-01.md`, `SPEC_RETRO=...SpecRetro.Lessons_Learned.md`, `NEXT_SRL=SRL-001`. Use these exact paths in the next steps.

- [ ] **Step 2: Write the Close-Out Report**

Create the file at `CLOSEOUT_REPORT` using this exact structure (fill the bracketed fields from the actual results of Tasks 1–9):

```markdown
---
sprint: remediation-2026-07-01
date: 2026-07-01
runtime: [Xm Ys]
tokens: [~NNNk]
status: [all-pass | has-regressions | has-discoveries]
---

# Pointer Close-Out: remediation-2026-07-01

## Sprint Brief

**Goal:** Close all seven gaps from the 2026-07-01 adversarial review (G1–G7).
**Result:** [Name what landed — e.g. conftest + launcher fix G1; full-suite CI G2; validator guard + deleted build_sprint_queue.py G4; skills.zip ignored + clean-room smoke G5; four skills split to references G7; this close-out G6; adversarial-review triggering-eval pilot G3.]
**Learned:** [Durable lesson — e.g. "namespace-package import roots must be pinned by conftest/launcher, never by cwd; CI must run the whole suite or the green check lies."]
**Recommend:** [Next direction — e.g. "wire the eval pilot into CI once a POSIX runner is available; consider a validator link-check for references/."]
**Bottom line:** [One sentence.]

## Findings

| # | Finding | Metric | Target | Actual | Pass/Fail | Delta from Prior | Severity |
|---|---------|--------|--------|--------|-----------|------------------|----------|
| 1 | Test files gated by CI | files | 5/5 | [5/5] | [Pass] | +3 | Discovery |
| 2 | Tests passing from repo root | count | all | [36] | [Pass] | +25 | Pass |
| 3 | Resurrected removed-files | count | 0 | [0] | [Pass] | -1 | Pass |
| [add rows per task as needed] | | | | | | | |

## Interpretation

[For each non-pass or notable item: what happened, likely cause, what it means.]

## Proposed Dispositions

[One per finding: Fix Now / Investigate / Defer / Accept / Log.]

## Governance Updates

[Destinations touched: roadmap, sprint queue, lessons learned, known traps, technical reference.]

## Roadmap & Queue Movement

- **Retired:** N/A — the seed roadmap queue is empty; this remediation was dispatched from a plan, not the conveyor belt.
- **Elevated:** N/A — no queued successor exists yet. Recommend `/roadmap-review` to seed the queue.

## Next Work Pointer

[Single next direction, no code box.]

## Gates

[What must be true before the next sprint dispatches.]

## Git Hand-Off

- [ ] Commit close-out report + retrospective per the project's Git Workflow.
```

- [ ] **Step 3: Append the retrospective entry**

Append to `Virtuoso/SpecRetro.Lessons_Learned.md` (use `NEXT_SRL` from Step 1, i.e. `SRL-001`):

```markdown
### SRL-001 — Pin import roots; gate the whole suite (remediation-2026-07-01, 2026-07-01)
**Verdict:** [1–2 sentence summary of the biggest workflow lesson from this sprint.]
**Evidence:** CI ran 2 of 5 test files while green; the flagship visualizer command failed from every repo root because `tools/` was importable only from one cwd.
**Recommendation:** For any namespace-package tool, ship a conftest + a `__file__`-anchored launcher; make CI run the full suite plus a repo-root smoke of the documented command.
**Applies to:** All Python-tool sprints in this plugin.
**Status:** Observation
```

- [ ] **Step 4: Verify the artifacts exist and are well-formed**

```bash
ls -la Virtuoso/Close-Outs/
grep -c "^##" Virtuoso/Close-Outs/CloseOut.remediation-2026-07-01.2026-07-01.md   # expect >= 8 section headings
grep -n "SRL-001" Virtuoso/SpecRetro.Lessons_Learned.md
```

Expected: the close-out file exists with all sections; `SRL-001` present in the lessons file.

- [ ] **Step 5: Decision + commit**

> **Decision point (surface to the user):** the `Virtuoso/` workspace is currently **untracked** (`?? Virtuoso/`). Decide whether these dogfood artifacts are durable project history (track + commit them) or runtime workspace state (leave untracked). If tracking:

```bash
git add -f Virtuoso/Close-Outs/CloseOut.remediation-2026-07-01.2026-07-01.md Virtuoso/SpecRetro.Lessons_Learned.md
git commit -m "docs: first dogfood close-out + SRL-001 for the remediation sprint (G6)"
```

> **Audit ceremony (G6, external half):** A genuine 3rd-party audit needs an external auditor and the docx package, so it can't be dogfooded here. Instead, record the completed adversarial review as the first **internal** audit artifact: copy this plan's source review into `Virtuoso/audits/OutsideAudit.1.2026-07-01/AuditReport.1.2026-07-01.md` and note in CLAUDE.md's audit history that audit #1 was internal. Treat the full external lifecycle as out of scope.

---

# GROUP E — Triggering-eval pilot (G3)

### Task 11: Stand up a triggering-eval for one skill  *(G3)*

Adopt skill-creator's automated triggering harness (`run_eval.py`) for a pilot on `adversarial-review`. The durable deliverable is the eval-case file + a README documenting the exact command; running it requires the `claude` CLI under a POSIX Python (see caveat).

**Files:**
- Create: `plugins/virtuoso/evals/adversarial-review-triggers.json`
- Create: `plugins/virtuoso/evals/README.md`

**Interfaces:**
- Consumes (at run time, not build time): skill-creator's `run_eval.py` (external plugin) and the local `claude` CLI (reuses session auth; no API key).

- [ ] **Step 1: Create the eval-case file**

Create `plugins/virtuoso/evals/adversarial-review-triggers.json`:

```json
[
  {"query": "before I send this diagnostic plan to the team can you red team it and tell me what im missing", "should_trigger": true},
  {"query": "here's my finished root-cause analysis for the calibration drift — is this rigorous enough to act on, or are there holes?", "should_trigger": true},
  {"query": "tear this architecture proposal apart, I think the failover section is hand-wavy", "should_trigger": true},
  {"query": "stress test this analysis before I present it at the phase-close review tomorrow", "should_trigger": true},
  {"query": "I finished the feature spec for the new dispatch queue. is it ready to hand to CLI?", "should_trigger": true},
  {"query": "poke holes in my claim that the KO-rate regression came from the HP multiplier change", "should_trigger": true},
  {"query": "proofread this doc and fix any typos or grammar issues", "should_trigger": false},
  {"query": "run the pytest suite and tell me which tests are failing", "should_trigger": false},
  {"query": "summarize this 20-page report into three bullet points for the standup", "should_trigger": false},
  {"query": "reformat this markdown table so the columns line up", "should_trigger": false},
  {"query": "/roadmap-status", "should_trigger": false},
  {"query": "write me a new adversarial-review skill from scratch", "should_trigger": false}
]
```

- [ ] **Step 2: Verify the JSON is well-formed and correctly shaped (the test)**

```bash
python -c "import json,sys; d=json.load(open('plugins/virtuoso/evals/adversarial-review-triggers.json')); assert isinstance(d,list) and len(d)==12; assert all(set(c)=={'query','should_trigger'} for c in d); assert sum(c['should_trigger'] for c in d)==6; print('OK: 12 cases, 6 positive / 6 negative')"
```

Expected: `OK: 12 cases, 6 positive / 6 negative`.

- [ ] **Step 3: Document the runner in a README**

Create `plugins/virtuoso/evals/README.md`:

```markdown
# Virtuoso skill evals

Triggering-accuracy evals for Virtuoso skills, using skill-creator's `run_eval.py`
harness (it drives the local `claude` CLI — no API key; it reuses your session auth).

## Run the adversarial-review pilot

> **Windows caveat:** `run_eval.py` uses `select.select()` on a pipe, which does not
> work under native Windows Python. Run this under Git Bash / WSL with a POSIX Python,
> or port the reader loop to a blocking `for line in process.stdout`.

```bash
cd "<skill-creator>/skills/skill-creator"   # dir containing scripts/run_eval.py
python -m scripts.run_eval \
  --eval-set "<repo>/plugins/virtuoso/evals/adversarial-review-triggers.json" \
  --skill-path "<repo>/plugins/virtuoso/skills/adversarial-review" \
  --runs-per-query 3 --trigger-threshold 0.5 --verbose
```

## Pass bar

Each query passes when its observed trigger_rate is on the correct side of 0.5
(positives ≥0.5 fire; negatives <0.5). Pilot passes at **≥11/12 with zero
false-positives on the near-miss negatives** — a false trigger is the expensive
failure for an auto-triggering plugin. If it fails, escalate to `run_loop.py`
(same eval set, `--max-iterations 5`) to auto-propose a better `description`
scored on a held-out 40% split.

## Deferred: protocol-compliance evals

"Once triggered, does the skill follow its protocol?" is a larger lift (subagent
dispatch + `evals/evals.json` with `expectations[]` + a grader subagent). Defer to
a second phase; keep this pilot to triggering only.
```

- [ ] **Step 4: Commit**

```bash
git add plugins/virtuoso/evals/
git commit -m "test: triggering-eval pilot for adversarial-review skill (G3)"
```

- [ ] **Step 5 (optional, environment-permitting): run the eval once**

Under Git Bash / WSL with a POSIX Python and `claude` on PATH, run the command from the README. Record the `Results: X/12 passed` line in the Task 10 close-out. If native Windows is the only option, note in the README that CI wiring awaits a POSIX runner — do not block the task on it.

---

## Self-Review

**1. Spec coverage** — every gap maps to a task:

| Gap | Task(s) | Recommendation |
|-----|---------|----------------|
| G1 — visualizer command / import root | 1, 3 | R1 |
| G2 — CI runs 2 of 5 test files | 2 | R2 |
| G3 — no behavioral/triggering evals | 11 | R4 |
| G4 — resurrected `build_sprint_queue.py`; no orphan guard | 5 | R5 |
| G5 — dev/publish import mask; build artifact | 1, 4 | R3 |
| G6 — empty `Close-Outs/`/`audits/` | 10 | R6 |
| G7 — four skills 668–1039 lines | 6, 7, 8, 9 | R7 |

No gap is unassigned. R3's broader "clean-room job" is realized as Task 4's repo-root smoke step (the honest, verifiable subset); full installed-layout parity remains the flagged design question, deferred.

**2. Placeholder scan** — Tasks 1–5 and 11 carry complete, verified code and exact commands. Group C uses precise cut-and-replace-by-verbatim-heading with the full pointer text given (a *move* is fully specified by source range + replacement — not a placeholder). Task 10's bracketed fields (`[Xm Ys]`, `[Name what landed]`) are genuine runtime data the executor fills from actual results — these are report fields, not code placeholders. No "TBD", "handle edge cases", or "similar to Task N".

**3. Type consistency** — the launcher and its test reference only `main()` (real signature `main(argv: list[str] | None = None) -> int`, read from source). `parents[1]` (launcher → `plugins/virtuoso/`) and `parents[3]` (test → repo root) verified against the tree. The validator guard's `removed_files`/`resurrected` names and insertion anchor (`print("VALIDATION RESULTS")`) were prototyped and confirmed red-then-green. The two `dispatch-readiness-rubric.md` files are intentionally distinct (R1–R11 vs R1–R10) and never shared.

**Verification status:** Tasks 1–5 were prototyped end-to-end (conftest → 35 passed from root; launcher → exit 0 + HTML generated; validator guard → red-with-file, green-without). Tasks 6–9 rest on a full read of the four skills (exact headings, line ranges, inbound-reference audit). Task 10 rests on the real `pointer-closeout` templates + helper-script path resolution. Task 11 rests on the real skill-creator `run_eval.py` contract.

## Execution notes

- **Dependency order:** 1 → 2, 3 → 4, then 5; Group C (6–9) is independent and parallel-safe (different files per skill); Task 10 should run **after** 1–9 so it closes out real completed work; Task 11 is independent. Recommended linear order: 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 10 (evals before the close-out so the eval result can be cited in it).
- **Two decision points** need the user before their steps land: the README installed-plugin invocation (Task 3 Step 5) and whether to track the `Virtuoso/` dogfood artifacts (Task 10 Step 5).
- **Git Workflow:** if the project's workflow has Cowork author-but-not-certify commits, treat each `git commit` as "stage + propose". Do not bump any version string.
