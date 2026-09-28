---
epic: [SLUG]
id: [PACKET-ID]   # the item's id; for a combination, EPIC- plus the slug in capitals
item: [ITEM-ID]   # the master-roadmap item this epic executes (Path: epic)
# items: [ITEM-ID, ITEM-ID, ITEM-ID]   # a combination instead: every item, in serial order
origin: roadmap — [ITEM-ID]   # a combination: roadmap — [ITEM-ID], [ITEM-ID], ...
created: [YYYY-MM-DD]
status: active   # active | complete | aborted — set complete only per launch.md Completion protocol
---

# Epic Charter — [TITLE]

<!-- FROZEN after launch. Only the user amends this file; the executor treats it as the
     contract. If reality proves the contract wrong, that is a BLOCKER(USER), not an edit. -->

## Outcome

[1–3 sentences describing the end state — what will be true, not what will be done.
Drawn from the item's roadmap entry and, where it was absorbed from a held plan, from its
storyboard's alignment record. For a combination: what the items deliver together.]

<!-- A combination only: the items, in the serial order `virtuoso_registry combine`
     returned, and why each sits where it does. Delete for a single item. -->

| # | Item | Lane | Runs after | Because |
|---|------|------|------------|---------|
| 1 | [Title] ([ITEM-ID]) | [lane] | — | [first in sequence] |
| 2 | [Title] ([ITEM-ID]) | [lane] | [ITEM-ID] | [prerequisite / shared files: path] |

## Definition of Done — all rows must pass

| # | Condition | Verify by | Expected evidence |
|---|-----------|-----------|-------------------|
| D1 | [verifiable condition] | [exact command or concrete procedure] | [what output proves it] |
| D2 | [...] | [...] | [...] |

Rules: the session claiming completion re-runs **every** row fresh and pastes the outputs
into state.md → Evidence. Any row unverified ⇒ the epic is not done. Rows may be tightened
by the user, never loosened by the executor. A combination carries every item's *Done
when* rows, each labelled with its item (`[ITEM-ID] — …`), and one row proving they all
pass together on the integrated tree.

## Constraints — hard limits

- **Git, from `policy.git` ([POLICY]):** all work on branch `[BRANCH]`, cut from
  `[DEFAULT]` at `[BASE SHA]`[, in the worktree at [PATH]]. Stage exact paths only, never
  `git add .` or `-A`. [Commit at every checkpoint / Stage but never commit / Leave
  changes in the tree and journal their paths — whichever the policy permits.] [Push to
  `[REMOTE]` after each checkpoint / Never push.] Never force-push, rebase, reset, stash,
  or clean. Divergence is a BLOCKER(USER). The recipe is launch.md's GIT WORK.
- [e.g. never publish/deploy; session/time budget ceiling: ~[M] sessions]

## Non-goals — explicitly out of scope

- [work adjacent to the outcome that must NOT be done]

## Autonomy grants — the executor decides alone (log each call in state.md → Decision log)

- [e.g. test structure and naming; refactors under ~30 lines that enable testing;
  dev-dependency additions; ordering of work within a phase]

## Escalation triggers — STOP and surface to the user

- Any action that is destructive, irreversible, or outward-facing beyond the grants above
- A DoD row that appears unachievable as written
- Reality contradicting this charter or a listed assumption's guard failing
- The session/time budget in Constraints is exhausted with DoD rows still unmet
- [goal-specific triggers]

When triggered: write a BLOCKER(USER) in state.md with the exact question and what it
unblocks, advance any unblocked front; if every front is blocked, append a final journal
entry and stop cleanly.

## Assumptions — gaps accepted at launch (unattended launches especially)

| Assumption | Risk if wrong | Guard |
|------------|---------------|-------|
| [what is being assumed] | [what breaks] | [cheap early check, escalation trigger, or both] |

## Lessons applied — the project's own history, read before the run

<!-- From `virtuoso_registry lessons --open`: each live lesson that bears on this outcome,
     by identifier, and where it landed above — a constraint, an assumption's guard, an
     escalation trigger. Or: "No live lesson applies — N read." Never leave this blank. -->

| Lesson | Bears on | Applied as |
|--------|----------|------------|
| [<prefix>-NNN — title] | [which DoD row, phase, or risk] | [the constraint, guard, or trigger it became] |
