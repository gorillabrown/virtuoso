# Roadmap review — applying the audit

Serves `roadmap-review` SKILL.md Phase A: A.4 (retiring items) and A.4b (absorbing held
plans that already ran). A.4b uses the external-register mutation handshake described in
[specifications.md](specifications.md) § D.5.3.

## A.4 Apply changes — in full

For each item being retired:
1. **Route its terminal record to the close-out ceremony.** A retirement is an
   *ordinary* terminal record, and only an actor `policy.terminalLedger.writers`
   names may append one. By default that is `dispatch-closeout` alone.
   `correctionWriters` does not cover a retirement: it permits only
   *corrections*, which are new records naming the record they correct, and a
   retirement corrects nothing. So invoke `/dispatch-closeout` for the item, as
   A.4b does for held plans. Its section *Retirement records routed here* says
   what runs:
   - completed but never closed out → its full crossing, because no record is
     appended without verified evidence and lessons;
   - completed and closed out, with only the record missing → its recording
     crossing;
   - dissolved or superseded → one record with that result, and this review's
     decision as the evidence.

   Append the record yourself only when `writers` names `roadmap-review`. That is
   a project's explicit choice, never a default. Terminal records are append-only:
   never reorder, rewrite, or delete one. When this audit finds a record wrong, it
   appends a correction, a new record naming the one it corrects. That is what
   `correctionWriters` lets this ceremony append.
2. Add its one-line entry to the roadmap's completed summary.
3. Move its full content to the current dated archive.
4. Remove the full content from the active roadmap.
5. Update the item in the live register through the provider: its status, a
   cleared sequence, the date, and the evidence link. Skip anything
   `/dispatch-closeout`'s crossing already wrote for a completion; never write it
   twice. Pass the `revision` you read, so a concurrent change is refused rather
   than clobbered.
6. Re-running this step must not duplicate anything: the provider's writes are
   idempotent, and a terminal record that already exists is a no-op.

If the register write succeeds but an external half fails, a recovery record is
written under `Virtuoso/.recovery/`. Surface it; do not paper over it.

Return to SKILL.md A.4b.

## A.4b Absorb held plans that already ran

An `executed` entry ran ad hoc and was closed out; it becomes a completed register item
now. For each `executed` entry, per `HB-<n>` item it closed out:

1. **Create the register item** through `create-item`, with an identifier in the
   register's own scheme. Give it the title, the effort (the size word, and the hours
   where the register carries `effort_hours`), and `notes` reading
   `origin: held plan <entry> (HB-<n>)`. Use the mutation handshake for an external
   register, as in D.5.3.
2. **Record its completion by invoking `/dispatch-closeout`'s recording crossing**
   (its *Held plans* section). Do not write the terminal ledger yourself: that ceremony
   is the ledger's writer. It appends the terminal record and closes the item, using
   the close-out, date, and result the entry's `executed` row names, and nothing is
   re-verified or re-taught.
3. Add its one-line entry to the roadmap's completed summary, citing the entry.
4. Record the absorption, naming what it became:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor roadmap-review holding --record <entry> --state absorbed --note "as <ITEM-ID> (completed)" --apply

A run that stopped partway returns its entry to `planned`, and the trail note names the
items that did close out. That entry is absorbed in two halves. The closed-out items take
the steps above, using their own close-outs. The rest go to C.3 as queued items. Record
the entry's absorption once, naming every item it became.

Return to SKILL.md A.5.
