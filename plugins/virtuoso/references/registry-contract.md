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
  "path": "docs/work-register.csv",      // OR "external": "monday:board/1234567890"
  "provider": "csv",                     // markdown csv xlsx jsonl json directory
                                         // snapshot connector issue-tracker database
                                         // external none
  "authority": "live",                   // live terminal mirror report evidence
                                         // archive reference unknown
  "mutability": "read-write",            // read-write append-only generated
                                         // read-only immutable
  "owner": "roadmap-review",             // owning ceremony
  "allowedWriters": ["roadmap-review", "pointer-closeout"],
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

Two roles are supported but never assumed: `create` lays down neither, and a project
registers each by adding its entry to the manifest when it first needs it.

| Role | Holds | Writers | Registered |
|---|---|---|---|
| `overlays` | project additions to shipped skills and agents (see *Project overlays*) | none (read-only) | when the project has something to overlay |
| `epics` | one directory per epic packet, `<yyyy-mm-dd>-<slug>/` | `epic` | when the project runs its first epic |

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
python <plugin>/scripts/virtuoso_registry.py --root . kpis
python <plugin>/scripts/virtuoso_registry.py --root . repo --expect <paths>
python <plugin>/scripts/virtuoso_registry.py --root . deps
python <plugin>/scripts/virtuoso_registry.py --root . protected
python <plugin>/scripts/virtuoso_registry.py --root . recovery
python <plugin>/scripts/virtuoso_registry.py --root . overlays
```

All of those are queries: none of them creates a directory, seeds a document, or heals
anything as a side effect. The commands that write say so explicitly — `snapshot`,
`closeout --prepare`, `create-item`, `policy-set --apply`, `mutation-plan`, and
`mutation-confirm`.

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

### Provenance and honesty

- Every derived metric states the provider, source, snapshot time, and fields it
  came from (item 29).
- A metric whose inputs are missing is reported as **not computable** with the
  missing inputs named. It is never approximated (item 30).
- A snapshot read offline is labelled with its age and flagged stale past the
  configured window (item 31).

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
  --operation set-status --item <ID> --fields-json '<JSON>' --revision <REVISION> --json
# execute the returned instruction with the host connector
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> mutation-confirm \
  --operation set-status --item <ID> --idempotency-key <KEY> --recovery-id <RECOVERY-ID> \
  --succeeded --actual-revision <NEW-REVISION> --json
```

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
  then refresh the canonical snapshot and check that `recovery` is empty.

A local register creates directly — this is a write:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> create-item \
  --item <ID> --fields-json '{"title": "...", "sequence": 42, "effort": "M"}' --json
```

An external register uses the same handshake as every other mutation:

```sh
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> mutation-plan \
  --operation create-item --item <ID> --fields-json '<JSON>' --json
# the plan carries expectedAbsent, snapshotTakenAt, projectFields (the project's own
# column names), defaultsApplied, preconditions for the host, and postconditions.
# Execute it with the host connector; read the created item back.
python <plugin>/scripts/virtuoso_registry.py --root . --actor <ceremony> mutation-confirm \
  --operation create-item --item <ID> --idempotency-key <KEY> --recovery-id <RECOVERY-ID> \
  --succeeded --provider-id <PROVIDER-ITEM-ID> --actual-revision <REVISION> --json
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
  `title`, `lane`, `group`, `effort`, `branch`, or a register column) holds one of
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
  the count down by the result words recorded, and lists what it excluded.
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
register (trailing points only), a scope that matches nothing. Nothing is estimated, and nothing
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

**Three links, each checked.**

1. **Close-out records.** `pointer-closeout` appends what the dispatch taught — or its
   report says `No new lesson — <reason>` — and records how the lessons its specification
   applied turned out. The crossing's verify step runs
   `lessons --check <report> --closeout --item <ID>`: a lesson the report names must be in
   the role (the append happened), or the report must give its reason. A report that fails
   is not a finished close-out.
2. **Specification applies.** Readiness check U9, *Lessons applied*, in the shared rubric:
   a specification names each live lesson that bears on it and the change it made, or
   states that no live lesson applies. `roadmap-review` reads the live lessons before it
   drafts and re-checks every existing dispatch-ready specification against lessons
   recorded since; `next-pointer` checks the head item before it prints.
   `lessons --check <spec> --item <ID>` is the mechanical half; a live lesson the section
   leaves uncited is listed, so the author's judgement is made rather than skipped.
3. **Direction applies.** An `epic` charter carries *Lessons applied* before an unattended
   run begins, and an epic ends through `pointer-closeout`, so its lessons reach the role.

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
  *Applies to*; **repair** — an identifier reused for a second lesson.
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

Read together over successive reviews: a flat or falling live count with a positive yield,
promotions above zero, a high held rate, a falling repeated-trap rate. Any one figure can be
gamed; the set is expensive to game, because yield without holds, or holds without
promotions, shows.

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

A disposition changes only by appending a record under the same id —
`**Disposition:** fixed by <item or commit>`, `accepted — <reason>`, `lesson <prefix>-NNN`.
Writers by default: `governance-sweep`, `adversarial-review`, `virtuoso` (for the agents it
dispatches), `pointer-closeout`, `roadmap-review`, `3rd-party-audit`. **Reader:**
`roadmap-review` B.3 reads every finding whose latest disposition is `open`, with the
previous review's lessons-applied, and carries each into the plan.

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

    virtuoso_registry --root . --actor pointer-closeout record-completion --item <ID> \
        --date <YYYY-MM-DD> --result <word> --evidence <close-out> [--revision R] [--apply]

It appends the terminal record (`TR-NNN`, under `policy.terminalLedger.writers`), then
records the completion in the live register at the revision read in Wave 1, then reads
both back from their sources. Without `--apply` it previews both writes. It is
idempotent: a record already in the ledger for the item, or an item already completed,
is reported and not repeated. When the register refuses the completion after the ledger
append — a stale revision, a permission — it opens a **recovery record** naming the steps
that remain (`close-in-register`, `verify-results`) and exits non-zero; `recovery` lists
it until it is resolved. An external register is refused and pointed at the
`mutation-plan --operation record-completion` handshake; an external ledger is refused by
name.

## Sprint guards

`scripts/sprint_guards.py` holds the executable halves of the execution rules, run
through the launcher: `"$HOME/.virtuoso/bin/virtuoso" sprint_guards <subcommand>`.
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

`pointer-closeout` runs `created-files` in Wave 1 to draft the report's *Files Created*
dispositions and again at Step 6: a close-out ends with nothing temporary and nothing
unreconciled beyond the files the report names.

## Preflight status contract (items 10, 11)

`scripts/virtuoso_preflight.py` always prints two parseable lines, plus a line
reporting overlays, a line reporting deadlines, and a line reporting the roadmap's
integrity:

```
virtuoso-status: <status>
writes: <N>
overlays: <state>
deadlines: <state>
roadmap-integrity: <state>
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
