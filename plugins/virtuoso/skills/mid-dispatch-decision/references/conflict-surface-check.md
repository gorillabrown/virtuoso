Serves `mid-dispatch-decision` Step 5.5: the cross-worktree conflict surface check.

# Cross-Worktree Conflict Surface Check

**Applies to** Types 1a, 1b, 2, 3, 3a, and 5 on the planner-side path (Step 6b Path B),
where the dispatch continues and the close-out happens later. **Skipped** for Type 4 (its
partial close-out runs immediately, so amendment and close-out integration happen in one
workflow with no cross-worktree timing gap) and for a worktree-resident dispatch (Path A: the
worktree never edits main governance documents, so the conflict surface is structurally
eliminated).

Before producing the instruction block and persisting amendments, scan for foreseeable merge
conflicts at close-out. Three conditions:

1. The dispatch spec lives in a document subject to archive-forward collapse (e.g. a Roadmap
   §Active Skeletons section that converts to a one-paragraph Completed Work Summary row at
   close-out).
2. An active execution worktree exists on the dispatch's feature branch.
3. The close-out edit will modify the same section the amendment is being appended to.

If all three hold, the rebase at close-out will produce a conflict on this file — or worse, a
silent revert if the pre-merge rebase isn't strict (both risks are described under Path B in
[amendment-paths.md](amendment-paths.md)). Surface the foreseeable conflict in the
Recommendation (Step 5), not after the fact:

> "Foreseeable conflict at close-out — [file] §[section]. Mitigation options:
> (1) push amendment inline + Close-Out Preservation note,
> (2) push only the lessons-learned append, hold the spec amendment,
> (3) stage both for close-out integration via the decision-trail staging file."

Let the user choose the mitigation before persisting. The default for projects that practice
archive-forward discipline is the staging-file path (Step 6b Path A); the user can override.

Return to SKILL.md Step 6.
