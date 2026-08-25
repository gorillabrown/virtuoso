# Migrating to Virtuoso 2.0

Virtuoso 2.0 is a **breaking change**. The plugin version moves 1.3.6 → 2.0.0 and the
registry schema moves 1 → 2.

Nothing about the migration is automatic or destructive. A v1 project keeps working in
read mode from the moment you upgrade; the migration itself is previewed and approved like
any other repair.

---

## Why

Three release-blocking behaviours drove the redesign:

1. **Silent governance-file rewriting.** The plugin regenerated the human registry from a
   fixed template, so user prose, custom rows, labels, comments, and ordering could be lost.
2. **Unattended startup writes.** The SessionStart hook ran a healing mode, so starting,
   clearing, or compacting a session could create, heal, vendor, or rewrite project files.
3. **An assumed source of truth.** A local CSV catalog was treated as authoritative because
   of its role *name*, regardless of what the project actually used.

The fix is structural: each project **declares** its live work register, terminal ledger,
compatibility artifacts, ownership rules, and permitted mutations, and the plugin resolves
everything through that declaration.

---

## What to do

### 1. Upgrade the plugin

```
/plugin marketplace update virtuoso-marketplace
/plugin install virtuoso@virtuoso-marketplace
```

### 2. Check, before anything else

```sh
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check --json
```

```powershell
& "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check --json
```

`check` writes nothing. It reports the migration findings you are about to act on.

### 3. Preview the migration

```sh
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode repair
```

The preview names the proposed paths, the semantic changes, the files affected, and where
backups will go. It writes nothing.

### 4. Apply it

```sh
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode repair --apply
```

The apply is transactional: the reconstructed registry is validated **before any write**,
every existing target is copied into a hash-verified backup set first, and any failure
restores from that set and leaves the original registry and manifest intact.

### 5. Classify what migration deliberately left unclassified

Migration is conservative on purpose. Two things need a human decision:

**Your live work register.** v1 had no such role. Add one:

```jsonc
"workRegister": {
  "path": "Project Documentation/2 operational/sprint-catalog.csv",
  "provider": "csv",
  "authority": "live",
  "mutability": "read-write",
  "owner": "roadmap-review",
  "allowedWriters": ["roadmap-review", "next-pointer", "pointer-closeout"],
  "validation": "csv-headers",
  "classification": "active",
  "origin": "authored"
}
```

It does not have to be a file. A connector-backed board, an issue tracker, or a database is
registered by identifier instead:

```jsonc
"workRegister": {
  "external": "monday:board/1234567890",
  "provider": "connector",
  "authority": "live",
  "mutability": "read-write",
  "allowedWriters": ["roadmap-review", "pointer-closeout"],
  "validation": "external",
  "classification": "active",
  "origin": "authored"
}
```

**Any unknown legacy role.** A v1 `paths` key the plugin did not recognize migrates with
`authority: "unknown"` and `mutability: "read-only"`. It is neither writable nor
authoritative until you classify it. The check output names each one.

### 6. Register a terminal ledger

v1 had no separate terminal record. Close-out cannot append one until you register it:

```jsonc
"terminalLedger": {
  "path": "Project Documentation/1 governance/CompletedWork.Ledger.md",
  "provider": "markdown",
  "authority": "terminal",
  "mutability": "append-only",
  "owner": "pointer-closeout",
  "allowedWriters": ["pointer-closeout"],
  "validation": "markdown",
  "classification": "active",
  "origin": "authored"
}
```

### 7. Re-check

```sh
"$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check
```

`ready` means done. `warning` lists what is still unclassified but usable.

---

## Compatibility adapter

Until you register a `workRegister` role, ceremonies still **read** a registered legacy
`sprintCatalog` through an explicitly-labelled compatibility adapter. Reads work; writes do
not, and every report says so.

The adapter is retained for the v2 line. Register a real `workRegister` role to leave it
behind.

---

## Deprecated and removed

### Removed files

| Removed | Replacement |
|---|---|
| `skills/roadmap-review/scripts/recalc.py` | nothing — the dashboard cache it refreshed no longer exists; figures are computed through the provider at read time |
| `scripts/build_sprint_queue.py` | `scripts/build_register_report.py`, which writes only roles the project declared generated |
| `skills/pointer-closeout/scripts/prepare_closeout_files.py` | `virtuoso_registry.py closeout`, read-only unless `--prepare` |
| `skills/roadmap-review/assets/sprint-queue.template.xlsx` | nothing — `create` no longer seeds a workbook |
| `tools/roadmap_visualizer/workbook.py` | the provider layer; the cockpit no longer reads a spreadsheet |
| `Virtuoso/scripts/` (vendored copies) | the version-qualified install record and the launchers |

