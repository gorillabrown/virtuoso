---
name: virtuoso-init
description: >
  Initialize or repair the Virtuoso workspace for a project. Use when setting up the
  virtuoso plugin in a new project, when a governance skill reports a missing workspace,
  or when the user says "virtuoso init", "set up virtuoso", "create the roadmap workspace",
  or "initialize virtuoso". Creates the plugin-only documentation tree (the only
  supported layout) plus the Virtuoso plugin workspace, and never overwrites user content.
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (its universal checks, at the version it declares, plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / xhigh / max. A property of the task's difficulty, never a ranking of whoever performs it.

<!-- virtuoso-overlay-clause v2 -->
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.

# Virtuoso Init

Register a project with Virtuoso, or initialize a new workspace. Four separate
operations, each doing exactly one thing.

| Operation | What it does | Writes |
|---|---|---|
| `check` | read-only validation and discovery | **none** |
| `adopt` | register an established project **in place** | the control files only |
| `create` | initialize a **new** workspace — requires `--authorize` | the scaffold |
| `repair` | preview proposed registry repairs; apply only with `--apply` | only what you approved |

## Always start with check

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check --json

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check --json

It performs discovery and validation with **zero project writes**, and prints:

```
virtuoso-status: <status>
writes: 0
```

Branch on the status:

| Status | What it means | Next |
|---|---|---|
| `ready` | registered and valid | nothing to do |
| `warning` | usable; non-blocking findings | report them; continue |
| `repair-needed` | error-severity findings | `--mode repair` (preview), then `--apply` after approval |
| `adoptable` | governance exists, unregistered | `--mode adopt` |
| `none` | nothing here and nothing to adopt | `--mode create --authorize` |
| `failed` | could not complete; nothing partial was written | report the error verbatim |

## Already have governance? Adopt it

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode adopt

Adoption registers what the project already has, **in place**. Nothing is moved,
nothing is duplicated, no parallel document is seeded, and no existing document is
rewritten. It writes exactly three control files: the workspace marker, the
manifest, and the human registry view.

Adoption reports, role by role, what it registered and why. Two of its decisions
matter:

- **A discovered local register is registered `unknown`, not authoritative.** The
  plugin never promotes a file to live authority on its own (redesign item 6).
  Classify it — set `authority`, `mutability`, and `allowedWriters` — before any
  ceremony can write to it.
- **A role it cannot find is not registered at all**, rather than pointed at a
  phantom path. Register it yourself when the project has one.

**Adoption never heals.** Run against an already-registered project, `adopt` behaves
exactly like `check` and says so. Repair is a separate, previewed operation.

## New project? Create, with explicit authorization

### First: ask where the work register lives

Before `create`, ask the user one question: **where should the work register — the
live list of items, their status, order and size — live?** The roadmap is always
created as Markdown in the repository; this question is only about the register.
Offer the choices in this order:

1. **A file in the repository** — a CSV (the default), a Markdown table, or a
   spreadsheet (`.xlsx`, which needs the `openpyxl` package).
2. **A task tool this session can reach** — look at the tools this session actually
   has, and list each task or database tool it has a connector for, marked
   "(connected)". Never list a tool you cannot see, and never mark one connected that
   is not.
3. **Another tool, by identifier** — a `<scheme>:<id>` the user gives (for example
   `notion:database/<id>`, `linear:team/<key>`, `jira:project/<key>`).

When the user names a tool this session has no connector for, say so: **"That tool
is not connected in this session, so I cannot read or write it yet."** Then offer to
record its identifier anyway, for a later session that has the connector, or to start
with a file in the repository. Record it only if they ask.

For a tool, ask how its columns map to the register's fields (at least `id`, `title`,
`status`; also `sequence`, `effort`, `prerequisites` where it has them) and how its
status words map to `queued`, `in-flight`, `blocked` and `completed`. Write the answer
to a small JSON file — `{"fieldMappings": {...}, "statusMappings": {...}}` — and pass it
with `--register-mappings`.

Then create, passing the choice:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode create --authorize --register <csv | markdown | xlsx | scheme:id> [--register-mappings <file.json>]

Without `--register`, `create` lays down a CSV register, as it always has.

### Then: create

`create` writes new files into the project, so it requires `--authorize`. Without
it the run reports `failed` and explains what to pass. It refuses outright if the
project already carries a registry.

It lays down the documentation tree, seeds the roles it creates, and writes the
registry. It never overwrites an existing file.

The registry it writes declares, for every role: the path or external identifier,
the provider type, the authority level, the mutability, the owning ceremony, the
allowed writers, the validation method, and whether the role is authored or
generated. Authority is **declared**, so you can change it — see
`references/registry-contract.md`.

### What create lays down

