# Close-Out Report Format

Serves dispatch-closeout SKILL.md, Wave 1 and Deliverable 1: the project-facing close-out
report — its brief, sections, findings and dispositions, and the *Files Created* review.
Template: [../assets/CloseOut.template.md](../assets/CloseOut.template.md).

## Report Flow

1. **Lead with the 5-line Dispatch Brief** (*Goal*, *Result*, *Learned*, *Recommend*,
   *Bottom line* — one sentence each). See *The five-line brief* below.
2. Findings table.
3. Interpret each non-pass result.
4. Propose dispositions for user confirmation.
5. Migrate any **Mid-Dispatch Decisions** into their own section — amendment blocks
   moved verbatim from the dispatch's staging file, one block per decision. This is the
   destination the `virtuoso` and `mid-dispatch-decision` skills name when they migrate
   an amendment; the section must exist here or that migration has nowhere to land.
   "None" is a complete entry.
6. Draft governance updates still needed.
7. Name the recommended next direction in prose (no kickoff code box — that is
   `/next-dispatch`'s job).
8. Check audit / milestone / merge gates.

## The five-line brief

```
# [Item title] Close-Out  *(ITEM-ID)*

**Goal:** [What the dispatch set out to do — one sentence.]
**Result:** [What actually happened — name the things, no aggregates.]
**Learned:** [The durable lesson, by identifier: <prefix>-NNN — title. Or: No new lesson — reason.]
**Recommend:** [Recommended next direction — prose only, no kickoff.]
**Bottom line:** [One-sentence takeaway.]
```

Optional one-line add-ons where they materially sharpen the story: **By the
numbers**, **Between the lines**, **Yes, but**, **What's at risk**. Past ~10
lines, cut.

**Substance rule:** name the actual things. "Shipped three fixes" hides the
conclusion — write which three, in one clause. Lead with the descriptive name;
the identifier is secondary.

## Findings Table

Use a flat table:

| # | Finding | Metric | Target | Actual | Pass/Fail | Delta from Prior | Severity |
|---|---------|--------|--------|--------|-----------|------------------|----------|

Severity meanings:

- **Regression**: moved in the wrong direction beyond noise threshold
- **Miss**: target missed without clear regression
- **Discovery**: unexpected result that may change future work
- **Pass**: target met or exceeded
- **Marginal**: near target and worth monitoring

## Interpretation Rules

For each non-pass item, write short prose covering:

- what happened
- likely cause
- what it means for the project

Group related findings when they share the same root cause.

## Dispositions

Use one of:

- **Fix Now**
- **Investigate**
- **Defer**
- **Accept**
- **Log**

Always present proposed dispositions to the user before saving the report.

## Cost and guards

Report the dispatch's cost from `virtuoso_registry cost --dispatch <ITEM-ID>` —
orchestration apart, each row beside its time, cold returns and model changes, every
figure with its kind (*not computable* when the dispatch has no binding, naming it). Copy
the guards' receipts into the project with `virtuoso_registry --actor dispatch-closeout
guards --dispatch <ITEM-ID> --copy --apply` when a `guardLog` role is registered (hooks
never write the project; this does, in this tree). A finding that carries a cost or a
saving uses the one finding format (tier, confidence, what happened, why it matters, what
to do, now → after, kind).

## Files Created

Wave 1 item 7 drafts this section from `dispatch_guards created-files --root . --base
"<base ref>"`, run against the ref the specification's *Branch* field says the dispatch
started from:

- each **temporary** (scratch, backup, cache, log, anything under the registered `temp`
  role) is proposed for removal — committed ones included;
- each **untracked** file is proposed to commit, add to the ignore file, or name for the
  user's decision;
- each **uncommitted** change is proposed to commit or revert.

Nothing is left unreconciled by default: a close-out that leaves litter makes the next
merge a forensic exercise. A record under `Virtuoso/.recovery/` is always proposed to
commit, never to remove or ignore, and is never a fault by itself: it is the trail that
keeps an external write from repeating, and a confirmed write marks its record resolved
and keeps it. Only `virtuoso_registry recovery` says whether anything is outstanding.

**Outside the repository**, `virtuoso_registry --root . footprint --dispatch <ITEM-ID>`
writes nothing, and lists the run's own worktrees (branch `<ITEM-ID>` or `<ITEM-ID>-*`),
and the pytest basetemps and `temp` role children made since the branch left its base,
each with its size, class and reason. Propose each `redundant` or `regenerable` one for
removal with the `footprint --remove <path> --apply` command it prints, after the merge
and the deliverable check. Name each `unique`, `evidence` or `in-flight` one for the
user's decision with its reason (extract first for `unique`). Record the result as the
section's `- **Footprint:**` line: what was removed, what was kept and why, and free
space before and after.

## Governance Update Drafting

Only draft the net-new updates still required.

Typical destinations:

- roadmap
- dispatch queue
- lessons learned
- known traps
- technical reference

If the dispatch already updated the docs fully, say so directly and do not invent additional work.

## Lessons

Every report carries a Lessons section. It names the entries this dispatch appended
to the registered `lessons` role — or says `No new lesson — <reason>` — and records
the outcome of each lesson the specification applied. It is the one section a later
ceremony reads mechanically: Wave 2 Step 6 runs
`virtuoso_registry lessons --check <report> --closeout --item <ID>`, and a report that
fails it is not a finished close-out.

## Next Work Check

Three cases:

1. **Already scoped and valid**: print the dispatch kickoff.
2. **Already scoped but stale**: revise the scope based on close-out data.
3. **Not scoped**: draft a rough follow-on problem statement and task shape.

When revising stale next work, include:

- revised problem statement
- targeting data table
- revised task shape
- revised success criteria
- scope fence
- recommended effort level

Return to SKILL.md, the Wave 1 item you came from (the brief is item 1; *Files Created* is item 7).
