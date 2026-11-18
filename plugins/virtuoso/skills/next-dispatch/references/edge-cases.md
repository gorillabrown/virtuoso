# Edge Cases

Serves next-dispatch: the output and handling for each edge case Phases 1–4 branch to (SKILL.md *Edge cases* indexes them).

## Edge case: Stub at head

```
# Cannot Dispatch — Stub at Head

The item at the head of the conveyor belt has no specification.

## Buffer status

| Seq | Item | Specification |
|---|---|---|
| 1 | [Title] ([ID]) | stub |
| 2 | [Title] ([ID]) | stub |

*Source: [register] via [provider], snapshot [timestamp].*

## Required action

Run **/roadmap-review** to author specifications up to the project's dispatch
buffer ([policy.roadmap.dispatchBuffer]). Then run /next-dispatch again.
```

---

## Edge case: Epic at head

```
# Route to Epic — [Item title]

The item at the head of the conveyor belt is epic-scale (Path: epic). It is
chartered for a long-horizon run rather than dispatched.

## Required action

Run **/epic [ITEM-ID]**. It builds the packet from this item's roadmap entry,
and from the storyboard it was absorbed from, if there is one.
```

If a packet for this item already exists in the registered `epics` role (a charter
whose `item:` or `items:` names it), the run is under way. Do not route it to `/epic` again. Name
the packet, and point to its launch file's resume prompt.

---

## Edge case: Queue empty

```
# Finish Line Reached

No active items remain in the work register.

## Status

- Last completed: [Title] ([ID]) on [date]
- Terminal records: [N]
- Finish line: [tier] — reached.

*Source: [register] via [provider], snapshot [timestamp].*

## Required action

Run **/roadmap-review** to introduce and plan new work.
```

---

## Edge case: No work register registered

```
# Cannot Dispatch — No Work Register

This project has not registered a `workRegister` role, so there is no live
pipeline to read.

## Required action

Register one in `Virtuoso/workspace-layout.json`. It can be a local CSV or
Markdown table, a spreadsheet, a connector-backed task manager, an issue tracker,
a database, or a read-only snapshot. Run
`virtuoso_preflight.py --mode repair` to preview the registry change.
```

If a legacy `sprintCatalog` exists, note that reads are available through the
compatibility adapter in the meantime, but nothing can be written back.

---

## Edge case: Structural gap

Halt the print and ask a bounded question. Example:

> The specification for **[Item title]** defers a decision the implementation
> agent should not be making: which secondary channel to gate on. Pick:
> - (a) Gate on the primary channel only *(recommended — matches the precedent in
>   [close-out])*
> - (b) Gate on both channels
> - (c) Pause — you will update the specification yourself
> - (d) Escalate to /roadmap-review

Capture the decision, update the specification in place, and continue to Phase 4.
On (c) or (d), halt.

---

## Edge case: Prerequisites pending

Run the full output with prerequisite readiness failing, the pending items named
**by descriptive name**, and the verdict "Not ready".

If a deeper item is dispatchable (specified, prerequisites met), add:

```
## Alternative dispatch

**[Title]** ([ID]) at sequence [N] has all prerequisites met and is dispatchable
now. Skipping ahead is appropriate only when the head item's blocker is external
(waiting on data, waiting on a person); otherwise hold the head and resolve it.
```

If the user takes the alternative, re-run Phases 2–3 against that item first.

---

## Edge case: Blocker escalation

A stop, hold, or block becomes an issue document routed per
`policy.issues.targets`:

- `local` — write it into the registered `issues` directory using
  `policy.issues.filenameTemplate`.
- `external` — create it in the tracker named by `policy.issues.externalRole`,
  through the host's connector, and record the identifier it returns.
- both — do both and cross-reference.

Then route to `/mid-dispatch-decision` by path or identifier.

---

## Edge case: No roadmap or specification store

```
# Cannot Dispatch — No Specification Store

The `roadmap` role is not registered, or its registered target is absent.

## Required action

A registered-but-absent target is reported, never replaced. Either point the role
at the real document (run `virtuoso_preflight.py --mode repair` to preview the
registry change) or create the document at the registered path, then run
/roadmap-review.
```

Return to SKILL.md at the step that branched here. A halting edge case (stub, epic, queue empty, no register, no specification store, or a structural gap answered (c) or (d)) ends the run with its output.
