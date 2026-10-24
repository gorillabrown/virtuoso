---
dispatch: [DISPATCH-ID]
date: YYYY-MM-DD
runtime: [Actual from timing --summary --dispatch <DISPATCH-ID>, or "not measured (no time log)"]
tokens: [~NNNk]
status: [all-pass | has-regressions | has-discoveries]
---

# Dispatch Close-Out: [DISPATCH-ID]

## Dispatch Brief

**Goal:** [What the dispatch set out to do.]
**Result:** [What actually happened — name things, no aggregates.]
**Learned:** [<prefix>-NNN — title. Or: No new lesson — reason.]
**Recommend:** [Recommended next direction.]
**Bottom line:** [One-sentence takeaway.]

## Time

<!-- Pasted as printed by `timing --dispatch <DISPATCH-ID> --summary`: every row's predicted,
     actual and waited minutes, its kind, whether it was added, and any flag. Leave the
     section out when the dispatch kept no time log. -->

## Findings

| # | Finding | Metric | Target | Actual | Pass/Fail | Delta from Prior | Severity |
|---|---------|--------|--------|--------|-----------|------------------|----------|

## Interpretation

## Proposed Dispositions

## Mid-Dispatch Decisions

<!-- Amendment blocks migrated verbatim from the dispatch's staging file (or, for a
     grandfathered dispatch, from the inline spec). One block per decision: date, title,
     decision type, context, decision, rationale. "None" is a valid and complete entry. -->

## Lessons

<!-- What this dispatch taught. Each new lesson is appended to the registered `lessons`
     role under its identifier and named here; or the one line "No new lesson — <reason>".
     Then the outcome of each lesson the specification applied: held, or did not.
     Verified in Wave 2 Step 6 with `virtuoso_registry lessons --check <this file> --closeout --item <ID>`. -->

- **New:** [<prefix>-NNN — title] *(or: No new lesson — [what was examined, by identifier: the lessons, standing rules or items that already cover what this dispatch met])*
- **Applied:** [<prefix>-NNN — held / did not hold: evidence] *(one line per lesson; `lessons --candidates` counts these words)*

## Files Created

<!-- From `dispatch_guards created-files --base <ref>` in Wave 1; re-run in Wave 2 Step 6.
     Every file the dispatch created is accounted for: nothing temporary survives, and
     nothing is left untracked or uncommitted without a named reason. -->

- **Removed (temporary):** [paths] *(or: none)*
- **Committed:** [count, or paths]
- **Ignored:** [patterns added] *(or: none)*
- **Left for a decision:** [path — why] *(or: none)*
- **Guard:** `created-files` exit [0 / 1: the files named above]
- **Footprint:** [`footprint --dispatch <ITEM-ID>`: removed paths and sizes / none; kept paths — class and why / none]; free space [before] → [after]

## Governance Updates

## Roadmap & Queue Movement

- **Retired:** [DISPATCH-ID] — moved out of the active queue head to completed/archive.
- **Elevated:** [NEXT-DISPATCH-ID] — promoted to the active queue head as next dispatch target.

## Next Work

## Gates

## Git Hand-Off

- [ ] `git-handoff` run to commit close-out report, retrospective, roadmap, and dispatch queue.
