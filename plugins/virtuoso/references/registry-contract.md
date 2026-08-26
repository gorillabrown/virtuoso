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
```

All of those are queries: none of them creates a directory, seeds a document, or heals
anything as a side effect. The commands that write say so explicitly — `snapshot`,
`closeout --prepare`, `mutation-plan`, and `mutation-confirm`.

**Negotiate capabilities before you plan work** (item 28). A provider declares
which of these it supports: `list-active`, `read-sequence`, `read-status`,
`write-status`, `read-prerequisites`, `read-effort`, `store-spec-link`,
`record-completion`, `next-eligible`. If a ceremony needs a capability the
selected provider lacks, say so up front and stop — do not start and fail halfway.

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

## Preflight status contract (items 10, 11)

`scripts/virtuoso_preflight.py` always prints two parseable lines:

```
virtuoso-status: <status>
writes: <N>
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

`--json` adds the full structured result. Modes: `check` (read-only; `detect` is
a retained alias), `adopt`, `create --authorize`, `repair [--apply]`.

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
