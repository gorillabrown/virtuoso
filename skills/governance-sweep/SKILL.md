---
name: governance-sweep
description: "Self-contained governance & operational document sweep for any project — directory structure via readme.md authority, orphan detection, stale-content and dead-reference scans, cross-doc consistency, archival candidates, and optional agent-roster checks. Runs in three gated phases: (1) read-only discovery that lists every issue and asks clarifying questions, (2) a complete work list presented for your approval, (3) implementation that performs the approved changes with backups and verification. Use when the user says 'governance sweep', 'doc cleanup', 'audit the docs', 'clean up the docs', 'organize the documents', 'check for stale references', 'are the docs consistent', 'doc hygiene', 'sync the docs', 'archive old content', 'find dead references', 'what files are orphaned', or wants to enforce a readme-based hierarchy, consolidate scattered files, or move outdated content to archive."
---

# Governance Sweep

Structured sweep of all governance and operational documents in a project. Works on any
project — from a folder of markdown files to a full multi-agent codebase. It discovers docs
dynamically, evaluates structural authority via readme.md files, identifies what's outdated
or misplaced, and — after your approval — **performs the cleanup itself**.

This skill is **self-contained**: it both diagnoses and fixes, in three gated phases. You
review and approve the complete plan before a single file changes.

---

## Operating Model — Three Gated Phases

The sweep runs in three phases. Each phase ends at a hard gate; the next phase does not begin
until the gate is cleared.

```
Phase 1 — DISCOVER & DIAGNOSE   read-only. Inventory, analyze, audit. List every issue.
                                Ask any clarifying questions.  → no files change
        ▼ (gate: questions answered)
Phase 2 — WORK LIST & APPROVAL  present the complete, ordered list of every change to be
                                made. Ask for explicit approval to proceed.  → no files change
        ▼ (gate: user approves)
Phase 3 — IMPLEMENTATION        back up, then execute the approved actions in order, and
                                verify each.  → files change here, and only here
```

**Phase boundaries are hard.** Phase 1 and Phase 2 are strictly read-only — they inventory,
classify, and plan, but change nothing. Files are modified **only in Phase 3, and only after
the user approves the Phase 2 work list.** If the user declines at the Phase 2 gate, the
sweep ends having changed nothing.

**Safety in Phase 3:** before any mutation, copy every file the plan will touch into a
timestamped backup directory. Execute actions in the documented order (lowest blast radius
first). Verify after each action group. If anything looks wrong, stop and report — do not
improvise recovery.

> Note on history: earlier versions of this skill were read-only and emitted a spec for a
> separate executor, because the original Cowork browser-sandbox could corrupt mounts/git on
> direct file writes. In a native environment (Claude Code) that constraint does not apply —
> so this skill performs the work directly, gated by approval and protected by backups.

---

## When to use

Project documentation drifts: files accumulate with no record of what belongs, stale memos
sit next to active specs, duplicate docs diverge, and nobody can confidently delete anything.
Run this skill to impose and maintain structure deliberately — discover what's wrong, agree
on the fix, and apply it in one controlled pass.

---

## Phase 1 — Discover & Diagnose (read-only)

Phase 1 runs four read-only stages — **Discover → Structure → Ground Truth → Audit** — then
lists every finding and asks any clarifying questions. **No files change in this phase.**

### Stage A — Discover

Scan the project directory to inventory document directories and files. Do not hardcode
paths — discover them.

| Category | Typical signals |
|----------|----------------|
| **Project rules** | `CLAUDE.md`, `README.md`, root-level config docs |
| **Operational docs** | `docs/`, `documentation/`, numbered doc folders |
| **Historical records** | `CloseOut.*`, `archive/`, dated folders |
| **Agent infrastructure** | `.claude/agents/`, `.claude/skills/` |
| **Reference material** | `references/`, `assets/`, `templates/` |

Print the inventory: directories, file counts, and which have a `readme.md`.

