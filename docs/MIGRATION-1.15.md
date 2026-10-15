# Migrating to Virtuoso 1.15

Virtuoso 1.15 renames the plugin's dispatch vocabulary. It is a **minor** release: every old
name keeps working for one release, with a warning that names the fix. The aliases are
removed in the next major release.

Nothing is rewritten for you. Your project's files, your close-outs, and your history stay
exactly as they are.

---

## Why

"Sprint" and "pointer" misled new users: neither names what a Virtuoso run is. A Scrum
sprint is a time-box of many items; a Virtuoso run is one item, or one epic, run by one
agent session — a **dispatch**. The block that starts one is its **kickoff**.

| 1.14 | 1.15 |
|---|---|
| skill `next-pointer` (`/next-pointer`) | skill `dispatch-kickoff` (`/dispatch-kickoff`) |
| skill `pointer-closeout` (`/pointer-closeout`) | skill `dispatch-closeout` (`/dispatch-closeout`) |
| "sprint" in skills, references, agents, templates | "dispatch" |
| "pointer", the printed block | "kickoff" |
| `sprint_guards` | `dispatch_guards` |
| `virtuoso_registry timing --sprint ID` | `virtuoso_registry timing --dispatch ID` |
| close-out template frontmatter `sprint:` and "Sprint Brief" | `dispatch:` and "Dispatch Brief" |
| `[SPRINT-ID]` placeholders | `[DISPATCH-ID]` |

---

## What to do

### 1. Upgrade the plugin

```
/plugin marketplace update virtuoso-marketplace
/plugin install virtuoso@virtuoso-marketplace
```

Start a new session, so the renamed skills load under their new names.

### 2. Check

```sh
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check
```

```powershell
& "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check
```

A project whose `Virtuoso/workspace-layout.json` names the old skills reports
`virtuoso-status: warning` with one `actor-renamed` finding that lists each replacement.
It keeps working: the warning is the only change.

### 3. Rename the skills in your workspace layout

In `Virtuoso/workspace-layout.json`, replace every `"next-pointer"` with
`"dispatch-kickoff"` and every `"pointer-closeout"` with `"dispatch-closeout"` — in each
role's `allowedWriters` and `owner`, and in `policy.terminalLedger.writers`,
`policy.terminalLedger.correctionWriters`, and `policy.workRegister.creators` — and anywhere
else the old names appear. Run the check again: the warning is gone.

### 4. Update anything of your own that calls the old names

Hooks, scripts, and notes that run `sprint_guards` or `timing --sprint`, or that tell an
agent to run `/next-pointer` or `/pointer-closeout`. `sprint_guards` and `timing --sprint`
keep working and print one deprecation line on stderr until you do. The slash commands
`/next-pointer` and `/pointer-closeout` do not: the skills load only under their new names.
The old skill names keep working only as actor names in a workspace layout.

---

## Compatibility — for one release

- **Actors.** Every check of who may write — `allowedWriters`, the terminal ledger's
  writers and correction writers, work-register creators, holding-bay recorders — reads
  `next-pointer` as `dispatch-kickoff` and `pointer-closeout` as `dispatch-closeout`, on
  either side. An old manifest admits the new skills, and `--actor pointer-closeout` still
  writes.
- **Holding-bay history.** Trail rows recorded by `pointer-closeout` stay valid history.
- **`sprint_guards`.** `scripts/sprint_guards.py` runs `dispatch_guards` with the same
  arguments and exit codes, and prints one deprecation line on stderr.
- **`timing --sprint`.** A hidden alias of `--dispatch` that prints one deprecation line on
  stderr.
- **Close-outs already written** keep their `sprint:` frontmatter and "Sprint Brief"
  heading; no code parses either.
- **`lane` is now `workstream`.** A register column named `Lane` reads as `workstream` and
  is never renamed in your file. A `fieldMappings` key `lane` maps to `workstream`; one that
  names both is refused. `roadmap.lanes` is read with a `policy-renamed` warning, and
  `combine --lane` works with one deprecation line on stderr. Full note: the plugin's
  `references/registry-contract.md`, *Migration note (1.15.0)*.

---

## Deprecated, and kept

### Deprecated — removed in the next major release

| Deprecated | Use |
|---|---|
| `next-pointer`, `pointer-closeout` as actor names in a workspace layout | `dispatch-kickoff`, `dispatch-closeout` |
| `scripts/sprint_guards.py` | `scripts/dispatch_guards.py` |
| `timing --sprint` | `timing --dispatch` |
| `lane` (a `fieldMappings` key), `roadmap.lanes`, `combine --lane` | `workstream`, `roadmap.workstreams`, `combine --workstream` |

### Kept as they are

| Kept | Why |
|---|---|
| the registry roles `sprintQueue` and `sprintCatalog`, their labels, and the `sprint-queue.template.xlsx` workbook template | names stored in projects' workspace layouts |
| the roadmap reader's legacy "Sprint Skeletons" heading | reads older roadmaps |
| register discovery and the "sprint code" column header | read files projects already have |
| `Timing.<id>.jsonl` time-log names | they never contained the word |

---

## Rolling back

Reinstall 1.14.0 through your plugin host. Nothing in your project needs restoring: 1.15
itself writes no project file.

1.14 knows only the old names. If you already renamed the skills in your workspace layout
(step 3), put the old names back, or 1.14 refuses the writes those skills make.
