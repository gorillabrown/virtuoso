# Virtuoso

A Claude Code plugin that packages a complete **governance & dispatch system**: a planning
surface that specifies and sequences work, hands dispatch-ready specifications to an
implementer, and closes the loop with terminal records, retrospectives, audits, and
documentation hygiene — driven by a **per-project governance registry** that each project
declares for itself.

## What it is

Virtuoso models a workflow between **roles**, never products:

| Role | What it does |
|---|---|
| **planner** | plans the roadmap, writes specifications, makes decisions, closes work out |
| **implementation agent** | executes a fully-specified item without inventing decisions |
| **reviewer** | reviews work against its specification |
| **repository operator** | performs the repository mutations the project's git policy permits |

Rename them in `policy.actors`. The same session may hold several roles at once; whether
they must be held by *different* actors is an optional project policy, not an assumption.

A specification must be complete because an incomplete one cannot be executed without
inventing the missing decisions — by anyone, at any capability. Virtuoso makes no claim
that one host or model is inherently more capable than another.

## Install

```
/plugin marketplace add gorillabrown/virtuoso
/plugin install virtuoso@virtuoso-marketplace
```

Then register your project:

```
/virtuoso:virtuoso-init
```

## The governance registry

Everything resolves through one authority.

| Artifact | Role |
|---|---|
| `Virtuoso/workspace-layout.json` | **the machine manifest — the authority** |
| `Virtuoso.Governance.Readme.md` | a synchronized human view, with protected sections that are yours |

The manifest declares its own `schemaVersion` and the plugin range it works with. Every
registered role carries its full metadata:

```jsonc
"workRegister": {
  "path": "docs/work-register.csv",     // OR "external": "monday:board/1234567890"
  "provider": "csv",                    // markdown csv xlsx jsonl json directory snapshot
                                        // connector issue-tracker database external none
  "authority": "live",                  // live terminal mirror report evidence archive
                                        // reference unknown
  "mutability": "read-write",           // read-write append-only generated read-only immutable
  "owner": "roadmap-review",
  "allowedWriters": ["roadmap-review", "pointer-closeout"],
  "validation": "csv-headers",
  "classification": "active",           // active | historical | unknown
  "origin": "authored",                 // authored | generated | unknown
  "generatedFrom": "",                  // for a derived artifact: its source role
  "generatedBy": ""                     // for a derived artifact: its registered generator
}
```

The rules every skill follows:

1. **Authority is declared, never inferred from a name.** A role called `sprintCatalog` is
   authoritative only if its `authority` says `live`.
2. **Resolve, never guess.** An unregistered role is an error naming the fix, not a fallback
   to a conventional path.
3. **A registered-but-absent target is reported**, never silently repointed at a lookalike.
4. **Write only where `allowedWriters` names you**, and never to an `archive`, `unknown`,
   `read-only`, or `immutable` role.
5. **Generated artifacts are regenerated, never hand-edited.**
6. **External identifiers are valid registrations** — a board, project, database, or service
   id is never reported as a missing file.
7. **Project extensions live under `x-`** and survive plugin upgrades verbatim.

Full contract: [`plugins/virtuoso/references/registry-contract.md`](plugins/virtuoso/references/registry-contract.md).

## Four separate operations

```
check    read-only validation and discovery.       ZERO project writes, always.
adopt    register an established project in place. Never rewrites its documents.
create   initialize a new workspace.               Requires --authorize.
repair   preview repairs; apply only with --apply. Transactional, with verified backups.
```

Every invocation prints two parseable lines:

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

`--json` adds the full structured result. **The SessionStart hook runs `--mode check`**, so
starting, clearing, or compacting a session never creates, heals, vendors, or rewrites a
project file.

## Work-register providers

Roadmap ceremonies never open a register file. They ask a provider, and negotiate its
capabilities before planning work.

| Provider | Registration |
|---|---|
| local CSV | a path |
| local Markdown table | a path |
| spreadsheet | a path (needs `openpyxl`) |
| connector-backed task manager | an external identifier, e.g. `monday:board/1234567890` |
| issue tracker | an external identifier, e.g. `jira:project/ABC` |
| database | an external identifier, e.g. `postgres:table/public.work_items` |
| read-only snapshot | a path to a timestamped capture |

Capabilities: `list-active`, `read-sequence`, `read-status`, `write-status`,
`read-prerequisites`, `read-effort`, `store-spec-link`, `record-completion`, `next-eligible`.

Three roles, deliberately separate:

- **`workRegister`** — the live work register, the only place item status is true;
- **`terminalLedger`** — the append-only record of finished work;
- **`sprintCatalog` / `sprintQueue`** — optional compatibility export and generated report.

**Field names and status words are yours.** Map them in
`policy.workRegister.fieldMappings` and `policy.workRegister.statusMappings`. Nothing
requires the literal words *Queued*, *In Flight*, or *Full Spec*.

Every derived figure states its provider, source, and snapshot time. A figure whose inputs
are missing is reported as **not computable** with the missing inputs named — never
approximated. Mutations are optimistically concurrent and idempotent; a cross-system
partial failure leaves a recovery record naming exactly what remains.

## Locating the plugin

Skill bodies cannot expand `${CLAUDE_PLUGIN_ROOT}`. Use the launcher, which resolves the
newest valid installed version from `~/.virtuoso/installs.json` — a record keyed **by plugin
version**, so two installed versions never overwrite each other's discovery state.

```sh
# Unix-like shell
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check
```

```powershell
# Windows PowerShell
& "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check
```

`VIRTUOSO_PLUGIN_ROOT` overrides both. If neither resolves, the plugin says it could not be
located rather than guessing a path.

