# The held plan's kickoff

Serves write-plan Step 5, *the kickoff*: the lines it carries and its one-block form. Step 7 writes the same block into the held entry's `## Plan` section.

```
[Item title]  (HB-<n>)
Origin: held plan — [entry] (HB-<n>), not yet on the roadmap
Placement: after [Title] ([ID]), before [Title] ([ID]) — for the review to apply
Effort: [size][ — N h, where the register carries hours]
Branch: [branch] from [default branch] @ [sha that carries the held plan, or "uncommitted — see git status"]
Specification: [holding bay path]/[entry].md#HB-<n>
Status: planned — held | Prerequisites: [descriptive names, met/pending]
Readiness: specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓
```

The kickoff and its recipe are one block, in next-dispatch's §4.2 form: after these lines,
inside the same fence, come the `REPOSITORY RECONCILIATION` label naming the shell, the
recipe indented two spaces, and the halt line last.

Return to write-plan Step 6, the plan gate.
