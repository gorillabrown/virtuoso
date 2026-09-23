# Launch — Loop hardening

## Walk-away preflight — completed BEFORE the user left

| Check | How | Result |
|-------|-----|--------|
| Paths in the goal exist (absolute) | `ls /home/user/virtuoso/plugins/virtuoso` | PASS |
| Canonical build/test/check commands run | `python -m pytest plugins/virtuoso/ -q` (775 passed, 3 skipped); `python plugins/virtuoso/scripts/validate.py` (All checks passed); `python plugins/virtuoso/scripts/bump_version.py --check` (in sync at 1.8.2) | PASS — baseline in state.md → Working set |
| Credentials live | `git push -u origin eb/zealous-einstein-zxvy3w` (1442ccc landed 18:04Z); CI runs readable through the GitHub connector | PASS |
| Remotes/services in the DoD reachable | `origin` fetch of four branches; CI run 35900011114 read | PASS |
| Runtime can act unattended | auto mode; no permission prompt has stalled any step of the day's work | PASS |
| Launch-blocking questions answered | Q&A list below | Q1 pending (default recorded); Q2, Q3 defaults recorded |

### Launch-blocking questions — answers recorded here

- **Q1 (parameter / default: do not merge; state.md Blockers #1).** Merge or retire
  `eb/gracious-mendel-juqys8` and `eb/charming-pasteur-9rigux`? Recommendation: merge both.
  **Answer:** _(pending)_
- **Q2 (parameter / default: charter A1).** Does the alternate host accept a capability
  string beyond `Interactive`, `Read`, `Write` (the plugin also executes Python through
  its session hook)?
  **Answer:** _(pending)_
- **Q3 (parameter / default: notes carry a separate v1.10.0 section).** Should 1.9.0 ship
  from `1442ccc` before this epic's commits, or should everything ship as 1.10.0?
  Either works: `release.py` bumps to the version named at release time.
  **Answer:** _(pending)_

## Kickoff / resume prompt

Paste into any session — first or fiftieth; it self-orients either way:

```
You are executing the epic at /home/user/virtuoso/docs/virtuoso/epics/2026-09-23-loop-hardening.
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
5. Close the epic through `/pointer-closeout`, with journal.md and done.md as its
   evidence. This repository keeps no `lessons` role, so the lessons the epic taught are
   recorded in done.md and in the v1.10.0 release notes, where the plugin's own history
   is read.

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
