Serves `virtuoso` Phase 6: the printed close-out block, its outcome types and layout rules, and the performance recommendations that may follow it.

# Phase 6 — Close-Out Format

After all tasks show ✓ (or the dispatch reaches a defined stop condition), print the
close-out. The close-out begins with the dispatch ID and follows this exact structure:

```
[DISPATCH-ID]   Phase 6: Close-Out — DISPATCH-NAME (Outcome Type)

Problem: 1-2 sentences — what was broken, missing, or inadequate before this work
started, or what opportunity/goal motivated it. Restate from the dispatch spec in
plain language.

Result: 1-2 sentences — what was done and what happened. Name the specific changes
(constants tuned, functions added, architecture decisions made) and whether the
outcome was success, partial, or pivot stop. If the work was empirically falsified
or a gate triggered early stop, say so directly.
---
Task Plan — DISPATCH-NAME | [X% of authorized scope] Outcome summary.
✓ 1.   Zeus:   Load spec, build plan, assign owners                  [cross-cutting] — 20 → 24 min
✓ 2.   hercules:       Modify calc_defense_effectiveness() — WEIGHT 3.0→2.0 [bounded] — 25 → 31 min
...
✗ 9.   socrates:       Full verification sweep — CANCELLED (pivot stop)          [bounded]
---
Worker Utilization Summary
┌─────────────┬────────────────┬──────────────────────────────────────────────┐
│    Owner    │     Tasks      │                  Key output                   │
├─────────────┼────────────────┼──────────────────────────────────────────────┤
│ Zeus        │ #1, #6, #10   │ Coordination, integration, decisions          │
│ hermes      │ #3, #10        │ 2 commits; repository updates                │
│ hercules    │ #2             │ Single-line constant edit                     │
│ aristotle   │ #6, #8         │ Cal interpretation; profiler analysis         │
│ hippocrates │ #4, #7         │ 1,990 tests; 1 stale-bound catch             │
│ socrates    │ #5, #9         │ Cal run; #9 full-cal cancelled at gate       │
│ marcusaurelius │ #9          │ CLAUDE.md + cal results documented            │
└─────────────┴────────────────┴──────────────────────────────────────────────┘
Effort mismatch to flag: [specific mismatch if any — model annotation vs actual
complexity, disproportionate token consumption, or task that needed a different
role/effort level than planned, etc.]
---
Repository state: [commit hash, merge/push status, notable remaining changes]
Key engineering finding for the planner: [the single most important technical insight
from this dispatch that affects future work — not a summary of what was done, but
what was learned]
```

**Outcome types** (use in the header after the dispatch name):
- **(Complete)** — all tasks ✓, tests pass, merged to main
- **(Partial)** — some tasks complete, changes preserved for later integration
- **(Pivot Stop)** — work empirically falsified or gate triggered early stop
- **(Blocked)** — escalated to user, awaiting direction

**Close-out layout rules:**
- The dispatch ID appears first, before "Phase 6" — it anchors the entire block
- Task Plan uses the dispatch name (not generic), with the percentage reflecting
  authorized scope completed (100% is valid even with cancelled tasks if the
  cancellation was the authorized response to a gate trigger). Each row shows its
  predicted → actual minutes, as `timing --status` prints them.
- Worker Utilization uses a compact summary table (owner → tasks → key output),
  not the verbose duration/tokens/tool-calls breakdown. The detail matters for
  performance analysis but not for the close-out record. If performance
  recommendations are warranted, append them after the close-out block.
- Git state and Key engineering finding close the block — these are what the planner
  reads first when processing a close-out into a Dispatch Close-Out Report.

**Performance Recommendations** (append after the close-out block when warranted):
Focus on three dimensions with concrete task references:
- **Tool efficiency**: redundant or collapsible tool-call sequences
- **Token efficiency**: tasks consuming disproportionate tokens relative to
  task complexity; model annotation changes needed
- **Speed**: critical-path bottlenecks; parallelizable tasks that ran sequentially

Be concrete — "Tasks #4 and #7 were both labeled hippocrates and ran
sequentially, but have no dependency — run them in parallel to save ~1m 20s."

### The time log among the close-out artifacts

Name the dispatch's time log among the paths the artifact-existence check confirms:
`<closeOuts>/Timing.<DISPATCH-ID>.jsonl`. Before close-out, end every row that never ran
with `timing --end N --result cancelled`: a log with a row still open never counts as
closed in `kpis`. A log left behind in a worktree never becomes history, so no later
dispatch can price from it. The close-out's Task Plan shows each row's predicted → actual
minutes, as `timing --status` prints them.

### For a held plan, the ledger row waits on purpose

`/dispatch-closeout` records the held entry `executed`, and the `/roadmap-review` that
absorbs it runs the recording crossing (`references/execution-paths.md`). The close-out
file and the deliverable-existence check still happen now.

### Integration through the merge slot — each step

1. **Claim the merge slot** for this workstream. Block until it is free; never merge without it.
2. **Merge the base branch into the feature branch** — not the other direction.
3. **Re-run the full gate on the combined tree.** The pre-merge gate result is stale
   the moment the base moves; a gate that ran only on the feature branch has not
   tested what is about to land.
4. **Merge** to base.
5. **Push.** An unpushed merge is invisible to every other workstream and to the slot.
6. **Remove the worktree** — only after the artifact-existence check has passed.
7. **Release the merge slot.**

If any step fails, release the slot before escalating. A held slot blocks every other
workstream on a dispatch that is no longer progressing.

### Hand-off

Run **`/dispatch-closeout`** on this block to fold the result into the roadmap, dispatch
queue, and retrospective. (The spec arrived through one of the three paths in
`references/execution-paths.md`: `/next-dispatch`'s kickoff, `/write-plan`'s held plan,
or `/epic`'s packet. `/dispatch-closeout` reads the origin line to close each one
correctly.)

Return to SKILL.md Phase 6: the close-out rules there (the three artifacts, the merge
slot, `/dispatch-closeout`) still apply.