### Deprecated registry fields

| v1 | v2 |
|---|---|
| `paths` (flat `role: path` map) | `roles` (a full metadata object per role) |
| `paths.scripts` | removed; preserved verbatim under `x-legacy-v1` |
| `paths.governanceReadme` | removed; the human view's location is fixed |
| `layout: "canonical"` | removed in 1.x already; falls back to `plugin-only` |

`paths` is **not** re-emitted after migration. Keeping a second path mapping alive is
precisely the dual-authority problem v2 removes.

### Removed machine state

| Removed | Replacement |
|---|---|
| `~/.virtuoso/plugin-root` (global, unversioned) | `~/.virtuoso/installs.json`, keyed by plugin version |
| — | `~/.virtuoso/bin/virtuoso` and `virtuoso.ps1`, version-agnostic launchers |

The old pointer was a single machine-global file two concurrently installed versions raced
each other for. You may delete it after upgrading; nothing reads it.

### Changed behaviour

| v1 | v2 |
|---|---|
| SessionStart hook ran `--mode detect` (which healed, and auto-scaffolded new roots) | runs `--mode check`: **zero project writes**, always |
| `adopt` healed a marked project | `adopt` against a registered project behaves exactly like `check` |
| `create` ran on request | `create` requires `--authorize` |
| the human registry was regenerated from a template | only its generated region is refreshed; everything else is preserved byte-for-byte |
| repair wrote immediately | repair previews, then applies transactionally with verified backups |
| `sprintCatalog` was "the source of truth" | authority is declared per role; the catalog defaults to a compatibility mirror |
| `--check-roadmap` | `--check-document` (the old flag still works) |
| the dispatch buffer was fixed at 5 | `policy.roadmap.dispatchBuffer`, and `0` disables eager specification |
| phases and stages were assumed | `policy.roadmap.hierarchy`, which may be `[]` |
| the readiness rubric was duplicated in two skills (and disagreed on its size) | one versioned rubric: `references/readiness-rubric.md` |
| "the planner never mutates git" | `policy.git.policy`, a five-rung ladder |
| `main` and `origin` were assumed | both are detected; a repository with no remote is supported |
| a stale lock file could be deleted | it is reported; the plugin never removes it |

---

## New policy block

Everything the plugin used to hardcode now lives under `policy` in the manifest, with a
documented default. Nothing below is required — set only what differs for you.

```jsonc
"policy": {
  "actors": { "planner": "planner", "implementer": "implementation agent" },
  "git": { "policy": "explicit-path-commit", "defaultBranch": "", "remote": "",
           "requireRemote": false, "networkOperations": "ask", "staleLock": "report" },
  "workRegister": { "fieldMappings": {}, "statusMappings": {}, "snapshot": "",
                    "staleAfterHours": 24 },
  "roadmap": { "dispatchBuffer": 5, "eagerSpec": true, "hierarchy": ["phase", "stage"],
               "specStorage": "inline", "lengthCeilingLines": 2000 },
  "rubric": { "version": "1.0", "extensions": [] },
  "standingRules": { "source": "roadmap", "ids": [] },
  "issues": { "targets": ["local"], "externalRole": "" },
  "terminalLedger": { "writers": ["pointer-closeout"],
                      "correctionWriters": ["pointer-closeout"], "format": "markdown" },
  "sweep": { "exclude": ["Virtuoso/.backups/**"], "deletionPolicy": "quarantine",
             "structuralAuthority": "registry", "backupRetention": 10 }
}
```

---

## Rolling back

Every repair and migration writes a verified backup set under `Virtuoso/.backups/` with a
manifest recording each entry's source, destination, byte count, SHA-256, timestamp, and
operation. To restore, verify the set and copy its contents back:

```python
from tools.governance import backup
backup_set = backup.load_set("<project>/Virtuoso/.backups/<stamp>-repair", "<project>")
print(backup.verify(backup_set))     # [] means restorable
backup.restore(backup_set)
```

`policy.sweep.backupRetention` (default 10) prunes older sets; backup and quarantine
directories are excluded from governance sweeps so they never become new findings.
