Serves `virtuoso` Phases 2, 4 and 6 (and `mid-dispatch-decision`, `dispatch-closeout`): the Worktree Governance Staging pattern, Rules 1–7.

# Worktree Governance Staging

Worktree-resident dispatches (any virtuoso-executed work running in a `git worktree`-
isolated directory) have a structural conflict surface: if the dispatch edits main
governance documents directly, those edits conflict with any concurrent planner-side
governance work on canonical main. The conflict either surfaces at pre-merge rebase
(friction) or produces silent-revert behavior (governance content lost undetected).

This section eliminates that conflict surface by making worktree-resident dispatches
structurally incapable of editing main governance documents. Two of its rules carry a
binding paragraph that stays in SKILL.md (*Worktree Governance Staging*): the registry
resolution of `<close-out-directory>` (Rule 2) and the open-obligation rule (Rule 7).

### Rule 1 — Worktree-Resident Dispatches MUST NOT Edit Main Governance Documents

During worktree-resident execution, virtuoso's task plan must not include direct
edits to documents classified as "main governance." The classification is
project-specific. Locate it by searching the project's CLAUDE.md (or equivalent)
for a **worktree edit prohibition** section and reading its list of protected
documents — do not match on a section title verbatim, because titles drift and a
restated title silently reads as "no such section, no prohibition."

Virtuoso reads that list at dispatch start (Phase 1). If no such section exists in
CLAUDE.md, the prohibition still applies to any document that:
- Spans multiple dispatches (roadmaps, dispatch queues, constitutions)
- Is edited by the planner between dispatches (SRL catalogs, debt logs, technical references)
- Contains the dispatch spec for the currently-running dispatch (the inline full spec)
- Defines how agents work: the plugin's agent files (`agents/<Agent>.md`), their
  registered overlays (`<overlays>/agents/<Agent>.md`), and project copies of agent
  briefs (`.claude/agents/`), unless the dispatch's own specification
  names the file as an edit site. A correction found mid-dispatch is a staging fold-in
  (Rule 2), which the planner applies between dispatches.

If a task in the task plan would edit a main governance document, virtuoso rewrites
that task to write to the staging file instead (see Rule 2).

### Rule 2 — All Governance-Change Intent Goes to a Staging File

For every governance change the dispatch would otherwise make to a main governance
document, virtuoso writes the change-intent to a staging file in the worktree:

```
<close-out-directory>/Memo.<dispatch-id>.GovernanceStaging.<YYYY-MM-DD>.md
```

`<close-out-directory>` is resolved through the registry, never guessed — the rule and
its lookup order are in SKILL.md (*Worktree Governance Staging*).

The staging file is created on first governance-change-intent and appended to
throughout the dispatch. It contains all the changes that would normally land in
main governance docs — formatted as **fold-in instructions**, not as raw edits.

### Rule 3 — Staging File Structure

The staging file is organized so dispatch-closeout can mechanically apply each entry.
Section headers name the target document; entries within name the target section
and the fold-in action.

```markdown
# Dispatch Close-Out Governance Staging — <dispatch-id>

This file enumerates every governance change the dispatch would have made to
main governance documents during execution, but staged here per virtuoso's
worktree-edit prohibition. dispatch-closeout processes this file at dispatch
close to apply the fold-ins to canonical main.

## Target: <document-name>

### Fold-in N — <short description>
Section: §<target section heading>
Action: <Append row | Replace | Insert after | Remove>
Content:
<exact content to fold in — verbatim, ready to paste>
```

**Fold-in action types:**

| Action | Meaning |
|--------|---------|
| **Append row** | Add content at the end of a table or section |
| **Replace** | Overwrite existing content with new content (include `Old:` and `New:` blocks) |
| **Insert after** | Add content after a named anchor (line, heading, or entry) |
| **Remove** | Delete specified content (include the exact content to remove) |
| **Migrate** | Move content from one location to another (include source and destination) |

**Ordering rule:** Within a single target document, fold-ins are numbered
sequentially and processed in order. Dependencies between fold-ins within the
same target are implicit in the numbering. Cross-target fold-ins have no ordering
constraint unless explicitly noted.

**Mid-Dispatch Amendment fold-ins:** When the mid-dispatch-decision skill adds
amendment entries, they use the `Migrate` action type with source = inline spec
subsection and destination = close-out memo §Mid-Dispatch Decisions. These must
be processed BEFORE inline spec collapse fold-ins (so amendment content is
preserved before the spec containing it gets collapsed).

### Rule 4 — dispatch-closeout Processes the Staging File as Wave 2 Step 0

dispatch-closeout's existing Wave 2 procedure gains a new first step:

**Step 0 (NEW): Read and process the dispatch's staging file.**

If `Memo.<dispatch-id>.GovernanceStaging.<date>.md` exists in the worktree (or has
already merged from the worktree), dispatch-closeout:

1. Parses all fold-in instructions
2. Applies them to canonical main as Edit calls against the named target documents
3. Processes Mid-Dispatch Amendment migrations BEFORE inline spec collapses
4. After applying all fold-ins, deletes the staging file (it has served its purpose)

