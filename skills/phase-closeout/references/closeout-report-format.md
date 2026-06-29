# Close-Out Report Format

Use this reference when drafting the project-facing close-out report.

## Report Flow

1. **Lead with the 5-line Sprint Brief** (*Goal*, *Result*, *Learned*, *Recommend*,
   *Bottom line* — one sentence each). See SKILL.md → "Sprint Brief — Lead of Wave 1".
2. Findings table.
3. Interpret each non-pass result.
4. Propose dispositions for user confirmation.
5. Draft governance updates still needed.
6. Name the recommended next direction in prose (no pointer code box — that is
   `/next-pointer`'s job).
7. Check audit / milestone / merge gates.

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

## Governance Update Drafting

Only draft the net-new updates still required.

Typical destinations:

- roadmap
- sprint queue
- lessons learned
- known traps
- technical reference

If the sprint already updated the docs fully, say so directly and do not invent additional work.

## Next Work Check

Three cases:

1. **Already scoped and valid**: print the sprint pointer.
2. **Already scoped but stale**: revise the scope based on close-out data.
3. **Not scoped**: draft a rough follow-on problem statement and task shape.

When revising stale next work, include:

- revised problem statement
- targeting data table
- revised task shape
- revised success criteria
- scope fence
- recommended effort level
