---
epic: [SLUG]
created: [YYYY-MM-DD]
status: active   # active | complete | aborted — set complete only per launch.md Completion protocol
---

# Epic Charter — [TITLE]

<!-- FROZEN after launch. Only the user amends this file; the executor treats it as the
     contract. If reality proves the contract wrong, that is a BLOCKER(USER), not an edit. -->

## Outcome

[1–3 sentences describing the end state — what will be true, not what will be done.]

## Definition of Done — all rows must pass

| # | Condition | Verify by | Expected evidence |
|---|-----------|-----------|-------------------|
| D1 | [verifiable condition] | [exact command or concrete procedure] | [what output proves it] |
| D2 | [...] | [...] | [...] |

Rules: the session claiming completion re-runs **every** row fresh and pastes the outputs
into state.md → Evidence. Any row unverified ⇒ the epic is not done. Rows may be tightened
by the user, never loosened by the executor.

## Constraints — hard limits

- [e.g. all work on branch X or a dedicated worktree; never force-push; never
  publish/deploy; session/time budget ceiling: ~[M] sessions]

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
