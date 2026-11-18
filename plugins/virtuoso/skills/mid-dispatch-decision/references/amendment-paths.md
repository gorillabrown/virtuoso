Serves `mid-dispatch-decision` Step 6b: where and how the dispatch-spec amendment is persisted.

# Amending the Dispatch Spec — Path A and Path B

The amendment is hard execution: the planner **executes an Edit call and confirms the edit
landed**. The workflow does not end until the amendment is persisted.

**Which path.** If the dispatch is running in a git worktree (check the dispatch spec or
project configuration), use Path A. If the planner is operating on canonical main directly,
use Path B. When in doubt, use Path A — it is always safe, and the staging file is deleted at
close-out regardless.

## PATH A — Worktree-resident dispatch (mandatory staging file)

Per virtuoso's Worktree Governance Staging rules (virtuoso skill §Rule 5), a worktree-resident
dispatch MUST NOT edit main governance documents; all governance-change intent goes to the
dispatch's staging file. A mid-dispatch amendment is a governance change, so it goes there —
never inline into the spec. This is a hard prohibition.

1. Identify the dispatch's staging file:
   `<close-out-folder>/Memo.<dispatch-id>.GovernanceStaging.<YYYY-MM-DD>.md`
   (where `<close-out-folder>` is wherever the project's close-out memos live).
2. If the staging file does not exist, create it with virtuoso's staging file header (see
   virtuoso skill §Rule 3) and the Amendment Registry (below).
3. Append a fold-in entry under `## Target: <roadmap-document>`:
   ```markdown
   ### Fold-in N — Mid-Dispatch Amendment (<title>)
   Section: §<dispatch-id> (inline full spec)
   Action: Migrate
   Source: This amendment block (below)
   Destination: Close-out memo §Mid-Dispatch Decisions
   Content:
   #### Mid-Dispatch Amendment — [date]
   **Pause point:** [1 sentence]
   **Decision:** Type [N] — [Name]
   **Rationale:** [1-2 sentences]
   **Scope change:** [What changed, or "None"]
   **Follow-up items:** [Deferred work, or "None"]
   ```
4. Update the Amendment Registry table with a new row.
5. Print confirmation: "Staged mid-dispatch amendment in
   `Memo.<dispatch-id>.GovernanceStaging.<YYYY-MM-DD>.md` (fold-in N).
   Registry shows [N] decisions for this dispatch."

At close-out, dispatch-closeout processes the staging file as Wave 2 Step 0: it migrates the
amendment content to the close-out memo's §Mid-Dispatch Decisions section and deletes the
staging file. The fold-in's `Action: Migrate` tells the handler exactly what to do.

- **No Close-Out Preservation field.** The fold-in instruction IS the preservation contract;
  its Destination field serves that function more directly.
- **No conflict-surface check (Step 5.5).** The worktree never touches the main governance
  document, so cross-worktree conflicts on governance files are structurally impossible.

## PATH B — Planner-side session (no worktree boundary)

When the planner decides outside a worktree context (e.g. the dispatch runs in the same
session, or the user is driving the implementation agent by hand):

1. Identify the specification's location through the registry (the roadmap role, a file
   under `policy.roadmap.specDirectory`, an external system, or a standalone file). If
   ambiguous, resolve it **before** printing the instruction block in 6a.
2. Read the file.
3. Append the amendment block (template below) inline to the dispatch spec.
4. Print confirmation: "Amended `[filename]`: added mid-dispatch amendment
   for [pause point description]."

Run Step 5.5 before any inline edit to a file the in-flight worktree might also touch at
close-out. Planner-side edits to canonical main while a dispatch is in flight (worktree
exists, feature branch active, work in progress) carry two risks:

1. **Shared-file conflict (visible at rebase).** The planner's edit on main and the
   worktree's edits modify the same file; the conflict surfaces at the pre-merge rebase per
   the project's worktree-complete discipline. Manageable, but it adds friction, especially
   in a structurally complex section (e.g. a Roadmap §Active Skeletons row).
2. **Silent revert (invisible at merge if the pre-merge rebase isn't strict).** The worktree's
   bootstrap snapshot pre-dates the planner's edit. If the rebase is skipped or the resolver
   accepts the worktree's older view, the planner's edit is silently discarded — no error,
   just missing content. This is the more dangerous failure.

**Amendment block template (Path B only):**

```markdown
#### Mid-Dispatch Amendment — [date]

**Pause point:** [1 sentence]
**Decision:** Type [N] — [Name]
**Rationale:** [1-2 sentences]
**Scope change:** [What changed, or "None"]
**Follow-up items:** [Deferred work, or "None"]
**Close-Out Preservation:** [Where this amendment migrates at close-out
(close-out memo path + section), what the integration action is
("migrate verbatim under §Mid-Dispatch Decisions"), the timing ("before
collapsing the inline spec to a Completed Work Summary row"), and the
silent-loss risk if skipped ("this decision evaporates and downstream
dispatches cannot reconstruct why the spec was amended"). Required field
for Path B only — Path A uses fold-in instructions instead.]
```

Never omit the Close-Out Preservation field on a Path B amendment: it is the contract that
prevents silent loss at close-out, telling the handler where to migrate the amendment, how,
when, and what is at risk if skipped.

## Amendment Registry (both paths)

The staging file (Path A), or a standalone decision-trail file (Path B, for projects that
want a registry even without a worktree), carries a table of every mid-dispatch decision for
the dispatch in chronological order:

```markdown
## Mid-Dispatch Decisions Registry — <dispatch-id>

| # | Date | Pause point | Decision type | Disposition |
|---|------|-------------|---------------|-------------|
| 1 | YYYY-MM-DD | [pause point in plain language] | Type [N] | [Resolved — one-line summary] |
| 2 | YYYY-MM-DD | [pause point] | Type [N] | [Resolved — one-line summary] |
```

Every amendment adds a row. The close-out handler reads the registry first, then walks and
processes each amendment or fold-in below it.

The amendment makes the eventual close-out compare results against the *amended* spec, not
the original.

Return to SKILL.md Step 6c.
