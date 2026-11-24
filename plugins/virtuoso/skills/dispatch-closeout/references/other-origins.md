# Held Plans, Combined Epics, and Retirement Records

Serves dispatch-closeout SKILL.md, before Wave 1: the close-out variants for a dispatch
whose origin line is not one roadmap item, and for a retirement another ceremony routes here.

## Held plans — ad hoc work that is not on the roadmap yet

Every execution path ends here (`references/execution-paths.md`). `Origin: held plan —
<entry> (HB-<n>)`, or a provisional `HB-<n>` identifier, means the work came through
`/storyboard` and `/write-plan`. It has no register row yet, because bringing work onto
the roadmap is `/roadmap-review`'s job. The close-out adapts in exactly these ways:

| Step | For a held plan |
|---|---|
| Wave 1, item 6 | Propose no register or roadmap change. The crossing plan says those wait for the review that absorbs the entry. |
| Step 1 — evidence | Unchanged. Verify every *Done when* row of the held specification. |
| Step 2 — artifact | Unchanged, keyed by `HB-<n>`: `closeout --item "HB-<n>"`. A staging fold-in that targets the roadmap or the register is not applied. List it in the report for the review. |
| Step 3 — terminal record | Deferred. There is no register item for the record to name yet. |
| Step 4 — persist | Lessons and the close-out only. The roadmap is not touched. |
| Step 5 — register | Deferred to the absorbing review. |
| Then | Record the entry `executed`, once every item of the entry has closed out, with the note naming each close-out, its result, and its date: |

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor dispatch-closeout holding --record <entry> --state executed --note "HB-<n>: <close-out path>, <result>, <YYYY-MM-DD>, estimate <e>, actual <a>" --apply

Take `<e>` and `<a>` from `timing --summary --json --dispatch <DISPATCH-ID> --item HB-<n>`
(its `estimate` and `actual`). A log whose rows name no item is one item's run, and
`--item` then takes every row. With no time log, or when the summary says
`"complete": false`, leave them out of the note. Never type a runtime in their place.

Step 6 verifies the close-out, the lessons gate, and that `holding --check <entry>` reads
`executed`. It does not verify a terminal record or a register status, because there are
none yet. The buffer check is skipped, since ad hoc work never drew on the buffer. If an
item set stops partway, the entry is not `executed`. The `virtuoso` skill, which
recorded it `in-flight`, returns it to `planned`, and the note names which items closed
out.

**The recording crossing.** When `/roadmap-review` absorbs an `executed` entry (its
A.4b), it creates each register item and then invokes this ceremony for **Steps 3, 5,
and 6 only**. Those steps append the terminal record and close the item:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor dispatch-closeout record-completion --item "<ITEM-ID>" --date "<close-out date>" --result "<result>" --evidence "<close-out path>" --estimate "<e>" --actual "<a>" --revision "<revision>" --apply

The values come from the entry's `executed` row. The evidence was verified, and the
lessons were recorded, when the work ran. Nothing is re-verified, and nothing is taught
twice. The item never stood on the conveyor belt, so Step 5 retires it and elevates
nothing.

## Combined epics — one run, several items

An epic packet whose charter names `items:` ran several roadmap items as one run
(`/epic`, Step 1b). Its origin line reads
`Origin: epic packet — <directory> (<PACKET-ID>: <ITEM-ID>, <ITEM-ID>, ...)`. On the belt
it is one **epic row**, `<PACKET-ID>`, with each item nested under it. It closes once, as
one crossing, and the crossing retires each item, then the epic row:

| Step | For a combined epic |
|---|---|
| Wave 1 | One brief and one findings table for the run. The register and roadmap changes name every item. |
| Step 1 — evidence | Every charter DoD row, fresh: each item's own *Done when* rows, and the row that proves they pass together. An item is complete only when all of its rows pass. The packet's done.md is on the default branch (Step 1). |
| Step 2 — artifact | One report, keyed by the packet: `closeout --item "<PACKET-ID>"`. |
| Step 3 — terminal record | One record per item, in the charter's serial order, then one for the epic row, each naming the one report as its evidence (`--ledger-only` for an external register). The epic row's record carries no estimate or actual: its items carry the effort. |
| Step 4 — persist | Lessons and the report once. A lesson's heading names the item that taught it, or the packet when the run as a whole taught it. |
| Step 5 — register | Each item closed, in serial order, then the epic row: `record-completion --item <ID>` for a local register, the mutation handshake for an external one — one plan per connector call, each read back before its confirm. |
| Step 6 — verify | Every item and the epic row terminal in the register, one record each in the ledger, and the lessons gate run for the whole run: `lessons --check "<report>" --closeout --item "<PACKET-ID>,<ITEM-ID>,<ITEM-ID>"`. |

A packet from before epic rows (1.17.5) has none in the register: its rows are skipped.

A run that stopped before `done.md` is not a completion. When the user closes it anyway,
retire only the items whose rows all pass, with their evidence. Return the rest to the
belt — `epic-row --packet <packet> --release` previews un-nesting them, `--apply` writes it
or emits the handshake — and say why for each in the report. Retire the epic row as
`dissolved` (a Step 3 record with the user's decision as its evidence, then its register
status), and set the charter's `status: aborted`. A charter left active keeps its items
out of `/next-dispatch`'s reach.

## Retirement records routed here

A roadmap review retires items at audit (its A.4): work that finished without a
close-out, and work it dissolves or supersedes. A status check's straggler migration
(roadmap-status, 2.1) retires finished work the same way. Each retirement needs one
terminal record, and a retirement is an *ordinary* record. Only an actor
`policy.terminalLedger.writers` names may append one, and by default that is this
ceremony alone. `correctionWriters` covers corrections only: records that name the
record they correct. So the retiring ceremony invokes this one, and what runs depends
on what the item already has:

| The retired item | What runs here |
|---|---|
| Completed, never closed out | The full crossing, both waves. No record is appended without verified evidence and lessons. |
| Completed and closed out, with the record missing | The recording crossing (above): Steps 3, 5 and 6, from the existing close-out, with `record-completion`. |
| Dissolved or superseded | Step 3 alone: one record whose result is `dissolved` or `superseded`, with the review's decision as its evidence, appended in the ledger's own format. `record-completion` is not used, because it closes the item as completed. The retiring ceremony sets the register status. |

Every case stays idempotent: a record already in the ledger for the item is a no-op.

Return to SKILL.md, *Wave 1 — Draft & Confirm*, and run the steps the variant keeps.
