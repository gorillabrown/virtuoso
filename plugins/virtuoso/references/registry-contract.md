# The Governance Registry Contract

Every Virtuoso ceremony resolves documents, work items, and permissions through
the project's registry. This file is the contract. It is the same for every skill.

## One authority

`Virtuoso/workspace-layout.json` — the **machine manifest** — is the authority.
`Virtuoso.Governance.Readme.md` — the **human registry** — is a synchronized view
of it with protected user sections. When the two disagree, that is a *diagnostic*,
never a reason to overwrite either (redesign item 13).

The manifest declares its own `schemaVersion` and `pluginCompatibility`, so a
plugin that cannot serve a registry says so instead of reinterpreting it (item 14).

## Roles

Each entry under `roles` carries the full metadata set (item 15):

```jsonc
"workRegister": {
  "path": "docs/work-register.csv",      // OR "external": "notion:database/<id>" | "monday:board/1234567890"
  "provider": "csv",                     // markdown csv xlsx jsonl json directory
                                         // snapshot connector issue-tracker database
                                         // external none
  "authority": "live",                   // live terminal mirror report evidence
                                         // archive reference unknown
  "mutability": "read-write",            // read-write append-only generated
                                         // read-only immutable
  "owner": "roadmap-review",             // owning ceremony
  "allowedWriters": ["roadmap-review", "dispatch-closeout"],
  "validation": "csv-headers",
  "classification": "active",            // active | historical | unknown
  "origin": "authored",                  // authored | generated | unknown
  "generatedFrom": "",                   // source role, for derived artifacts
  "generatedBy": ""                      // registered generator command
}
```

**Presence** is computed at read time, never stored: `present`, `absent`,
`external`, or `unverifiable`.

### Authority classifications (item 16)

| authority | meaning |
|---|---|
| `live` | live operational authority |
| `terminal` | append-only terminal record |
| `mirror` | compatibility mirror generated from a live role |
| `report` | generated presentation output |
| `evidence` | historical evidence |
| `archive` | immutable archive |
| `reference` | informational |
| `unknown` | unclassified legacy role — not writable, not authoritative |

### Rules every ceremony follows

1. **Authority is declared, never inferred from a name** (item 6). A role called
   `sprintCatalog` is authoritative only if its `authority` says `live`.
2. **Resolve, never guess.** An unregistered role is an error naming the fix, not
   a fallback to a conventional path (item 87).
3. **A registered-but-absent target is reported**, never silently repointed at a
   similarly named file (item 20).
4. **Write only where `allowedWriters` names you**, and never to `archive`,
   `unknown`, `read-only`, or `immutable`.
5. **Generated artifacts are regenerated, never hand-edited** (item 58). Use the
   role's `generatedBy` command and verify the result against `generatedFrom`.
6. **External identifiers are valid registrations** (item 17). A board, project,
   database, or service id is never reported as a missing file.
7. **Project extensions live under `x-`** and are preserved verbatim across
   plugin upgrades (item 18).
8. **Archive paths cannot host live authority.** A terminal ledger is different:
   it may be registered beneath an archive directory when its authority is
   `terminal` and its mutability is `append-only`, because it is the durable
   completion record rather than live operational state. Terminal authority is
   still forbidden beneath backups, snapshots, and quarantine.

### Opt-in roles

These roles are supported but never assumed: `create` lays down none of them, and a
project registers each by adding its entry to the manifest when it first needs it.

| Role | Holds | Writers | Registered |
|---|---|---|---|
| `overlays` | project additions to shipped skills and agents (see *Project overlays*) | none (read-only) | when the project has something to overlay |
| `epics` | one directory per epic packet, `<yyyy-mm-dd>-<slug>/` | `epic` | when the project runs its first epic |
| `holdingBay` | one held plan per piece of ad hoc work, `<yyyy-mm-dd>-<slug>.md` (see *The holding bay*) | `storyboard`, `write-plan`, `virtuoso`, `dispatch-closeout`, `roadmap-review` | when the project storyboards its first piece of ad hoc work |
| `board` | the roadmap board, one generated page | `roadmap-review`, `dispatch-closeout`, `next-dispatch` | the first roadmap review (`generate_board --create`) |
| `boardComments` | row comments people leave on the board (JSON) | `roadmap-review` | with the board |
| `guardLog` | the cost guards' receipts for each dispatch (`jsonl`, append-only), copied in at close-out by `guards --copy`; hooks never write it | `dispatch-closeout` | when the project wants guard figures in its own tree |

`changeLedger` is not opt-in: `create` scaffolds it (`Change.Ledger.jsonl` beside the
lessons), and `changes` and `results` show an existing project the entry to add.

## The change ledger

When each change took effect, so `results` can split the work at it. One JSON line per
change, never rewritten; an undo is its own line (`"undoes": "CH-NNN"`):

```json
{"at": "…Z", "id": "CH-014", "action": "apply|undo", "kind": "guard|policy|lesson|standing-rule|plugin-version|manual",
 "subject": "guards.retry.enabled", "from": …, "to": …, "scope": {"hosts": [], "agents": []},
 "effectiveFrom": "…Z", "actor": "…", "note": "…"}
```

Writers by hand (`changes --record`, `--undo`): `roadmap-review`, `dispatch-closeout`,
`project-profile`. An **automatic** line is not a separate permission: it rides on an
operation authorized on its own role, inside it — `policy-set` writes one line per leaf it
changes (and puts the manifest back if the line cannot be written), `lessons --record-status`
one per status (dated with the record), and the next ceremony that writes the `closeOuts`
role a `plugin-version` line when the running version is new. Preflight and session start
never write it. Lines are appended under a lock; changes stack (undoing the latest puts back
the one before). Its authority is `evidence`, like the close-outs.

**`results [CH-NNN]`** compares the closed time logs that ended before a change with those
that started after it (until it was undone or replaced): cost per measured row — tokens,
and dollars unless `policy.cost.units` is `tokens`; for a lesson or standing rule, the share
of time on rows the first listing missed. Its policy: `results.minimum` (`activeDays` 3,
`closedLogs` 3, `measuredRows` 30 after the change before any verdict) and
`results.noEffect` (0.10: a smaller move either way is *no clear effect*). The baseline is 14
days, extended to 30 as the change ages; 3-, 5- and 7-day baselines give a range when they
disagree. A dispatch whose work straddles the change belongs to neither side and is named.
Across a change of price card, dollars are not compared and tokens carry the verdict. A
verdict's kind is the weaker of its two sides'.

A ceremony that needs an opt-in role the project has not registered stops and shows the
entry to add; it never falls back to a conventional path.

## Three distinct work roles (item 24)

| Role | What it is |
|---|---|
| `workRegister` | the **live** work register — the only place item status is true |
| `terminalLedger` | the **append-only** record of finished work |
| `sprintCatalog` / `sprintQueue` | optional **compatibility export** / generated report |

The local CSV catalog is optional (item 25): it may be the live register, a
generated mirror, or absent entirely.

### The terminal ledger's columns

A ledger's format is `policy.terminalLedger.format` (or the role's provider): `markdown`,
`csv`, or `jsonl`. Its fields are `recordId`, `itemId`, `completed` (a `YYYY-MM-DD` date),
`result`, `evidence` and `corrects`. A CSV or JSONL ledger may use the camelCase names or the
documented headers `Record`, `Item`, `Completed`, `Result`, `Evidence`, `Corrects`, in any case.
A ledger kept in the project's own columns names them in `policy.terminalLedger.fieldMappings`,
for example:

```json
"terminalLedger": {"format": "csv",
                   "fieldMappings": {"itemId": "Sprint Code", "completed": "Date Completed",
                                     "result": "Implementation Status",
                                     "evidence": "Close-Out File"}}
```

Two optional fields record effort: `effortEstimate` and `effortActual`, as durations
(`90m`, `1.5h`, `2h30m`; a bare number is hours) — headers `Estimate` / `Actual` (or the
camelCase names) in a CSV or JSONL ledger, and in a markdown ledger only when its own table
header carries *Estimate* and *Actual* columns after the six documented ones. A ledger
without them reads and appends exactly as before; `kpis` computes `effort-calibration` from
them. Close-out takes both from the dispatch's time log (`timing --summary --json`), never
from a typed runtime.

One optional field records size: `effort`, the item's size word on the effort scale
(`xs` … `xl`) exactly as the register held it at close-out — not a duration, and kept apart from
*Estimate* and *Actual*. Its header is *Effort* (or `effort`), or the column
`fieldMappings.effort` names, in every format; a markdown ledger reads it only when its own
table header carries the column. `record-completion` writes it from the register item.
Pace converts it through `policy.roadmap.effortScale`. A ledger without the column reads
`effort` blank and appends exactly as before.

### The time log

A dispatch's rows and their measured working time: `Timing.<dispatch-id>.jsonl` in the
`closeOuts` role, one JSON object per line, append-only, written only through
`virtuoso_registry timing` by an actor that may write `closeOuts`. Every event has `event`
and `at` (UTC, `YYYY-MM-DDTHH:MM:SSZ`, from the machine clock; no flag accepts a time or a
duration):

