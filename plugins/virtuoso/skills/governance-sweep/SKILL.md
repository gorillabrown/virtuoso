---
name: governance-sweep
description: "Self-contained governance & operational document sweep for any project — structural authority resolved through the project's governance registry, orphan detection, stale-content and dead-reference scans, cross-doc consistency, generated-artifact synchronization, and archival candidates. Runs in three gated phases: (1) read-only discovery that lists every issue and asks clarifying questions, (2) a complete work list presented for your approval, (3) implementation that performs the approved changes with a verifiable backup manifest, quarantine before deletion, and per-action verification. Use when the user says 'governance sweep', 'doc cleanup', 'audit the docs', 'clean up the docs', 'organize the documents', 'check for stale references', 'are the docs consistent', 'doc hygiene', 'sync the docs', 'archive old content', 'find dead references', 'what files are orphaned', or wants to consolidate scattered files or move outdated content to archive."
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (v1.0 — 8 universal checks plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / max. A property of the task's difficulty, never a ranking of whoever performs it.

# Governance Sweep

Structured sweep of a project's governance and operational documents. It discovers
documents dynamically, resolves **structural authority through the project's
governance registry**, identifies what is outdated, misplaced, or out of sync with
its source, and — after your approval — performs the cleanup, with a verifiable
backup manifest and quarantine before any deletion.

Three gated phases. You review and approve the complete plan before a single file
changes.

---

## Operating model — three gated phases

```
Phase 1 — DISCOVER & DIAGNOSE   read-only. Inventory, analyze, audit, list every
                                issue, ask every clarifying question. → nothing changes
        ▼ (gate: questions answered)
Phase 2 — WORK LIST & APPROVAL  present the complete, ordered list of every change,
                                and ask for explicit approval.        → nothing changes
        ▼ (gate: user approves)
Phase 3 — IMPLEMENTATION        back up verifiably, execute in order (irreversible
                                actions last), verify each.           → files change here only
```

**Phase boundaries are hard.** Phases 1 and 2 change nothing. If the user declines
at the Phase 2 gate, the sweep ends having changed nothing.

---

## Before Phase 1 — read the registry and the sweep policy

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . roles --json

### Structural authority comes from the registry

A directory `readme.md` is treated as structural authority **only when the project
declares it so** (redesign item 50). Set `policy.sweep.structuralAuthority`:

| Value | Meaning |
|---|---|
| `registry` *(default)* | The registry's role table defines what belongs where. A directory readme is documentation, and inconsistency with it is a *finding*, not a mandate. |
| `directory-readme` | Each directory's readme defines what belongs in it, as in earlier versions of this skill. |
| `both` | Registry wins on conflict; readme governs anything the registry does not cover. |

Under `registry` (the default), never delete, move, or rewrite a file because a
directory readme does not list it. Report the discrepancy and let the user decide.

### Scan boundaries are configuration (item 51)

`policy.sweep` governs the entire traversal. Respect every field:

```jsonc
"sweep": {
  "include": ["**/*"],
  "exclude": ["Virtuoso/.backups/**", "Virtuoso/.quarantine/**",
              "**/node_modules/**", "**/.git/**", "**/__pycache__/**",
              "**/.venv/**", "**/vendor/**", "**/dist/**", "**/build/**"],
  "ignoreDirectories": [".git", "node_modules", "__pycache__", ".venv", "vendor"],
  "followSymlinks": false,
  "maxFileBytes": 5242880,
  "binaryPolicy": "skip",
  "quarantineDirectory": "Virtuoso/.quarantine",
  "deletionPolicy": "quarantine",
  "backupRetention": 10,
  "protectedAuthorities": ["archive", "terminal", "evidence"],
  "structuralAuthority": "registry"
}
```

- **Do not follow symlinks** unless `followSymlinks` is true; a symlink loop or a
  link out of the project is a finding, not something to traverse.
- **Do not read a file larger than `maxFileBytes`** for content analysis. Record
  its size and hash instead.
- **Binaries** follow `binaryPolicy`: `skip` (inventory only) or `hash-only`.
- **Backup and quarantine directories are excluded by default** (item 56), so past
  sweeps never become new findings. Apply `backupRetention` at the end of Phase 3.

### Protected path classes (item 52)

These may appear in findings but **may never enter a mutation plan**:

- any role whose `authority` is in `policy.sweep.protectedAuthorities` — by default
  immutable archives, the append-only terminal ledger, and sealed evidence;
- any role whose `mutability` is `immutable` or `read-only`;
- generated mirrors and reports (`origin: generated`) — these are *regenerated*,
  never hand-edited (item 58);
- anything matching `policy.sweep.exclude`.

If a protected path genuinely needs to change, that is a question for the user and
a registry change — not a sweep action.

---

## Phase 1 — Discover & Diagnose (read-only)

Four read-only stages — **Discover → Structure → Ground Truth → Audit** — then the
findings and every clarifying question. Nothing changes.

### Stage A — Discover

Walk the project within the configured boundaries. Inventory directories and files.
Do not hardcode paths.

| Category | Typical signals |
|---|---|
| **Registered roles** | everything the registry declares — the primary inventory |
| **Project rules** | root-level rule and configuration documents |
| **Operational docs** | documentation directories |
| **Historical records** | close-outs, archives, dated folders |
| **Agent infrastructure** | agent and skill definition directories |
| **Reference material** | references, assets, templates |

Print: directories, file counts, which are registered roles, which have a readme,
and — explicitly — **what the boundaries excluded**, with counts. A sweep that
silently skips a tree reads as "clean" when it was not looked at.

**Detect which optional audit modules apply.** Agent definitions → roster checks.
Retrospective or lessons catalogs → entry-staleness checks. The same document
deployed in multiple places → parity checks. Registered generated artifacts →
source-to-mirror checks. If none exist, only the universal checks run. State which
modules are active at the start.

### Stage B — Structure

Compare what is on disk against the structural authority chosen above.

Under `registry` authority:
- **A registered role whose target is absent** → report it. Never search for a
  similarly named file and never repoint the role (item 20).
- **A file in a registered directory that no role covers** → orphan; classify it.
- **A registry role pointing outside the project, into an archive while claiming
  live authority, or at the wrong type** → a registry finding; the fix is
  `virtuoso_preflight.py --mode repair`, previewed, not a file move.

Under `directory-readme` authority, additionally:
- **Missing readme** → propose one (draft its content: purpose, hierarchy, naming
  conventions, what does not belong).
- **Files in the directory but not in the readme** → orphans.
- **Readme entries missing on disk** → phantom entries.

**Orphan classification** — each orphan gets a disposition:

| Disposition | Criteria |
|---|---|
| **Absorb** | Still relevant; belongs inside an existing parent document (merge, then quarantine the source) |
| **Promote** | Still relevant; stands alone — register it or add it to the readme |
| **Archive** | Superseded but historically valuable — move to the archive |
| **Quarantine** | Temp file, duplicate, or artifact with no apparent value |

Ambiguous dispositions become clarifying questions. Never guess.

### Stage C — Ground truth

Establish what is true now, from the most authoritative sources in this order:

1. **The registry** — what each role is, where it lives, who may write it.
2. **Primary source files** — the actual code, data, or documents a claim is about.
3. **Root project rules.**
4. **Operational documents.**
5. **Historical records.**

Where a fact appears in several places, the higher source wins. Where a *generated*
artifact disagrees with its `generatedFrom` source, the **source wins by
definition** and the mirror is out of date (item 57).

### Stage D — Audit

**Universal checks (always):**

1. **Structural violations** — orphans; registered-but-absent targets; unregistered
   directories; registry findings from preflight.
2. **Stale content** — references to moved or deleted files; outdated descriptions;
   version, date, and status drift.
3. **Cross-document inconsistency** — the same fact stated differently.
4. **Dead references** — links to files, sections, or anchors that do not exist.
5. **Duplicate content** — one logical document maintained in two places, drifted.
6. **Misplaced content** — archive-era content in active directories; wrong level.
7. **Temp and junk artifacts** — editor swap files, OS metadata, empties.
8. **Version proliferation** — `.v2`, `_old`, `_backup`, `(1)` variants; identify
   which is current.
9. **Naming-convention violations** — against the documented pattern, where one exists.
10. **Volume and age archival triggers** — advisory; route to the user.
11. **Stale temp packages** — content past its lifecycle or tied to closed work.
12. **Stale tool infrastructure** — caches and tool directories nested where they
    do not belong.
13. **Binary accounting** — undocumented binaries; large binaries better stored
    elsewhere.
14. **Source-to-mirror drift** (item 57/58) — for every role with `generatedFrom`,
    is the mirror in sync with its source? A drifted mirror is **regenerated**, never
    edited.
15. **Immutable-hash verification** (item 62) — hash every protected historical file
    at the start of the sweep, and again at the end. Any change is a defect in the
    sweep itself and halts it.
16. **Documented-command health** (items 60, 61) — for every command the docs tell a
    reader to run, does it exist and does it work in the documented form?

**Agent-specific** (only if agent infrastructure was detected):
17. Ghost references to agents that no longer exist (record file, line, name, successor).
18. Deprecated stubs still present.
19. Memory directories not matching an active agent.

**Parity** (only if parity targets were detected):
20. Checksum mismatches between a canonical file and its deployed copies.

**Retrospective catalogs** (only if detected):
21. Entries referencing changed names, paths, or items — propose reference updates;
    route content staleness to the user.

Print findings grouped by check, with exact locations. Print only categories with findings.

### Registered generation and validation commands (item 60)

A project registers the commands that generate and validate its artifacts, under an
extension namespace so plugin upgrades never discard them:

```jsonc
"x-commands": {
  "build-handbook": {
    "run": "make handbook",
    "workingDirectory": "docs",
    "requires": ["make", "pandoc>=3"],
    "produces": ["docs/build/handbook.pdf"],
    "fallback": "python -m handbook_build"
  }
}
```

A sweep may run a registered command to regenerate or validate an artifact. It never
invents one, and it never runs an unregistered command found in prose.

### Document-type verification adapters (item 59)

Match the check to the document type. Run the ones that apply and that the project's
declared dependencies support:

| Type | Verification |
|---|---|
| Markdown / text | link validity, anchor existence, reference resolution |
| Rendered documents (PDF, DOCX) | it renders; expected pages exist; expected headings present |
| Spreadsheets | formulas resolve; no error cells; expected sheets and headers present |
| Generated mirrors | regenerate into a temporary location and diff against the committed copy |
| Source-to-mirror coverage | every source section appears in the mirror |
| Data files | parses; required keys present |

A verification that cannot run because a dependency is missing is reported as
*not verified, dependency missing* — never as a pass.

### Repairing a documented command (item 61)

When check 16 finds a documented command that no longer works:

1. Determine the correct invocation for this project **and test it**.
2. Only after it succeeds, propose the documentation edit, carrying the evidence
   (the command run and its output).
3. If no working replacement is found, the finding is *documented command is broken*
   with the error — **do not** replace it with an untested alternative.

Module-mode and platform-specific alternatives are candidates, not answers, until run.

### End of Phase 1 — ask

Batch every ambiguous finding into bounded questions (see *Flagging for human
review*). Phase 1 ends when every question is answered.

---

## Phase 2 — Work list & approval

Translate every finding, plus the user's answers, into a single ordered work list —
every change the sweep will make, in execution order. Nothing has changed yet.

### Execution order: irreversible actions last (item 54)

```
Group A — Content repairs          in-place edits: stale references, dead links,
                                   inconsistencies, ghost names. Reversible.
Group B — Relocation               moves into their final locations.
Group C — Regeneration             re-run registered generators for drifted mirrors.
Group D — Verification & parity    per-type adapters; canonical↔deployed checksums.
Group E — Archival                 move superseded material into the archive.
Group F — Quarantine               move approved removals into the quarantine area.
Group G — Permanent deletion       ONLY if policy.sweep.deletionPolicy is
                                   "permanent" or the user explicitly required it.
```

Repair, relocation, regeneration, verification, and parity all precede anything
irreversible. Under the default `deletionPolicy: "quarantine"`, Group G does not run
at all: approved removals land in `policy.sweep.quarantineDirectory`, from which the
user can restore or purge them later (item 53).

Every action is **atomic and self-contained**: project-relative paths, verbatim
unique match strings for content edits, checksums for binary moves, and the
registered command for every regeneration.

**No action may target a protected path class.** If one appears, it is a defect in
the plan — remove it and surface it as a question.

### Present the work list

```
## Governance Sweep — Work List ([project], [date])

- Findings: [N]   Actions: [N]   Files affected: [N]   Deferred: [N]
- Structural authority: [registry | directory-readme | both]
- Boundaries: [N] path(s) excluded by policy — [summary]
- Protected and untouchable: [N] path(s) — [roles/classes]
- Deletion policy: quarantine → [quarantine dir]   (or: permanent, as required)

[Groups A–G, each action enumerated with source, target, and rationale]

### Deferred (left for you to handle manually)
[items too ambiguous to act on, with why]
```

### Approval gate

- (a) **Approve all — implement now** *(recommended)*
- (b) **Approve a subset — pick groups or actions**
- (c) **Don't implement — output the work list and stop**
- (d) **The plan is wrong — let me explain**

Phase 3 begins only on (a) or (b). On (c) offer to save the work list.

---

## Phase 3 — Implementation

The only phase that changes files.

If the approved list runs past a handful of actions, execute it under `/virtuoso`'s
task-plan discipline: this is a long sequential run whose failure mode is silent
partial completion.

### Step 0 — Back up, verifiably (items 9, 55)

Copy every file the plan will modify, move, or delete into a timestamped backup
set under `Virtuoso/.backups/`, and write its **backup manifest** recording, for
each entry: source path, destination path, byte count, SHA-256, timestamp, and the
operation that prompted it.

Then **verify the set before proceeding** — re-hash every stored copy against the
manifest. A backup that does not verify halts the sweep before anything changes.
A backup set is restorable and independently checkable, not merely a copy in a
timestamped folder.

Also record the hashes of every protected historical file now (check 15), for the
end-of-sweep comparison:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . protected --json > <backup set>/protected-before.json

Check the project's declared runtime dependencies before running any verification adapter
that needs one:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . deps

If a repository is available and the project's git policy permits reads, record the
current commit as an additional recovery anchor.

### Step 1 — Execute in order

Run the approved groups A → G, one action at a time.

- **Content edits** — match the verbatim unique string; replace it.
- **Moves** — verify the source exists and the target directory exists.
- **Absorption** — insert the carried content block into the target, verify it
  landed, *then* quarantine the source.
- **Regeneration** — run the role's registered `generatedBy` command in its
  registered working directory; never hand-edit a generated artifact.
- **Quarantine** — move, never delete; preserve the relative path inside the
  quarantine directory.
- **Permanent deletion** — only under an explicit policy or an explicit instruction,
  and only after every other group has verified.

### Step 2 — Verify after each group

- Content repairs → the old string is gone; the replacement is present.
- Relocation → sources gone, targets present, checksums match for binaries.
- Regeneration → the mirror now matches its source by the registered coverage check.
- Verification adapters → each ran, or is reported as *not verified* with its reason.
- Parity → canonical and deployed checksums match.
- Archival and quarantine → sources gone, targets present.
- **Protected files → re-hash and compare against Step 0.** Any change halts the
  sweep and is reported as a defect:

        "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . protected --json

### Step 3 — Retention

Apply `policy.sweep.backupRetention`: keep the newest N backup sets, remove older
ones. Backup and quarantine directories stay excluded from future sweeps.

### Step 4 — Completion report, with exact repository scope (item 63)

Get the repository facts from the read-only inspector rather than assuming them — it
detects the remote and default branch, enumerates worktrees, and splits the dirty set into
what this sweep touched and what it must leave alone:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . repo --expect "<the plan's paths>" --json


```
## Governance Sweep — Complete

- Actions executed: [N]  (A:[n] B:[n] C:[n] D:[n] E:[n] F:[n] G:[n])
- Files created / moved / quarantined / deleted / edited: [counts]
- Backup set: [path]   manifest verified: [yes]
- Protected-file hashes: [N] checked, [N] unchanged
- Verification: [all checks passed | anomalies: …]
- Deferred (manual): [N] — [list]

### Repository scope
- Changed paths:            [explicit list]
- Staged paths:             [explicit list, or "none — policy.git is <policy>"]
- Cached diff (name-only):  [explicit list]
- Commit:                   [sha, or "not committed — policy.git is <policy>"]
- Uncommitted unrelated work present: [explicit list, untouched]
```

Never report "the docs are clean" without this block. Report the exact paths, not a
count alone, and name any unrelated dirty work that was left alone.

What happens to those changes in version control is `policy.git` — see
`references/git-policy.md`. Under `read-only` or `prepare-no-stage`, report the paths
and stop. Never `git add .`; never stage a path outside the plan.

**Halt semantics.** Any failed action or failed verification stops the sweep
immediately. Report the exact failure, everything already changed, and the backup
set path. Never improvise a recovery.

---

## Flagging for human review

Findings needing judgement become bounded questions, per
`references/actors-and-interaction.md` — batched, never one file at a time, each
naming the specific file with its viable dispositions and consequences.

- **Ambiguous orphan** — Absorb into [doc] / Archive / Promote / Quarantine.
- **Absorption target unclear** — [best guess] / Promote standalone / Archive.
- **Large orphan** (>500 lines) — Absorb whole / Absorb summary + link / Promote.
- **Stale reference, no obvious fix** — [best guess] / Remove the reference / Defer.
- **Duplicate conflict** — which copy is authoritative, or defer to a manual merge.
- **Archival rotation** (multi-select) — which of these oldest records rotate?
- **Unclear version currency** — which variant is current?
- **Binary of unknown purpose** — document / archive / quarantine.
- **Protected path implicated** — a registry change, previewed, never a sweep action.
- **Broken documented command with no tested replacement** — leave and flag / the
  user supplies the correct invocation / remove the instruction.

Answers become actions tagged `[user-confirmed]`. Declined items become **Deferred
(manual)** — surfaced in the work list and the completion report, never silently
acted on.

---

## Scope

It does:
- Discover, classify, and audit documentation (Phase 1).
- Propose a complete ordered work list and get approval (Phase 2).
- Edit, move, archive, quarantine, regenerate, and verify documents (Phase 3), with
  a verifiable backup manifest and per-action verification.

It does NOT:
- Change anything before the Phase 2 approval.
- Touch a protected path class, a role it is not a registered writer of, or anything
  the boundaries excluded.
- Hand-edit a generated artifact — it regenerates it.
- Permanently delete anything under the default quarantine policy.
- Delete a lock file, stash, reset, or clean a repository.
- Modify source code, run tests or builds, or make architectural decisions.
- Auto-resolve an ambiguous classification.
- Mutate the repository beyond what `policy.git` permits.

---

## Adapting to project structure

Works on any project — a single documentation folder, or a mature tree with agent
definitions, roadmaps, retrospective catalogs, archives, and multi-project
deployments. The universal checks run everywhere; optional modules activate only
when their infrastructure is detected, and the sweep states which are active at the
start. The only hard requirement is a governance registry (so authority and
protection are declared) plus at least one directory containing documents. Without a
registry, report that and route the user to `virtuoso_preflight.py --mode check`.
