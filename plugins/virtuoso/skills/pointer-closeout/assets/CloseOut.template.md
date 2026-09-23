---
sprint: [SPRINT-ID]
date: YYYY-MM-DD
runtime: [Xm Ys]
tokens: [~NNNk]
status: [all-pass | has-regressions | has-discoveries]
---

# Pointer Close-Out: [SPRINT-ID]

## Sprint Brief

**Goal:** [What the dispatch set out to do.]
**Result:** [What actually happened — name things, no aggregates.]
**Learned:** [<prefix>-NNN — title. Or: No new lesson — reason.]
**Recommend:** [Recommended next direction.]
**Bottom line:** [One-sentence takeaway.]

## Findings

| # | Finding | Metric | Target | Actual | Pass/Fail | Delta from Prior | Severity |
|---|---------|--------|--------|--------|-----------|------------------|----------|

## Interpretation

## Proposed Dispositions

## Mid-Dispatch Decisions

<!-- Amendment blocks migrated verbatim from the sprint's staging file (or, for a
     grandfathered sprint, from the inline spec). One block per decision: date, title,
     decision type, context, decision, rationale. "None" is a valid and complete entry. -->

## Lessons

<!-- What this dispatch taught. Each new lesson is appended to the registered `lessons`
     role under its identifier and named here; or the one line "No new lesson — <reason>".
     Then the outcome of each lesson the specification applied: held, or did not.
     Verified in Wave 2 Step 6 with `virtuoso_registry lessons --check <this file> --closeout --item <ID>`. -->

- **New:** [<prefix>-NNN — title] *(or: No new lesson — [reason])*
- **Applied:** [<prefix>-NNN — held / did not hold: evidence] *(or: the specification applied none)*

## Files Created

<!-- From `sprint_guards created-files --base <ref>` in Wave 1; re-run in Wave 2 Step 6.
     Every file the dispatch created is accounted for: nothing temporary survives, and
     nothing is left untracked or uncommitted without a named reason. -->

- **Removed (temporary):** [paths] *(or: none)*
- **Committed:** [count, or paths]
- **Ignored:** [patterns added] *(or: none)*
- **Left for a decision:** [path — why] *(or: none)*
- **Guard:** `created-files` exit [0 / 1: the files named above]

## Governance Updates

## Roadmap & Queue Movement

- **Retired:** [SPRINT-ID] — moved out of the active queue head to completed/archive.
- **Elevated:** [NEXT-SPRINT-ID] — promoted to the active queue head as next dispatch target.

## Next Work Pointer

## Gates

## Git Hand-Off

- [ ] `git-handoff` run to commit close-out report, retrospective, roadmap, and sprint queue.