| event | carries | written by |
|---|---|---|
| `open` | `rows`: each `id`, `title`, `owner`, `tier`, `effort`, `item`, `parallel`, optional `kind` and `estimate`, the optional fields below, and the `predicted` minutes and `basis` timing priced | `--open --rows-file` |
| `add` | one or more such rows, numbered after the last, and `origin` (`added`, `review` or `audit`; a log without it reads `added`), shown as `+N`, `RN` or `AN` | `--add --rows-file` (`--origin`) |
| `start`, `resume` | `row`; optional `model` and `host` | `--start N`, `--resume N` (`--model`, `--host`) |
| `wait` | `row` and `reason`: `owner`, `approval`, `blocked` or `session-ended`; a wait without one is refused | `--wait N --reason R` |
| `end` | `row`, `result` (`done`, `blocked`, `cancelled`, or `split`), optional `tokens` (a whole number the host reported), and `evidence` (what proves the row, or `null` when `--end` was given none; an end written before evidence existed has no key); a `split` end also carries `rows`, the parts, each with `splitFrom` | `--end N` (`--tokens`, `--evidence`), `--split N --rows-file` |
| `park` | `row` and `reason` (words, required): a row not yet started that the run will not do; shown `◇` under *Parked*, and a `findings` entry at the close-out | `--park N --reason R` |
| `confirm` | `row`: the owner confirms a flagged row was real work | `--confirm N` |
| `timebox-reached` | `row`: a frontier row has worked its timebox; refused before the clock reaches it | `--timebox-reached N` |