The close-out memo is the durable record. The staging file is transient infrastructure.

**Discrepancy handling:** If a fold-in instruction conflicts with current canonical
main state (e.g., the target section no longer exists, or content has changed since
the fold-in was staged), dispatch-closeout surfaces the discrepancy as a reconciliation
prompt to the user rather than silently overwriting or failing.

### Rule 5 — Mid-Dispatch Amendments Use the Staging File

The mid-dispatch-decision skill currently writes amendment blocks directly to the
dispatch spec (which is in a main governance document). Per Rule 1, this is the
exact write virtuoso forbids.

**Integration:** mid-dispatch-decision writes the amendment to the staging file
under a fold-in entry, NOT to the inline spec. Specifically:

```markdown
## Target: <roadmap-document>

### Fold-in N — Mid-Dispatch Amendment (<amendment title>)
Section: §<dispatch-id> (inline full spec)
Action: Migrate
Source: This amendment block (below)
Destination: Close-out memo §Mid-Dispatch Decisions
Content:
##### Mid-Dispatch Amendment — <date> — <title>
Decision Type: <type>
Context: <what the implementation agent reported>
Decision: <what was decided>
Rationale: <why>
```

The mid-dispatch-decision skill's Step 6b becomes: "Append amendment to the dispatch's
staging file under the appropriate target document section." The Close-Out Preservation
field becomes implicit — the staging file IS the preservation contract. The conflict-
surface check becomes unnecessary because the conflict surface no longer exists.

### Rule 6 — Planner-Side Dispatches Follow the Same Pattern by Default

planner-side governance work that runs in a single session (e.g., /dispatch-closeout,
/roadmap-review, /governance-sweep) doesn't have a worktree boundary, so the conflict
surface doesn't apply in the same way. But the staging-file pattern still has value:

- The planner's mid-session governance edits become recoverable if the session crashes
- The staging file documents WHAT changed and WHY for the change summary
- It provides an audit trail of governance mutations within the session

**Enforcement level:**
- **Worktree-resident dispatches:** staging file is **mandatory**. Virtuoso
  rejects any task plan that edits main governance documents directly.
- **planner-side sessions:** staging file is **optional** (best practice, not enforced).
  The planner may edit main governance documents directly since there's no worktree
  boundary to create conflicts.

### Rule 7 — A Resident Staging Memo Is an Open Obligation

The rule's paragraph — any memo still resident is an open obligation — is in SKILL.md
(*Worktree Governance Staging*). Its four lifecycle hazards:

- **Sweep the directory at every close-out.** Enumerate every resident
  `Memo.*.GovernanceStaging.*.md` and confirm each is processed **by checking the
  destination documents, not by reading the memo's claims about them.** A memo that
  says its fold-ins were applied is a claim; the target document containing them is
  the evidence. Run:
  ```bash
  "$HOME/.virtuoso/bin/virtuoso" dispatch_guards staging-sweep --root <project-root>
  ```
  A non-zero exit means resident memos exist. Report them; do not delete a memo you
  did not verify against its targets.
- **A gate claim needs a backing artifact before it is folded in.** A staging memo
  asserting "gate approved" is not approval. Locate the artifact — the gate log, the
  run output, the signed check — before that claim reaches a canonical document. An
  unverified "approved" has come within one edit of being written into governance.
- **Lesson numbers proposed inside a worktree are provisional labels only.** The
  worktree's view of the catalog is frozen at branch time, so any number it proposes
  collides with numbers consumed since. Treat every in-worktree lesson number as a
  placeholder to be reassigned at fold-in.
- **Pass the current catalog tip into the authoring agent's prompt.** The paired fix
  for the above: an agent that is told the tip proposes from it instead of from a
  stale snapshot.

### Migration — Dispatches Already in Flight

Dispatches started before this pattern was introduced continue under the old pattern
(mid-dispatch-decision writes amendments inline to the roadmap). The new staging-file
pattern starts with the next dispatch started after this skill update.

When processing a close-out for a grandfathered dispatch, dispatch-closeout checks for
BOTH: a staging file (new pattern) and inline Mid-Dispatch Amendment blocks with
Close-Out Preservation instructions (old pattern). If both exist, surface as a
reconciliation prompt. The transition point should be noted in CLAUDE.md so it's
clear which dispatches used which pattern.

### What This Prevents

The pattern of:
1. The planner edits canonical main governance doc
2. Worktree edits same file from a stale base
3. Pre-merge rebase produces conflict (visible) OR silent revert (invisible)
4. Governance content potentially lost or scrambled

Under the new pattern: the worktree NEVER edits canonical main governance documents.
Conflicts on those files between the worktree and the planner are structurally impossible.
The staging file consolidates intent; dispatch-closeout applies it once at close-out,
with full visibility of any concurrent planner edits at that moment.

**Trade-off:** dispatch-closeout becomes mechanically heavier (more fold-ins to process)
and the staging file is one more artifact per dispatch. Both are small costs for the
structural elimination of a recurring failure mode.

Return to the SKILL.md phase that sent you here.