**Detect project type** (determines which optional audit modules activate in Stage D):
`.claude/agents/*.md` → agent-roster checks; `**/SpecRetro*` / `*lesson*` → SRL staleness;
skills in multiple locations → parity checks; `**/roadmap*` / `**/sprint-queue*` → sprint
artifact checks. If none exist, only the universal checks run.

### Stage B — Structure

For each document directory, the `readme.md` is the structural authority — it defines what
files belong, what subdirectories exist, and the naming conventions. Compare each directory's
actual contents against its readme.

- **Missing readme** → note that one should be created (draft its proposed content: purpose,
  file hierarchy with one-line descriptions, naming conventions, "what does NOT belong here").
- **Files in directory but not in readme** → orphans (classify below).
- **Files in readme but not on disk** → phantom entries (flag for removal or recovery).
- **Undocumented subdirectories** → flag.

**Orphan classification** — for each orphan, choose a disposition:

| Disposition | Criteria |
|-------------|----------|
| **Absorb** | Still relevant; belongs inside an existing parent doc (merge then delete) |
| **Promote** | Still relevant; stands alone — add it to the readme |
| **Archive** | Outdated/superseded but has historical value — move to archive |
| **Delete** | Temp file, duplicate, or artifact with no value |

Ambiguous dispositions become clarifying questions (see Flagging for Human Review).

### Stage C — Ground Truth

Establish what is actually true now, from the most authoritative sources: project root docs
(`CLAUDE.md`/`README.md`), directory readmes, and the real on-disk file state. If agent
infrastructure exists, read `.claude/agents/*.md` frontmatter to build the active-agent roster
and the deprecated→successor mapping. Where the same fact appears in multiple docs, pick the
authoritative source (priority: primary source files → root docs → operational docs →
historical records).

### Stage D — Audit

Compare every document against ground truth and the structural authority. Enumerate every
finding. Run the universal checks always; run the optional modules only if their
infrastructure was detected.

**Universal checks (always):**
1. **Structural violations** — orphans needing action; readme entries missing on disk; undocumented dirs.
2. **Stale content** — references to moved/deleted files, outdated descriptions, version/date/status drift.
3. **Cross-document inconsistency** — the same fact stated differently across docs.
4. **Dead references** — links/pointers to files, sections, or headers that don't exist.
5. **Duplicate content** — the same logical doc maintained in two places, drifted apart.
6. **Misplaced content** — archive-era content in active dirs; wrong hierarchy level; tool dirs nested in doc trees.
7. **Temp/junk artifacts** — `.tmp`/`.bak`/swap files, hash-like names, empties, `.DS_Store`/`Thumbs.db`/`desktop.ini`.
8. **Version proliferation** — `file.v2.xlsx`, `_old`, `_backup`, `(1)` variants; identify the current one.
9. **Naming-convention violations** — files not matching the directory readme's documented pattern.
10. **Volume/age archival triggers** — high-count close-out/memo dirs where the oldest should rotate to archive (advisory — route to human review).
11. **Stale temp packages** — content in `temp/`/`scratch/` past its lifecycle or tied to completed work.
12. **Stale tool infrastructure** — `.claude/`, `agent-memory/`, `__pycache__/` nested where they don't belong.
13. **Binary file accounting** — `.xlsx`/`.docx`/`.pdf`/`.zip` not documented in their directory's readme; large binaries better stored elsewhere.

**Agent-specific (only if agent infra detected):**
14. **Ghost agent references** — agent names in docs that match no active agent file (record file, line, ghost name, successor).
15. **Deprecated stub presence** — `disabled: true` agent files still present (flag with merge target).
16. **Agent memory dir names** — dirs in `.claude/agent-memory/` not matching an active agent.

**Multi-project (only if parity targets detected):**
17. **Parity divergence** — checksum mismatches between canonical and deployed copies of shared files.

**SRL-specific (only if SRL/lessons catalog detected):**
18. **SRL/finding staleness** — entries referencing changed agent names, paths, or sprints (propose name updates; flag content staleness for human review).

