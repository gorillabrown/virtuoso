# Launch — [TITLE]

## Walk-away preflight — completed BEFORE the user left

<!-- Filled at scaffold time. Anything not PASS here must appear in charter Assumptions
     with a guard — deliberately accepted, never silently skipped. -->

| Check | How | Result |
|-------|-----|--------|
| Paths in the goal exist (absolute) | [e.g. `Test-Path <repo>`] | [PASS / assumption A1] |
| Canonical build/test/check commands run | [command + baseline output pointer] | [...] |
| Credentials live | [e.g. `gh auth status`] | [...] |
| Remotes/services in the DoD reachable | [...] | [...] |
| Runtime can act unattended | permission mode / allowlist covers the run's tool needs — no approval prompt will stall it | [...] |
| Launch-blocking questions answered | Q&A list below | [...] |

### Launch-blocking questions — answers recorded here

<!-- Hard blockers first. Each question carries an empty Answer slot the user fills
     before leaving (or on return); state unanswered-fallback behavior per question:
     hard blockers → first session raises BLOCKER(USER) and stops cleanly; parameter
     questions → proceed on the charter default/assumption named in the slot. -->

- **Q1 ([hard blocker / default: charter A-n]).** [the question]
  **Answer:** _(pending)_

## Kickoff / resume prompt

Paste into any session — first or fiftieth; it self-orients either way:

```
You are executing the epic at [ABSOLUTE PATH TO THIS DIRECTORY].
You may have no memory of prior sessions and the run may be partially complete.
Read state.md and follow its RESUME PROTOCOL exactly before doing anything else.

The finish line is charter.md's Definition of Done — every row verified with fresh
evidence — and nothing else. Keep working until that holds or a charter escalation
trigger fires. Plan your own path within plan.md's phases; replan phases if reality
demands it (log it), but never touch charter.md.

Do not wait on the user. If an escalation trigger fires, record a BLOCKER(USER) in
state.md with the exact question, continue on any unblocked front, and stop cleanly
only when every front is blocked.

Keep durable files distilled: conclusions and evidence pointers, never raw logs. Push
noisy exploration into subagents when your runtime offers them.

Before ending any work burst: update state.md, append a journal.md entry, leave the
working tree at a committed or clearly-journaled checkpoint. Disk handoff-ready,
always.
```

## Completion protocol — the only way this epic ends as "complete"

1. In one session, re-run **every** charter DoD row fresh; paste full outputs into
   state.md → Evidence.
2. Any row fails ⇒ not done: journal it, keep working.
3. All rows pass ⇒ write `done.md` in this directory — completion date, the DoD table
   with per-row evidence pointers, caveats and loose ends, recommended follow-ups — and
   set charter.md frontmatter `status: complete`.
4. Final journal entry, then stop. **`done.md` existing is the stop signal** for any
   loop or scheduler driving sessions: check it before launching another session. Never
   create it under any other circumstances.

## Monitoring — for the user

- **Glance (10 seconds):** state.md → "Where we are" block: phase, next action,
  blockers, DoD status.
- **Catch-up (2 minutes):** last two journal.md entries.
- **Intervene when:** a BLOCKER(USER) is waiting in state.md, or the journal shows no
  movement across two consecutive sessions, or `done.md` exists (review it).
- **To answer a blocker or launch question:** write your answer inline in its `Answer:`
  slot (state.md → Blockers, or the launch questions above) — the next session adopts it
  via the resume protocol.
- **To change course:** amend charter.md yourself (you are the only one who may), then
  add a journal entry noting the amendment so the next session re-anchors.
