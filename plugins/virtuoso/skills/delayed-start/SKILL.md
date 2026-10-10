---
name: delayed-start
description: >
  Defer one task to a clock time or a delay without pausing the session. Use when the user
  says "start at 3pm", "in N minutes/hours", "at midnight/noon", "kick off at 9:30", or
  otherwise wants a task to wait for a clock time or relative delay. Parses absolute times,
  named times, and relative delays; starts a wait that blocks only that task while other
  work carries on; runs the task when the time comes. Pauses everything only when the user
  asks for that.
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (its universal checks, at the version it declares, plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / max. A property of the task's difficulty, never a ranking of whoever performs it.

<!-- virtuoso-overlay-clause v2 -->
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.

Before executing the task below, wait until the specified target time.

## Instructions

1. Parse the target start time from my message. Handle all of these formats:
   - Absolute clock time: "12:00 AM", "3:30 PM", "23:45"
   - Named times: "midnight" → 00:00, "noon" → 12:00
   - Relative delay: "in 10 minutes", "in 2 hours", "in 90 seconds"

2. Calculate the wait in seconds between now and the target time. For absolute times, assume the **next occurrence** — if it's 11:50 PM and I say "start at 12:00 AM", that's 10 minutes from now, not 22 hours. If the target has already passed today, schedule for tomorrow.

3. Print a confirmation block, its *How it waits* line filled from the choice in step 4:
   ```
   ⏳ Deferred:      <brief summary of the task>
      Starts at:     <target, local time with the zone, e.g. 21:00 (-05:00)>
      Current time:  <now, same zone>
      Waiting:       <X minutes and Y seconds>
      How it waits:  <host scheduler | scheduled wake-up | background timer | foreground, after the work in hand | blocking, as asked>
      Meanwhile:     <other work carries on | everything holds, as you asked>
   ```

4. Start a wait that blocks only the deferred task. Use the first of these the host offers:
   - **The wait may outlive the session** — the host can reclaim this session while it
     sits idle, or the wait is longer than the host lets a wake-up or background command
     run: hand the task to the host's scheduler as a one-time run at the target time,
     carrying the full task text and what it needs to resume. The task then runs there;
     the confirmation says so. If the host has no scheduler, say the task will not run if
     the session is reclaimed, and ask whether to keep the session alive or schedule it
     another way.
   - **A scheduled wake-up:** the host can resume this conversation at a set time — set
     it for the target.
   - **A background timer:** the host can run a command in the background and report
     when it ends — run the wait there (`sleep <seconds>` or the shell's equivalent).
   - **None of these:** say so in the confirmation, finish the other work in hand first,
     then wait in the foreground in steps the host allows, re-reading the clock after
     each.

5. **While the task waits.** Carry on with any other work in hand; other work carries on
   exactly as without the wait, and a background agent's report that arrives during the
   wait is read and integrated as it comes. If a task plan is open, mark the deferred task
   ✗ with the reason `deferred until <time> <zone>`, and each task that depends on it ✗
   with `waits on #N`; the host's task tracker, if it keeps one, carries the same. This is
   a wait the user asked for, not a stop: it raises no issue document. Nothing that does
   not depend on the deferred task waits with it.

6. **When the wait ends**, mark the waiting tasks □ again and run the deferred task. If
   another step is part-way, finish that step, then start. If the wake-up arrives late,
   start at once and say how late. A task handed to the host's scheduler runs there: mark
   it ✓ as handed off, and keep each task that depends on it ✗ with `waits on #N` until
   its result is reported, then mark them □. This skill governs only the wait — everything
   after is normal execution under whatever other instructions apply.

7. **Pause everything only when asked.** When the user asks for all work to wait —
   "hold everything until 9", "pause until noon", "start nothing before 6" — wait in the
   foreground in steps the host allows, re-reading the clock after each, and start
   nothing else until the target. The confirmation reads `blocking, as asked` and
   `everything holds, as you asked`.

## Rules
- Don't ask for confirmation unless the wait exceeds 8 hours. For very long waits, double-check since I may have specified the wrong day.
- Use the system's local timezone, and show it with every time. Don't convert or assume UTC unless I explicitly say so.
- The wait blocks only the deferred task and the tasks that depend on it. Never hold the whole session unless I ask for everything to pause.
- Aim for second-level accuracy. Sub-second precision isn't needed.

## Examples
- "Start next dispatch at 12:00 AM" → defer the dispatch to midnight; other work in hand carries on.
- "Run this in 30 minutes" → a 1800-second wait for this task only.
- "Kick off the build at 6:15 AM tomorrow" → a wait that outlives most sessions: the host's scheduler, where it has one.
- "Check the board in an hour", while background agents are still reporting → defer the check, and keep reading and integrating their reports during the hour.
- "Hold everything until 9" → the one case for a blocking wait.

$ARGUMENTS
