# Done — Loop hardening

**Completed:** 2026-09-23, session 1 (of ~3 budgeted). Every charter DoD row re-run fresh in
one session; outputs in state.md → Evidence. Final code commit `d8ef633`, CI run #126
(35907177454) green on ubuntu and windows.

## Definition of Done

| # | Condition | Result | Evidence |
|---|-----------|--------|----------|
| D1 | Metadata parity, both hosts + marketplace | met | 13 manifest tests; version sync in sync at 1.8.2 — `6343e1e` |
| D2 | `roadmap-integrity:` printed; skills match | met | 11 tests; preflight docstring lists it (fixed in the fresh run) — `64216e8`, `d8ef633` |
| D3 | Invalid policy is a warning at preflight | met | 3 tests — `64216e8` |
| D4 | Default writers match the skills | met | 18 tests — `f17a22f` |
| D5 | `## Decision` step and its reader | met | step 6d; close-out reads it — `f17a22f` |
| D6 | No ghost skill, agent or case | met | validator reference check; ghost grep 0 files — `f17a22f` |
| D7 | Epic resolves the `epics` role | met | 0 conventional paths — `f17a22f` |
| D8 | Sprint guards read v2 roles | met | 20 tests; `registry:scripts` 0 — `c1c66de` |
| D9 | `record-completion` | met | 4 crossing tests incl. recovery record — `cb81cc4` |
| D10 | Standing rules paired, one source | met | 7 tests; Zeus reads the source — `216ce91` |
| D11 | Promotion candidates computed | met | 3 tests; D.4.2 runs it — `7eae11a` |
| D12 | Anchored no-lesson reason; lesson-yield | met | 12 tests — `7eae11a` |
| D13 | `findings` role and reader | met | 19 tests — `f7bd2fd` |
| D14 | Effort calibration per project | met | 14 tests — `b458fa7` |
| D15 | Six loop-health metrics | met | 3 tests; contract documents each — `7eae11a` |
| D16 | No project residue in agents | met | validator scan extended; grep 0 — `2970be9` |
| D17 | One memory boundary | met | guide states it; Plato defers — `2970be9` |
| D18 | Rule-text hashes; buffer readiness | met | 27 rules hashed; `dispatch-buffer-ready` — `2970be9` |
| D19 | Stranded branches: owner decision | met as raised | BLOCKER(USER) #1 with inspection and recommendation; nothing merged |
| D20 | Contract and notes | met | 32 docs-contract tests; `## v1.10.0` — `d8ef633` |
| D21 | Green on both legs | met | run #126 success |
| D22 | Sweep tidies, merges, retires lessons *(owner amendment)* | met | 3 tests; check 21 — `7eae11a` |
| D23 | Close-out reviews every created file *(owner amendment)* | met | 3 tests; Wave 1 / Step 4 / Step 6 — `c1c66de` |

Full suite 874 passed, 3 skipped; 104 passed with child output forced to cp1252.

## Caveats and loose ends

- **D19 is the owner's.** `eb/gracious-mendel-juqys8` (close-out acceptance and evidence
  reconciliation, 7 rule anchors) and `eb/charming-pasteur-9rigux` (stale vendored-tool
  warning) are not merged. Recommendation: merge both. If gracious-mendel merges, its seven
  anchors need `RULE_TEXT_HASHES` entries (`python scripts/skill_rules.py --hashes`).
- **Launch Q2, Q3 unanswered:** a capability string beyond Interactive/Read/Write (left at
  three); whether 1.9.0 ships alone or with this as 1.10.0 (notes carry both sections).
- CI runs #119–#121 were red on Windows (test encoding), fixed in `80047fa`; no product change.
- `dispatch-buffer-filled` keeps its meaning; `dispatch-buffer-ready` is the new figure.
- Existing workspaces get the `findings` role and ledger effort columns only by adding them.

## What this epic taught (no lessons role in this repository — recorded here and in the notes)

1. **A gate ships with a test that holds the plugin's own templates to it.** Applied from
   the start; it caught the close-out skill's own example reason failing the new
   anchored-reason gate before release.
2. **Any test helper that pins an encoding pins the child's too.** The Windows leg found it
   three commits late; reproduce locally with `PYTHONIOENCODING=cp1252`.
3. **A DoD row's "verify by" names where the fact is observable, not an implementation
   file.** D2's grep pointed at the wrong file; the fresh run turned it into a real fix (the
   docstring) rather than a paper one.

## Recommended follow-ups

- Answer BLOCKER(USER) #1, Q2, Q3; then release (see the hand-off).
- In each governed project after upgrading: add the `findings` role and the ledger's
  Estimate/Actual columns if wanted; run `lessons --hygiene` once and act on it.
- Next analysis cycle: re-grade the 21 hand-offs against this release.
