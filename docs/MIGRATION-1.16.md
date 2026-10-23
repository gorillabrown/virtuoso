# Migrating to Virtuoso 1.16

Virtuoso 1.16 renames the skill that starts the next roadmap item. It is a **minor**
release: the old name keeps working for this release, with a warning that names the fix.
The alias is removed in the next major release.

Nothing is rewritten for you. Your project's files, your close-outs, and your history stay
exactly as they are.

---

## Why

The skill that starts the next item now reads like the `virtuoso_registry next` command that
picks it.

| 1.15 | 1.16 |
|---|---|
| skill `dispatch-kickoff` (`/dispatch-kickoff`) | skill `next-dispatch` (`/next-dispatch`) |

`/dispatch-closeout` is unchanged, and the printed block keeps its "Kickoff" heading.

---

## What to do

### 1. Upgrade the plugin

```
/plugin marketplace update virtuoso-marketplace
/plugin install virtuoso@virtuoso-marketplace
```

Start a new session, so the renamed skill loads under its new name.

### 2. Check

```sh
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check
```

```powershell
& "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check
```

A project whose `Virtuoso/workspace-layout.json` names `dispatch-kickoff` (or the 1.14 name
`next-pointer`) reports `virtuoso-status: warning` with one `actor-renamed` finding that
lists each replacement. It keeps working: the warning is the only change.

### 3. Rename the skill in your workspace layout

In `Virtuoso/workspace-layout.json`, replace every `"dispatch-kickoff"` (and any remaining
`"next-pointer"`) with `"next-dispatch"` — in each role's `allowedWriters` and `owner`, and
in `policy.terminalLedger.writers`, `policy.terminalLedger.correctionWriters`, and
`policy.workRegister.creators` — and anywhere else the old name appears. Run the check
again: the warning is gone.

### 4. Update anything of your own that calls the old name

Hooks, scripts, and notes that tell an agent to run `/dispatch-kickoff`. Unlike 1.15's
rename, the old slash command keeps working: `/dispatch-kickoff` prints that it is now
`/next-dispatch` and then runs it in full.

---

## Compatibility — for one release

- **Actors.** Every check of who may write reads `dispatch-kickoff` and `next-pointer` as
  `next-dispatch`, on either side. An old manifest admits the renamed skill, and
  `--actor dispatch-kickoff` still writes.
- **The slash command.** `/dispatch-kickoff` is a thin skill that redirects to
  `/next-dispatch`.
- **New projects** are created naming `next-dispatch`, so they read `ready`.

---

## Deprecated — removed in the next major release

| Deprecated | Use |
|---|---|
| `/dispatch-kickoff` | `/next-dispatch` |
| `dispatch-kickoff`, `next-pointer` as actor names in a workspace layout | `next-dispatch` |

---

## Rolling back

Reinstall 1.15.0 through your plugin host. Nothing in your project needs restoring: 1.16
itself writes no project file.

1.15 does not know `next-dispatch`. If you already renamed the skill in your workspace
layout (step 3), put `dispatch-kickoff` back, or 1.15 refuses the writes that skill makes.
