Serves `virtuoso` Phase 1 (and every gate after it): the riders and corollaries of the verification rules whose binding paragraphs sit in SKILL.md.

# Verification Rules — Riders and Corollaries

Each section below continues the rule of the same name in SKILL.md Phase 1. The rule's
own paragraph is there; what follows here is binding with it.

### Every acceptance criterion and stop gate must be mechanical

Two riders:

- **A stop gate that names a rollback must also name what happens when the rollback
  fails.** An unhandled failed rollback is how a gate turns into an improvised
  decision under pressure.
- **A contingency is pre-registered as a decision table covering every axis the
  measured fact touches** — not only the axis that prompted the contingency. If the
  measurement can come back high, low, or unreadable, all three rows exist before the
  measurement runs.

### If completion depends on a suite gate, measure the base before implementing

- **Base green** → proceed; any new failure is yours.
- **Base red** → do **not** diagnose it in-dispatch. File it as an issue via the Phase 5
  contract, escalate, and continue only against the pre-existing-failure list. Verify
  each suspected pre-existing failure against the base before spending a single debug
  cycle on it.

A dispatch that discovers a red base halfway through cannot tell its own breakage from
the base's, and every hour after that point is spent on the wrong question.

### Never trust a null result from an unvalidated instrument

Before a null result is allowed to close anything:

- **Show the check fail.** Run it against a deliberately broken fixture, or against a
  known-bad input, and observe the failure. A check whose red state was never observed
  is unproven coverage.
- **Say which real inputs it fires on today.** A rule that matches no real row is not
  protecting anything, however correct its logic.
- **Distinguish a structural zero from a guarded one.** "This cannot happen" and "this
  is currently prevented" are different claims with different blast radii; a zero used
  as proof of unreachability must say which it is.
- **A verifier must exercise the real thing.** A check that reimplements the logic it
  is checking, or hardcodes a copy of the data it is validating, can pass while the
  production path is broken — and can be wrong on its own.

### Gates and acceptance criteria state identities, not counts

- Never state a suite criterion as a count, or as "passes". State it as the failing
  node-ID set measured against the base.
- A numeric carve-out ("up to N failures allowed") is a licence that widens silently as
  its baseline goes stale. Enumerate instead.
- **Name the tested tree by hash.** When workstreams stay unsynchronised during implementation,
  "the combined tree" describes nothing; a result whose tested-tree hash differs from the
  tree proposed for merge is a result about a different tree.

### Name which fork the acceptance test runs against

Two corollaries with teeth: verification must run against **the artifact that ships**,
not a convenient local stand-in; and a gate's trigger must cover the **union** of the
paths it guards, or it sits vacuous over whatever it does not reach.

### Cite a searchable anchor, not a line number

The same applies to a cited rule or lesson **number**: verify it by content, not by
existence. A number that resolves to unrelated text is worse than a missing citation,
because it reads as verified.

### Prove state by content, not by presence

- **Capture evidence at the right point in the lifecycle.** A hash taken before flush,
  checkpoint, or close reproduces the pre-change value and proves nothing — a "before"
  and "after" that match after a real change is a measurement error, not a finding.
- **Hash canonical content, not local bytes.** A pin computed over working-tree bytes
  fails on a fresh checkout for line-ending reasons alone, which makes the pin useless
  precisely where it matters.
- **Truncated output read as absence is a false negative.** An existence check piped
  through `head` reports "not found" for something present further down.

Return to SKILL.md Phase 1, where you left it.