A row's optional fields, recorded from the first run because an append-only log cannot
backfill them:
`class` (`calculable`, `repeat`, `frontier`), `model` and `host` (identities, never a
time; a row keeps those named at its start), `specRevision`, `group` (the parallel
group's id), and, on a frontier row only and both required, `timebox` (minutes) and
`onTimebox` (the action when it is reached). A frontier row is never estimated: it is
priced at its timebox, basis `timeboxed`. `splitFrom` is written only by `--split`.
Writers refuse a malformed value. Readers show a field a row does not carry, including
every field of a log written before these existed, as `not recorded`.

A row's working time is end − start − waits. A row missing its start or end, or ended
before it started, is *not measured*. A row priced by `kind` uses the median of at least 3
measured rows of that kind, else of its tier and effort, else its `estimate` (`estimated`).
A row measured at over 3× its prediction is flagged `possible unseen wait` and kept out of
pricing until confirmed. `timing --summary` gives the close-out's table and, with `--json`,
`estimate` (the first listing's predicted total) and `actual` (the measured working total),
both over non-parallel rows, as durations the ledger reads. `--item` limits it to one item's
rows (a log whose rows name no item is one item's run). `complete` is false when a row that
ran has no measured time; the ledger then takes neither total. Flagged time stays in the
Actual, `total-error` and `added-share`; only `row-error` and pricing leave it out.
The table names each row's *Model* (the one its `start` named) and *Effort* (its own, else
its tier's). With `--json`, `byModelEffort` lists each (model, effort) pair's measured rows
and their median actual ÷ predicted, `not computable` below 3 rows; rows whose log recorded
no model are skipped and counted in `skippedNoModel`, never refused. The table's last column
is each row's *Evidence*; parked rows are listed under it, and `--json` carries them as
`parked` (`id`, `label`, `title`, `reason`).

`timing --status` opens with the counted header `[D/N ✓ · R ■ · X ✗ · O □ · P ◇]`: only a row
ended `done` is ✓; blocked, cancelled and split rows are ✗. `--status --compact`, past 12
rows, prints the header, every row not done and the last 3 done. `timing --check` reads the
log against its own promises and is read by its exit code: 0 clean; 1 with findings — a
row number used twice, a row ended `done` whose end carries `evidence: null`, a parked row
without a reason, a row still running or waiting, or a log that cannot be read; 2 for a
usage error (no `--dispatch`, no `closeOuts` role, a flag `--check` does not take) or no log
for the dispatch. A log whose rows have all ended or been parked counts as closed.

Every other column is kept, untouched. A mapped field is found by its mapped header and nowhere
else. An append lays its row out under the file's own header and is refused, naming the missing
columns, when the file has no column for `itemId`, `completed` or `result` — a record is never
written under the wrong header.

## Working through providers

Never open a work register file directly. Ask the provider layer:

```
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> provider
python <plugin>/scripts/virtuoso_registry.py --root . items
python <plugin>/scripts/virtuoso_registry.py --root . next
python <plugin>/scripts/virtuoso_registry.py --root . combine --items <ID> <ID> ...
python <plugin>/scripts/virtuoso_registry.py --root . kpis
python <plugin>/scripts/virtuoso_registry.py --root . review --date <YYYY-MM-DD>
python <plugin>/scripts/virtuoso_registry.py --root . repo --expect <paths>
python <plugin>/scripts/virtuoso_registry.py --root . deps
python <plugin>/scripts/virtuoso_registry.py --root . protected
python <plugin>/scripts/virtuoso_registry.py --root . recovery
python <plugin>/scripts/virtuoso_registry.py --root . overlays
```

All of those are queries: none of them creates a directory, seeds a document, or heals
anything as a side effect. The commands that write say so explicitly — `snapshot`,
`closeout --prepare`, `create-item`, `policy-set --apply`, `mutation-plan`,
`mutation-confirm`, and `mutation-abandon`.

`next` returns the first eligible item that is not in flight, with `inFlight` (the items
already in flight) and `missingPrerequisites` (each active item's prerequisites the
register does not hold) beside it.

`policy-set` writes the **declaration** half of a project rule. It runs on the same
transaction `repair` does: the candidate registry is validated before anything is touched,
the manifest is backed up, and a registry that would not reload cleanly is rolled back. It
refuses a key the plugin does not document, because a key no ceremony reads is
configuration that looks live and is inert.

```sh
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> \
  policy-set rubric.extensions --value-json '["db-migration"]' --apply
```

**Negotiate capabilities before you plan work** (item 28). A provider declares
which of these it supports: `list-active`, `read-sequence`, `read-status`,
`write-status`, `read-prerequisites`, `read-effort`, `store-spec-link`,
`record-completion`, `next-eligible`, `create-item`. If a ceremony needs a
capability the selected provider lacks, say so up front and stop — do not start
and fail halfway.

### Field and status vocabulary

Both are project configuration (items 26, 27). A project maps its own column
names in `policy.workRegister.fieldMappings` and its own status words in
`policy.workRegister.statusMappings`. The canonical statuses the plugin reasons
in are `queued`, `in-flight`, `blocked`, `completed`, `dissolved`, `superseded`,
`unknown`; the literal words "Queued", "In Flight", "Full Spec" are defaults, not
requirements.

**Migration note (1.15.0): `lane` is now `workstream`.** Each item may also carry a
`deliverable`, and `policy.roadmap.workstreams` lists
`{id, name, purpose, deliverables: [{id, name, purpose}]}`. A deliverable id under two
workstreams is a policy problem. For one release the old names still work. A
register column named `Lane` reads as `workstream` and is never renamed in the
project's file. A `fieldMappings` key `lane` maps to `workstream`, and one that names both
`lane` and `workstream` is refused. `roadmap.lanes` is read with a `policy-renamed` warning,
and `combine --lane` works with one deprecation line on stderr. The rule anchor ids
`lane-declaration`, `merge-through-slot` and `lane-concurrency` are unchanged, so an
overlay that cites them still resolves.

**Proposing and applying a structure (1.15.0).** `structure --propose [--json]` is
read-only. It proposes workstreams and deliverables from the active items, or, once a
structure is approved, a place for each unassigned item plus split and merge suggestions.
`structure --apply --file <approved.json>` writes the owner-approved structure. It writes
`roadmap.workstreams` and `roadmap.hierarchy` through `policy-set`, then each assigned
active item's `workstream` and `deliverable`, as ids. A local register is written through
the provider's `assign(item_id, workstream, deliverable, *, revision)`, which needs
`write-status`, checks the revision, and is idempotent. For an external register it
returns one `set-status` mutation plan per item. When the approved file assigns items
and the register serves no column for either field, it stops before any write, policy
included, and names the missing columns. For an external register that means a field
the snapshot lacks or `policy.workRegister.fieldMappings` does not name. Finished items
are never touched. `structure --propose` runs the same check, read-only, and reports it as
`registerColumns`: `ready`, the `missing` fields, and the `fix`.

**Adding the workstream and deliverable columns.** Run this once per project, before the
first structure is approved:

1. Add two plain-text columns, `Workstream` and `Deliverable`. Existing rows may stay
   empty.
   - CSV or Markdown table: add both to the header row.
   - Spreadsheet: add two header cells on the register's sheet.
   - Connected tool (a database, board or tracker): add two text properties or fields,
     in the tool or through its connector.
2. Map them. A local register whose headers read `Workstream` and `Deliverable` needs no
   mapping. An external register needs both named. Write the current
   `policy.workRegister.fieldMappings` with the two added
   (`"workstream": "Workstream", "deliverable": "Deliverable"`):
   `virtuoso_registry --root . policy-set workRegister.fieldMappings --value-json '<mappings>' --apply`.
3. For a connected tool, refresh the snapshot: read every row, with both new columns, and
   import it (*Refreshing a connector-backed register's snapshot*).
4. Run `structure --propose` again. `registerColumns.ready` is now `true`.

### Provenance and honesty

- Every derived metric states the provider, source, snapshot time, and fields it
  came from (item 29).
- A metric whose inputs are missing is reported as **not computable** with the
  missing inputs named. It is never approximated (item 30).
- A snapshot read offline is labelled with its age and flagged stale past the
  configured window (item 31).

### Refreshing a connector-backed register's snapshot

A board, tracker, or database register is read through the snapshot role
`policy.workRegister.snapshot` names, stale after `policy.workRegister.staleAfterHours`
(24 by default). The host refreshes it; the plugin builds it. **One contract serves
every tool:** read the register with whatever connector the session has, write the rows
to a file keyed by the register's **own** column names, then import them:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . snapshot --import <rows.json> \
  [--taken-at <ISO time of the read>] [--parent-column <column>] [--json]
```

The rows file is a JSON list of row objects, or `{"takenAt": "<ISO time>", "rows": [...]}`.
A cell may be text, a number, a list (prerequisites), or an object with a `text`,
`name`, `id`, or `value` field; anything nested deeper, the session flattens to one of
those. Two conversions, for illustration:

- A **database** read (a page per item, a property per column): write
  `{"Item ID": "ABC-7", "Name": "Export to CSV", "Status": {"name": "In progress"},
  "Depends On": ["ABC-3"]}` — the status select keeps its `name`, the relation becomes a list.
- An **issue-tracker** read (an issue per item, fields by name): write
  `{"Key": "ENG-12", "Title": "Retry webhooks", "State": "Todo", "Order": 4,
  "Size": {"value": "m"}}` — each field under the column name the mappings use.

An item with no prerequisites gets `[]`, an empty cell, or a placeholder (see *Depends
On* below).

The import:

- maps each row through `policy.workRegister.fieldMappings` and `statusMappings`,
  exactly as a local CSV row is read;
- keeps **subitems** out of the work list. A row whose parent column holds a value
  (`Parent`, `Parent Item`, `parent_id` and similar, or `--parent-column`) is part of
  its parent card, such as an owner decision, and is never a card of its own. Include
  subitems only with their parent reference, or leave them out;
- skips a row with no identifier, refuses two rows under one identifier, and names
  every status outside the project's vocabulary, because no ceremony can read one;
- stamps the read time: `--taken-at`, else the file's `takenAt`, else now. A time
  must carry a UTC offset;
- writes the snapshot role, and nothing else. It refuses a role whose provider is not
  `snapshot`, or that is live, terminal, evidence, archive, immutable, or append-only.
  Without a snapshot role, `--out <path>` names the file.

A snapshot's reader applies the same subitem rule to a snapshot another builder
wrote: an item carrying `parent` is not a card.

**A convenience: a connector's raw page imports as it came.** The rows file above is
the way for every tool. A connector that keys cells by column **id** (an items page
whose `items[]` carry `column_values`) can skip the conversion:
save the page (or a list of every page) and the board's column list, and import both:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . snapshot --import <page.json> --columns <columns.json> [--taken-at <ISO time of the read>] [--json]
```

`--columns` takes a list of `{id, title}` objects, or the connector's board information
(an object whose `columns` or `board.columns` is that list). Each cell is read under its
column's title, so the same mappings apply; the item's name fills the title, its group's
title the group, and `providerId`, `revision` and `url` ride along in `extra`. The import
refuses a raw page without `--columns`, a page set whose last page says
`pagination.has_more: true` (a partial read never passes for a full one), and a page whose
`board.id` is not the board the registered `workRegister` names. Every import of a raw page
reports **column drift**, one `[DRIFT]` line each (and `missingColumns`,
`unmappedColumns` in `--json`): a declared `fieldMappings` column the board no longer has,
and a board column nothing maps, which is left out of the snapshot. It still exits 0;
fix `policy.workRegister.fieldMappings` before any `mutation-plan` writes a missing
field. Title-keyed rows remain the fallback for any other shape.

A *Depends On* placeholder cell (`None`, `-`, `—`, `n/a`, in any case) means no
prerequisite, for imported rows and local CSV rows alike.

**Moving the register to another tool** is `virtuoso_registry move-register`: a preview
that writes nothing, `--plan --apply` (one move record; create instructions for a tool,
rows written for a local target), `--confirm` per created item, and `--finish`, which
compares the new register's rows with the record and only then repoints `workRegister`
(the last write, with a manifest backup). History is never touched; an interrupted move
stays listed by `recovery`. The `virtuoso-init` skill walks it.

Refresh at three points: before `mutation-plan --operation create-item`, at roadmap
review, and at close-out.

**A stale snapshot is refreshed before it is acted on.** `next` and `items` print
`[STALE]` with the age; a ceremony that is about to name the head of the belt, or
check a combination for an epic, refreshes the snapshot first. When it cannot, it
reports the external-register finding as a gap, with the age, and does not treat
what it read as the current state.

### Mutations

- **Optimistic concurrency** (item 32): read the item, keep its `revision`, pass
  it back on write. A changed item is refused, not clobbered.
- **Idempotent** (item 33): re-running a close-out never duplicates a terminal
  record or repeats an external status change.
- **Partial failure** (item 34): if local files commit but the external register
  update fails, a recovery record is written under `Virtuoso/.recovery/` naming
  exactly what remains. Check it with `virtuoso_registry.py recovery`.
- **External registers are mutated by the ceremony, not the plugin.** The
  provider advertises mutation capabilities only to an authorized writer, then
  returns a structured instruction containing the expected revision and an
  idempotency key. Planning opens a durable recovery record. The ceremony
  executes the instruction with the host's connector and calls `confirm()` with
  the result; success resolves the record, while failure or interruption leaves
  the exact remaining work visible. Direct Python mutation methods still reject
  the write because they cannot impersonate the host connector.

For connector-backed work registers, use the supported handshake rather than
crafting an untracked mutation:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> mutation-plan \
  --operation set-status --item <ID> --fields-file <fields.json> --revision <REVISION> --json
# execute the returned instruction with the host connector, then read the item back
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> mutation-confirm \
  --recovery-id <RECOVERY-ID> --succeeded --actual-revision <NEW-REVISION> --json
```

- **Send one plan per connector call.** Each connector call carries exactly one planned
  mutation. Several changes sent in one call leave no record of which landed.
- **Read back before every confirm**, not only after a creation. The read-back, not the
  connector's reply, says what landed.
- **Some fields landed:** confirm `--partial --written FIELD[,FIELD…]`. The record notes
  `partial: {written, unwritten}` and stays outstanding. A later plan for the same item
  covering only the unwritten fields supersedes it (`supersededBy`) and resolves it with
  outcome `superseded`.
- **A plan that will not be executed** — planned against a stale snapshot, or no longer
  wanted — is closed with `mutation-abandon --recovery-id <RECOVERY-ID> --reason <TEXT>`.
  The record resolves with outcome `abandoned` and the reason. Nothing is sent.
- **Fields come from a file.** `--fields-file <path>` reads UTF-8 JSON, which no shell
  quoting can damage; `--fields-json` remains for simple values. Give one, not both.
- **Confirm by recovery id.** The record supplies the operation, item and idempotency
  key; any of `--operation`, `--item`, `--idempotency-key` given must match it, and a
  mismatch is refused, naming the field.
- **A field the register has no column for is refused at planning.** When
  `policy.workRegister.fieldMappings` is declared, a canonical field it does not name
  (`id` excepted) cannot land on the board, so the plan names it and stops.

A resolved record carries its `outcome` — `succeeded`, `abandoned`, or `superseded` (a
later plan replaced it; `detail.supersededBy` names that plan). A record resolved before
outcomes were recorded reads as `succeeded`, or as `superseded` when it names a
`supersededBy`.

### Bringing a new item into existence

A specification on disk is not a work item. Until the live register carries a row
for it, no ceremony can queue, sequence, or dispatch it — and the act that creates
that row is governed exactly like the acts that change it. `create-item` is the
registered operation; a connector's raw "create" is never called outside it.

- **Absence is the concurrency guard.** A creation has no revision to compare. It
  is planned only against a snapshot that is present and not stale, and only when
  the id is absent from that snapshot — terminal items included, because an
  identifier that has ever been retired is not reusable.
- **Creation is not an update.** Re-issuing an identical creation is a no-op that
  returns the existing item; a creation whose fields disagree with an existing item
  is refused by field name (`duplicate-item`). Change an existing item through
  `set-status` / `store-spec-link`.
- **A new item enters the pipeline.** `status` and the specification state default
  to the project's own spelling of `queued` and `stub`; a status word outside the
  project's vocabulary is refused, because an item no ceremony can read is invisible
  to all of them.
- **Creation is separately authorized.** `policy.workRegister.creators` names who
  may create; unset, every writer in the role's `allowedWriters` may. A writer
  entitled to change items is not thereby entitled to bring new ones into existence.
- **The trail holds idempotency across the refresh gap.** A confirmed creation is
  never planned twice under the same idempotency key (default
  `create-item:<register>:<id>`), even before the snapshot shows the new item. A
  plan whose previous attempt was confirmed *failed* may be retried; the retry's
  instruction tells the host to verify nothing was created before executing, and
  the superseded record is resolved with a pointer to its replacement.
- **The crossing ends with a readable item.** Confirm with the identifier and
  revision the external system assigned (`--provider-id`, `--actual-revision`),
  then refresh the canonical snapshot (`snapshot --import`, below) and check that
  `recovery` is empty.

A local register creates directly — this is a write:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> create-item \
  --item <ID> --fields-json '{"title": "...", "sequence": 42, "effort": "M"}' --json
```

An external register uses the same handshake as every other mutation:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> mutation-plan \
  --operation create-item --item <ID> --fields-file <fields.json> --json
# the plan carries expectedAbsent, snapshotTakenAt, projectFields (the project's own
# column names), defaultsApplied, preconditions for the host, and postconditions.
# Execute it with the host connector; read the created item back.
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> mutation-confirm \
  --recovery-id <RECOVERY-ID> --succeeded --provider-id <PROVIDER-ITEM-ID> \
  --actual-revision <REVISION> --json
# then refresh the canonical snapshot and confirm nothing is outstanding:
python <plugin>/scripts/virtuoso_registry.py --root . recovery
```

## Project overlays

A project that needs a shipped skill or agent to behave differently registers an
**overlay** instead of forking the file. The `overlays` role points at one
directory; inside it, a file at the *same relative path* as a shipped file carries
that project's additions:

| shipped file | its overlay |
|---|---|
| `skills/<skill>/SKILL.md` | `<overlays>/skills/<skill>/SKILL.md` |
| `agents/<Agent>.md` | `<overlays>/agents/<Agent>.md` |
| `references/<file>.md` | `<overlays>/references/<file>.md` |

A reference is read by whichever skill follows a pointer to it, so a skill applies its own
overlay *and* the overlay of every reference it is sent to.

```jsonc
"overlays": {
  "path": "Virtuoso/overlays",
  "provider": "directory",
  "authority": "reference",
  "mutability": "read-only",     // no ceremony writes a project's overlays
  "allowedWriters": [],
  "validation": "exists",
  "classification": "active",
  "origin": "authored"
}
```

Rules:

1. **Optional, and opt-in.** `create` does not register the role or lay down the
   directory. An unregistered role, an absent directory, and no matching file all
   mean the same thing: proceed on the shipped file alone.
2. **Read-only.** The role is registered `read-only` with no `allowedWriters`, so
   rule 4 above already refuses every ceremony write to it. Overlays are the
   project's files; the plugin reads them and never edits them.
3. **Case-exact everywhere.** Lookup compares each path segment against the names
   the filesystem reports, not against a case-folded match. `skills/Epic/SKILL.md`
   never stands in for `skills/epic/SKILL.md` — a mismatch is reported on every
   platform instead of working on one and vanishing on another.
4. **Additive, and bounded.** An overlay adds to a shipped instruction and wins on
   conflict, with one exception: it may not loosen a shared-contract safety rule —
   registry resolution, read-only preflight, write permission, git safety,
   provenance, or the issue contract. Anyone who can write the project folder can
   write an overlay; without that floor, so could anyone who can switch off the
   plugin's own guards.
5. **Only `skills/`, `agents/`, and `references/` are addressable.** An overlay elsewhere
   under the directory mirrors nothing, is never applied, and is reported.
6. **`references/registry-contract.md` cannot be overlaid.** This file defines what an
   overlay is and what it may do, including rule 4 above. A project able to overlay it could
   rewrite the rules governing its own overlay. The exclusion is a bootstrap argument rather
   than a judgement about the file, and it is the only one: every other shipped reference —
   the readiness rubric, the git policy, the actor vocabulary, the workflow reference — is a
   project's to extend.

Resolve them — both are read-only queries, and neither creates the directory:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . overlays
python <plugin>/scripts/virtuoso_registry.py --root . overlays --for skills/<skill>/SKILL.md
python <plugin>/scripts/virtuoso_registry.py --root . overlays --scaffold
```

`--scaffold` prints an overlay skeleton and **writes nothing**. With `--for`, the output is
exactly that file's content, so the operator's own redirect is the whole write. The plugin
never writes a project's overlays, and there is no flag that makes it: that sentence has no
exception clause, and scaffolding was not worth adding one.

A scaffolded section carries a placeholder, and the pairing check reports it as
`pairing-body-stub` until real prose replaces it. A remedy that satisfies the gate it was
produced by is not a gate, so saving the skeleton does not clear the warning that produced it.

Findings are informational or warnings, never errors: an overlay problem is the
project's to fix and must not turn a working registry into one that reports
`repair-needed`, because repair has nothing to propose for a file the project owns.

| finding | meaning |
|---|---|
| `overlays-absent` | the role is registered; the directory does not exist yet |
| `overlay-orphan` | the overlay mirrors no shipped file and is never applied |
| `overlay-case-mismatch` | it differs from a shipped file only in case |
| `overlay-outside-mirror` | it is not under `skills/`, `agents/`, or `references/`, so nothing addresses it |
| `overlay-not-overlayable` | it mirrors a shipped file that may not be overlaid (rule 6) |
| `overlay-unreadable` | the file's bytes are not decodable as text; re-save it as UTF-8 |
| `overlays-external` | the role registers an external identifier; overlays are read as files |
| `overlays-writable` / `overlays-has-writers` | registered writable; register it read-only |
| `pairing-body-missing` | a policy key declares an id that no overlay section defines |
| `pairing-body-stub` | the section exists but is empty, or still the scaffold's placeholder |
| `pairing-mirror-unregistered` | ids are declared but no `overlays` role exists to hold their bodies |

### Declarations and bodies

A project-specific rule has two halves. The **declaration** — a registry role or a `policy.*`
key — is typed and validated, so the machinery can count it and gate on it. The **body** is
prose in an overlay, which only an agent reads. A declaration with no body is an identifier
no ceremony can apply; a body with no declaration is prose no gate consults.

Where the plugin can check the pair, it does. `policy.rubric.extensions` declares readiness
extension ids; their bodies are sections in the overlay of `references/readiness-rubric.md`,
and a declared id with no section is reported at session start.

The corollary matters as much as the rule: **if a project constraint can be a policy value or
a mechanical check, make it one.** An overlay is prose applied at the agent's discretion; a
policy value is enforced. A dispatch buffer is a value. "Migrations need a data-loss analysis"
is prose. Do not ship the first as the second because prose is easier to write.

## Deadlines and pace

A deadline is a declaration with a body, like any other project rule. The **declaration** is
`policy.roadmap.deadlines.<id>`: a date and who set it, written through `policy-set`. The
**body** is the roadmap heading that defines the finish line the date is for.

```json
"roadmap": {
  "deadlines": {
    "game-build": {"date": "2027-01-01", "owner": "Evan", "label": "Overall game build",
                   "finishLine": "Finish Line C",
                   "scope": {"field": "group", "values": ["B1", "B2", "B3", "C"]},
                   "recorded": "2026-09-22"}
  },
  "pace": {"trailingWeeks": 4, "tolerance": 0.1}
}
```

| Field | Required | Meaning |
|---|---|---|
| the id | yes | letters, digits, `-`, `_`; one segment of a dotted key, so never a dot |
| `date` | yes | `YYYY-MM-DD`, a real calendar date; due by the end of that day |
| `owner` | yes | who ruled. A date nobody owns is not a ruling |
| `label` | no | the name shown; the id when absent |
| `finishLine` | no | the roadmap heading that defines done — the body |
| `scope` | no | `{"field": ..., "values": [...]}`: which items count. Absent means every item |
| `recorded` | no | the date it was set or last moved |

Any other field is refused: a misspelled field is stored and ignored, which reads as configured
and is not. `policy-set roadmap.deadlines.<id>` adds or replaces one deadline,
`policy-set roadmap.deadlines.<id>.date` moves one date, and `--value-json null` on an id
withdraws it — none of them restates the others. Every `--apply` reads the value back from the
manifest on disk and says so.

**One authority.** The date lives in the manifest and nowhere else. The roadmap's finish-line
section defines what done means and points at the policy for the date; reviews, briefings and
assessments cite the computed pace *as of* their own date, which is history rather than a second
authority. Memory, charters and boards point at the policy instead of repeating the date, so
there is one place to move it and nothing to drift. `finish_line:` in a roadmap is a marker that
discovery uses to recognize a roadmap; it is not a date and nothing reads a value from it.

**The plugin never reverts a successful `policy-set`.** The write restores its backup only when
the write itself or the re-validation after it fails, and it says so. A project that runs its
own guard over the manifest should let `policy-set` writes through; each leaves a backup set
labelled `policy-set` that names the ceremony which asked.

### What pace computes

`kpis` reports pace against every declared deadline, in date order, from the same snapshot as
its other figures. It is computed as of the **snapshot's** date, never the reader's clock.

- **Scope** — every item in the register, or the items whose `scope.field` (canonical `id`,
  `title`, `workstream`, `deliverable`, `group`, `effort`, `branch`, or a register column) holds one of
  `scope.values`, in any case. A scope that matches nothing is **not computable** — never met.
- **Remaining** — non-terminal items in scope, and their points through
  `policy.roadmap.effortScale`. **Blocked** — the canonical `blocked` share of what remains.
- **Required** — remaining ÷ weeks to the date, in items and in points.
- **Trailing** — distinct items completed in the last `policy.roadmap.pace.trailingWeeks`
  weeks, divided by that many weeks. It is the project's delivery capacity, not a per-scope
  rate. Completions come from the terminal ledger when one is registered (read through
  `policy.terminalLedger.fieldMappings`), with corrections
  applied and results read through `policy.workRegister.statusMappings`; only a project with no
  ledger uses the register's completion dates, and the two are never mixed. The output breaks
  the count down by the result words recorded, and lists what it excluded. Trailing points
  read each completion's effort from the ledger first and the register second.
- **Verdict** — per unit: `ahead` above the required rate by more than
  `policy.roadmap.pace.tolerance`, `on track` within it, `behind` below it. The headline is the
  worse of the two units and names the unit. `met` when nothing in scope remains; `overdue`
  when the date has arrived with work remaining. The order, worst first:

| verdict | meaning |
|---|---|
| `overdue` | the date has arrived and work in scope remains |
| `behind` | the trailing rate is below the required rate by more than the tolerance |
| `on track` | the trailing rate is within the tolerance of the required rate |
| `ahead` | the trailing rate exceeds the required rate by more than the tolerance |
| `met` | nothing in scope remains |

- **Projection** — the date the remaining work finishes at the trailing rate, per unit.

A figure whose inputs are missing is **not computable**, with the inputs named — a completion
source that holds no recorded completion at all (a board that keeps only live items, or a
ledger whose columns are not mapped), an undatable completion (append a correction that dates
it), an unsized item, a completed item that left the
register and whose ledger record carries no Effort (trailing points only), a scope that
matches nothing. Nothing is estimated, and nothing
silently becomes zero.

| finding | severity | meaning |
|---|---|---|
| `deadline-unanchored` | info | the deadline names no `finishLine`; pace is computed, but nothing defines done |
| `deadline-finish-line-missing` | warning | `finishLine` names a heading the registered roadmap does not have |
| `deadline-invalid` | warning | a hand-edited entry fails validation; `policy-set` refuses such an entry outright |

Deadline findings are never `error` severity and never change the registry status: the project
fixes them, and `repair` has nothing to propose.

## The learning loop: lessons

New work is done by the dispatch ceremonies; the plugin gets *better* at it only if what a
dispatch taught reaches the next specification. That path is standard practice, and each
of its three links is checked.

**Where a lesson lives.** The registered `lessons` role — append-only, `reference`
authority. One entry per lesson, under an identifier `<prefix>-NNN` where the prefix is
`policy.lessons.idPrefix` (`SRL` by default):

```
### <prefix>-NNN — Short title (ITEM-ID, YYYY-MM-DD)
**Verdict:** what was learned
**Evidence:** what happened, with numbers
**Recommendation:** the concrete change a future specification should make
**Applies to:** when it bears on future work
**Status:** Observation
```

A status is never edited in place: promoting, retiring, or superseding a lesson appends a
new entry under the same identifier whose field is its `**Status:**`, and the latest one
recorded is current. A lesson is **live** until a status beginning `Promoted`, `Retired`,
or `Superseded` is appended. `virtuoso_registry lessons [--open]` lists them.

**Which item a lesson came from.** The heading's `(ITEM-ID, date)` names it, and so may an
`**Item:** <ITEM-ID>` field in the entry. Those link it **by identifier**. A heading that
described the item in words instead cannot be corrected in an append-only catalog, so two
more links count, in this order:

- a **link record**, appended under the lesson's identifier; it carries no status, so
  the lesson's status is unchanged:

  ```
  ### <prefix>-NNN — link (ITEM-ID, YYYY-MM-DD)
  **Item:** ITEM-ID
  ```

  `lessons --record-link <prefix>-NNN --item <ITEM-ID> --actor <ceremony> [--apply]`
  appends it: previewed without `--apply`, refused for an actor the role's
  `allowedWriters` does not name, an unknown lesson, or an item that is not one
  identifier, a no-op when the lesson is already linked, and read back after;
- a link **by name**: every word of a word-built identifier appears in the heading's
  source, in any order and case (`checkout follow-ups epic` for
  `EPIC-CHECKOUT-FOLLOW-UPS`), or every word after its leading one when at least two
  remain. An identifier with a digit in it is a code, never a name. A link by name counts,
  and the check that relies on it warns (`lesson-linked-by-name`) and names the link
  record that makes it exact.

`lessons --item <ITEM-ID>` lists the lessons recorded from an item, and how each is linked.

**Three links, each checked.**

1. **Close-out records.** `dispatch-closeout` appends what the dispatch taught — or its
   report says `No new lesson — <reason>` — and records how the lessons its specification
   applied turned out. The crossing's verify step runs
   `lessons --check <report> --closeout --item <ID>`: a lesson the report names must be in
   the role (the append happened), or the report must give its reason. A report that fails
   is not a finished close-out.
2. **Specification applies.** Readiness check U9, *Lessons applied*, in the shared rubric:
   a specification names each live lesson that bears on it and the change it made, or
   states that no live lesson applies. `roadmap-review` reads the live lessons before it
   drafts and re-checks every existing dispatch-ready specification against lessons
   recorded since; `next-dispatch` checks the head item before it prints.
   `lessons --check <spec> --item <ID>` is the mechanical half; a live lesson the section
   leaves uncited is listed, so the author's judgement is made rather than skipped.
3. **Direction applies.** An `epic` charter carries *Lessons applied* before an unattended
   run begins, and an epic ends through `dispatch-closeout`, so its lessons reach the role.

`lessons --check` exits 0 when the check passes, 1 when it fails, 3 when there is no
`lessons` role to read. Its findings:

| finding | meaning |
|---|---|
| `lessons-section-missing` | no *Lessons applied* (specification) or *Lessons* (close-out) section |
| `lessons-section-empty` | the section cites no lesson and gives no reason (no live lesson applies; No new lesson — reason) |
| `lesson-unknown` | a specification cites an identifier no lesson carries |
| `lesson-not-appended` | a close-out names a lesson that is not in the role — the append did not happen |
| `lesson-closed-cited` | a specification cites a promoted or retired lesson; cite what it became (warning) |
| `lessons-not-cited` | live lessons the specification does not cite, listed for the author to confirm (info) |
| `lessons-item-section-missing` | `--item` names an item the document has no section for |
| `lesson-reason-unanchored` | a close-out's "No new lesson" reason names nothing it examined — no lesson, standing rule or item identifier — while the catalog or `policy.standingRules.ids` holds something to examine |
| `lesson-linked-by-name` | a close-out names a lesson whose heading names the item in words, not by identifier; it counts, and the message names the link record that makes it exact (warning) |

A close-out's `--item` may name several items, comma-separated: a combined epic's
close-out names its packet and every item it closes, and a lesson recorded from any of
them counts.

A lesson the close-out recorded and no specification applied was learned once and paid
for twice. That is the failure this loop exists to make visible.

### Keeping the catalog short: hygiene, candidates, status records

U9 holds every specification to every live lesson, so the catalog's value is its
shortness. Two read-only reports keep it short, and one command changes it — by appending.

- **`lessons --hygiene`** (`governance-sweep`) reads the catalog and every close-out
  report in the `closeOuts` role (`CloseOut.*.md`) and proposes: **merge** — live lessons
  that record one pattern (the same *Applies to*, or near-identical titles), kept under the
  first recorded and the rest superseded by it; **retire** — a live observation older than
  `policy.lessons.staleAfterDays` (default 180; 0 turns it off) that no close-out ever
  applied; **tidy** — a live lesson missing *Verdict*, *Evidence*, *Recommendation* or
  *Applies to*; **record** — a live lesson whose prose claims a status (`Promoted to
  SR-12`) that no status record carries, with the `lessons --record-status` command that
  records it; **repair** — an identifier reused for a second lesson. A field line may be
  written as a list item (`- **Status:** …`) and reads exactly as the plain form; an
  existing catalog migrates in one sweep, by appended status records only.
- **`lessons --candidates`** (`roadmap-review` D.4) lists the lessons that have earned a
  decision: **promote** a pattern that recurred (the second occurrence) or a lesson applied
  and held in two close-outs; **revise or retire** one that did not hold in two. A
  close-out's *Lessons* section records each applied lesson on a line with `held` or
  `did not hold`; that line is what these counts read.
- **`lessons --record-status <ID> --status "<status>" --actor <ceremony> [--item <ID>]
  [--date <date>] [--apply]`** appends one status record under the lesson's identifier —
  `Promoted -> <destination>`, `Retired — <reason>`, `Superseded -> <ID>` (a recorded
  lesson other than itself), or `Observation`. It previews without `--apply`; refuses an
  actor the role's `allowedWriters` does not name, an unknown or already-closed lesson,
  and a status that says nothing; and reads the record back as the lesson's current status.
  It never edits an earlier entry.

Merging is two records: the survivor stays, each duplicate is superseded by it. A
promotion is a status record plus the rule written where `policy.standingRules.source`
says rules live.

### The buffer, as a gate would see it

`kpis` carries `dispatch-buffer-ready` beside `dispatch-buffer-filled`. *Filled* counts the
buffer's items whose register row says the specification is written; *ready* counts those
whose specification a dispatch gate would pass — found (inline in the roadmap under a
heading naming the item, or at the item's `spec_link` when `policy.roadmap.specStorage` is
`files`) and passing U9. It is *not computable* when there is no lessons role, when
specifications are external, or when a written item's specification cannot be located —
naming the items.

### Loop-health metrics

`kpis` carries a `learning` group beside pace: six figures on whether the loop is
improving, from the catalog and the close-out reports, with their sources and as-of date.
Each is *not computable*, naming the missing input, when the sources cannot support it —
never zero.

| metric | definition | not computable without |
|---|---|---|
| `live-count` | live lessons | a recorded lesson or a close-out |
| `lesson-yield` | lessons recorded per close-out report, and how many reports said "No new lesson" | a close-out report |
| `held-rate` | of the applied-lesson outcomes close-outs recorded, the share that held | a close-out recording an outcome |
| `promotion-rate` | the share of lessons whose status is `Promoted` | a recorded lesson |
| `time-to-apply` | median days from a lesson's date to the first dated close-out that applied it | a dated lesson applied in a dated close-out |
| `repeated-trap-rate` | the share of lessons that record a pattern already recorded (the merge groups) | two recorded lessons |
| `effort-calibration` | the median of actual ÷ estimate over terminal records carrying both as durations; above 1 the project under-estimates. `effort-levels` sizes by it when computable | three records with both |
| `row-error` | the median of \|actual − predicted\| ÷ predicted over the measured rows of closed time logs (flagged rows left out) | three closed time logs |
| `total-error` | the same over each closed log's sequential totals: actual against the first listing's estimate | three closed time logs |
| `added-share` | the share of working minutes spent on rows added after the first listing — what the listing missed | three closed time logs |
| `row-error-by-model-effort` | `row-error` per (model, effort) pair, as `{"<model> {<effort>}": value}`; rows with no model recorded are skipped and counted in the unit | three measured rows of one pair, in closed time logs |

Read together over successive reviews: a flat or falling live count with a positive yield,
promotions above zero, a high held rate, a falling repeated-trap rate. Any one figure can be
gamed; the set is expensive to game, because yield without holds, or holds without
promotions, shows.

## Figures and cost

**Every figure says what kind of number it is.** `kind` is `measured` (read from a log, a
transcript or host-reported usage), `inferred` (derived from measured data by a stated
rule) or `estimated` (assumes how something would behave — a prediction, a rate not yet
recorded on that day); `basis` is the calculation in one line, and `unit` the unit alone.
JSON carries both; text shows the kind beside each figure, and `--why` (on `kpis`,
`timing --summary`, `cost`, `results`) prints how each was calculated and what it assumes.
`confidence` is a level, never a percentage. A figure whose inputs are missing is *not
computable*, naming them.

**`cost [--dispatch <id>] [--last N] [--why]`** prices work at API prices (on a subscription,
a measure of the work, not the bill). A dispatch's transcript is found through its binding —
recorded by the pre-tool hook when its session runs `timing --dispatch <id>` with a row verb —
never by guessing; without one, transcript figures are not computable, unless the time log
carries a `cost` event the backfill wrote. Its **row cost** is the calls of the workers whose
spawn names the row (`row N`, or a task name starting `row_N_`); everything else in the top-level
session between the log's first and last work stamp is **orchestration**. Prices come from
`references/model-prices.json` (dated cards per model; a call is priced at the card in force
on its day, one before the first card at that card and `estimated`), merged under the user's
`~/.virtuoso/prices.json`; a model with no card is not computable, never approximated.
**`policy.cost.units`** is `both` (default, `$1.30 (162K tokens)`), `tokens` or `dollars`; a
user default may be set in `~/.virtuoso/config.json`, which the project's value overrides.

**The backfill.** The next ceremony that writes the `closeOuts` role records, in each closed,
settled (24 h), unbound time log with no token count, a `cost` event — dispatch-level, tokens
`measured`, marked `backfilled` — from the transcripts the host still keeps: the sessions of
this project that worked a row of the dispatch inside its work. A log with none left is marked
*not computable* once; it is measured again only if its work later moves past the marked
window.

**`policy.guards`** switches the cost guards: `enabled` for all, and per guard `coldReturn`
(`minContextTokens` 50000, `minRewrite` 0.50 dollars, `minRewriteTokens` 50000,
`idleMinutes` 5), `retry` (`limit` 2 failures in one folder, the last within `withinMinutes`
30), `bigRead` (`bytes` 65536), `compactNudge` (`share`
0.75 of `windowTokens` 200000) and `weekly`, each with its own `enabled`. Setting any of them
through `policy-set` lands in the change ledger. **`guards --dispatch <id>`** lists the
receipts a dispatch's sessions kept (a hold counts as kept only if its step never came
again); `--tried` prints what it tried and dropped; `--context [--model <m>]` reads the
top-level conversation's context now from the bound transcript (read-only), and with a model
the reload a switch to it costs (`estimated`); `--copy --apply` (dispatch-closeout)
copies its receipts into `guardLog`.

## Findings

The `findings` role holds what a governance sweep, an adversarial review, or an agent
finds that is not yet a lesson — one append-only document, scaffolded by `create`
(`Findings.md` beside the lessons). An existing manifest without it stays valid; a
ceremony that would record a finding in a project without the role shows the entry to
add and says the findings exist only in its report.

```
### F-NNN — Short title (source, YYYY-MM-DD)
**Source:** governance-sweep / adversarial-review / <agent>
**Severity:** critical / major / minor / info
**Where:** path:line, or document § section
**Finding:** what is wrong, with the evidence
**Disposition:** open
```

A finding that carries a cost or a saving adds four lines: **Tier:** `FIX` (clear waste;
removing it leaves the work unchanged) / `TRY` (a likely saving that changes what the agent
does, shown `+` a figure) / `TEST` (a trade-off sized from the project's own runs, "up to" a
figure) — never added across tiers; **Confidence:** `high` / `likely` / `possible`, never a
percentage; **Kind:** `measured` / `inferred` / `estimated`; **Figure:** now → after. Shown
in a report, the same finding reads as one block:

```
<TIER>  <title> · <confidence>
        What happened   …
        Why it matters  …
        What to do      …
        now <figure>  ->  after <figure>   (<n> rows, <share> of the dispatch)   <kind>
```

A disposition changes only by appending a record under the same id —
`**Disposition:** fixed by <item or commit>`, `accepted — <reason>`, `lesson <prefix>-NNN`.
Writers by default: `governance-sweep`, `adversarial-review`, `virtuoso` (for the agents it
dispatches), `dispatch-closeout`, `roadmap-review`, `3rd-party-audit`. **Reader:**
`roadmap-review` B.3 reads every finding whose latest disposition is `open`, with the
previous review's lessons-applied — the set `virtuoso_registry review --date <YYYY-MM-DD>`
names as `previous`, latest by date, then run — and carries each into the plan.

## Dates

Every governance date is the UTC calendar date. The tooling generates its dates in
UTC: `kpis` as-of dates, deadline countdowns, the default `--date` of `lessons`,
`holding` and `review`, and every snapshot, recovery and time-log stamp. A date you
supply — `closeout --date`, `record-completion --date`, `review --date`, a heading you
write — is today's UTC date too; when unsure, read it from `review`'s `date`. Local time
appears only in human-facing clock lines — the `timing` header's estimated finish. A
session near midnight may therefore record the next calendar day; that is the date, not
a slip.

## Combining roadmap items into one epic

An epic is one epic-scale item marked `Path: epic`, or a **combination**: several items a
roadmap review already specified and placed, none epic-scale alone, run together as one
unattended run (`references/execution-paths.md`). Whether a set combines is checked, not
assumed:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . combine --items <ID> <ID> ... [--json]
python <plugin>/scripts/virtuoso_registry.py --root . combine --workstream <workstream> [--from <seq>] [--to <seq>] [--json]
```

It is read-only. It reads the register through its provider and each item's
specification where `policy.roadmap.specStorage` keeps it: inline under the roadmap
heading naming the item, or at the item's `spec_link` for `files`. The files an item
touches are the paths its *Edit sites* and *Staging plan* fields name: backticked
tokens with a slash or a file extension, and bare tokens with a slash. A bare file name
matches the longer path it ends, and a directory matches the files beneath it. It
returns:

- the **serial order**: every prerequisite in the set first, then, for two items that
  share a file, the one earlier in the register's sequence. Ties go to sequence, then to
  the order the items were named;
- the **workstreams**: groups with no prerequisite and no shared file between them, which may
  run side by side;
- every ordering **edge** with its reason, the **effort** in points (or *not computable*,
  naming the missing effort or scale entries), and the snapshot's provenance.

Exit 0 means combinable, 1 means a blocking finding stands, and 3 means the question
cannot be answered.

| finding | severity | meaning |
|---|---|---|
| `combine-item-unknown` | error | the identifier is not in the register |
| `combine-item-terminal` | error | the item is already completed, dissolved or superseded |
| `combine-item-blocked` | error | the item is blocked |
| `combine-item-in-flight` | error | the item is already being dispatched |
| `combine-item-stub` | error | the item's specification is not written (`full-spec`) |
| `combine-item-epic` | error | the item's entry declares `Path: epic`; it is chartered on its own |
| `combine-item-chartered` | error | an active charter in the `epics` role names the item (`item:` or `items:`) |
| `combine-prerequisite-outside` | error | a prerequisite is neither done nor in the set |
| `combine-cycle` | error | the prerequisites within the set form a cycle |
| `combine-single` | error | one item is not a combination |
| `combine-selection-empty` | error | the selection names no active item |
| `combine-snapshot-stale` | error | the register snapshot is stale; refresh it first |
| `combine-spec-unlocated` | warning | the specification could not be read; the item runs serially with every other |
| `combine-files-unlisted` | warning | the specification names no file; the item runs serially with every other |
| `combine-workstream-unmapped` | warning | a workstream selection, and the register serves no workstream field |

An item whose files are unknown is never assumed to touch nothing: an unknown overlap is
not a known absence. The judgement the command cannot make, such as two items changing
one interface through different files, is `epic`'s, and it records every ordering it
adds, with the reason, in the packet's plan.

A combination's charter lists its items under `items:`, in serial order, and its packet
identifier is `EPIC-` plus the slug in capitals. While the charter is active,
`next-dispatch` does not dispatch those items separately and `roadmap-review` does not
re-specify them. The close-out retires each one (`dispatch-closeout`, *Combined epics*).

## The holding bay

Work that arrives between roadmap reviews enters through `storyboard` (scoping, to a
draft stub) and `write-plan` (the full specification, with its slot in roadmap order),
and only the `virtuoso` skill executes it. Neither ad hoc ceremony writes the roadmap or
the live register — bringing work onto the roadmap is `roadmap-review`'s — so what they
produce waits in the `holdingBay` role: one Markdown file per piece of work, named
`<yyyy-mm-dd>-<slug>.md`,
copied from the storyboard skill's `held-plan.template.md` and marked
`<!-- virtuoso-held-plan v1 -->`. Items inside it carry provisional identifiers,
`HB-<n>`, never reused; the register assigns their real ones when a review absorbs them.

The file's **trail** is its state machine: a table under `## Trail`, one row per move
(`| date | state | by | note |`), appended through `virtuoso_registry holding --record`
and never edited. The last row is the current state.

| State | Recorded by | The entry must carry | Next |
|---|---|---|---|
| `storyboarded` | `storyboard`, `write-plan` | an alignment record whose verdict reads *Aligned* | `storyboarded`, `planned`, `absorbed`, `withdrawn` |
| `planned` | `write-plan`; `virtuoso` only out of `in-flight` | a `## Plan` with at least one `HB-<n>` specification; never epic-scale | `storyboarded`, `planned`, `in-flight`, `absorbed`, `withdrawn` |
| `in-flight` | `virtuoso` | as `planned` | `planned`, `executed` |
| `executed` | `dispatch-closeout` | as `planned`; the note names the close-out and its result | `absorbed` |
| `absorbed` | `roadmap-review` | a note naming the register item(s) it became | — |
| `withdrawn` | `storyboard`, `write-plan`, `roadmap-review` | a note giving the reason | — |

`write-plan` may record `storyboarded` over a plan: anything that changes what was agreed
goes back to the storyboard, and the plan is rewritten after it. Only the `virtuoso`
skill executes, so only it records `in-flight`. It may record `planned` only out of
`in-flight`, to hand back a run that stopped: it never plans. A trail row an earlier
release allowed stays valid history. In 1.11.0 `write-plan` recorded `in-flight`
itself, and `holding --check` still reads such a row as legal. A new row is held to the
table above. An entry that is neither
`absorbed` nor `withdrawn` is **open**, and the next roadmap review reconciles every open
entry that is not `in-flight`: it absorbs it into the roadmap or withdraws it. Nothing is
carried past a review.

```sh
python <plugin>/scripts/virtuoso_registry.py --root . holding --open        # what a review reconciles
python <plugin>/scripts/virtuoso_registry.py --root . holding --check <entry>
python <plugin>/scripts/virtuoso_registry.py --root . holding --next-id     # the next HB-<n>
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> holding \
  --record <entry> --state <state> --note "<one line>" --apply
```

The read side writes nothing; `--record` previews without `--apply`, and refuses an actor
the role does not name, a state that ceremony does not own, an illegal move, and a state
whose content the entry does not yet carry. No `holdingBay` role is exit 3 with the entry
to add, which also means nothing is held.

| finding | meaning |
|---|---|
| `held-marker-missing` | no `<!-- virtuoso-held-plan v1 -->` marker: not a held plan |
| `held-name-invalid` | the file is not named `<yyyy-mm-dd>-<slug>.md` |
| `held-entry-mismatch` | the *Entry* field disagrees with the file name |
| `held-size-invalid` | *Size* is not `single item`, `item set`, or `epic-scale` |
| `held-trail-missing` | no `## Trail` section |
| `held-unrecorded` | the trail has no row: the entry was never recorded |
| `held-state-unknown` | a row records a state that does not exist |
| `held-transition-illegal` | a row records a move the state machine does not allow |
| `held-recorder-wrong` | a row was recorded by a ceremony that does not own that state |
| `held-date-invalid` | a row's date is not `YYYY-MM-DD` |
| `held-note-missing` | an `executed`, `absorbed`, or `withdrawn` row says nothing |
| `held-not-aligned` | the entry stands past `unrecorded` without an *Aligned* verdict |
| `held-plan-missing` | the entry stands at `planned` or later without a plan |
| `held-epic-planned` | an epic-scale entry was planned here; it waits for review, then `/epic` |

## Standing rules

`policy.standingRules.ids` declares the rules every item inherits;
`policy.standingRules.source` names the registered role whose document defines them
(`roadmap` by default). Each declared id must head a section there — a depth 2-4 heading
starting with the id, outside fenced examples — the same pairing rule overlays and
deadlines follow. The preflight checks it at session start from the same read of the
roadmap, and every ceremony and agent reads the rules from that one source.

| finding | severity | meaning |
|---|---|---|
| `standing-rule-unpaired` | warning | a declared id heads no section in the source document |
| `standing-rules-source-unregistered` | warning | `standingRules.source` names a role the registry does not declare |
| `standing-rules-source-unread` | warning / info | the source cannot be read (warning), or is external and not read here (info) |

## Recording a completion

The close-out crossing's two record-keeping writes are one governed command for a
local register and ledger:

    virtuoso_registry --root . --actor dispatch-closeout record-completion --item <ID> \
        --date <YYYY-MM-DD> --result <word> --evidence <close-out> [--revision R] [--apply]

It appends the terminal record (`TR-NNN`, under `policy.terminalLedger.writers`), then
records the completion in the live register at the revision read in Wave 1, then reads
both back from their sources. Without `--apply` it previews both writes. It is
idempotent: a record already in the ledger for the item, or an item already completed,
is reported and not repeated. When the register refuses the completion after the ledger
append — a stale revision, a permission — it opens a **recovery record** naming the steps
that remain (`close-in-register`, `verify-results`) and exits non-zero; `recovery` lists
it until it is resolved. An external ledger is refused by name.

**An external register: `--ledger-only`.** Without the flag an external register is
refused, and the refusal names `--ledger-only`. With it, the command appends the terminal
record exactly as above — next `TR-NNN`, the date, result, evidence, estimate and actual,
and Effort taken from the item in the register snapshot — then reads the ledger back.
Its two steps are `append-terminal-record` and `verify-results`; it never writes the
register, which the `mutation-plan --operation record-completion` handshake closes
afterwards. It previews without `--apply`, and a record already in the ledger for the
item makes it a no-op that still verifies. A local register refuses `--ledger-only`,
because `record-completion` closes it itself. It opens a recovery record only when the
appended record does not read back (`completed_steps` `append-terminal-record`,
`remaining_steps` `verify-results`, `detail.ledgerOnly` true); a handshake that fails
later is covered by the handshake's own recovery record.

**Who may append what.** The terminal ledger takes two kinds of record, and each is
checked against its own list:

| Record | What it is | Who may append | Default |
|---|---|---|---|
| ordinary | a completion, or a retirement (`dissolved`, `superseded`) | `policy.terminalLedger.writers` | `dispatch-closeout` |
| correction | a new record that names the record it corrects, in `corrects` | `policy.terminalLedger.correctionWriters` | `dispatch-closeout`, `roadmap-review` |

A retirement corrects nothing, so it is an ordinary record. A ceremony that is not a
writer routes it to `/dispatch-closeout` (its section *Retirement records routed here*)
and never relabels it as a correction. `record-completion` refuses a non-writer before
it previews, so a preview never promises an append the apply would refuse.

## Dispatch guards

`scripts/dispatch_guards.py` holds the executable halves of the execution rules, run
through the launcher: `"$HOME/.virtuoso/bin/virtuoso" dispatch_guards <subcommand>`.
Paths resolve through the manifest's v2 `roles` (a v1 `paths` map, then the readme's
machine block, for older workspaces); an external role has no path to inspect. Every
subcommand is read-only and exits **0** clean, **1** on a finding, **2** when a ref or
role does not resolve.

| Subcommand | Reports |
|---|---|
| `unpushed` | commits on HEAD not on its upstream (2 when no upstream is set) |
| `artifacts-exist --ref <ref> <path>...` | named artifacts missing from a ref, before a worktree is removed |
| `staging-sweep` | governance staging memos still resident in the `closeOuts` directory |
| `created-files --base <ref> [--json]` | every file the dispatch created or left changed since `<ref>`: `committed`, `temporary` (scratch, backup, cache and log names, anything under the registered `temp` role — committed ones included), `untracked` (not ignored), `uncommitted` |

`dispatch-closeout` runs `created-files` in Wave 1 to draft the report's *Files Created*
dispositions and again at Step 6: a close-out ends with nothing temporary and nothing
unreconciled beyond the files the report names.
An untracked file under `Virtuoso/.recovery/` carries its own verdict, `commit: a
recovery record, never remove or ignore` (see *What git versions*).

## What git versions

The plugin keeps some of its state under `Virtuoso/` and some in the registered
`temp` role. Each has one right answer:

| Path | Git | Why |
|---|---|---|
| `Virtuoso/workspace-layout.json`, `Virtuoso/.virtuoso`, `Virtuoso/work-register.snapshot.json` | commit | the registry, its marker, and the register snapshot every session reads |
| `Virtuoso/.recovery/` | commit | the idempotency trail for external writes. A confirmed write marks its record resolved and keeps it; a clone without the records can repeat a write that already happened |
| `Virtuoso/.backups/` | ignore | repair backups for this machine |
| `policy.sweep.quarantineDirectory` (default `Virtuoso/.quarantine/`) | ignore | files the sweep set aside instead of deleting |
| the `temp` role (default `Project Documentation/3 temp/`) | ignore | scratch; `created-files` reports anything in it as temporary until it is ignored |

`create` appends the three ignore lines to the workspace's `.gitignore`, after a
`# Virtuoso: machine-local state` header, adding only the lines it lacks. `adopt` never
writes one. Instead, `check` and `adopt` report what is wrong (see *Preflight status
contract*).

## Preflight status contract (items 10, 11)

`scripts/virtuoso_preflight.py` always prints two parseable lines, plus a line
reporting overlays, a line reporting deadlines, a line reporting the roadmap's
integrity, and a line reporting the roadmap board's freshness:

```
virtuoso-status: <status>
writes: <N>
overlays: <state>
deadlines: <state>
roadmap-integrity: <state>
board: <state>
```

| status | meaning | writes |
|---|---|---|
| `ready` | registered, valid, nothing to do | 0 |
| `warning` | usable; non-blocking findings | 0 |
| `repair-needed` | error-severity findings; a repair plan exists | 0 |
| `repair-preview` | a repair plan was produced, not applied | 0 |
| `repaired` | an approved repair was applied | ≥0 |
| `adoptable` | established project, not yet registered | 0 |
| `adopted` | adopt registered it in place | ≥1 |
| `created` | create initialized a new workspace | ≥1 |
| `none` | nothing here and nothing to adopt | 0 |
| `failed` | could not complete; nothing partial was written | 0 |

The `overlays:` line is printed in every mode and survives `--quiet`. It always
states a result — `not registered` for a project that never declared the role —
because no output is indistinguishable from an all-clear, which is how a project
ends up believing its overlays are in force while nothing reads them.

| overlay state | meaning |
|---|---|
| `not registered` | the project declares no `overlays` role |
| `registered but absent (<path>)` | declared; the directory is not there |
| `registered, none present (<path>)` | the directory exists and holds nothing that applies |
| `<N> applied (<path>)` | N overlays mirror a shipped file; findings are appended |

The `deadlines:` line follows the same rule — every mode, never suppressed, always a
result — and carries dates and days only. It never carries pace: pace needs the work
register, which may be external, and session start never reads one.

| deadline state | meaning |
|---|---|
| `not registered` | the project is not registered |
| `none declared` | registered; `policy.roadmap.deadlines` is empty |
| `<id> <date> (<N> days)` | one deadline; `(due today)` or `(passed N days ago)` once it arrives |
| `<N> declared; next <id> <date> (<N> days)` | several; the earliest not yet passed (`latest` once all have) |
| `invalid (<problem>)` | every declared entry fails validation; the first problem is shown |

A `; N finding(s)` suffix counts the deadline findings above.

The `roadmap-integrity:` line follows the same rule. It reports the registered
roadmap's bytes, read once at session start (the deadline check reads the same bytes).
The ceremonies that rewrite the roadmap act on it before touching the file, and
`--check-document <path>` prints the same state for any one document, with exit code
0 / 2 / 3 for `ok` / `warn` / `fail`.

| integrity state | meaning |
|---|---|
| `not registered` | the project is not registered |
| `no roadmap role` | registered; no `roadmap` role is declared |
| `external (not read at session start)` | the roadmap is an external role |
| `ok size=<N>` | readable text of N bytes |
| `warn (<why>) size=<N>` | `empty`, or `oversize:<N>-bytes(><limit>)` |
| `fail (<why>) size=<N>` | `not-text` (undecodable, a byte-order mark honoured) or `null-bytes` (after decoding) |
| `fail (missing: <path>)` | the registered path is not a file |

The `board:` line follows the same rule, with JSON key `board`. It is advice and never
changes the status. The roadmap board embeds, at generation, the modification time of
each local file it was built from (the register or its snapshot, the terminal ledger,
the roadmap, the board comments); the line compares those with the times now. It reads
file times, the manifest and the page — never the work register.

| board state | meaning |
|---|---|
| `not registered` | the project declares no `board` role |
| `missing (<path>; ...)` | the role is registered and the page is absent (a fresh clone): `generate_board --root .` builds it |
| `stale (<roles> changed since <time>)` | a source changed after the page was generated: regenerate it |
| `current (generated <time>)` | every source is as it was when the page was generated |
| `unreadable (<why>)` | the page carries no board model, or the check itself failed |

### Stale vendored tools

Installs before 1.4 copied plugin scripts into `Virtuoso/scripts/`; 1.4 stopped vendoring
and never removed the copies. Each retired tool still present there is a
**`retired-vendored-tool`** warning at every load, naming what replaces it. A stale copy
reads the v1 `paths` map and answers from conventional fallbacks instead of failing, so
it is reported — never deleted by the plugin.

### Plugin state git treats the wrong way

`check`, `adopt` and `create` ask git (read-only, `git check-ignore`) how it treats the
paths in *What git versions*. Each problem is a warning that names the fix:
**`local-state-not-ignored`** lists the ignore lines the project lacks, and
**`recovery-records-ignored`** says that `Virtuoso/.recovery/` is ignored and must not
be. Outside a git repository, or without git, nothing is reported. The check runs in
preflight only, not at every registry load, so only session start pays for the git
call.

### Policy validated at every load

Every registry load checks the project's own `policy` block the way `policy-set`
checks a write: a documented key whose value has the wrong type, and every problem the
policy's own validation finds (an unknown git policy, an invalid ledger mapping, lesson
prefix or pace block). Each is a **`policy-invalid`** warning naming the key; the value
falls back to its documented default. Warning, never error: a project's configuration is
the project's to fix. Undocumented keys are inert rather than invalid and are not
reported; deadline problems are reported on the `deadlines:` line instead.

`--json` adds the full structured result, including the resolved overlays and the
safety floor they may not loosen, `deadlines` (the declared dates, days remaining
and findings), and `roadmapIntegrity` (its state). The JSON follows the machine lines; read it from its first line (the one
beginning `{`), never from a fixed line count, because the set of machine lines grows.
Modes: `check` (read-only; `detect` is a retained alias), `adopt`, `create --authorize`,
`repair [--apply]`.

## Locating the plugin

Skill bodies cannot expand `${CLAUDE_PLUGIN_ROOT}`. Resolve the plugin root
through the version-qualified install record (item 12) — never through a
hardcoded home-directory path.

**Unix-like shell:**

```sh
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check
```

**Windows PowerShell:**

```powershell
& "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check
```

Both launchers resolve the newest valid installed version from
`~/.virtuoso/installs.json`, or `VIRTUOSO_PLUGIN_ROOT` when it is set. If neither
resolves, report that the plugin could not be located — do not guess a path.
