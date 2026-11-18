# Roadmap review — planning detail

Serves `roadmap-review` SKILL.md Phase C: C.2 (workstreams and deliverables) and C.3
(absorbing the open held entries and setting each item's path).

## C.2 Group them — the proposal, the approval, the apply

What `structure --propose` proposes:

- **A first review** (no `policy.roadmap.workstreams`): it proposes the whole structure.
  Candidate workstreams are joined by prerequisites or by mostly shared files, and
  candidate deliverables inside them by prerequisites or an existing grouping. Give each
  candidate a name and a one-line purpose. Show its signals, and the crossings between
  workstreams as a hint only: the files and prerequisites they share. Run-time ordering
  stays `combine`'s. An item flagged `noSignal` is named as its own candidate, never merged
  without the owner saying so. Every item under `unread` is named too.
- **A later review** (a structure approved): it proposes only a place for each item the
  register does not assign, a split for a deliverable over 8 items, and a merge for two
  deliverables sharing more than half their files.

The owner approves, renames or rejects the whole structure at a first review, and only
the proposals at a later one. Nothing is written before the owner approves. Then write
the approved file, `{"workstreams": [{id, name, purpose, deliverables: [{id, name,
purpose}]}], "assignments": {"<ITEM-ID>": {"workstream": "<id>", "deliverable":
"<id>"}}}`, and apply it with `structure --apply --file <approved.json>`.

The apply writes `roadmap.workstreams` and `roadmap.hierarchy: ["workstream",
"deliverable"]` through `policy-set`, which backs them up. Then it writes each assigned
active item's workstream and deliverable to the register. A local register is written
directly. For an external register it prints one `set-status` plan per item, which the
host's connector executes and `mutation-confirm` records. Finished items are never
touched. When the register has no workstream or deliverable column, it stops before any
write and names the missing columns: adding them is the owner's call. A rejected proposal
is an empty file, and nothing is written. After a rejection, the next review puts the
proposal to the owner again only if the active items changed since: a judgement for the
review, which the command does not track.

After an apply, the roadmap's active section is grouped under `### <workstream>` and
`#### <deliverable>` headings (the template in [roadmap-format.md](roadmap-format.md)).
Each item keeps its own `####` heading after its deliverable's, so its section still ends
at the next heading.

Return to SKILL.md C.2.

## C.3 Decompose into items — absorbing held entries and setting paths

**Absorb the open held entries.** Each `storyboarded` or `planned` entry either
comes onto the roadmap here or is withdrawn. Ask the user, in a batch, using the
bounded-question protocol. Nothing is carried past the review.

| Held as | Absorbed as |
|---|---|
| `planned` | Each `HB-<n>` becomes an item. Its specification moves into `policy.roadmap.specStorage`, with the provisional id replaced by the register's id. It is re-audited in D.3/D.4.5 before it counts as dispatch-ready, because code moves between planning and review. |
| `storyboarded`, dispatch-sized | A stub per item in its draft stub, with the entry's alignment record and frames cited as its source |
| `storyboarded`, epic-scale | One item whose structural fields carry `Path: epic`, with the entry cited as the source its charter is built from. `/next-dispatch` routes it to `/epic` when it reaches the head. |

Create each item through `create-item`, with `notes` reading
`origin: held plan <entry> (HB-<n>)`. Add the entry's downstream flags to the
non-blocking follow-up queue, and read the entry's placement into C.4: the exact slot
`/write-plan` recorded for a `planned` entry (its *Roadmap placement*), or the storyboard's
recommendation for a `storyboarded` one. Apply the slot unless the review's own
sequencing shows it is wrong, and say why when it does.
Then record the absorption. The note names what the entry became, for example
`as ADD-052 (queued, full-spec)`, `as ADD-053, ADD-054 (queued, stubs)`, or
`as ADD-055 (Path: epic)`. A note is one line, and it cannot contain `|`:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor roadmap-review holding --record <entry> --state absorbed --note "as <ITEM-ID> (queued, full-spec)" --apply

A withdrawn entry records `--state withdrawn --note "<the user's reason>"`.

**Set the path of items already on the roadmap.** `Path` arrived in 1.11, so an older
roadmap carries none, and a missing field means `dispatch`. Walk the active items. One
that is epic-scale on its own (outcome-stated, multi-phase, multi-session or walk-away)
gets `- **Path:** epic — <why it cannot be one dispatch>` in its entry, so
`/next-dispatch` routes it to `/epic`. Dispatch-sized items that belong together keep
their own path: `/epic` combines them when the user wants them run as one
(`references/execution-paths.md`). Name each item this review marks, with the reason,
in the plan.

Return to SKILL.md C.4.
