---
epic: [SLUG]
last_updated: [YYYY-MM-DD HH:MM]
updated_by: session [N]
---

# State — single source of current truth

<!-- Rewrite freely; keep under ~80 lines. History belongs in journal.md; the route in
     plan.md; the contract in charter.md. Never end a work burst with this file stale —
     sessions die without warning, and the disk must be handoff-ready at all times. -->

## RESUME PROTOCOL — no memory of this epic? Do this first, in order

1. Read charter.md (the contract), then plan.md (the route), then all of this file, then
   the **last** entry of journal.md.
2. Distrust, then verify: these files are MEMORY; the repo/system is REALITY. Run the
   cheapest check that confirms the "Where we are" block below (usually the current
   phase's exit-gate command). On conflict: believe reality, fix this file, note the
   correction in journal.md.
3. If `done.md` exists in this directory, do not start work — re-verify its claims
   against the charter DoD and report.
4. If `last_updated` above is older than the newest journal entry, trust the journal and
   repair this file before working.
5. Append a session-start entry to journal.md, then continue from "Next actions".

## Where we are

```
phase:        [P1 — name]
next_action:  [the single next concrete thing]
blockers:     [none]
session:      [N] of ~[M] budgeted   # N matches the latest journal S-number
dod:          D1 [unmet] | D2 [unmet] | D3 [unmet]
```

## Next actions — max 5, near horizon only

1. [ ]

## Working set — verified facts this epic relies on

<!-- Absolute paths, canonical commands, credential status, versions — plus hard-won
     gotchas future sessions must not relearn (flaky commands, environment quirks,
     approaches that failed). Anything not verified this run is marked HEARSAY until a
     session confirms it. -->

| Fact | Value | Verified how / when |
|------|-------|---------------------|
| [repo path] | [...] | [command, date] |

## Blockers

<!-- BLOCKER(USER): the exact question + context (what's known, options weighed) + what
     it unblocks + date raised + an empty `Answer:` line the user fills in place. Treat
     a filled Answer as charter-grade instruction; journal its adoption.
     BLOCKER(tech): the exact error + what was tried. Remove when cleared (journal the
     resolution). -->

- (none)

## Decision log — append; never silently re-litigate

| # | Date | Decision | Why | Charter authority |
|---|------|----------|-----|-------------------|
| 1 | [date] | [call made] | [reason] | [autonomy grant it falls under] |

## Evidence

<!-- Interim gate evidence: one line + pointer. Final DoD outputs: pasted in full, fresh,
     by the session claiming completion — see launch.md → Completion protocol. -->

- (none yet)
