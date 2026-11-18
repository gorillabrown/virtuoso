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

# Governance Sweep

Structured sweep of a project's governance and operational documents: it discovers
documents dynamically, resolves **structural authority through the project's governance
registry**, finds what is outdated, misplaced, or out of sync with its source, and — only
after your approval of the complete plan — performs the cleanup, with a verifiable backup
manifest and quarantine before any deletion.

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
declares it so** (redesign item 50), in `policy.sweep.structuralAuthority`: `registry`
*(default)*, `directory-readme`, or `both` (registry wins on conflict) — each value's
meaning is in [references/sweep-policy.md](references/sweep-policy.md).

Under `registry` (the default), never delete, move, or rewrite a file because a
directory readme does not list it. Report the discrepancy and let the user decide.

### Scan boundaries are configuration (item 51)

`policy.sweep` governs the entire traversal; respect every field (names and shipped
defaults: [references/sweep-policy.md](references/sweep-policy.md)). In particular:

- **Do not follow symlinks** unless `followSymlinks` is true; a symlink loop or a link out
  of the project is a finding, not something to traverse.
- **Do not read a file larger than `maxFileBytes`** for content analysis; record its size
  and hash instead.
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
Do not hardcode paths. Categories: **registered roles** (everything the registry declares —
the primary inventory), **project rules** (root-level rule and configuration documents),
**operational docs** (documentation directories), **historical records** (close-outs,
archives, dated folders), **agent infrastructure** (agent and skill definition
directories), **reference material** (references, assets, templates).

Print: directories, file counts, which are registered roles, which have a readme,
and — explicitly — **what the boundaries excluded**, with counts. A sweep that
silently skips a tree reads as "clean" when it was not looked at.

**Detect which optional audit modules apply** — agent definitions → roster checks; a
registered `lessons` role → lessons hygiene (check 21); one document deployed in several
places → parity checks; registered generated artifacts → source-to-mirror checks. With
none, only the universal checks run. State which modules are active at the start.

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

**Before running the checks, read [references/audit-checks.md](references/audit-checks.md)**
— every check in full, registered commands, verification adapters, and documented-command
repair. Run universal checks 1–16 always (check 15: any change to a protected file halts
the sweep); agent checks 17–19, parity check 20, and lessons hygiene check 21 only where
Stage A detected their module; **Disk footprint** check 22 always, in a git repository.
Run only registered commands; a verification whose dependency is missing is *not verified,
dependency missing*, never a pass; replace a broken documented command only with one that
ran and succeeded.

Print findings grouped by check, with exact locations. Print only categories with findings.

### End of Phase 1 — ask

Batch every ambiguous finding into bounded questions (see *Flagging for human
review*). Phase 1 ends when every question is answered.

**Applied findings.** Before listing open findings, read `virtuoso_registry changes --json`
(`inForce`) and `results --json`: a finding or lesson whose subject has a change in force is
not an open finding — list it in an **Applied** block with its verdict so far. A finding that
prices something uses the one finding format (tier, confidence, kind, now → after).

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

Check 22's removals never pass through the quarantine area (they are not project files):
each is its own Group F action, the `footprint --remove <path> --apply` command, run after
every other Group F move. Only `redundant` and `regenerable` candidates enter the work
list; a `unique` or `evidence` candidate is a question for the user, never an action.

Every action is **atomic and self-contained**: project-relative paths, verbatim
unique match strings for content edits, checksums for binary moves, and the
registered command for every regeneration.

**No action may target a protected path class.** If one appears, it is a defect in
the plan — remove it and surface it as a question.

<!-- rule:grep-registry-before-moving (registry-before-move) -->
**Before proposing that any document move, grep the registry contents for its path.**
The registry is `Virtuoso/workspace-layout.json` plus the `virtuoso-governance-registry`
machine block in the project-root governance readme. A registered document that moves
without its registry entry moving in the same change leaves every skill resolving that
role to a path that no longer exists — and the next heal will either mark the role
`⬜ not present` or repoint it somewhere nobody chose.

Concretely, for each proposed move:

```bash
grep -rn "<current/relative/path>" Virtuoso/workspace-layout.json <governance-readme>
```

If the path appears, the move is not a file operation — it is a **registry amendment
plus** a file operation, and both land in the same change. If it does not appear, the
document is unregistered and moving it is safe.

### Present the work list

Present it in the *Work list* format of
[references/sweep-formats.md](references/sweep-formats.md): the counts, structural
authority, excluded boundaries, protected paths, deletion policy, Groups A–G with each
action's source, target and rationale, and the Deferred items with why.

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

Copy every file the plan will modify, move, or delete into a timestamped backup set under
`Virtuoso/.backups/`, with a **backup manifest** recording, per entry: source path,
destination path, byte count, SHA-256, timestamp, and the operation that prompted it.
Then **verify the set before proceeding** — re-hash every stored copy against the manifest.
A backup that does not verify halts the sweep before anything changes. A backup set is
restorable and independently checkable, not merely a copy in a timestamped folder.

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
- **Lesson records** — for each approved merge, retirement, tidy or **record**, append
  the status record (and any restatement first), one at a time, and read it back:

      "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --record-status <ID> --status "<status>" --actor governance-sweep --item sweep --apply

  Never edit or delete an existing entry. Re-run `lessons --hygiene` afterwards; the
  approved proposals, approved `unrecorded` entries included, must be gone from it.

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

Get the repository facts from the read-only inspector, never by assumption — it detects the
remote and default branch, enumerates worktrees, and splits the dirty set into what this
sweep touched and what it must leave alone:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . repo --expect "<the plan's paths>" --json

Then write the completion report in the *Completion report* format of
[references/sweep-formats.md](references/sweep-formats.md), including its
**Repository scope** block.

**Record what outlives the sweep.** Every deferred item, every flag for human review,
and every audit finding the work list did not fix is appended to the registered
`findings` role as its own entry — `### F-NNN — title (governance-sweep, YYYY-MM-DD)`
with **Source**, **Severity**, **Where**, **Finding** and **Disposition:** `open` —
so the next roadmap review reads it instead of a chat nobody reopens. If the project
registers no `findings` role, show the entry to add to the manifest and say the findings
exist only in this report.

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
`references/actors-and-interaction.md` — batched, never one file at a time, each naming the
specific file with its viable dispositions and consequences.

**Before asking, read [references/sweep-formats.md](references/sweep-formats.md)**,
*Human-review questions* — each finding type with the dispositions to offer.

Answers become actions tagged `[user-confirmed]`. Declined items become **Deferred
(manual)** — surfaced in the work list and the completion report, never silently
acted on.

---

## Scope

It does: discover, classify, and audit (Phase 1); propose the work list and get approval
(Phase 2); edit, move, archive, quarantine, regenerate, and verify documents (Phase 3).

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

Works on any project, from a single documentation folder to a mature multi-project tree;
optional modules activate only when detected (Stage A). The only hard requirement is a
governance registry (so authority and protection are declared) plus at least one directory
containing documents. Without a registry, report that and route the user to
`virtuoso_preflight.py --mode check`.
