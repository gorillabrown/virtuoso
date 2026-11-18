Serves `virtuoso` Phase 5: the 7-field issue format, the riders on the two Phase 5 rules, and the full "do not" list.

# Phase 5 — Issue Format and Blocker Rules

### When to stop

**STOP executing immediately when:**
- A test fails that the plan expected to pass
- A file or function referenced in the plan doesn't exist
- You're unsure which of two approaches is correct
- The results of a step contradict the plan's assumptions
- You've been working on a single task for significantly longer than expected
- An external dependency is missing or broken
- A required tool, file, dependency, or instruction is unavailable
- The environment cannot satisfy a required isolation or permission boundary

### What to do when stopped

1. Mark the current task ✗ (blocked), and its band step `blocked` ([progress-band.md](progress-band.md)).
2. Reprint the full task plan showing current state.
3. **Render the issue in the 7-field format below** and **save an identical `.md`** to
   the `issues` directory from `Virtuoso/workspace-layout.json` as
   `Issue.<DISPATCH-ID>.<YYYY-MM-DD>.md` (append `-N` if more than one on a date).
4. Hand the saved path to **`/mid-dispatch-decision`** — it reads the file and returns the
   call. Do not pick a path yourself without approval.

### Issue format

Every stop / hold / block / elevation routed to `/mid-dispatch-decision` is defined with
these seven fields (the saved `.md` holds fields 1–6; field 7 is its path):

1. **tl;dr:** one line.
2. **Executive Summary:** 2–4 sentences — what happened and why it blocks.
3. **Evidence of issue:** errors, failing test, contradicted assumption, file:line, logs —
   and a **Tried and failed** list: what was tried and dropped, read mechanically from the
   transcripts by `virtuoso_registry guards --dispatch <DISPATCH-ID> --tried`, so the next
   session does not retry it.
4. **Possible cause(s):** ranked hypotheses.
5. **Likely solution(s):** candidate fixes/paths.
6. **Confidence in cause and solution identification (1–10):** integer + one-line justification.
7. **Exported issue documentation path:** the saved `.md` path.

The saved file IS the handoff token — `/mid-dispatch-decision` expects a path to it.

Each section below continues the rule of the same name in SKILL.md Phase 5.

### Reaching a decision that belongs to the operator is a SUCCESS terminal

Two riders, both observed:

- **Halt rather than degrade.** When the environment cannot satisfy a required isolation
  or permission boundary, stop — do not substitute a dirty tree, an unregistered worktree,
  or a bypassed safety helper. A capability shortfall is not permission to lower the
  boundary.
- **Autonomy grants and STOP conditions must be disjoint.** A pre-registered halt names
  which grants it suspends; no grant may cover a condition that is also a STOP trigger,
  or the run can authorise itself past its own gate.

### The entity that performed a change is never the sole certifier that git reflects it

- **Every dispatch verifies live git state as its first action** — current branch and
  tree — before its first edit, not only the dispatch that commits.
- **Feature branches are created by the orchestrator**, never inside a worker's transient
  worktree.
- **Committed is not pushed**, and a long-lived branch that becomes the de-facto trunk
  leaves `main` stale — check what a new dispatch would actually branch from.

### Do not

- Guess and keep going ("it's probably fine")
- Try a different approach without saying so
- Skip the blocked task and come back later (unless explicitly told to)
- Retry the same thing more than twice (the retry guard holds a third identical failing
  command once, in workers too; sending it again unchanged goes through)
- Silently change scope or absorb a failed task without updating the plan

Return to SKILL.md Phase 5: save the issue and hand its path to `/mid-dispatch-decision`.