## Command-line surface

| Script | Purpose |
|---|---|
| `virtuoso_preflight.py` | check / adopt / create / repair, plus `--check-document` |
| `virtuoso_registry.py` | read-only queries: `roles`, `resolve`, `provider`, `items`, `next`, `kpis`, `closeout`, `repo`, `recovery`; and the explicit writers `snapshot`, `closeout --prepare` |
| `generate_cockpit.py` | the planning cockpit, read from the configured provider |
| `build_register_report.py` | the generated spreadsheet report (declared generated roles only) |
| `validate.py` | structural validation of the plugin itself |

## Skills

Invoked through the plugin namespace, e.g. `/virtuoso:roadmap-review`.

| Skill | Slash | Purpose |
|-------|-------|---------|
| `virtuoso` | — | Multi-step execution discipline |
| `epic` | `/virtuoso:epic` | Launch materials for goal-scale, multi-session runs |
| `roadmap-review` | `/virtuoso:roadmap-review` | Heavyweight roadmap recalibration |
| `roadmap-status` | `/virtuoso:roadmap-status` | Read-only status briefing |
| `next-pointer` | `/virtuoso:next-pointer` | Finalize and dispatch the next item |
| `pointer-closeout` | `/virtuoso:pointer-closeout` | The transactional close-out crossing |
| `mid-dispatch-decision` | `/virtuoso:mid-dispatch-decision` | Decide when a dispatch pauses mid-run |
| `governance-sweep` | `/virtuoso:governance-sweep` | 3-phase doc hygiene: discover → approve → fix |
| `3rd-party-audit` | `/virtuoso:3rd-party-audit` | External audit lifecycle |
| `ultrathink` | `/virtuoso:ultrathink` | Deep first-principles reasoning |
| `effort-levels` | — | Effort sizing (modifier) |
| `adversarial-review` | — | Structured red-team review (modifier) |
| `git-handoff` | — | Hand-off packet for a session that cannot mutate the repository |
| `delayed-start` | `/virtuoso:delayed-start` | Defer execution to a clock time or delay |
| `virtuoso-init` | `/virtuoso:virtuoso-init` | Register a project, or initialize a workspace |

## Shared references

One home each, so nothing can drift apart:

| Reference | What it settles |
|---|---|
| [`registry-contract.md`](plugins/virtuoso/references/registry-contract.md) | roles, providers, capabilities, the status contract |
| [`readiness-rubric.md`](plugins/virtuoso/references/readiness-rubric.md) | the single versioned readiness rubric (v1.0) |
| [`git-policy.md`](plugins/virtuoso/references/git-policy.md) | the git policy ladder, detection, and the universal safety rules |
| [`actors-and-interaction.md`](plugins/virtuoso/references/actors-and-interaction.md) | actor roles and the interaction adapter |

## Git behaviour is project policy

`policy.git.policy` picks one rung of the ladder: `read-only`, `prepare-no-stage`,
`explicit-path-stage`, `explicit-path-commit`, `push`. The default branch and remote are
**detected**, never assumed; a repository with **no remote** is fully supported; branch
cleanup is maintenance, not a dispatch prerequisite; a stale index lock is **reported**,
never removed automatically; and the plugin is worktree-aware, so a dirty primary tree does
not invalidate a clean dedicated execution worktree.

Under every policy: inspect first, stage exact paths, preserve unrelated work, no
destructive flags, and no force-push without explicit authorization.

## Agents

A dispatchable roster in `plugins/virtuoso/agents/`, routed by **task tier** — a property of
the task, not a ranking of whoever runs it:

| Agent | Task tier | Role |
|-------|-----------|------|
| `Aristotle` | cross-cutting | Lead — investigation, cross-system work, root cause |
| `Hercules` | bounded | Single-domain implementation |
| `Hermes` | mechanical | Prescribed changes (config, renames, repository operations) |
| `Hippocrates` | mechanical | Test execution and coverage-gap reporting |
| `Plato` | bounded | Code-quality review |
| `MarcusAurelius` | bounded | Documentation, compliance, drift detection |
| `Socrates` | bounded | Measurement and tuning specialist |
| `Pythagoras` | bounded | Data-integrity auditing |
| `Archimedes` | bounded | Display and statistics auditing |
| `Hesiod` | cross-cutting | Behavioural KPI evaluation |

`skills/virtuoso/references/zeus.md` is the orchestration protocol the `virtuoso` skill
reads; it is not a dispatchable subagent. The specialist agents read their commands from the
project's **registered commands**, so they carry no project's script names, sample sizes, or
thresholds of their own.

## External prerequisites (optional)

- **`anthropic-skills`** — `docx` and `xlsx`, for document and spreadsheet mechanics.
- **`product-management`** — `write-spec` and `roadmap-update`, used by `roadmap-review`.

## Requirements

- Python 3.12+ with the standard library for the registry, the providers, and the CLI.
- `openpyxl` only for the spreadsheet provider and the generated report. It is a **declared**
  dependency: when it is absent, those capabilities are withdrawn with a message naming it,
  never an import error mid-ceremony.

## Upgrading from 1.3.x

Virtuoso 1.4 carries breaking changes despite the minor version number: the registry schema
moves 1 → 2 and several bundled scripts are removed. See
[`docs/MIGRATION-1.4.md`](docs/MIGRATION-1.4.md). Migration itself is non-destructive and
previewed; unknown legacy roles stay unclassified, and the legacy local catalog migrates as
a read-only compatibility mirror rather than being reinterpreted as authoritative.

## License

MIT
