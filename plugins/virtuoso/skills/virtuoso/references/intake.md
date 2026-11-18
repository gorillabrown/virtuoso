Serves `virtuoso` Phase 1, step 6: the conflict check, the held-plan intake, and workstream detail, all before the first edit and before the work branch exists.

# Phase 1 Intake — Conflict Check, Held Plan, Workstream

### Phase 1 steps — in full

Before touching any file or running any command:

1. **Read the full task specification.** If the task references external docs, read those too.
   When the task is a governed dispatch, read its **origin line** as well
   (`references/execution-paths.md`). The spec may be a roadmap item from `/next-dispatch`, a
   held plan handed off by `/write-plan`, or an epic packet from `/epic`. All three arrive
   meeting the same destination contract. The origin tells the intake below which checks
   to run, and tells Phase 6 how the close-out runs.
2. **Read the behavioral reference** — the bundled [`zeus.md`](zeus.md)
   (Virtuoso's orchestration protocol: routing decision tree, agent hierarchy, escalation
   rules), or the project's own lead-agent definition if it overrides — to load the routing
   decision tree, escalation rules, and coordination protocol.
3. **Identify every discrete deliverable.** A deliverable is something you can point to when done
   (a file changed, a test passing, a document updated, a commit made).
4. **Flag anything unclear.** If a step is ambiguous, a file path might be wrong, or a dependency
   might not exist — stop and ask NOW. Guessing wastes 10x more time than asking.
5. **Declare the workstream and its surface manifest** when the project runs workstream-based
   concurrency. Read the workstream assignment from the dispatch spec; if the spec does not
   name one, ask before touching a file.
6. **Run the conflict check** (below) for a governed dispatch, and the **held-plan
   intake** when the origin is a held plan. Both come before the first edit and before
   the work branch exists.
7. **Read the milestones** of a governed dispatch or epic, derive them if the specification
   has none, show them, and open the progress band's run ([progress-band.md](progress-band.md)).
   The milestones group the task list Phase 2 builds.

### The conflict check — before the first edit

A written plan was safe to run when it was written. This check makes sure it is still
safe now, against the roadmap and the work around it. It is read-only: lock-free git
(`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`) and the registry helper's read side
(`items --all --json`, `holding --open`, `lessons --open`).

| Direction | What to check | A conflict looks like |
|---|---|---|
| **Upstream** | Every prerequisite is terminal through the provider. A prerequisite in a held entry reads `executed` (`holding --check`). | A prerequisite that is still queued, in flight, or blocked |
| **In flight** | Nothing else in flight touches these edit sites: in-flight register items, in-flight held entries, and other open branches and worktrees (`git worktree list`, then `git log --oneline <default>..<branch> -- <edit sites>` for each) | Another run changing the same files now |
| **Roadmap order** | Where the plan sits against the current order: its kickoff's *Placement* line, or its sequence. Any item ahead of it that is not terminal and touches the same edit sites, or that it depends on. | Landing underneath work the roadmap put first, or jumping ahead of the head without a recorded reason |
| **Downstream** | The items the plan's impact map and placement name as downstream, and any dispatch-ready specification that cites a location this plan moves (search the specification store for the edit sites' anchors) | A specification this run will make stale |
| **Drift** | Commits at the edit sites since the base the kickoff names (`git log --oneline <kickoff's sha>..<default branch> -- <edit sites>`), and live lessons recorded since the plan was written | Code that moved under the plan |

Straight from the ceremony that just gated the plan, in this session, the check is quick:
it confirms what that ceremony read. From another session, or on a later day, it is the
check that matters. For an epic packet, run it at the first session against the
charter's scope. The packet's resume protocol covers the sessions after that.

What a conflict does (SKILL.md Phase 1 carries the same gates in short):

- **Upstream pending, or in-flight work on the same edit sites** → stop before the first
  edit. Render the issue (Phase 5) and route it to `/mid-dispatch-decision`. Two runs
  never change the same edit sites at once.
- **Roadmap order** → ask one bounded question: wait for the earlier item, run now with
  the user's reason recorded in the plan, or send it back to be planned again.