- **`Virtuoso/workspace-layout.json`** — the machine manifest. The authority.
- **`Virtuoso.Governance.Readme.md`** — the human view of it, with a generated
  region the plugin maintains and protected sections that are yours. Everything
  outside the generated region is preserved byte-for-byte forever.
- **A roadmap** — the specification store (`live`, read-write).
- **A work register** — the live pipeline, where the user chose (`--register`): a CSV
  by default, a Markdown table, a spreadsheet, or a connected tool's identifier — then
  registered external with a snapshot role (`Virtuoso/work-register.snapshot.json`)
  and the mappings, and no register file is seeded.
- **A terminal ledger** — append-only completion records (`terminal`, append-only).
- **A lessons catalog**, close-outs, issues, reviews, outside audits, and reference
  directories.

The local CSV is **optional** and it is **not special**. It is authoritative here
only because `create` explicitly declared it so; a project may make it a generated
mirror or drop it entirely.

## Move the work register to another tool

A project that already has a register can move it — from a CSV to a connected tool,
or from one tool to another — without re-entering its open work. History (the terminal
ledger, close-outs, reviews, archives) is never touched; finished items stay in the
ledger only.

1. **Ask where it should live**, exactly as in *First: ask where the work register
   lives* above, and collect the new tool's column and status mappings into a file.
2. **Preview** — writes nothing; show the user what it prints:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . move-register --to <scheme:id | csv | markdown | xlsx> --mappings <file.json>

   It lists the open items that will be created and says how many finished items stay
   in the ledger only.
3. **Plan**, only after the user approves the preview:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso-init move-register --to <target> --mappings <file.json> --plan --apply

   It writes one move record. For a local target it writes the rows itself. For a
   tool it prints one create instruction per open item: execute each with the
   session's connector, read the item back, then confirm it:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . move-register --confirm <ITEM-ID> --provider-id <id> --recovery-id <record id>

4. **Finish**: for a tool, read the new register into a rows file (the registry
   contract's rows contract) and hand it over; for a local target, leave `--snapshot`
   out — the new file is read directly:

       "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso-init move-register --finish --recovery-id <record id> --snapshot <rows.json> --apply

   It refuses while any item is pending, and refuses — changing nothing — unless the
   new register holds the same ids and statuses, and the same order wherever the new
   mappings name a sequence column (a local target always does). On a match it
   repoints the registry with a backup and prints the before/after table.
5. **Refresh the governance readme**, which still names the old register:
   `virtuoso_preflight --root . --mode repair` previews it; apply only with the user's
   approval.

A move interrupted part-way leaves its record; `virtuoso_registry recovery` names the
items created and the ones still pending, and the project keeps its old register until
`--finish` succeeds. A `--finish` interrupted after its repoint can simply be run
again. A move that will not finish — a local move that failed while writing rows cannot
resume — is closed with `move-register --abandon --recovery-id <id> --reason "<why>"`,
which names the items already created at the target; remove a partly written local file
by hand before planning again. Like `--mode repair`, the move rewrites the manifest
on the owner's say-so: `--actor` names who ran it; no role's `allowedWriters` gates it.

## Repair — always previewed

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode repair

Prints the proposed paths, the semantic changes, the files affected, and where
backups will go. It writes nothing. Show that preview to the user.

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode repair --apply

Applies it transactionally: the reconstructed registry is validated **before any
write**, every existing target is copied into a hash-verified backup set first, and
any failure restores from that set and leaves the original registry and manifest
intact.

Repair will **not**:
- regenerate a user-authored registry from a template — it only refreshes its own
  generated region, or offers to *append* one, preserving every existing byte;
- reclassify an unknown legacy role as writable or authoritative;
- repoint a registered-but-absent role at a similarly named file.

Anything it cannot fix safely is listed as *not repairable automatically*, with the
reason.

## Migrating from schema v1

A v1 registry (a manifest with a flat `paths` map) is read and migrated
conservatively:

- Recognized roles migrate with their documented defaults.
- **Unknown legacy roles stay unknown** — not writable, not authoritative — until
  a human classifies them.
- **The legacy `sprintCatalog` migrates as a compatibility mirror, not as the live
  register.** v1 described it as authoritative by convention; v2 does not carry
  that claim forward — only the registry assigns authority. Ceremonies can still *read* it through the compatibility adapter;
  writing requires registering a `workRegister` role explicitly.

Migration is non-destructive and previewed like any other repair.

## Locating the plugin

Skill bodies cannot expand `${CLAUDE_PLUGIN_ROOT}`, so use the launcher. It resolves
the newest valid installed version from `~/.virtuoso/installs.json` — a record keyed
**by plugin version**, so two installed versions never overwrite each other's
discovery state. `VIRTUOSO_PLUGIN_ROOT` overrides it.

If neither launcher resolves, say the plugin could not be located and stop. Do not
guess a path, and do not read a hardcoded home-directory file.
