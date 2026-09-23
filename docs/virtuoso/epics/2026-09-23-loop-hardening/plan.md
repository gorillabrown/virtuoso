---
epic: loop-hardening
charter: charter.md
---

# Phase Plan — Loop hardening

<!-- The route, not the contract. The executor may reshape phases as reality teaches —
     log the replan in state.md → Decision log and journal.md. Exit gates may tighten,
     never loosen. Plan at phase altitude: intents and gates here; steps live inside the
     run. At every exit gate: re-read charter.md before opening the next phase. -->

## Phases

### P1 — Discovery and metadata
- **Intent:** verify every charter assumption that can be verified from the tree
  (marketplace keys, host vocabulary, the preflight's roadmap read, sprint-guard tests),
  baseline the DoD commands, merge the alternate-host metadata commit, and bring the
  Claude manifest and marketplace entry to parity with a test that pins it.
- **Exit gate:** D1 passes; `state.md` → Working set holds the verified facts; the
  stranded-branch inspection is recorded as a BLOCKER(USER) (D19).
- **Rough size:** one work burst.

### P2 — Remove the dangling and the unsafe
- **Intent:** gaps 2, 7, 6, 11, 13, 18, 12 — the `roadmap-integrity:` line, policy
  validation at preflight, writer defaults, the Decision step and issue readers, ghost
  names and pasted paragraphs with a validator check, the epic role, v2 sprint guards.
- **Exit gate:** D2–D8 pass; full suite, validator and version sync green; pushed.
- **Rough size:** one to two work bursts.

### P3 — Make the prose links mechanical
- **Intent:** gaps 5, 4, 3, 10 and D22 (owner amendment) — lessons hygiene for `governance-sweep`, `record-completion`, the standing-rules pairing with one
  source, `lessons --candidates`, the anchored no-lesson reason and `lesson-yield`.
- **Exit gate:** D9–D12 and D22 pass; `test_crossing.py` runs the new command; pushed.
- **Rough size:** two work bursts.

### P4 — Give every output a reader
- **Intent:** gaps 8, 9 and the six loop-health metrics — the `findings` role and its
  readers, effort calibration through the ledger, the `learning` metric group.
- **Exit gate:** D13–D15 pass; every new metric has a tested *not computable* path; pushed.
- **Rough size:** two work bursts.

### P5 — Hygiene and owner decisions
- **Intent:** gaps 14, 15, 16, 17 — project residue out of the shipped agents, the memory
  boundary, rule-text hashes and `dispatch-buffer-ready`, the stranded-branch decision
  surfaced with a recommendation.
- **Exit gate:** D16–D19 pass; pushed.
- **Rough size:** one work burst.

### P6 — Contract, notes, fresh DoD, completion
- **Intent:** the registry contract and docs tests for everything new, the v1.10.0
  release notes, then the full charter DoD re-run fresh with evidence, and
  launch.md → Completion protocol.
- **Exit gate:** D20 and D21 pass; every DoD row re-verified in one session; `done.md`
  written; the release handoff given.
- **Rough size:** one work burst plus the CI wait.

## Gate log

<!-- One line per gate passed: date, phase, evidence pointer (journal entry / command output). -->

| Date | Gate | Evidence |
|------|------|----------|
| 2026-09-23 | P1 | D1 met — journal S1 |
| 2026-09-23 | P2 | D2–D8, D23 met — journal S1 (cont.); 820 passed |
| 2026-09-23 | P3 | D9–D12, D15, D22 met — journal S1 (P3); 848 passed |
| 2026-09-23 | P4 | D13, D14 met — journal S1 (P4); 866 passed |
| 2026-09-23 | P5 | D16–D18 met, D19 raised — 873 passed |
| 2026-09-23 | P6 | fresh DoD all met; CI #126 green — done.md |

## Current-phase worklist

<!-- Owned by the executor. Regenerate when a phase opens; keep it short-horizon. -->

- [ ] Merge 4e00672 and run the overlay suite
- [ ] Claude manifest and marketplace parity + test
- [ ] Verify A2 against the marketplace documentation in the tree, if any
- [ ] Record the stranded-branch inspection as BLOCKER(USER)
- [ ] Baseline outputs into Working set
