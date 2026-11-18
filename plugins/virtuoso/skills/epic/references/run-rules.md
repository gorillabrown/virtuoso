# The run rules the templates embed

Serves epic Step 5, *Scaffold and hand off*, item 1: the run rules the five templates carry, so the executor gets them from files it must read anyway and the packet works even for an executor that has never seen this plugin. When you fill the templates and delete unused optional sections, keep every one of these intact.

- **Resume protocol** at the top of state.md: charter → plan → state → last journal entry;
  distrust-then-verify; files are memory, the repo is reality.
- **Handoff-ready always:** sessions die without warning; update state.md and journal.md
  before ending any work burst. Each update refreshes state.md's *Tried and failed* from
  `virtuoso_registry guards --dispatch <session id> --tried`, so the next session does not
  retry a dead end.
- **Never idle:** blocked on one front → advance another; blocked on all →
  BLOCKER(USER) with the exact question, clean journal exit.
- **Fresh evidence:** completion claims re-run every DoD verification in the claiming
  session; `done.md` is written once, by that session, and is the loop's stop signal. It
  reaches the default branch in a docs-only merge after the code merge, never inside it.
- **Re-anchor at gates:** every phase gate re-reads the charter before the next phase
  opens; goal drift compounds silently across compaction and session boundaries.
- **Context hygiene:** raw tool output stays out of durable files and the long-lived
  session; record distilled conclusions and evidence pointers, and where the runtime
  offers subagents, push noisy exploration into them and keep only their results.

Return to epic Step 5, item 2 (*Fill the run's git work*).