Print findings grouped by check type with exact locations. Only print categories that
produced findings.

### End of Phase 1 — ask clarifying questions

Collect every ambiguous finding (ambiguous orphan dispositions, unclear absorption targets,
stale references with no obvious replacement, duplicate-merge conflicts, archival-rotation
candidates, unclear version currency, binaries of unknown purpose) and ask them now via
AskUserQuestion (see Flagging for Human Review). Do not guess. The answers feed the Phase 2
work list. **Phase 1 ends when every clarifying question is answered.**

---

## Phase 2 — Work List & Approval

Translate every Phase 1 finding (plus the user's answers) into a single, complete, ordered
**work list** — every change the sweep will make, in execution order. Present it in chat and
**ask for explicit approval before proceeding.** Nothing has changed yet.

### Work-list structure

Group actions to minimize blast radius if something errors mid-run (this is also the Phase 3
execution order):

- **Group A — Junk removal** — delete temp files, OS artifacts, swap files, empties. (Lowest risk, first.)
- **Group B — Misplaced-content relocation** — `move` source → target, each with a one-line rationale.
- **Group C — Archival** — move orphans, old versions, and approved rotation candidates to archive.
- **Group D — Orphan absorption** — merge a file's content into a target doc §section, then delete the source. (Carries the exact content block to insert.)
- **Group E — readme.md synchronization** — create/update readme files (each carries the full proposed content).
- **Group F — Content repairs** — in-place edits for stale references, dead links, cross-doc inconsistencies, ghost agent names. (Each carries file, exact match string, replacement, rationale.)
- **Group G — Parity sync** (if applicable) — copy canonical → deployment targets, with checksum verification.

Every action is **atomic and self-contained**: absolute or project-relative paths; verbatim,
unique match strings for content edits; checksums for binary moves.

### Present the work list

Show the user:
```
## Governance Sweep — Work List ([project], [date])
- Findings: [N]   Actions: [N]   Files affected: [N]   Deferred to manual: [N]

[Action groups A–G, each action enumerated with source/target/rationale]

### Deferred (left for you to handle manually)
[items too ambiguous to act on, with why]
```

### Approval gate (AskUserQuestion)

Ask: **proceed with implementation?**
- (A) **Approve all — implement now** [RECOMMENDED]
- (B) **Approve a subset — let me pick which groups/actions**
- (C) **Don't implement — output the work list and stop** (read-only result)
- (D) **The plan is wrong — let me explain**

**Phase 3 begins only on (A) or (B).** On (C) the sweep ends having changed nothing; offer to
save the work list to `governance-sweep-worklist.<date>.md` for later.

---

## Phase 3 — Implementation

Execute the approved actions. **This is the only phase that changes files.**

### Step 0 — Back up

Create a timestamped backup directory and copy every file the approved plan will modify,
move, or delete (preserving relative paths):
```
<project-root>/.governance-sweep-backup/<YYYY-MM-DD-HHMMSS>/
```
(Pass the timestamp in, or derive it from the OS — do not fabricate.) If git is available and
the project's workflow permits it, note the current commit for an extra recovery anchor.

### Step 1 — Execute in order

Run the approved groups in order A → B → C → D → E → F → G. Within each group, apply actions
one at a time. Rationale for the ordering: junk removal is irreversible-but-safe and shrinks
the working set; moves/archival run before absorption so targets are in final locations;
readme sync runs after files have moved so it reflects reality; content repairs run last so
they edit files already in place; parity sync is fully derivative and runs last.

For content edits, match the verbatim unique string and replace it. For moves, verify the
source exists and the target directory exists (create it if the plan said to). For merges,
insert the carried content block, then delete the source.

### Step 2 — Verify

After each group, verify its effect:
- readme sync → every file in the directory appears in its readme, and every readme entry exists on disk.
- content repairs → the old match string is gone and the replacement is present.
- agent sweeps → grep for any retired agent name returns zero hits.
- parity → re-checksum canonical/target pairs match.
- junk/moves/archival → the sources are gone and targets exist.

### Step 3 — Completion report

Print what changed:
```
## Governance Sweep — Complete
- Actions executed: [N]  (A:[n] B:[n] C:[n] D:[n] E:[n] F:[n] G:[n])
- Files created/moved/deleted/edited: [counts]
- Backup: <path to backup dir>
- Verification: [all checks passed | anomalies: ...]
- Deferred (manual): [N] — [list]
```

If the project uses version control, remind the user to review `git status`/`git diff` and
commit — this skill does not run git itself unless the project's workflow explicitly allows it.

**Halt semantics:** if any action fails or a verification check fails, stop immediately,
report the exact failure and what was already changed, and point the user to the backup
directory. Never improvise a recovery that could lose data.

---

## Flagging for Human Review

Findings that need judgment become **AskUserQuestion** prompts — in Phase 1 (clarifications)
and at the Phase 2 approval gate. Batch them (up to 4 per call); never prompt one-at-a-time
per file. Each question names the specific file and offers the viable dispositions with
consequences. Common patterns:

- **Ambiguous orphan** — "What should happen to `X.md`?" → Absorb into [doc] / Archive / Promote / Delete.
- **Absorption target unclear** — "`X.md` is relevant but has no clear parent. Where?" → [best-guess doc] / Promote standalone / Archive.
- **Large orphan absorption** (>500 lines) — Absorb (full) / Absorb (summary + link) / Promote standalone.
- **Stale reference, no obvious fix** — "`X` references '[old]' which is gone. Replacement?" → [best guess] / Remove reference / Defer.
- **Duplicate-merge conflict** — "`spec.md` exists in two places, both with unique content. Which is authoritative?" → A primary / B primary / Defer (manual merge).
- **Archival rotation** (`multiSelect`) — "These [N] oldest close-outs — which rotate to archive?"
- **Unclear version currency** — "`file.xlsx`, `file.v2.xlsx`, `file.v2.bak.xlsx` — which is current?"
- **Stale tool infra** — "`.claude/agent-memory/...` nested in a reference dir — relocate / delete / leave (document)?"
- **Binary of unknown purpose** — "`data.sqlite` in docs/ — what is it?" → [best guess, document] / Archive / Delete.
- **SRL content staleness** — "SRL-[ID] references [outdated concept]. Still valid?" → Update refs only / Needs rewrite (defer) / Retire.

Resolved answers become actions in the Phase 2 work list (tagged `[user-confirmed]`).
Unresolved/declined items become **Deferred (manual)** entries — surfaced in the work list and
the completion report, never silently acted on.

---

## Scope

This skill audits **documents and their organization** and, after approval, fixes them. It
does:
- Discover, classify, and audit documentation (Phase 1).
- Propose a complete, ordered work list and get approval (Phase 2).
- Create/edit/move/archive/delete documentation files, create/update readmes, repair stale
  references, and sync parity copies (Phase 3) — with backups and verification.

It does NOT:
- Change anything before the user approves the Phase 2 work list.
- Modify source code (it flags stale code references for repair as content edits; it does not
  refactor code).
- Run tests, builds, or calibrations.
- Make architectural or design decisions.
- Auto-resolve ambiguous classifications — those always go through AskUserQuestion or land in
  the deferred list.
- Run git itself unless the project's documented workflow explicitly permits it; otherwise it
  reminds the user to review and commit.

---

## Adapting to Project Structure

Works on any project. A minimal project might be a single `docs/` folder with five markdown
files; a mature one has agent definitions, roadmaps, SRL catalogs, close-out archives, and
multi-project deployments. The universal checks (structure, orphans, staleness, cross-doc
consistency, dead references) run everywhere; the optional modules (agent roster, SRL, parity)
activate only when their infrastructure is detected. The skill states which modules are active
at the start of Phase 1. The only hard requirement is at least one directory containing
documents — if none exists, the skill reports that and exits.
