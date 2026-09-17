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

## Three distinct work roles (item 24)

| Role | What it is |
|---|---|
| `workRegister` | the **live** work register — the only place item status is true |
| `terminalLedger` | the **append-only** record of finished work |
| `sprintCatalog` / `sprintQueue` | optional **compatibility export** / generated report |

The local CSV catalog is optional (item 25): it may be the live register, a
generated mirror, or absent entirely.

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
`closeout --prepare`, `create-item`, `mutation-plan`, and `mutation-confirm`.

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
```

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
| `overlays-external` | the role registers an external identifier; overlays are read as files |
| `overlays-writable` / `overlays-has-writers` | registered writable; register it read-only |
| `pairing-body-missing` | a policy key declares an id that no overlay section defines |
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

## Preflight status contract (items 10, 11)

`scripts/virtuoso_preflight.py` always prints two parseable lines, plus a third
line reporting overlays:

```
virtuoso-status: <status>
writes: <N>
overlays: <state>
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

`--json` adds the full structured result, including the resolved overlays and the
safety floor they may not loosen. Modes: `check` (read-only; `detect` is a
retained alias), `adopt`, `create --authorize`, `repair [--apply]`.

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
