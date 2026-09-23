# Journal — Loop hardening

<!-- Append only. Never edit or delete an old entry — corrections get their own entry.
     One entry per session or work burst, newest last. -->

## S0 — 2026-09-23 18:30 — scaffold

- **Did:** epic packet created ([charter](charter.md), [plan](plan.md), [state](state.md),
  [launch](launch.md)). Source material: the SWOT and gap analysis (18 gaps, 21 hand-offs)
  and the white paper written earlier the same day. No project work performed yet beyond
  the merge of `4e00672` (metadata), which P1 verifies.
- **Learned:** the repository keeps no lessons role, so the charter's Lessons applied
  reads the SWOT and the release notes instead (0 read from a role; six applied). The two
  stranded branches are finished, additive work; whether they merge is the owner's call
  (state.md → Blockers #1). Preflight baseline: 775 passed, validator clean, version sync
  at 1.8.2, push and CI reachable.
- **Next:** P1 per plan.md — parity of the Claude manifest and marketplace entry with the
  Codex `interface` block, pinned by a test.

## S1 — 2026-09-23 18:45

- **Did:** merged `4e00672` (alternate-host `interface` block, icon assets, pinning test)
  as `b06ec0d`; brought the Claude manifest and the marketplace entry to parity with it
  (one description that names the learning loop, `displayName`, author with URL, one
  keyword list; marketplace gains `category` and `tags`); a third prompt chip for the
  close-out; `longDescription` says "prepare outside audits" instead of "audit
  third-party code", which the skill never did. Parity test added.
- **Learned:** A2 verified from the Claude Code docs (plugin-marketplaces, plugins-reference):
  `displayName`, `category`, `tags` are documented; `plugin.json` ignores unknown keys.
  The marketplace description had drifted ("16 skills") with nothing to notice it.
- **Decisions:** charter amended by the owner mid-session — D22, `governance-sweep`
  tidies, merges and retires lessons. Scheduled into P3 beside gap 3 (candidates),
  which reads the same close-out outcomes.
- **Gate/DoD movement:** D1 met (`pytest -k "manifest or marketplace"` 13 passed;
  version sync in sync at 1.8.2).
- **Next:** P2 — `roadmap-integrity:` line (one read), policy findings at preflight.
