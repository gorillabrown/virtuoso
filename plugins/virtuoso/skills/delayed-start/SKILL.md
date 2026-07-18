---
name: delayed-start
description: >
  Wait until a specified target time before executing the task that follows. Use when the
  user says "start at <time>", "in N minutes/hours", "at midnight/noon", "kick off at
  <clock time>", or otherwise wants execution deferred to a clock time or relative delay.
  Parses absolute times, named times, and relative delays; sleeps until the target; then
  runs whatever task comes after. Governs only the wait — normal execution resumes after.
---

<!-- virtuoso-shared-contract v1 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — the project-root governance readme's machine-readable block and `Virtuoso/workspace-layout.json` together form the registry. The manifest wins for any role it already carries a key for; the readme is the carrier for roles the manifest does not yet hold. Resolve every governance path through the registry — never hardcode one.
- **Workspace adopt** — bringing an established project under management is non-destructive: nothing is moved, nothing is duplicated, no parallel document is seeded beside a registered one, and user content is never overwritten.
- **Git ownership** — stage explicitly (`git add <path>`); never `git add .` or `git add -A`. Run a tripwire status check against the expected dirty set before any commit and stop on anything unexpected. No destructive flags, no force-push.
- **Effort levels** — low / medium / high / max. Model tier sets the default (haiku→low, sonnet→medium, opus→high); annotate a task only when overriding its default.
- **Issue contract** — any stop, hold, block, or elevation becomes the 7-field issue document, saved to the registered `issues` directory as `Issue.<SPRINT-ID>.<YYYY-MM-DD>.md`, then routed to `/mid-dispatch-decision` by path.
- **Governance staging** — a worktree-resident run never edits a main governance document directly; the change-intent goes to a staging file as fold-in instructions, applied at close-out.

Before executing the task below, wait until the specified target time.

## Instructions

1. Parse the target start time from my message. Handle all of these formats:
   - Absolute clock time: "12:00 AM", "3:30 PM", "23:45"
   - Named times: "midnight" → 00:00, "noon" → 12:00
   - Relative delay: "in 10 minutes", "in 2 hours", "in 90 seconds"

2. Calculate the wait in seconds between now and the target time. For absolute times, assume the **next occurrence** — if it's 11:50 PM and I say "start at 12:00 AM", that's 10 minutes from now, not 22 hours. If the target has already passed today, schedule for tomorrow.

3. Print a confirmation block:
   ```
   ⏳ Scheduled start: <target time>
      Current time:    <now>
      Waiting:         <X minutes and Y seconds>
      Task:            <brief summary of the task that follows>
   ```

4. Run this to sleep until the target time (replace HH, MM with parsed values):
   ```bash
   python3 -c "
   import time
   from datetime import datetime, timedelta
   now = datetime.now()
   target = now.replace(hour=HH, minute=MM, second=0, microsecond=0)
   if target <= now:
       target += timedelta(days=1)
       print('Target time passed today — scheduling for tomorrow.')
   wait = (target - now).total_seconds()
   print(f'Sleeping {int(wait)}s until {target.strftime(\"%I:%M %p\")}...')
   time.sleep(wait)
   print('Timer resolved. Starting now.')
   "
   ```
   For relative delays, just `sleep <seconds>` directly.

5. After the sleep completes, execute the task that follows. This skill only governs the wait — everything after the timer is normal execution under whatever other instructions apply.

## Rules
- Don't ask for confirmation unless the wait exceeds 8 hours. For very long waits, double-check since I may have specified the wrong day.
- Use the system's local timezone. Don't convert or assume UTC unless I explicitly say so.
- The sleep is blocking — hold the terminal until the timer resolves.
- Aim for second-level accuracy. Sub-second precision isn't needed.

## Examples
- "Start next dispatch at 12:00 AM" → sleep until midnight, then begin.
- "Run this in 30 minutes" → sleep 1800 seconds, then begin.
- "Kick off the build at 6:15 AM tomorrow" → sleep until 06:15 next calendar day.
- "Start at 2 PM — here's the dispatch: [task]" → sleep until 14:00, then execute.

$ARGUMENTS
