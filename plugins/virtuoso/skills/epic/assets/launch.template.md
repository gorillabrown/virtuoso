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
| Repository detected | remote, default branch, worktrees, dirty paths; `policy.git` read | [PASS — remote [REMOTE or none], default [DEFAULT], policy [POLICY]] |
| Network operations settled | under `networkOperations: ask`, fetch and push granted or denied for the whole run | [granted / denied / not applicable — no remote] |
| Launch-blocking questions answered | Q&A list below | [...] |

### Launch-blocking questions — answers recorded here

<!-- Hard blockers first. Each question carries an empty Answer slot the user fills
     before leaving (or on return); state unanswered-fallback behavior per question:
     hard blockers → first session raises BLOCKER(USER) and stops cleanly; parameter
     questions → proceed on the charter default/assumption named in the slot. -->

- **Q1 ([hard blocker / default: charter A-n]).** [the question]
  **Answer:** _(pending)_

## Kickoff / resume prompt

Paste into any session — first or fiftieth; it self-orients either way. It carries the
run's git work, so one paste carries both the git work and the epic's instructions.

<!-- Fill the GIT WORK block at scaffold time from policy.git and the detected repository,
     as /next-pointer fills its reconciliation recipe. Keep only the lines the policy
     permits (read-only: no add, commit, or branch creation, so the operator creates the
     branch before launch and the first session only verifies it; prepare-no-stage: no
     add; explicit-path-stage: add, no commit; explicit-path-commit: commit, no push;
     push: commit and push). With no remote, drop every fetch, merge-from-remote and push
     line. With network operations denied, drop them too. No placeholder survives into
     the packet. -->

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
working tree at a checkpoint as GIT WORK below defines it. Disk handoff-ready, always.

GIT WORK — before the first edit of every session. Filled from policy.git at scaffold.
Repository [ABSOLUTE REPO PATH] | remote [REMOTE, or "none"] | default branch [DEFAULT]
Run branch [BRANCH] from [DEFAULT] @ [BASE SHA] | policy [POLICY] | network [granted/denied]
Read-only git runs lock-free: GIT_OPTIONAL_LOCKS=0 git --no-optional-locks ...

First session (state.md's Working set says the branch is not created yet):
  git status --porcelain            # dirty paths outside this run: report them, touch nothing
  git fetch [REMOTE] --prune
  git switch [DEFAULT]
  git merge --ff-only [REMOTE]/[DEFAULT]   # diverged -> STOP, BLOCKER(USER); no force, no reset
  git switch -c [BRANCH] [DEFAULT]  # then record "branch created, session 1" in state.md
Every later session (verify the branch; never create it again):
  git branch --show-current         # must print [BRANCH]; anything else -> STOP, BLOCKER(USER)
  git log -1 --format=%H            # compare with the Git line of the last journal entry,
  git status --porcelain            # and with its uncommitted paths. A mismatch: believe
                                    # the repo, journal the difference, then work
  git fetch [REMOTE] --prune
  git rev-list --left-right --count [BRANCH]...[REMOTE]/[BRANCH]   # once the branch is
                                    # pushed. Both sides > 0 is divergence -> STOP,
                                    # BLOCKER(USER); never rebase. Behind only: merge --ff-only
  git rev-list --count [BASE SHA]..[REMOTE]/[DEFAULT]   # the base moved: journal it and
                                    # keep working; never rebase or merge to catch up
Every checkpoint:
  git add -- <exact paths>          # never `git add .` or `-A`; unrelated paths stay out
  git commit -m "[PACKET-ID]-S<n>: <what this burst did>"
  git push [REMOTE] [BRANCH]
  record the Git line in the journal entry: [BRANCH] @ <sha>; uncommitted: <paths or none>
Never: force-push, rebase, reset --hard, stash, clean, or delete a lock file.

Run this session under the virtuoso skill when it is available: this packet is your
dispatch spec, and your sprint identifier is [PACKET-ID]-S<n>, where n is the next session
number in journal.md.
```

## Goal line — for `/goal`

Printed straight after the kickoff prompt, in its own block. One line: what the epic must
achieve, and how completion is proven.

```
[THE CHARTER'S OUTCOME, ONE SENTENCE] — done only when every Definition-of-Done row in [ABSOLUTE PATH TO THIS DIRECTORY]/charter.md passes with fresh evidence in one session and [ABSOLUTE PATH TO THIS DIRECTORY]/done.md is written; the only other clean stop is every front blocked on a BLOCKER(USER) recorded in state.md.
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
5. Close the epic through `/pointer-closeout [PACKET-ID]`, with journal.md and done.md as
   its evidence. A combination's close-out retires every item the charter's `items:`
   names. That ceremony records what the epic taught in the registered `lessons`
   role — where the next charter reads it — or says why it taught nothing. An epic
   that ends without it leaves its lessons in a journal no future run consults.

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
