Serves `virtuoso` Phase 3: the owner hierarchy, the worker scan and roster, the full routing tree, and the assignment table.

# Phase 3 — Assign Parent And Worker Owners

With the task plan built, the parent thread decides which tasks it should do locally
and which tasks are good child-worker candidates. This gives the human a clear
execution map without creating a fresh parent chat for the dispatch.

### The Owner Hierarchy

```
Zeus — owns plan, scope, integration, verification, close-out [cross-cutting]
  ├── hermes-worker  — mechanical execution, known-correct changes   [mechanical]
  ├── hercules-worker — single-domain implementation, bounded judgment [bounded]
  ├── aristotle-worker — cross-system implementation, architectural  [cross-cutting]
  └── specialist workers — bounded job descriptions
        ├── Hippocrates — test execution                          [mechanical]
        ├── MarcusAurelius — spec compliance, chronicles, docs    [bounded]
        ├── Plato — code quality review                           [bounded]
        └── [Project specialists as available]
```

Workers are child agents under the current dispatch run when delegation is authorized.
They are not standalone `$virtuoso` chats and they do not own the parent plan.

### Step 1: Scan for available workers

Search the project directory for role/agent definitions if they help preserve local
language. Look in:
- `.claude/agents/` — project agent definitions
- The plugin's bundled `agents/` (e.g., `Socrates`, the calibration specialist)
- The dispatch spec or task description for named roles
- The bundled behavioral reference [`zeus.md`](zeus.md) for the routing decision tree

Build a compact inventory. Do not spawn yet; spawning only happens during Phase 4
after the plan identifies a concrete worker task.

**Worker Name Resolution:** For every worker/agent file discovered, read its YAML
frontmatter `name:` field and use that label in the plan when helpful. The `name:`
field is authoritative for worker naming.

### Step 2: Analyze each worker's intent and tier

For every discovered worker role, read its definition and extract:
- **Intent**: what is this worker designed to do?
- **Tier**: which task tier is it built for (mechanical / bounded / cross-cutting)?
- **Type**: doer (general implementation) or specialist (bounded job)?
- **Constraints**: any specializations, limitations, or scoping rules?

Print the roster:

```
## Worker Roster
Doers:
- hermes [mechanical] — mechanical execution, prescribed changes
- hercules [bounded] — single-domain implementation with judgment
- aristotle [cross-cutting] — cross-system implementation, architectural decisions, root-cause analysis

Specialists:
- hippocrates [mechanical] — runs test suites, reports pass/fail
- marcusaurelius [bounded] — spec compliance, documentation, governance updates
- plato [bounded] — code quality review
```

If doer roles are not defined in the project, use the generic labels above. The
concept (cheap/mid/expensive work tiers) applies regardless of whether formal role
files are present.

### Step 3: Pair owners to tasks — the routing decision tree

For every task in the plan, walk this tree top-to-bottom. Take the FIRST match.

**0. Parent-owned?**
Is this task on the critical path, tightly coupled to current integration work,
mostly orchestration, or unsafe to hand off because the parent needs the result
immediately?
→ **Zeus**

**1. Specialist match?**
Does a specialist label match this task exactly?
- Running tests → **hippocrates**
- Running a calibration / measurement harness → **socrates**
- Verifying spec compliance → **marcusaurelius**
- Reviewing code quality → **plato**
- Updating governing docs → **marcusaurelius**
- Diagnosing unknown bug → **aristotle**
- Project specialist exists and matches → **that specialist**

If yes and the task is independent enough to hand off → assign to the specialist
worker. Stop. (Measurement is not regression — SKILL.md Phase 3 carries that rule, and
it decides every measurement run before this branch does.)

**The tell is the output shape, not the vocabulary.** Renaming a measurement run
"quick verification" or "acceptance verification" does not convert it into a
regression check — if a seed count or a target band appears anywhere in its
definition, it is measurement. A grep tuned to the old words will certify a clean
bill on an intact defect, which is how this rule was violated after it was written.

**2. Exact diff known?**
Can you write the precise file + old text + new text right now, with zero judgment?
(Config value changes, renames, version bumps, git stage/commit/push, file copies)
→ **hermes-worker**

**3. Single module / single domain?**
Does the work only need to understand ONE area of the codebase?
(Write a function, fix a known bug, implement a scoped feature, apply a fix spec,
write tests for one module)
→ **hercules-worker**

**4. Cross-system / architectural?**
Does the work need to hold multiple subsystems in mind? Could a change in file A
break file B? (Multi-module refactors, interface changes, pipeline integration,
data flow redesigns)
→ **aristotle-worker**

**5. When in doubt:** Default to **Zeus** for urgent/blocking work, or
**hercules-worker** for independent implementation work with bounded scope.

The parent may execute any task directly when that keeps the critical path moving.
Use workers for bounded sidecar tasks that materially advance the dispatch.

### Step 4: Print the assignment table

Reprint the task plan with owner labels replacing `unassigned:`. This is the
final plan that governs execution.

```
## Task Plan (single parent chat — child workers allowed)
✓ 1. Zeus: Load spec, build plan, assign owners                [cross-cutting]
□ 2. hercules-worker: Modify calc_defense_effectiveness() — WEIGHT 3.0→2.0 [bounded]
□ 3. hermes-worker: Update constants.toml default                      [mechanical]
□ 4. hippocrates-worker: Run fast test suite — all shards pass         [mechanical]
□ 5. hippocrates-worker: Run the full verification sweep                   [mechanical]
□ 6. Zeus: Interpret cal results + decide if tuning needed     [cross-cutting]
□ 7. hippocrates-worker: Generate profiler snapshot with pathway metrics [mechanical]
□ 8. aristotle-worker: Analyze profiler — does freed space flow to both? [cross-cutting]
□ 9. marcusaurelius-worker: Update CLAUDE.md with constants and cal results [bounded]
□ 10. Zeus: Commit, merge to main, push                        [mechanical]
```

The header states that the parent chat remains singular even when child workers are
used. Note: Task #1 is already ✓ because printing this table IS the completion of
Task #1.

Return to SKILL.md Phase 3, then go on to Phase 4.
