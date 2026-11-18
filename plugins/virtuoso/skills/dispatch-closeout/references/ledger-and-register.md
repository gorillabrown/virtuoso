# Terminal Record and Register — Detail

Serves dispatch-closeout SKILL.md, Wave 2 Steps 3 to 6: the values the terminal record
carries, the parked-row findings, the external-register handshake, and the flagged-row check.

## Estimate and Actual (Step 3)

`--estimate` and `--actual` are what effort calibration learns from. Take both from the
dispatch's time log: `virtuoso_registry timing --summary --json --dispatch <DISPATCH-ID>`
(add `--item <ITEM-ID>` for a combined epic). `estimate` is the first listing's
predicted total, and `actual` is the measured working total, both over the rows that ran
one after another. When the dispatch kept no time log, or the summary says
`"complete": false` (a row ran without a measured time), pass neither. Settle the
summary's `flagged` rows with the owner before this step: the Actual includes their time
either way, and a confirmation returns them to pricing history, not to the ledger. A
typed runtime is never an actual.

## Effort and Hours (Step 3)

The record's Effort (the item's size word, which pace reads trailing points from) and
Hours (the item's hours estimate, which pace reads trailing hours from) are the
register's: `record-completion` records both itself, and reports `effortRecorded: false`
when the ledger has no Effort column. Then add the *Effort* header and separator cell to
the ledger's table, never touching a record row, and append a correction of the new
record carrying its Effort. Hours lands only where the ledger has an *Hours* column; add
it the same way when the project sizes in hours.

With `--ledger-only` (an external register) it records Effort and Hours from the
register snapshot, so refresh the snapshot first if the item's size or hours changed in
the register since Wave 1.

## Parked rows (Step 4)

Each row `timing --summary --json` lists under `parked` — a row the run set aside and
did not do — is appended to the registered `findings` role as its own entry:
`### F-NNN — <row title> (<dispatch-id> parked row, YYYY-MM-DD)`, **Source:** the
dispatch, **Severity:** `info` unless Wave 1 confirmed otherwise, **Where:** the time
log and row label, **Finding:** the park reason, and **Disposition:** `open`, so the
roadmap review decides it. A project without the role gets the entries in the close-out
instead, with the manifest entry to add.

## The external-register handshake (Step 5)

External registers are mutated by this ceremony, not by the plugin. The provider
returns a structured instruction — operation, item, fields, expected revision,
idempotency key. Execute it with the host's connector — one plan per connector call —
read the item back, then confirm what the read-back shows: `mutation-confirm
--recovery-id <ID>` with `--succeeded`, `--failed`, or `--partial --written <fields>`
when only some landed. A plan that will not be executed is closed with
`mutation-abandon --recovery-id <ID> --reason <why>`. A field the register has no column
for (`policy.workRegister.fieldMappings`) is refused at planning; leave it out.
Re-running with the same idempotency key must not repeat the change.

## Flagged rows (Step 6)

The record's Estimate and Actual must equal `estimate` and `actual` from `timing
--summary --json --dispatch <DISPATCH-ID>`; this matters most on an external register.
The summary's `flagged` rows ran over 3× their prediction and may hide a wait nobody
saw, such as a host approval prompt. Ask the owner about each one: `timing --confirm N
--dispatch <DISPATCH-ID> --actor dispatch-closeout` returns it to the history as real
work. Otherwise it stays out, and the report names it.

Return to SKILL.md, the step you came from.
