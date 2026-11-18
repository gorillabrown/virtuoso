# Hand-off procedures and the summary

Serves write-plan Step 8, *Hand off to Virtuoso*: what to do for each answer the user gives, and the summary that ends the skill.

### (a) Hand off here

Print the summary (below), which ends this skill. Then load the **virtuoso** skill and
give it the held entry (kickoff, placement, reconciliation recipe, specifications) as the
dispatch spec. The run now belongs to the virtuoso skill: it checks the plan against
upstream, downstream, and in-flight work, records the entry `in-flight`, runs the recipe,
executes, returns the entry to `planned` if the run stops, and hands a finished run to
`/dispatch-closeout`. This skill records nothing more.

### (b) Another session

Print one fenced block the next session, which has no memory of this one, can start from:

```
Use the virtuoso skill to execute the held plan [entry] ([HB ids]) at
[holding bay path]/[entry].md. Its Plan section carries the kickoff, the roadmap
placement, the repository-reconciliation recipe, and the specifications.
Before the first edit, run the skill's written-plan intake: the conflict check against
upstream, downstream, and in-flight work, then record the entry in-flight, then run the
recipe. Close out with /dispatch-closeout.
If the conflict check finds that the code or the roadmap has moved since the plan was
recorded, stop and run /write-plan [entry] to re-verify it.
If a roadmap review has absorbed the entry in the meantime, it is a roadmap item now:
use /next-dispatch instead.
```

The entry stays `planned`; the virtuoso skill records `in-flight` when that session
starts.

### (c) Hold for roadmap review

Nothing more to write. End with the entry's path and state: the next `/roadmap-review`
places it at the recorded slot.

### (d) Withdraw

`--actor write-plan holding --record <entry> --state withdrawn --note "<reason>" --apply`.

## Output — the summary

```
# Write Plan — [Title]

**[One-to-two-sentence plain-language summary.]** *(held as [entry] · [HB ids])*

| | |
|---|---|
| Storyboard | aligned YYYY-MM-DD[; re-anchored — no drift / drift folded in] |
| Specifications | [HB-n — title: rubric PASS], … |
| Readiness | specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓ |
| Lessons applied | [ids, or none apply — N read] |
| Placement | after [Title] ([ID]), before [Title] ([ID]) — for the review to apply |
| Held | [entry] — planned |
| Hand-off | virtuoso here / virtuoso in another session / hold for review / withdrawn |

*Source: [register] via [provider], snapshot [timestamp] — read only.*
```

Return to write-plan Step 8: the skill ends with this summary.
