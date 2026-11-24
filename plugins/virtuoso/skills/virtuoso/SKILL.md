---
name: virtuoso
description: "Structural execution discipline for multi-step tasks in one parent conversation. Use this skill whenever running a dispatch, executing a checklist, or performing any work that involves 3+ sequential tool calls. This skill enforces task planning, narration, progress tracking, and optional child-agent swarms while preserving each dispatch as a clearly named dispatch record. Trigger on: \"execute this plan\", \"run this dispatch\", \"implement these changes\", any dispatch prompt with multiple steps, or any task where completion quality depends on maintaining focus across many tool calls. When in doubt, use this skill — the overhead is minimal and the discipline prevents regressions. It is the only skill in the plugin that executes: storyboard scopes, write-plan and roadmap-review plan, next-dispatch and epic prepare, and all of them hand off here. Before the first edit on a written plan it checks for upstream, downstream, in-flight, and roadmap-order conflicts."
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (its universal checks, at the version it declares, plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / xhigh / max. A property of the task's difficulty, never a ranking of whoever performs it.

<!-- virtuoso-overlay-clause v2 -->
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.

# Virtuoso

Rules read at session start fade after 10+ tool calls; this skill holds because you return to
it at every step boundary. This file is the flow, gates and stops; each phase names the
`references/` file to read at its point of use.

**Announce at start:** "Using the Virtuoso skill to maintain execution discipline."

**The only skill that executes** (`references/execution-paths.md`): `/storyboard` scopes,
`/write-plan` and `/roadmap-review` plan, `/next-dispatch` gates, `/epic` prepares; none edits
an edit site, creates the work branch, or runs the change. This skill does, only from a
written plan; a draft stub or an idea goes back to `/storyboard` and `/write-plan`.

**Before implementation begins, read [references/session-setup.md](references/session-setup.md)
and do it:** title the record `[DISPATCH-ID] — [short dispatch name]`, state Remote Control
(prompt; never switch it, never turn it off), and keep one parent chat — workers are bounded,
never a new parent. Effort is the header's default, a task's own override, or its tier's default.

## Phase 1: Load and Understand

Before touching any file or running any command:

1. **Read the full task specification**, what it cites, and a governed dispatch's **origin
   line** (`references/execution-paths.md`), which sets the intake and the Phase 6 close.
2. **Read [`references/zeus.md`](references/zeus.md)**, or the project's overriding lead-agent definition.
3. **Identify every discrete deliverable** — something you can point to when done.
4. **Flag anything unclear** — stop and ask NOW. Guessing wastes 10x more time than asking.
5. **Declare the workstream and surface manifest** when workstreams are in use; ask if the spec names none.
6. **Run the conflict check** and, for a held plan, the **held-plan intake**, before the first
   edit and the work branch. **Read [references/intake.md](references/intake.md) first.**
7. **Read or derive the milestones**, show them, and open the band's run
   ([references/progress-band.md](references/progress-band.md)).

**What a conflict does.** Upstream pending, or in-flight work on the same edit sites → stop
before the first edit; issue (Phase 5) to `/mid-dispatch-decision`. Roadmap order → one
bounded question: wait, run now with the user's reason recorded, or send it back. Drift, or a
plan that no longer fits the code → stop: a held plan to `/write-plan <entry>`, a roadmap item
to `/next-dispatch`; never re-plan here. Downstream staleness → not a stop: name each item in
Task #1's notes and the close-out. Print under Task #1:
`Conflict check: upstream ✓ · in flight ✓ · roadmap order ✓ · downstream [n flagged] · drift ✓`.

**Phase 1 rules** bind as written. Before writing or accepting any criterion, gate, or null
result, read their riders in [references/verification-rules.md](references/verification-rules.md).

<!-- rule:lane-declaration (lane-concurrency) -->
**Workstream discipline.** Under workstream-based concurrency the dispatch declares, at Phase 1 and
before any edit:

workstream, surface manifest, and merge slot (`references/intake.md`); none stated → stop and ask.

<!-- rule:mechanical-acceptance-criteria (mechanical-criteria) -->
**Every acceptance criterion and stop gate must be mechanical.** A criterion is
mechanical when two people reading the same output cannot disagree about whether it was
met: a numeric threshold, a boolean check, or an enumerable list. Words like
"reasonable", "approximately", "acceptable", "sufficient" and "significant" are banned
from a completion condition — if the spec uses one, resolve it to a number before
Task #1 is marked ✓, or stop and ask.

<!-- rule:red-base-procedure (red-base) -->
**If completion depends on a suite gate, measure the base before implementing.**
Capture the base branch's suite result as its own step, before the first edit, so
attribution is unambiguous later. Then:

**base green** → proceed; new failures are yours. **Base red** → do **not** diagnose it
in-dispatch: file a Phase 5 issue, escalate, and continue only against the verified
pre-existing-failure list.

<!-- rule:instrument-positive-control (INSTRUMENT-CONTROL) -->
**Never trust a null result from an unvalidated instrument.** "No change", "zero",
"identical", "not reproducible" and "no matches" are claims about the **instrument**
until the instrument has been shown capable of reporting the opposite. A green check
and a check that examines nothing report the same symbol.

<!-- rule:identity-not-counts (GATE-IDENTITY) -->
**Gates and acceptance criteria state identities, not counts.** A gate that tolerates
known failures records the failing **node IDs** and compares them against the expected
waived set. A matching count with a narrative attribution is not a pass — it is a
coincidence that has been argued for.

<!-- rule:name-the-fork-under-test (FORK-SURFACE) -->
**Name which fork the acceptance test runs against.** When a fix lands on a path that
forks by backend, environment, or deployment target, the spec names the fork the test
exercises, plus a check that the suite is not entirely the blind fork. "Tests pass" is
not a completion condition when two forks exist and only one is covered.

<!-- rule:cite-searchable-anchor (CITE-ANCHOR) -->
**Cite a searchable anchor, not a line number.** Any `file:line` inherited from a
document older than the current session is **unverified by default** — citation drift is
structural, not careless. Cite a function name, a constant, a heading, or a verbatim
fragment: an anchor survives edits above it, a line number does not.

<!-- rule:state-integrity-by-hash (content-not-presence) -->
**Prove state by content, not by presence.** A recovery, health check, or "did it land"
check that confirms a file or row *exists* accepts a truncated, tampered, or
half-completed state as clean. Compare the actual hash against the recorded expectation.

Raise concerns about the plan now; once executing, follow it unless genuinely blocked.

## Phase 2: Build the Task Plan

**Read [references/task-plan.md](references/task-plan.md)**, then print one numbered row per
deliverable (`□` not started · `■` in progress · `✓` done · `✗` blocked, with reason):
`□ N. owner-label: Task description [tier] {effort} ‹model› @kind  M min (basis)`.
**Task #1 is always `Zeus: Load spec, build plan, assign owners [cross-cutting]`**, ✓ only
when the conflict check and the assignment table are printed. One row per deliverable: **no
collapsing tasks into batches or waves**, no silently absorbed step; add a step found later
(`+N`) and park, never delete, one not to be done. **Open the time log** as the list is first
listed; if `timing` refuses, stop and report the message.

<!-- rule:tier-by-blast-radius (blast-radius) -->
**Blast-radius override — ask what breaks if this output is wrong, not how hard it is
to produce.** Cheapness is the right axis only when a wrong answer is cheap to detect
and cheap to redo. Three cases where it is not:

a baseline, an interpretation labelled mechanical, and top-effort cross-module work (`references/task-plan.md`).

## Phase 3: Assign Parent And Worker Owners

**Read [references/owners.md](references/owners.md)** and route each task by its tree, first
match wins: Zeus for critical-path work, then an exact specialist, then hermes (exact diff),
hercules (one domain), aristotle (cross-system). Reprint with owners; that completes Task #1.

<!-- rule:calibration-routing (measurement-dispatch) -->
**Measurement is not regression.** A run whose output is a *distribution compared
against target bands* routes to an agent permitted to interpret results — never to
the test runner, regardless of how mechanical the invocation looks. The test runner
reports pass/fail against a known-correct answer; a measurement run has no pass/fail,
it has a measured value that someone has to interpret. Routing it to the
execution-only tier produces numbers nobody can defend and a gate that has to be
re-derived. This holds for small-sample sanity runs and full multi-seed runs alike.

## Phase 4: Execute With Parent-Owned Swarm Control

**Read [references/execution.md](references/execution.md).** Per task, in order: start its
clock and band step → run it locally or launch one bounded worker → verify mechanically →
end its clock with `--evidence "<what proves it>"`, mark ✓ or ✗ → reprint. Run `timing
--dispatch <DISPATCH-ID> --check` after a compaction and again before the close-out.

<!-- rule:worker-output-validation (evidence-not-assertion) -->
**A "completed" message is not evidence that work happened.** The evidence is the
tool-use trail and the repository delta. Before marking any delegated task ✓:

run the three checks in `references/execution.md`.

<!-- rule:re-derive-dont-restate (re-derivation) -->
**An agent that restates an upstream number inherits its errors; one that re-derives it
catches them.** When a worker's deliverable is a figure the dispatch will act on — a
count, a rate, a pass/fail tally — do not accept it restated from another tool's summary.
Have it re-derived from the underlying data, or re-run independently.

<!-- rule:enforcement-not-disclosure (enforcement-required) -->
**A computed marker that nothing enforces is disclosure theatre.** A script can honestly
record that a precondition was violated — a dirty-tree provenance stamp, a documented
exclusion, a "not yet authorized" status — without that computation being wired to an
abort. The record is then true and inert, and the run proceeds.

<!-- rule:orchestrator-owns-long-runs (long-run-ownership) -->
**The orchestrator owns any run that outlives the sub-agent tool timeout.** This is a
real exception to "the parent coordinates, workers implement", and it exists because a
sub-agent holding a long handle is a single point of silent failure: the sub-agent's
background process dies when the sub-agent returns, and the parent inherits a handle
to nothing.

<!-- rule:inline-safety-into-worker-prompts (safety-inlined) -->
**Brevity applies to context, never to safety.** A rule that lives behind a pointer
the worker was told to read, but not in the worker's own task text, does not exist for
that worker. Every dispatch inlines these verbatim — they are short, and their absence
is what gets violated:

- **A tool refusal is a stop, not a `--force` invitation.** If a tool, hook, or gate
  refuses, stop and report the refusal. This holds even when you believe you have
  proven the refusal spurious — *especially* then. Verification and override authority
  belong to the orchestrator, not to the worker that hit the wall.
- **Git scope fence, stated affirmatively.** When another agent owns commit and merge:
  "You may edit files under `<manifest>`. You may not run `git add`, `git commit`,
  `git merge`, `git push`, or `git checkout`. Leave your changes in the working tree."
  State what is permitted, not only what is forbidden.
- **Working-directory assertion as the first action.** Any dispatch that writes to the
  filesystem opens by printing its resolved working directory and confirming it matches
  the expected worktree, before the first edit.

Narrate before each action, stay in scope, and check
[references/rationalizations.md](references/rationalizations.md) before any shortcut.

<!-- rule:checkpoint-commits (task-boundary-commit) -->
**A task boundary is a commit boundary.** Commit when a task completes, and push at
burst end — do not carry a whole dispatch's work to one terminal commit at the end of the
plan. An uncommitted working tree is not a git-verified state: a crashed session, a
reverted edit, or a worktree removed early takes everything that was never committed,
and no amount of correct work survives that.

**After each task, reprint the FULL plan** under `timing --status`'s header, never "see
above"; Past 12 rows, `timing --status --compact`, and the full list every fifth task. One
plan only. **Three-call rule:** three tool calls without narration → stop and narrate. At
every burst end, count what has not left the machine (exit 2: no upstream):

```bash
"$HOME/.virtuoso/bin/virtuoso" dispatch_guards unpushed --root <project-root>
```

## Phase 5: Handle Blockers

**STOP immediately** when an expected pass fails, a named file or function is missing, you
are unsure between two approaches, results contradict the plan, a task runs far over, a
needed dependency, tool or instruction is missing, or a required isolation or permission
boundary cannot be met. **Read [references/blockers.md](references/blockers.md).**

<!-- rule:user-gate-is-success (operator-gate) -->
**Reaching a decision that belongs to the operator is a SUCCESS terminal, not a failure.**
An unattended run that arrives at a genuine operator decision has finished its job. Record
the question, state precisely what it unblocks, advance every front that does not depend on
it, and stop cleanly. Do not treat the stop as incompleteness to be worked around, and do
not manufacture a decision to keep moving.

<!-- rule:git-separation-of-duties (separation-of-duties) -->
**The entity that performed a change is never the sole certifier that git reflects it.**
Self-grading invites bias. The worker performs mutating git inside its own worktree; an
independent reader verifies state with **read-only** git — and read-only git must be
invoked lock-free (`git --no-optional-locks status`, or `GIT_OPTIONAL_LOCKS=0`) so it
never writes `.git/index.lock` or races a concurrent mutation.

**When stopped:** mark the task ✗, reprint, and write the 7-field issue
(`references/blockers.md`) to the registry's `issues` directory as
`Issue.<DISPATCH-ID>.<YYYY-MM-DD>.md`. Hand its path to **`/mid-dispatch-decision`**; never
choose a path without approval, guess on, or retry a failure more than twice.

## Phase 6: Close Out

Print the close-out block per **[references/closeout.md](references/closeout.md)**, then end
the band (`--complete` only once the completion check passes, else `--stop`).

<!-- rule:closeout-is-an-artifact (closeout-artifact) -->
- **The printed block is not the deliverable — three artifacts are, and each needs its
  own numbered task in the plan, created back in Phase 2:**
  1. **The durable close-out file**, written to the registry-resolved `closeOuts`
     directory. A plan authored without an explicit authoring task completes with
     governance updates that reference a file nobody produced. If the plan
     has no such task when you reach Phase 6, add it and reprint — do not write the
     file as an unnumbered aside.
  2. **The completed-work ledger row.** Close-out authoring and ledger entry are
     separate acts, and only the first has a natural owner, so the ledger silently
     falls behind. This is a standing rule, not a nicety.
  3. **Deliverable existence, verified on the merged branch, before teardown.** Every
     artifact this close-out names must be confirmed present on the branch it merged
     into — not in the worktree. Worktree-only artifacts vanish at removal, and a
     referenced deliverable has been found never to have existed in git.
     Run:
     ```bash
     "$HOME/.virtuoso/bin/virtuoso" dispatch_guards artifacts-exist --ref <merged-branch> <path> [<path> ...]
     ```
     Removing the worktree before this check passes destroys the evidence that would
     have caught the gap.

  Include `<closeOuts>/Timing.<DISPATCH-ID>.jsonl`, with every unrun row ended `--result cancelled`.
- **For a held plan, the ledger row waits on purpose:** `/dispatch-closeout` records it
  `executed`; the absorbing `/roadmap-review` runs the recording crossing. The file and check happen now.

<!-- rule:verification-spawns-remediation (verification-scope) -->
- **A verification task that finds more than a handful of issues stops and spawns a
  remediation task.** It does not quietly become an implementation task. Silent
  conversion is how a minimal-effort verification once consumed more tool calls than
  any maximum-effort task in its dispatch — and the plan showed one ✓ line for it. If
  verification turns up substantive work, mark the verification ✓ with its findings,
  add a numbered remediation task, and reprint.

<!-- rule:merge-through-slot (lane-concurrency) -->
- **Integration runs through the merge slot, in this order.** A worktree-resident
  dispatch is not done when its tasks are ✓ — it is done when it has merged. Serialized
  integration exists because two workstreams that each pass their own gate can still break
  the combined tree:

  1 claim the slot · 2 merge base into the feature branch · 3 re-run the full gate on the
  combined tree · 4 merge · 5 push · 6 remove the worktree after the existence check · 7
  release the slot (release it first if any step fails).
- Then run **`/dispatch-closeout`** on the block.

## Project-Specific Overlays

Never copy or edit this file for a project: register an `overlays` role with additions at
`skills/virtuoso/SKILL.md`. A one-run rule goes in an `EXECUTION RULES` block in the prompt
(both in `references/session-setup.md`).

## Worktree Governance Staging

A worktree-resident dispatch never edits a main governance document; it stages each change
as a fold-in for `/dispatch-closeout`. **Read
[references/governance-staging.md](references/governance-staging.md)** (Rules 1–7) first.

<!-- rule:registry-resolved-staging (AMEND-THE-RESTATEMENTS) -->
**`<close-out-directory>` is resolved through the registry, never guessed.** Read the
`closeOuts` key from `Virtuoso/workspace-layout.json`; if the manifest does not carry
it, read `closeOuts` from the `virtuoso-governance-registry` machine block in the
project-root governance readme. Those two together are the registry, and the registry
is the declared authority for exactly this lookup. Do not infer the directory from
where memos happen to sit, and do not hardcode a conventional path — a guessed
location writes an open obligation somewhere close-out will never sweep.

<!-- rule:staging-memo-lifecycle (staging-lifecycle) -->
Rule 4 says the staging file is deleted once processed. That makes any memo still
resident in the close-outs directory an **open obligation**, not an archive artifact —
and the failure mode is that nobody ever looks. Four lifecycle hazards:

Rule 7, `references/governance-staging.md`.