- **Drift, or a plan that no longer matches the code** → stop. A held plan goes back to
  `/write-plan <entry>`, and a roadmap item to `/next-dispatch`. Never re-plan here.
- **Downstream staleness** → not a stop. Name each affected item in Task #1's notes and
  in the close-out, so the review acts on it. Another item's specification is not this
  run's to edit.

Print the result as one line under Task #1:
`Conflict check: upstream ✓ · in flight ✓ · roadmap order ✓ · downstream [n flagged] · drift ✓`.

### The held-plan intake

A held plan (`Origin: held plan — <entry> (HB-<n>)`) comes straight from `/write-plan`'s
hand-off, in this session or another. `/storyboard` scoped it and `/write-plan` specified
it. Neither executed anything. As part of Task #1:

1. **Read its state:** `"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . holding --check <entry>`.
   - `planned` → continue.
   - `in-flight` → another run holds it. Stop and ask. Never run it twice.
   - `storyboarded` → there is only a draft stub, and no plan. Route to `/write-plan <entry>`.
   - `absorbed` → it is a roadmap item now. Route to `/next-dispatch`.
   - `executed` or `withdrawn` → there is nothing to run. Say so and stop.
2. **Run the conflict check** above, against the entry's kickoff, placement, and impact map.
3. **Record the start of execution.** Preview first, then run it with `--apply`:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso holding --record <entry> --state in-flight --note "executing: <branch>" --apply

   If the command refuses because `virtuoso` may not write the `holdingBay` role, the
   project registered the role before this skill recorded there. Show the user the fix,
   which is adding `virtuoso` to the role's `allowedWriters`, and stop until they make
   it. Never record under another ceremony's name.
4. **Run the kickoff's repository-reconciliation recipe first**, before the first edit.
   Halt on any STOP it contains, and report the git output.
5. The dispatch identifier is the `HB-<n>`. An item set runs every item, in prerequisite
   order, in this one run.

**If the run ends without completing**, and will not resume from `/mid-dispatch-decision`
in this run, hand the entry back to the bay:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso holding --record <entry> --state planned --note "stopped: <why>; <what is preserved, where>" --apply

Name any item of a set that did close out, so the review absorbs it as completed. The
holding bay lets this skill record `planned` only out of `in-flight`: it hands a run
back, and it never plans. A finished run goes to `/dispatch-closeout`, which records the
entry `executed`.

### Workstream discipline — detail

This continues the workstream-discipline rule in SKILL.md Phase 1. The declaration, at
Phase 1 and before any edit:

| Declaration | What it is |
|---|---|
| **Workstream** | Which workstream this dispatch occupies. A project with an exclusive engine workstream admits exactly one engine dispatch at a time. |
| **Surface manifest** | The explicit set of paths this dispatch may write. Anything outside it is another workstream's surface. |
| **Merge slot** | The per-workstream serialization token claimed at integration, not at dispatch. |

The manifest is what makes a dirty file someone else's problem rather than a blocker:
dirt inside the manifest stops the dispatch, dirt outside it is disclosed and ignored.
A dispatch that cannot state its workstream and manifest is not ready to dispatch — stop and
ask, do not infer one from the files the spec happens to mention.

**Resolve the concurrency cap from the project's own gate; never assume one, and never
restate a number here.** The cap and the workstream set are project configuration, enforced by
the project's worktree/workstream tooling. Read them from that tool at dispatch time. A cap
written into this skill body would be a restatement that goes stale the moment a project
changes its workstream count — which is the failure this skill's own citation discipline exists
to prevent.

**Concurrency supersedes serialization — do not re-introduce "one dispatch at a time."**
Workstream-based concurrency with serialized *integration* replaced the older
one-dispatch-in-flight rule. A project that has adopted workstreams has retired serialization-first
deliberately; re-adding it contradicts both that project's governance and its shipped
tooling. Serialized mode survives only as the **default for a dispatch that declares no
workstream**, which is a different rule.

Return to SKILL.md Phase 1: print the conflict-check line, then continue at step 7.
