---
name: next-pointer
description: |
  MANUAL INVOCATION ONLY. Dispatch-finalization + pointer skill. ONLY
  runs when the user types "/next-pointer", "next pointer", "show
  next", or "what's next". Reads the next fully-specced sprint at the
  head of the conveyor belt, runs a dispatch-readiness audit, finalizes
  the spec so a lower-capability implementer cannot fail, drives every
  pre-flight check to done (or elevates it as a question), reconciles
  git on both sides, and prints a plain-language summary, roadmap KPIs,
  and a code-boxed dispatch pointer. If the head is a stub or has
  unresolved structural gaps, it STOPS and tells the user to run
  /roadmap-review.
---

# Next Pointer

## Preflight — workspace check (run first)

This skill operates on the project's Virtuoso workspace. Before anything else, bring the project under management non-destructively:

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode adopt

`adopt` never moves or duplicates anything. Read the `virtuoso-status:` line it prints and branch:

- `ready` — a `Virtuoso/` workspace already exists (it was healed if needed); continue.
- `adopted roadmap=<path>` — the project already had an established documentation tree (e.g. `Project Documentation/` or `2. Project Documentation/`) with its own roadmap, so a thin `Virtuoso/` control marker was written that points at that existing roadmap. Tell the user it was adopted in place — nothing was moved or duplicated — then continue.
- `none` — there is no workspace and no documentation tree to adopt (treat a missing `~/.virtuoso/plugin-root` the same way). Stop this skill and route the user to `/virtuoso-init`, which asks whether to use the plugin-only or the canonical `Virtuoso/Project Documentation/` layout.

**Workspace paths.** Read `Virtuoso/workspace-layout.json` first and use its `paths` map. For an adopted project, `paths.roadmap` and `paths.sprintQueue` point at the project's own existing files under whatever names they use (e.g. `GoG_Roadmap.md`). Key entries include `roadmap`, `sprintQueue`, `closeOuts`, `issues`, `outsideAudits`, `reference`, and `scripts`. If the manifest is missing, run `/virtuoso-init`; only fall back to legacy flat `Virtuoso/` paths for older projects.


The dispatch gate. Reads the head of the conveyor belt, finalizes the
full spec so a lower-model CLI agent can implement it without
judgment calls, **completes every pre-flight check** (or elevates it
as a question) so nothing is left dangling, then prints:

1. **Plain-language summary** of what's next
2. **Roadmap KPIs** (sourced from the Dashboard tab)
3. **Sprint Pointer** in a code box, including a complete **git
   reconciliation protocol** the CLI implementer runs as step 0

The skill assumes you (Cowork) are the highest-capability model in
the pipeline and the CLI agent doing the implementation is of lower
capability. Therefore the spec must contain every decision, every
file:line reference, every test name, every constant, every edge-case
response — explicit enough that perfect implementation is the only
possible outcome.

**Bookend with `/pointer-closeout`.** This skill opens a dispatch; `pointer-closeout`
closes it. After the dispatched sprint completes and the implementer reports back, run
`/pointer-closeout` to process the result into the roadmap and the retrospective. The two
are a matched pair — every pointer this skill prints is later closed by a
`pointer-closeout` run.

## Completely reconciling git — two halves

"Completely reconciles git" spans **two** reconciliations, and the
gate is not "ready" until both hold:

- **Upstream — the enrichment commit (folded into the sprint's git
  reconciliation).** When Cowork enriches the head spec inline (Phase 3), that
  edit lands in the working tree *uncommitted*. Rather than quarantining it into a
  separate pre-dispatch hand-off, the dispatch pointer's git reconciliation recipe
  lands it **as part of the sprint**: the implementer commits the finalized spec
  (to the default branch, or the sprint branch, per the project's Git Workflow) as
  step 0, before cutting the worktree — so the work always proceeds from a branch
  that carries its own spec. Cowork authored the edit and verifies the
  working-tree state read-only; the sprint's implementer commits it (separation of
  duties — the author doesn't certify its own commit).
- **Downstream — the worktree recipe (embedded in the pointer, the CLI
  implementer's job).** /next-pointer bakes a complete, ordered git
  reconciliation recipe into the dispatch pointer. The implementer runs
  it before writing any code, landing the repo in a fully reconciled
  state: clean working tree, local main fast-forwarded to
  `origin/main`, orphan/stale branches cleared, sprint branch created
  from clean main. It is a positive, copy-pasteable sequence — not a
  checklist of prohibitions — so a lower-model agent cannot misorder it.

**The git invariant (holds in every project).** Cowork **never runs
mutating git** — no `add`, `commit`, `push`, `merge`, `rebase`,
`branch`, `checkout`, `switch -c`, `reset`, `stash`, `worktree add`,
or any state-changing subcommand. Cowork verifies from **primary
evidence**, never from a pasted summary ("tree clean", "reconciled").
**Read-only git is always available** — Cowork runs `status`, `log`, `diff`, and
`show` freely and lock-free (`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`) in
**every** project, as the independent reconciler. Legacy mutating-handoff
conventions (e.g. `git-handoff`) govern only *state-changing* git — they never
gate reads, and "no commits" never means "no git at all." Cowork verifies from
this primary evidence, and still never trusts a pasted *summary* claim ("tree
clean", "reconciled") without the underlying output.

## When to use

- About to dispatch a sprint and want the spec finalized
- Checking what's queued before committing to a dispatch
- Quick "where am I + what's next" status

## Do NOT use this for

- Full status briefing — use /roadmap-status
- Replanning, sequencing, or generating new sprints — use
  /roadmap-review
- Dispatching when the head is still a stub — run /roadmap-review
  first; this skill refuses to dispatch a stub

## Invocation

Manual only. Triggered by:
- `/next-pointer`
- "next pointer"
- "show next"
- "what's next"

## Glossary

These terms are used precisely throughout this skill.

- **Sprint** — A discrete unit of work (1-5 days, S-M t-shirt) with
  clear acceptance criteria. Identified by a code like `SK-XX`.
- **Phase** — A coherent shippable chunk containing multiple
  sprints, with a clear theme, goal, and exit criteria.
- **Stage** — Optional sub-grouping within a phase.
- **Stub** — A placeholder sprint card with just code, title, and
  optionally a one-line gist. Lives inline in the roadmap; the
  Catalog row marks Written Status as `Stub` (or `None`).
- **Full spec** — A sprint card with all 7 structural fields PLUS
  implementation detail. Lives inline in the roadmap. The Catalog
  row marks Written Status as `Full Spec`.
- **Dispatch-ready full spec** — A full spec that has passed the
  Dispatch-Readiness Rubric below. Every code reference is verified
  against current state. Every decision is made. Every Done-when
  criterion is mechanically verifiable. No "TBD" remains.
- **Dispatch** — The act of sending a sprint to the implementer.
  The implementer reads the dispatch-ready full spec inline in the
  roadmap and runs it. No judgment required.
- **Pointer** — A small code-boxed textual block telling the
  dispatcher exactly where the spec lives plus immediate context.
- **Buffer** — The next 5 sprints. /roadmap-review keeps it at 5.
- **Scope** — What's included in / excluded from a sprint.
- **Conveyor belt** — The sequenced list of all uncompleted sprints
  in the roadmap's active section, mirrored in `sprint-queue.xlsx`.

## Operating principles

1. **Spec finalization is the primary job.** This skill is the last
   line of defense between Cowork's planning and the CLI agent's
   implementation. A spec that passes through /next-pointer must be
   dispatch-ready by the rubric below.
2. **Cowork is the highest model in the pipeline.** All judgment,
   investigation, and decision-making happens here. The CLI
   implementer follows the recipe; it does not improvise.
3. **Writes are permitted to enrich the head spec AND to complete
   pre-flight checks for this dispatch.** The skill may edit the
   roadmap document to add verified file:line refs, test names,
   constants; recalc the `sprint-queue.xlsx` Dashboard; and advance
   the head sprint's own Catalog row to reflect reality (e.g. a merged
   wave). It does NOT re-sequence, add new sprints, or modify other
   sprints' skeletons — that is /roadmap-review's job.
4. **Hard halt on stub head.** If the sprint at the head has
   Written Status ≠ `Full Spec`, STOP and tell the user to run
   /roadmap-review. No partial dispatch.
5. **Hard halt on structural gaps.** If the spec has gaps requiring
   genuine human judgment (a design decision deferred, a scope
   question unresolved), STOP and AskUserQuestion. Do NOT improvise
   the decision.
6. **Three-section output, in this order:** plain-language
   summary, roadmap KPIs, code-boxed pointer.
7. **Plain language first.** The summary is one-to-two sentences in
   complete plain English. Same LEDE rules as /roadmap-status.
8. **AskUserQuestion only when forced.** Most rubric gaps can be
   closed by grep / code-read / DB query / file inspection. Only
   escalate to AskUserQuestion when the gap is a real decision.
9. **Cowork never runs mutating git.** No `add`/`commit`/`push`/
   `merge`/`rebase`/`branch`/`checkout`/`switch -c`/`reset`/`stash`/
   `worktree add` — ever, in any project. **Read-only inspection is always
   allowed**: run it lock-free (`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`)
   in every project as the independent reconciler (legacy mutating-handoff rules
   never gate reads). **Verify from primary evidence, never from a pasted
   summary.**
10. **The enrichment commit rides with the sprint.** If Phase 3 edited the spec
    inline, that edit is uncommitted in the working tree. Rather than blocking
    dispatch on a separate hand-off, fold it into the pointer's git reconciliation
    recipe: the implementer commits the finalized spec as step 0 of the sprint
    (before cutting the worktree), per the project's Git Workflow. Cowork verifies
    the uncommitted edit read-only; the implementer commits it (separation of
    duties — the author doesn't certify its own commit).
11. **Don't let the spec sit uncommitted.** The author-can't-commit rule bars
    exactly one entity: the author (Cowork). The sprint's implementer (or the
    user) is the sanctioned committer and lands the enrichment as part of the
    sprint's git reconciliation. If anyone cites "no git" to refuse, correct the
    misread — reads are always allowed and the implementer commits — and do not
    let a bounce-back loop leave the spec uncommitted.
12. **Every pointer carries a complete git reconciliation recipe.**
    The recipe is mandatory and non-negotiable per dispatch. It lands
    the repo in a fully reconciled state (clean tree, synced main, no
    orphan/stale branches, correct branch from clean main) before a
    single line of implementation. It is a positive ordered sequence;
    it preserves uncommitted work (never auto-discards) and halts on
    divergence rather than forcing.
13. **Pre-flight checks are completed, not just reported.** This is the
    rule that gates the verdict. Every pre-flight check must end ☑ —
    either already satisfied, or **completed by Cowork now** (recalc
    the Dashboard, advance the head's Catalog row, embed/repair the
    recipe, re-verify git), or **explicitly accepted by the user**.
    A check Cowork cannot close by itself is **elevated as an
    AskUserQuestion**, not deferred to a later /roadmap-status. **Never
    print "Ready to dispatch" with a bare ☐ check** — a dangling ☐
    means either the work isn't done (do it) or a decision is pending
    (ask it). "Note it and move on" is forbidden.

---

## Dispatch-Readiness Rubric

Every full spec must pass these checks before /next-pointer
proceeds to print the pointer. Walk them in order in Phase 2.

### Rubric R1 — Edit Sites
For every `file:line` reference in the spec's Implementation Detail:
- [ ] The file exists at that path.
- [ ] The line number is current (grep / read to verify; line
      numbers can shift after upstream sprints land).
- [ ] The code at that line matches the spec's intent (the function
      name / constant / structure mentioned in the spec is actually
      there).
- [ ] If line numbers have shifted, **update them inline in the
      spec**.

### Rubric R2 — Test Names
For every test mentioned in Done-when or Implementation Detail:
- [ ] The test name is a full path:
      `tests/test_module.py::test_function` (or test class form).
- [ ] For new tests: the target file is explicit; the test function
      name is explicit; the assertion content is explicit
      ("assert f(X) == Y", not "verify it works").
- [ ] For existing tests being modified: the current assertion is
      quoted in the spec; the new assertion is quoted in the spec.
- [ ] If any test reference is vague, **enrich the spec inline**
      with concrete details.

### Rubric R3 — Constants
For every named constant in the spec:
- [ ] The constant exists in the codebase (grep to confirm).
- [ ] Current value is documented in the spec.
- [ ] Target value (or removal directive) is explicit.
- [ ] Constant's file location is named.
- [ ] If any constant is unverified, **grep and add the verified
      file:line + current value to the spec**.

### Rubric R4 — Done-When Criteria
For every Done-when bullet:
- [ ] The criterion is **mechanically verifiable** — a shell
      command, a test assertion, or a file-existence check that
      returns true/false unambiguously.
- [ ] No criterion requires human judgment ("looks right", "is
      reasonable", "matches design intent" — all forbidden).
- [ ] Each criterion's verification command is in the spec (e.g.,
      `grep -c '<constant>' .` returns 0).
- [ ] If a criterion is vague, **rewrite it inline to be
      mechanical**.

### Rubric R5 — Branch + Commit Hygiene
- [ ] Branch name is explicit (e.g., `sk-fu12-e-wave-a`).
- [ ] Source branch is explicit ("from clean main").
- [ ] Commit hygiene rules referenced (CL-WF-01 clean-tree gate;
      no `git add .` / `-A`; no destructive flags).
- [ ] If missing, **add to the spec**.
- [ ] The full git reconciliation recipe (R11) is present in the
      pointer. R5 names the branch; **R11 reconciles the repo**.

### Rubric R6 — Calibration Cadence (if applicable)
For any sprint touching calibration:
- [ ] Quick-cal config explicit: N value, seed count, deterministic
      flag.
- [ ] Full-cal escalation rule explicit: threshold (e.g., ">3pp on
      any primary metric"), reference SRL (e.g., SRL-113).
- [ ] Band check explicit: what bands are being measured, what the
      current values are, what the targets are.
- [ ] Pre-authorized halt conditions explicit (when to STOP and
      escalate to Cowork).
- [ ] If missing, **enrich the spec**.

### Rubric R7 — Edge Cases + Failure Modes
- [ ] "If X fails, do Y" is explicit for each known failure mode.
- [ ] Rollback plan stated (revert command, branch deletion, etc.).
- [ ] Retry ceiling explicit (3 attempts max per wave is the
      default).
- [ ] If gaps exist, **enrich the spec**.

### Rubric R8 — Prerequisites Verified
- [ ] Every prerequisite is `Completed` in the Catalog OR
      `Dissolved`/superseded with a documented disposition.
- [ ] If any prerequisite is `Queued` / `In Flight` / `Blocked`,
      the head sprint is **not dispatchable now**. Halt printing
      and flag the blocker.

### Rubric R9 — No Deferred Decisions
- [ ] Search the spec for: "TBD", "to be decided", "decide later",
      "ask Cowork", "consult", "verify with user".
- [ ] If any of these appear, the decision must be resolved before
      dispatch. If Cowork can resolve via investigation
      (grep / DB query / file read), do it and update the spec. If
      it requires user judgment, AskUserQuestion.

### Rubric R10 — Source Citations
- [ ] The Source line links to specific close-outs, audits, or
      decision docs.
- [ ] Citations include exact section anchors (e.g., "FAS-1 §9
      Decision 10") where applicable.
- [ ] If missing, **enrich the spec**.

### Rubric R11 — Git Reconciliation (mandatory, every dispatch)
The pointer MUST embed the complete git reconciliation recipe (see
**Git Reconciliation Protocol** below) for the CLI implementer to run
as step 0. Verify all four guarantees are expressed:
- [ ] **Clean working tree** — recipe checks `git status --porcelain`
      and HALTS (does not stash/reset/clean) if non-empty; stale
      `.git/index.lock` handling is described.
- [ ] **Main synced with remote** — recipe fetches `origin`, switches
      to the default branch, and `merge --ff-only origin/<default>`;
      on divergence it HALTS (no force/reset/rebase) but offers the
      sanctioned fallback — branch off `origin/<default>` directly,
      leaving local main for a human — as an explicit, flagged option.
- [ ] **No orphan / stale branches** — recipe inspects `git branch -vv`,
      safe-deletes fully-merged `[gone]` branches with `-d` (never
      `-D`), and runs `git worktree prune`.
- [ ] **Correct branch from clean main** — recipe creates the R5
      branch name with `git switch -c <branch> <default>`, and HALTS
      if the branch already exists on a stale base.
- [ ] The recipe's default branch name (`main` vs `master`) matches
      this repo. Determine it by reading the repo's git config (e.g.
      `git config`, `git symbolic-ref` — both read-only) or a committed
      reference; if unknown, the recipe derives it via
      `git symbolic-ref refs/remotes/origin/HEAD`.
- [ ] Final **verification block** is present (tree empty, HEAD on the
      sprint branch, `main..origin/main` count == 0).
- [ ] If any element is missing, **insert the canonical recipe into
      the pointer** (this is enrichment Cowork performs; it does NOT
      require running git).

---

## Inputs

1. The project's roadmap document (filename from `roadmap_doc`
   frontmatter; default `Roadmap.md`)
2. `sprint-queue.xlsx`:
   - **Dashboard tab** for pre-computed KPIs (read with
     `data_only=True`)
   - **Catalog tab** for the head sprint's metadata and
     prerequisite status
   - Use the xlsx skill (anthropic-skills:xlsx) for mechanics
3. Most recent file in `roadmap-reviews/` — for "last review"
   timestamp
4. Most recent assessment file — for pace read
5. Standing Rules section of the roadmap document
6. Completed Work Summary table — for prerequisite verification
7. **Project codebase** — for rubric verification (grep, code
   reads, schema queries)
8. **The project's Git Workflow rules** (CLAUDE.md / governance doc) —
   to identify the sanctioned committer for the enrichment commit (the
   sprint's implementer, or the user). Read-only git is always available
   for inspection — no project gates reads.

## Outputs

1. A single formatted briefing in chat (the three-section output)
2. Possibly: edits to the head sprint's full spec inline in the
   roadmap document, made during Phase 3 enrichment
3. A complete git reconciliation recipe embedded in the Sprint
   Pointer for the CLI implementer to run as step 0 (R11)
4. If Phase 3 edited the spec: a verified read of git state and a
   handoff for the enrichment commit (Phase 3.5) — Cowork never runs
   the commit itself
5. Possibly: pre-flight completions (Phase 3.6) — a recalced Dashboard
   and/or the head sprint's Catalog row advanced to reflect reality, so
   no pre-flight check is left dangling
6. Possibly: AskUserQuestion(s) for any pre-flight check that needs a
   decision before it can be closed

---

## Git Reconciliation Protocol

This is the canonical recipe embedded in every Sprint Pointer
(Phase 4) and audited by Rubric R11 — the **downstream** half of
reconciliation. **The CLI implementer runs it verbatim as step 0,
before any implementation.** Cowork only emits it into the pointer
(text enrichment — no git). It is distinct from the **upstream**
enrichment-commit reconciliation Cowork performs in Phase 3.5.

The recipe is git-shell-agnostic (git is git on PowerShell or Git
Bash). Substitute `<default>` with the repo's default branch (`main`
unless the repo says otherwise) and `<branch-name>` with the R5
sprint branch. It preserves uncommitted work and halts on divergence
rather than forcing.

```
# ── Step 0: GIT RECONCILIATION — run before writing any code ──

# 0a. Confirm repo + resolve default branch.
git rev-parse --is-inside-work-tree
git symbolic-ref --short refs/remotes/origin/HEAD   # → origin/<default>

# 0b. Clean working tree gate (CL-WF-01).
git status --porcelain
#   EMPTY     → tree clean, continue.
#   NON-EMPTY → STOP. Do NOT stash / reset / clean. Report the dirty
#               paths and halt; uncommitted work is never discarded.
#   Stale lock: if `.git/index.lock` exists AND no git process is
#               running, delete only that lock, then re-check status.

# 0c. Sync the default branch with remote.
git fetch origin --prune
git switch <default>
git merge --ff-only origin/<default>
#   ff-only fails (local <default> diverged) → STOP reconciling <default>.
#   Do not force, do not reset --hard, do not rebase without authorization.
#   SANCTIONED FALLBACK (flag it, don't do it silently): cut the sprint
#   branch directly off the remote tip and leave local <default> for a
#   human to reconcile separately —
#       git switch -c <branch-name> origin/<default>
#   This unblocks the sprint from a correct base WITHOUT touching the
#   diverged local <default>. Report that you took the fallback and that
#   local <default> is still diverged (the "main synced" guarantee is
#   deferred to that separate human reconciliation). If you take this
#   fallback, SKIP 0e (the branch is already created).

# 0d. Clear orphan / stale branches and worktrees.
git branch -vv                 # branches tagged [gone] are merged/deleted upstream
git branch -d <gone-branch>    # safe delete, fully-merged only; never -D
git worktree list
git worktree prune             # drop refs to deleted worktree dirs

# 0e. Create the sprint branch from clean <default>.
git switch -c <branch-name> <default>
#   If <branch-name> already exists → confirm it is based on current
#   <default>; if stale, STOP and report (do not reuse a stale base).

# 0f. Verify reconciled state — ALL must hold before coding:
git status --porcelain                    # → empty
git branch --show-current                 # → <branch-name>
git rev-list --count <default>..origin/<default>   # → 0  (main up to date)
```

**During the sprint** (carried in commit hygiene, not part of step 0):
stage explicit paths only — never `git add .` / `git add -A`; no
destructive flags (`--hard`, `--force`, `clean -fd`) without explicit
authorization; no force-push.

**Halt semantics.** Steps 0b, 0c, and 0e can HALT. On any halt the
implementer stops, reports the exact git output, and escalates — it
never improvises a recovery that could destroy work. A halt here is a
dispatch blocker, surfaced the same way as a failed prerequisite.

---

## Phase 1 — READ AND IDENTIFY

### 1.1 Determine the head sprint
Read the `sprint-queue.xlsx` Catalog tab. Filter rows where
`Implementation Status = "Queued"` or `"In Flight"`. Sort by `Seq`
ascending. The first row is the head sprint.

Extract: Sprint Code, Title, Phase, Stage, LOE, Dependencies,
Implementation Status, Written Status, Description, Branch.

If no `Queued` / `In Flight` rows → **Queue empty** edge case.

### 1.2 Hard-halt check (stub at head)
If the head sprint's `Written Status ≠ "Full Spec"`:
- STOP. Branch to the **Buffer empty / stub at head** edge case.

### 1.3 Locate the full spec in the roadmap
Read the roadmap document and find the head sprint's block under
its Phase → Stage → Sprint heading. Parse all 7 structural fields
and the Implementation Detail sub-section.

### 1.4 Pull KPIs from Dashboard
Read with `data_only=True`. Source cells:

Sprint data lives on the **`DATA.sprint-catalog`** sheet (table `sprint_catalog`).

**From the Dashboard** (`data_only=True`):
| KPI | Cell |
|---|---|
| % Complete (by LOE) | B24 |
| LOE remaining (points) | B21 |
| Sprints to finish line (sprints remaining) | B25 |
| Avg sprint size (points) | B26 |

**Computed from the Catalog** (no longer on the Dashboard in this workbook):
| KPI | How |
|---|---|
| Fully specced sprints remaining (incl. this one) | count rows where Implementation Status `Queued` ∧ Written Status `Full Spec` |
| Buffer health | from that count → ≥5 Healthy / ≥3 Running low / ≥1 Critical / else Empty |
| Sprints to end of current phase | count rows where Phase = current phase and not done |

Compute "% remaining by LOE" = 1 − B24.

Last /roadmap-review = mtime of most recent file in
`roadmap-reviews/`.

Pace = read from most recent assessment file's pace verdict.

If Dashboard cells appear stale (empty/`None` because formulas were
never recalced after manual Catalog edits), compute the KPIs directly
from the Catalog now so the figures you report are correct — and do
NOT leave "Dashboard stale" as a dangling ☐. Closing it is a Phase 3.6
pre-flight item: recalc the workbook (don't just flag it). Carry the
Catalog-direct figures forward as authoritative in the meantime.

### 1.5 Identify applicable Standing Rules
Read the roadmap's `### Standing Rules All Skeletons Inherit`
section. Match against the head sprint's domain by keyword:
- Calibration → SRL-113, SRL-155
- Git operations → CL-WF-01, commit-hygiene rules
- RNG / randomness → SRL-130
- Data population → SRL-126, SRL-150
- (Generalize for whatever rules exist in the project.)

Pick the top 1-2 most relevant rules.

---

## Phase 2 — DISPATCH-READINESS AUDIT

Walk the rubric (R1-R11) against the head sprint's full spec.

For each rubric item:
- **PASS** → check the box, move on.
- **CLOSABLE GAP** → the spec has a verifiable assertion that can
  be confirmed by investigation (grep, code read, DB query). Flag
  for Phase 3 enrichment.
- **STRUCTURAL GAP** → the spec has a real decision deferred or
  scope ambiguity. Halt printing the pointer; AskUserQuestion. If
  the user cannot resolve in <5 min, escalate to /roadmap-review.

Produce a Phase 2 audit summary internally:
- N rubric items checked
- M passed
- K closable gaps (proceed to Phase 3)
- J structural gaps (halt + AskUserQuestion or escalate)

### 2.1 Verify prerequisites
For each prerequisite from R8:
- Search the Catalog for the prereq's row.
  - `Completed` → `✓ met`
  - `Dissolved` → `✓ resolved (superseded)`
  - `Queued` / `In Flight` / `Blocked` → `✗ pending`
- If not found in Catalog, also check `## Completed Work Summary`
  in the roadmap → if found, `✓ met`
- Otherwise `? unknown`

If any prereq is `✗ pending` or `? unknown`, the sprint is **not
dispatchable now**. Still produce the output but flip the bottom
line to "Not ready" with the reason and suggest an alternative
sprint deeper in the queue if one is dispatchable (Written Status
= `Full Spec` AND all prereqs met).

---

## Phase 3 — ENRICHMENT (only if Phase 2 flagged closable gaps)

For each closable gap from Phase 2, do the investigative work and
update the spec inline.

### 3.1 Investigation playbook

| Gap type | How to close |
|---|---|
| Stale `file:line` ref | Grep for the symbol; read the file; update the line number inline. |
| Missing test name | Read the test file area; propose a specific test name + assertion; insert into spec. |
| Unverified constant | Grep for the constant; document current value + file location. If constant doesn't exist, flag as structural gap. |
| Vague Done-when | Rewrite the criterion as a mechanical check (shell command, test assertion, file existence). |
| Missing branch name | Apply convention `<sprint-id>-wave-<N>`. |
| Missing cal cadence | Look at recent close-outs of similar sprints for the cadence convention. Apply project-standard defaults if no precedent. |
| Missing rollback plan | Standard pattern: revert the wave's commit, delete the feature branch, re-baseline. Insert into spec. |
| Missing edge case | Identify common failure modes (test failure, grep-verification failure, cal escalation); add "if X, do Y" lines. |
| Missing source citation | Search for relevant close-outs / audits / decisions; add specific section refs. |
| Missing/partial git reconciliation recipe (R11) | Insert the canonical **Git Reconciliation Protocol** into the pointer with `<default>` and `<branch-name>` substituted. No git run — pure text enrichment. |

### 3.2 Update the spec inline in the roadmap

Use targeted edits to the roadmap document. Be surgical:
- Don't rewrite sections that don't need it
- Preserve existing structure and formatting
- Add new content under the appropriate Implementation Detail
  bullet (or create the bullet if missing)
- Mark enrichment additions with a comment if helpful for audit
  trail: `<!-- enriched by /next-pointer YYYY-MM-DD -->` (optional)

### 3.3 Re-audit
After enrichment, walk the rubric again. If any item still fails,
either:
- Try a second enrichment pass (max 2 passes)
- Escalate to AskUserQuestion
- Escalate to /roadmap-review (halt printing)

### 3.4 Update Catalog row (optional)
If enrichment added significant content, the Catalog row's
Description may benefit from a one-line refresh. Optional — not
required. (Distinct from advancing the row's *status* to reflect a
merged wave, which is a mandatory Phase 3.6 pre-flight item, not
optional.)

---

## Phase 3.5 — ENRICHMENT-COMMIT RECONCILIATION (only if Phase 3 edited the spec)

This is the **upstream** half of "completely reconciles git." If
Phase 3 did NOT edit the roadmap, skip this phase. If it did, the
finalized spec is sitting **uncommitted in the working tree** — and
the implementer's worktree (downstream) will be cut from `main`. If
`main` doesn't carry the spec, the implementer cuts a worktree
**missing its own spec**. So the gate is not "ready" until `main`
carries the finalized spec.

**Cowork never runs mutating git, and never commits its own authored edit** — but
read-only git is always available here. This phase verifies state and folds the
enrichment commit into the sprint's git reconciliation recipe; the sprint's
implementer (or the user) runs the commit as step 0 of the sprint.

### 3.5.1 Verify state from primary evidence
Inspect with read-only, lock-free git (always available — reads are never gated):

```
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks status -sb        # branch + dirty paths
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks diff --stat       # what changed
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks log --oneline -1  # current HEAD
```

Confirm: the ONLY dirty path is the roadmap doc you edited; the diff
is confined to the head sprint's section; nothing is staged unexpectedly.
**Verify from this evidence, not from any prior summary.**

### 3.5.2 Hand off the governance commit (separation of duties)
Cowork authored the edit, so Cowork does NOT commit it. Emit a
copy-paste handoff for the user (or instruct a dispatched non-author
agent, e.g. Hermes, per the project's Git Workflow). Stage **explicit
paths only** — never `git add .` / `-A`:

```
git add "<path/to/roadmap_doc>"
git commit -m "docs(roadmap): <SPRINT-CODE> dispatch-ready spec (finalized at /next-pointer)"
git push origin <default>
git --no-optional-locks log --oneline -1   # paste this back
```

### 3.5.3 Re-verify after the commit lands (primary evidence, not the report)
When the user says it's done (or pastes a reconciliation report), do
NOT take "tree clean" / "reconciled" at face value. Re-inspect and
confirm against ground truth:

```
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks status -sb
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks log --oneline -1
# decisive: is the enrichment actually on the committed roadmap?
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks show HEAD:"<path/to/roadmap_doc>" | grep -c "<a distinctive token from the enrichment>"
```

If a pasted report claims "clean" but the enrichment isn't on `HEAD`,
**flag the contradiction explicitly** — the spec was not lost (it's
the uncommitted working-tree edit), it simply was never committed. The
commit still has to land.

### 3.5.4 Break a commit deadlock
If a bounce-back loop forms — user defers to the agent, agent declines
citing "the author never certifies its own commit" — name the misread
and break it: **the author-can't-commit rule bars only Cowork (the
author).** A non-author committing is the *sanctioned* path, not a
violation. Point to it (user runs the handoff, or the dispatched agent
commits) and do not let the spec sit uncommitted.

### 3.5.5 Gate consequence
Until `main` carries the spec, the Phase 4 bottom line is **"Not ready
— enrichment uncommitted; main does not yet carry the spec."** The
pre-dispatch check "Spec committed to main" stays ☐. Once re-verified
on `HEAD`, flip it ☑ and the gate clears.

---

## Phase 3.6 — PRE-FLIGHT COMPLETION

**The verdict gate. Walk every pre-flight check and drive each to ☑ —
complete it, or elevate it — before composing the output.** A check
left ☐ and merely "noted" is a defect: "Ready to dispatch" with a
dangling ☐ is forbidden (principle 13).

For each check, classify and act:

| State | Action |
|---|---|
| **SATISFIED** | Mark ☑. |
| **AUTO-COMPLETABLE** | Cowork does the work now, then ☑ (note what was done). |
| **NEEDS A DECISION** | AskUserQuestion; on the answer, complete it → ☑ (or user-accept). |
| **EXTERNALLY BLOCKED** | Cannot be closed by Cowork or a quick decision (a prereq sprint isn't done; the enrichment commit must be run by a non-author). Surface the handoff and flip the bottom line to **Not ready**. This is the only legitimate ☐ at print time. |

### 3.6.1 The pre-flight checklist (drive each to ☑)
1. **Dispatch-readiness rubric 11/11** — closed in Phase 2+3. If a
   structural gap remains → AskUserQuestion / escalate (already
   handled). R1 re-confirmed against current HEAD (no code drift since
   the spec's edit sites were verified).
2. **Prerequisites met** — if a prereq is pending, it is *externally
   blocked*: AskUserQuestion (hold vs. the alternative-dispatch path).
3. **Spec committed to `main`** — Phase 3.5. Externally blocked on a
   non-author commit → handoff; Not ready until verified on HEAD.
4. **KPIs accurate / Dashboard fresh** — if the Dashboard cache is
   stale, **recalc it now** (auto-completable). Mechanic: run the bundled
   recalc script — `python <scripts>/recalc.py <sprintQueue>`, resolving both values from
   `Virtuoso/workspace-layout.json`
   — then reload and confirm the cells populate. (The recalc engine always
   ships with the plugin, so there is no "no engine" fallback.) Do not leave a
   bare "Dashboard stale ☐".
5. **Catalog reflects reality** — if the head's row is behind reality
   (e.g. a merged wave not recorded), **advance the head sprint's own
   row** (auto-completable when the correct state is unambiguous). If
   representing it correctly needs a judgment (how to show a partially
   complete wave-decomposed sprint in one row) → AskUserQuestion. Do
   not leave a bare "Catalog housekeeping ☐" or punt it to
   /roadmap-status.
6. **Serialization clear** — verify (read-only, per project Git
   Workflow) that the worktree set is canonical-only and **no branch
   for this sprint is already in flight**. An in-flight branch means a
   dispatch may already be running → AskUserQuestion before
   re-dispatching.
7. **R11 recipe embedded** — auto-completable (text); embed if missing.

### 3.6.2 Concern → question, not a footnote
When a check is NEEDS A DECISION, raise an AskUserQuestion with the
concern stated plainly, ≥2 options, one `[RECOMMENDED]`, and an escape
hatch. Capture the answer, complete the check, then proceed. Only a
genuinely EXTERNALLY-BLOCKED check survives to print time as ☐ — and
it forces the bottom line to **Not ready**.

---

## Phase 4 — COMPOSE AND PRINT

### 4.1 Plain-language summary writing rules

Same LEDE rules as /roadmap-status:
- Lead with `[SPRINT-CODE]` in brackets, then a bolded one-to-two
  sentence LEDE.
- The LEDE answers: what the sprint does + why it matters.
- Plain English. Complete sentences. No fragments. No bare
  acronyms.
- Lead with news, not process.

The "stranger test" applies.

### 4.2 Standard output format

```
# Dispatch Pointer — [SPRINT-CODE]

## What's next

[SPRINT-CODE] **One-to-two-sentence plain-language LEDE: what the
sprint does and why it matters.**
- *Optional sub-bullet: adaptation, risk, or upstream consideration.*

## Roadmap KPIs

| Metric | Value |
|---|---|
| Fully specced sprints remaining (incl. this one) | N / 5 — [healthy / running low / critical / empty] |
| Sprints to end of current phase ([Phase Name]) | X |
| Sprints to finish line | Y sprints — ~Z% remaining by LOE |
| Prerequisites for [SPRINT-CODE] | all met / blocked on [list] |
| Last /roadmap-review | N days ago |
| Pace | On track / Behind / Ahead — [one-line reasoning] |

## Sprint Pointer

\```
[SPRINT-CODE] — Title
Phase X / Stage Y
LOE: [size] | Effort: [estimate]
Branch: [branch-name] from clean [default] @ [HEAD-sha carrying the spec]
Full spec: [roadmap_doc] §Phase X / Stage Y / [SPRINT-CODE] — committed [sha]
Status: next up (not in flight) | Deps: [list with ✓ or ✗ markers]
Dispatch-Readiness Rubric: [N/11] PASS  (enriched [if Phase 3 ran])
\```

## Git Reconciliation — CLI implementer runs this FIRST

\```
# ── Step 0: GIT RECONCILIATION — before any implementation ──
# (Cowork does not run git; the implementer executes this verbatim.)

git rev-parse --is-inside-work-tree
git symbolic-ref --short refs/remotes/origin/HEAD   # → origin/[default]

git status --porcelain          # EMPTY → continue; NON-EMPTY → STOP (never discard)

git fetch origin --prune
git switch [default]
git merge --ff-only origin/[default]    # diverged → STOP (no force/reset/rebase)
#   FALLBACK on divergence (flag it): git switch -c [branch-name] origin/[default]
#   — branch off the remote tip, leave local [default] for a human; then SKIP the
#   switch -c below. Report that local [default] is still diverged.

git branch -vv                  # [gone] = merged/deleted upstream
git branch -d [gone-branch]     # safe delete only; never -D
git worktree prune

git switch -c [branch-name] [default]   # exists on stale base → STOP

git status --porcelain                          # → empty
git branch --show-current                       # → [branch-name]
git rev-list --count [default]..origin/[default]   # → 0
\```

Halt on any STOP above and report the git output — it is a dispatch
blocker, not something to improvise around. Commit hygiene during the
sprint: explicit paths only (no `git add .` / `-A`); no destructive
flags without authorization.

## Standing Rules to remember
- **[SRL-XXX] — [short title].** [One-sentence rule statement.]
- **[CL-XX] — [short title].** [One-sentence rule statement.]

## Pre-dispatch checks
*(Phase 3.6 already drove these to ☑ or elevated them. Under a "Ready"
verdict EVERY box is ☑ — there are no dangling ☐ items. If something
can't be closed, the verdict is "Not ready" and that item is named.)*
- [☑] Dispatch-readiness rubric passed (11/11; R1 re-confirmed vs current HEAD)
- [☑] Prerequisites met
- [☑] Spec committed to `main` ([sha]) and present in the trunk roadmap
- [☑] KPIs accurate (Dashboard recalced — or user-accepted Catalog-direct)
- [☑] Catalog reflects reality (head row advanced for any merged wave)
- [☑] Working tree clean; worktree canonical-only; no in-flight branch for this sprint (serialization clear)
- [☑] Git reconciliation recipe embedded in the pointer (R11) — the
  implementer's step-0 worktree reconciliation lives in that recipe

[If any check above could NOT be driven to ☑ — a pending prerequisite,
an uncommitted enrichment, a stale Dashboard with no recalc engine, an
in-flight branch — DO NOT print this list as all-☑. Show the open item
as ☐, append its handoff / the AskUserQuestion you raised, and set the
bottom line to "Not ready."]

[Ready to dispatch — every pre-flight check is ☑; the CLI agent can
implement this spec without judgment calls.] | [Not ready — [the named
open check].]
```

### 4.3 Pre-print verification

Before sending the output:
1. Did the plain-language summary pass the stranger test?
2. Is the LEDE bolded and 1-2 sentences? Leads with news?
3. Are all KPI cells filled?
4. Are ✓/✗ markers consistent across the table, pointer, and
   pre-dispatch checks?
5. Does the bottom line match prereq + rubric status?
6. If Phase 3 enrichment ran, did the rubric re-audit pass?
7. Is the git reconciliation recipe present in the pointer with
   `[default]` and `[branch-name]` substituted to real values (no
   placeholders left), and does its branch match the Pointer's
   `Branch:` line?
8. If Phase 3 edited the spec, did Phase 3.5 run — is the enrichment
   commit either verified on `HEAD` (☑) or surfaced as the gating
   handoff with the bottom line set to "Not ready"? Never print
   "Ready" with the spec still uncommitted.
9. **Did Phase 3.6 drive every pre-flight check to ☑ or elevate it?**
   Scan the pre-dispatch list: under a "Ready" verdict there are **no
   ☐ items at all**. Any ☐ (Dashboard stale, Catalog housekeeping,
   prereq pending, enrichment uncommitted, branch in flight) means
   either complete it now, or flip the verdict to "Not ready" and name
   it — never "noted, non-blocking" under "Ready." The implementer's
   step-0 reconciliation is the embedded recipe, not a checkbox.

---

## Edge case: Buffer empty / stub at head

```
# Cannot Dispatch — Stub at Head

The next sprint at the head of the conveyor belt does not have a
full spec.

## Buffer status

| Seq | Sprint | Title | Written Status |
|---|---|---|---|
| 1 | [SK-XX] | [title] | stub |
| 2 | [SK-XX] | [title] | stub |
| ... | | | |

## Required action

Run **/roadmap-review** to author full specs for the buffer of 5.
After the review, /next-pointer will be able to finalize and
dispatch.
```

---

## Edge case: Queue empty (finish line reached)

```
# Finish Line Reached

The sprint queue is empty. All scheduled work is complete.

## Status

- Last completed: [SK-XX] on [date]
- Total sprints in archive: [N]
- Finish line: [tier name] — reached.

## Required action

If new work needs to be added, run /roadmap-update to introduce
new initiatives, then /roadmap-review to plan and spec.
```

---

## Edge case: Structural gap (requires user judgment)

If Phase 2 surfaces a structural gap that Cowork cannot resolve
via investigation, halt printing and AskUserQuestion. Example:

> The full spec for SK-FU12-E defers Decision 12 (which submission
> sub-channel to gate on) to the implementer. The CLI agent should
> not be making this call. Pick:
> - (A) Gate on the closer-submission channel only [RECOMMENDED]
> - (B) Gate on both closer and inverted-submission channels
> - (C) Pause — let me investigate offline and update the spec
>   manually
> - (D) Escalate to /roadmap-review

Capture the chosen decision, update the spec inline, and proceed
to Phase 4.

If the user picks (C) or (D), halt this skill and instruct
accordingly.

---

## Edge case: Prerequisites pending

If 2.1 finds pending prerequisites, the standard output runs in
full but with adjustments:

- KPI row "Prerequisites for [SPRINT-CODE]" shows "blocked on
  [list]"
- Sprint Pointer's `Deps:` line shows ✗ for unmet prereqs
- Pre-dispatch check "Prerequisites met" is ☐
- Bottom line: "Not ready — prerequisites pending: [list]. Either
  complete the listed prereqs first, or run /roadmap-review to
  re-sequence."

If a deeper Catalog row IS dispatchable (Written Status = Full Spec
AND prereqs met), add:

```
## Alternative dispatch

[SK-YY] at Seq=[N] has all prereqs met and is dispatchable now if
you want to skip ahead. Skipping is permitted only if the head
sprint's blocker is external (waiting on data, waiting on user);
otherwise hold the head and resolve the blocker.
```

If the user picks the alternative, re-run Phase 2 + 3 against that
sprint before printing.

---

## Edge case: Enrichment uncommitted / commit deadlock (Phase 3.5)

If Phase 3 edited the spec and it is not yet on `main`, the gate is
**not ready** — surface it, don't bury it:

- Bottom line: "Not ready — enrichment uncommitted; main does not yet
  carry the spec. Cutting a worktree now would start from a main
  missing its own spec."
- Append the Phase 3.5 commit handoff (explicit-path `add`, `commit`,
  `push`, `log --oneline -1`).
- Pre-dispatch check "Spec committed to `main`" is ☐ (the verdict is
  "Not ready," so the ☐ is legitimate here).

**If a bounce-back loop forms** (the user defers to a dispatched agent;
the agent declines citing "the author never certifies its own
commit"), break it — that rule bars only the **author** (Cowork). A
non-author committing is the sanctioned path. Say so plainly:

> The commit isn't deadlocked — the "author never certifies its own
> commit" rule bars only me (I wrote the edit). The dispatched agent is
> not the author, so it committing is exactly the sanctioned path; or
> run the handoff yourself. Either clears the gate. Until the commit
> lands on `main`, the spec exists only as the uncommitted working-tree
> edit (nothing is lost — it just isn't on main yet).

When the user reports it done, **re-verify from primary evidence**
(`git show HEAD:<roadmap_doc> | grep -c <token>`), never from the
pasted "clean"/"reconciled" summary. Flag any contradiction.

---

## Edge case: No roadmap document

```
# Cannot Dispatch — No Roadmap Document Found

## Required action

Run **/roadmap-review** to establish the project's roadmap, then
run /next-pointer again.
```

---

## Edge case: No sprint-queue.xlsx

```
# Cannot Dispatch — Sprint Queue Spreadsheet Missing

## Required action

Run **/roadmap-review** — it will create `sprint-queue.xlsx` from
the active section of the roadmap.
```

---

## Question protocol reminder

Use AskUserQuestion only for structural gaps (Phase 2) and for
alternative-dispatch decisions (Edge case: Prerequisites pending).
Closable gaps should always be resolved via investigation, not
escalated to the user. Every AskUserQuestion: at least 2
alternatives, one tagged [RECOMMENDED], an escape hatch on
consequential decisions.
