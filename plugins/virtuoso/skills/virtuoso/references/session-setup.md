Serves `virtuoso` at dispatch start, before Phase 1: naming the dispatch record, stating Remote Control, the parent-and-worker architecture, and effort levels.

# Session Setup

## Dispatch Record Naming

When Virtuoso starts a dispatch, the visible record must be named for the work, not for
the trigger token. If the implementation agent's host creates a new chat/thread/record for the run,
the desired title is:

`[DISPATCH-ID] — [short dispatch name]`

Examples:
- `NARR-DEEPEN-2 — Chunk Timing Narration`
- `POSTV2-REVIEW-1 — Review Closeout`
- `DISPATCH-QUEUE-MIGRATE — Workbook Queue Transition`

A kickoff that carries a `Session:` line gives the title already fixed: use that line's
value up to ` · Remote Control:`, without the `Session:` label, as written.
Title the session by the first means the host offers — a session-title tool, a title
command, the first visible line — and do it before implementation begins. Try them in
this order:

1. **A session-title tool.** When the host exposes a tool that sets this session's own
   title, call it with the title. Done.
2. **A title command the owner types.** When the host has no such tool but has a command
   the owner can type to rename the session, print that command filled in with the title,
   ready to run, in the announcement, and ask the owner to run it. Carry on; do not wait.
3. **The first visible line.** When the host offers neither, the title is the
   first substantive visible line after the short Virtuoso announcement:

`[DISPATCH-ID] — [short dispatch name]`

Print that line in every case, even after a tool set the title, so the record reads the
same on any host.

Do not let the record remain titled `$virtuoso`, `/virtuoso`, "Virtuoso", or any
other skill-trigger-only name when the dispatch or dispatch name is knowable. If the
dispatch ID is unknown at intake, use a temporary descriptive title and update the
first plan heading once the ID is discovered.

### Remote Control: state it, prompt for it

At dispatch start, right after the title is set, say whether Remote Control is on for this
session, so the owner can follow and answer it from another device. Prompt; do not switch:

- **On:** say so, and leave it as it is.
- **Off:** print the one step that turns it on, ready to use: the host's switch or the
  command the owner types. Carry on; do not wait.
- **A Remote Control tool** the host exposes is called only when the owner asks for it,
  on record for this dispatch: the owner said so in the session, or the kickoff asks for
  it in so many words. The `Session:` line's Remote Control slot is the kickoff's
  best-known state, not a request; restate the live state here.
- **State unknown:** when the host has a switch but cannot report it, say so and print
  the step.
- **No switch at all:** say in one line that this host offers no Remote Control switch.

A session never turns it off: not by a tool, and not by printing a step for a switch that
is already on.

## Architecture: Parent Chat + Optional Swarm

Virtuoso runs inside the active parent conversation or the implementation agent's parent
record. It is acceptable for the implementation agent to preserve a separate record per dispatch run, but
that record must be named for the dispatch, not for the skill invocation. Do not create,
request, or suggest an additional top-level chat just to re-run Virtuoso inside a
dispatch record that already exists.

Agent swarms are allowed when the user or dispatch spec authorizes parallel
implementation. Child agents are workers attached to the current dispatch plan, not
new `$virtuoso` parent chats. The parent thread reads the dispatch spec, builds the
task plan, launches child agents only for concrete independent tasks, integrates
their results, runs verification, and keeps the human oriented.

**No orphan-chat rule:** Virtuoso may use `Agent()` / `spawn_agent` for bounded
worker tasks, but never as a way to start a new parent chat, restart the dispatch in
another conversation, or invoke `$virtuoso` recursively. If a legacy workflow says
"open a new Virtuoso chat," ignore that instruction and continue in the current
parent conversation.

**The boundary that matters is parent vs worker.** The parent owns the plan,
scope, narration, integration, and close-out. Workers own bounded task execution.
All worker output returns to the one visible dispatch plan in the parent chat.

## Effort Levels

Every dispatch may declare a **default effort level** that controls how deeply the
parent thread and child workers should reason. Effort is set when authoring the
spec; Virtuoso respects it and records mismatches during close-out. The full
decision framework, cost implications, and task-type reference live in the
`effort-levels` skill. The five levels are tabled in [task-plan.md](task-plan.md).

1. **Read the dispatch's declared effort** from the dispatch header (e.g., `Effort: Medium`).
2. **Check for task-level overrides** — individual tasks may annotate `{high}`, `{xhigh}`
   or `{max}` to override the dispatch default.
3. **Record effort on the task plan** and pass it through to any child worker prompt.
4. **Effort ↔ task-tier defaults** — when effort is not explicitly annotated on a task, it
   inherits from the task tier: mechanical→low, bounded→medium, cross-cutting→high.
5. **Print effort on every row.** A `[bounded]` task with no annotation is `{medium}`, and
   its row says `{medium}`; a task that overrides says its own level, `[bounded] {high}`.

**Close-out: effort mismatches.** In Phase 6, flag any task where the declared effort
didn't match actual complexity. "Task #3 was spec'd as {low} but required 3 retries —
recommend {medium} for similar tasks." This feedback helps the planner calibrate future
dispatches.

## Project-Specific Overlays

This skill provides the generic execution framework. A project layers its own requirements
on top of it without copying or editing this file. Copying it forks it, and a fork drifts
from the plugin in both directions while both copies load at once.

**The durable mechanism — a registered overlay.** The project registers an `overlays` role
and puts its additions at the skill's own mirror path, `skills/virtuoso/SKILL.md`, beneath
that directory (and `skills/virtuoso/references/<file>.md` for a reference file). Every
session reads it automatically; nothing has to be restated per dispatch. Check what is in
force:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . overlays

The overlay inherits everything here and adds to it, winning on conflict — except that it
may not loosen a shared-contract safety rule. See the overlay clause at the top of SKILL.md
and the plugin's `references/registry-contract.md`.

**For one run only — an `EXECUTION RULES` block.** When a constraint applies to a single
dispatch rather than to the project, state it in the dispatch prompt or agent brief instead
of registering it:

```
### EXECUTION RULES (Virtuoso + this dispatch)
- All rules from the Virtuoso skill and any registered overlay apply
- Additional: <constraint that is true for this run only>
```

A constraint that turns out to be true every time belongs in the registered overlay, not
re-pasted into every brief.

Return to SKILL.md and begin Phase 1.
