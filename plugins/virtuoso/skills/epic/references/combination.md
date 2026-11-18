# Deciding a combination

Serves epic Step 1b, *A combination of roadmap items*: how to read the `combine` report, the judgement the command cannot make, and what to show the user before Step 2.

## What `combine` reports

It reads the register and each item's specification, and reports:

| Check | Combinable when | Finding when not |
|---|---|---|
| Each item is on the roadmap and ready to run | in the register, not terminal, blocked, or in flight; its specification written (`full-spec`) | `combine-item-unknown`, `-terminal`, `-blocked`, `-in-flight`, `-stub` |
| Each item runs only here | no active charter's `item:` or `items:` names it, and its entry does not declare `Path: epic` | `combine-item-chartered`, `combine-item-epic` |
| Each prerequisite is met | done already, or another item in the set | `combine-prerequisite-outside`, `combine-cycle` |
| Shared files are serialized | two items whose *Edit sites* or *Staging plan* name the same file run one after the other; items with nothing between them may run in separate workstreams | an item whose files cannot be read runs serially with everything (`combine-spec-unlocated`, `combine-files-unlisted`, warnings) |
| It is more than one item | two or more items | `combine-single` |
| The register is current | a fresh snapshot | `combine-snapshot-stale` |

It also returns the **serial order** (prerequisites first, then shared files, ties broken
by register sequence), the **workstreams**, every ordering edge with its reason ("shared
files: src/checkout/gateway.py"), and the effort in points. Exit 0 means combinable; exit
1 means a blocking finding stands. Every error is a reason not to charter: say which, and
route it (a stub or a missing prerequisite to `/roadmap-review`, an item in flight to its
own close-out, a stale snapshot to a refresh).

## The judgement the command cannot make

- **Readiness.** Each specification passed the rubric when a review made it
  dispatch-ready, but lessons may have been recorded since: re-run its mechanical half
  (`lessons --check <spec> --item <ITEM-ID>` for each) and walk the rest of
  `references/readiness-rubric.md` against each specification as `/next-dispatch` would.
  A structural gap stops the combination, as it stops a dispatch.
- **Hidden overlap.** Read each item's edit sites against the code: two items that change
  the same interface, schema, or fixture through different files still serialize. Record
  every ordering you add, with its reason, in the plan.
- **One outcome.** A combination is chartered because its items together make one outcome
  worth an unattended run. Items that merely share a workstream do not: say so and
  charter only the set that does.

## Show the user

Present the combination as one table in serial order (item by title then identifier,
workstream, what it waits on, the files it shares), then the sizing verdict (epic Step 1,
*Epic scale*). A combination the user trims is re-checked with `combine`.

Return to epic Step 1 for the sizing verdict, then Step 2.
