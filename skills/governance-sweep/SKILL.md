---
name: governance-sweep
description: "Read-only audit of governance and operational documents in any project — directory structure via readme.md authority, orphan detection, stale content scan, cross-doc consistency, dead references, archival candidates, and optional agent roster checks. Produces an enumerated CLI dispatch spec saved to the project root; CLI implements all changes. Cowork never modifies project files during a sweep. Use this skill whenever the user says 'governance sweep', 'doc cleanup', 'audit the docs', 'clean up the docs', 'organize the documents', 'check for stale references', 'are the docs consistent', 'doc hygiene', 'sync the docs', 'archive old content', 'find dead references', 'what files are orphaned', or any request to verify that project documentation is organized, current, and structurally sound. Also trigger when the user wants to create or enforce a readme-based document hierarchy, consolidate scattered files into parent documents, or move outdated content to archive folders."
---

# Governance Sweep

Structured audit of all governance and operational documents in a project. Works on
any project — from a simple folder of markdown files to a full multi-agent
orchestration codebase. Discovers docs dynamically, evaluates structural authority
via readme.md files, identifies what's outdated or misplaced, and produces a
**CLI-ready dispatch spec** that enumerates every change to be made.

The skill itself does not change a single file. Cowork's role is diagnosis. CLI's
role is execution.

---

## Operating Mode — Read-Only

This skill is **strictly diagnostic**. While running a sweep, Cowork:

- **Does** read project files, walk directories, and inspect contents.
- **Does** classify findings, propose dispositions, and use AskUserQuestion to
  resolve ambiguity.
- **Does NOT** create, edit, move, rename, delete, or back up any file in the
  project being swept.
- **Does NOT** create readme.md files for directories that lack them. It proposes
  their content in the spec instead.
- **Does NOT** absorb, archive, or promote orphans. It enumerates the action.
- **Does NOT** execute git operations. CLI handles version control after running
  the spec.

The single artifact this skill produces is a **Governance Sweep Spec** —
a markdown document saved to the project root, formatted for CLI to read top-to-
bottom and execute. Every action in the spec has a source path, a target path
(if applicable), a rationale, and a verification step.

**Why this boundary exists:** Cowork's sandbox file operations against project
directories on the user's filesystem have caused mount and git issues in the
past. CLI runs natively and is the safe execution layer for filesystem mutations.
Keeping Cowork strictly read-only also enforces clean review — Evan sees the
full plan before anything changes.

---

## When This Skill Exists

Project documentation drifts. Files accumulate in directories with no record of
what belongs and what's stale. Investigation memos from three months ago sit
next to active specs. Two copies of the same document exist in different folders
with different content. Nobody can confidently delete anything because nobody
knows what's still needed.

This skill exists to impose and maintain structure — not piecemeal, not reactively,
but as a deliberate sweep that produces a complete, ordered remediation plan
ready for CLI to execute in a single pass.

---

## Execution Model

The sweep runs in seven phases. Each phase completes fully before the next begins.
The skill enumerates everything it would change and produces a structured spec
at the end. **No phase modifies files.**

```
Phase 1: DISCOVER          — find all document directories and files
Phase 2: STRUCTURE         — analyze readme.md authority for each directory
Phase 3: GROUND TRUTH      — build the authoritative reference state from primary sources
Phase 4: AUDIT             — compare every doc against ground truth, enumerate findings
Phase 5: SPEC GENERATION   — translate findings into ordered, CLI-executable actions
Phase 6: SPEC VALIDATION   — verify the spec is complete, unambiguous, and well-ordered
Phase 7: HANDOFF           — save the spec to the project root and brief the user
```

---

## Phase 1: Discover

Scan the project directory to build an inventory of document directories and files.
The skill does not hardcode paths — it discovers them from the project structure.

### What to scan for

Look for directories that contain governance, operational, or reference documents.
Common patterns (non-exhaustive — discover what actually exists):

| Category | Typical signals | Examples |
|----------|----------------|----------|
| **Project rules** | `CLAUDE.md`, `README.md`, root-level config docs | Project instructions, conventions, setup guides |
| **Operational docs** | Directories named `docs/`, `documentation/`, numbered doc folders | Specs, roadmaps, runbooks, process docs |
| **Historical records** | `CloseOut.*`, `archive/`, dated folders | Sprint close-outs, meeting notes, past decisions |
| **Agent infrastructure** | `.claude/agents/`, `.claude/skills/` | Agent definitions, skill files, workflow refs (if present) |
| **Reference material** | `references/`, `assets/`, `templates/` | Reusable content, templates, external references |
| **Configuration** | `.claude/`, config directories | Project settings, tool configs |

### Discovery output

Print the inventory in chat:

```
## Document Inventory — [project name]
Found [N] files across [M] directories.

| Directory                        | Files | Has readme.md |
|----------------------------------|-------|---------------|
| ./                               | 3     | YES           |
| docs/                            | 12    | NO            |
| docs/archive/                    | 8     | NO            |
| .claude/                         | 4     | NO            |
```

### Detecting project type

After discovery, classify what kind of project this is based on what exists. This
determines which optional audit modules activate in Phase 4:

| If you find...                        | Activate module        |
|---------------------------------------|------------------------|
| `.claude/agents/*.md` with YAML frontmatter | Agent roster checks |
| `**/SpecRetro*`, `**/lessons*learned*` | SRL staleness checks  |
| Skills deployed to multiple locations | Parity verification    |
| `**/roadmap*`, `**/sprint-queue*`     | Sprint artifact checks |

If none of these exist, the sweep still runs — it just focuses on the universal
checks (structure, orphans, staleness, cross-doc consistency). The agent-specific
modules are additive, not required.

---

## Phase 2: Structure (Analysis Only)

Every document directory ideally has a `readme.md` that defines its intended
hierarchy — what files belong there, what subdirectories exist, what purpose each
serves. The readme.md is the structural authority. Files outside the defined
structure are candidates for absorption, promotion, archival, or deletion.

**This phase does not create or modify any readme.md.** Where a readme is missing
or stale, the spec records a "create readme" or "update readme" action with the
proposed content for CLI to write later.

### Step 1: Check for existing readme.md

For each document directory discovered in Phase 1, check whether a `readme.md`
(case-insensitive) exists at the directory root.

```
## Structure Check
| Directory              | readme.md | Disposition for spec   |
|------------------------|-----------|------------------------|
| docs/                  | YES       | Review & update         |
| docs/operational/      | NO        | Spec: create readme.md |
| docs/archive/          | NO        | Spec: create readme.md |
| .claude/               | NO        | Spec: create readme.md |
```

### Step 2: Draft proposed readme.md content for missing files

For each directory missing a readme.md, survey its current contents and **draft
the proposed readme content** (do not write it). The draft becomes the body of
a `create_file` action in the spec.

The proposed readme.md defines three things:

1. **Purpose** — one sentence: what this directory is for
2. **File hierarchy** — every file and subdirectory that belongs here, with a
   one-line description of each
3. **Naming conventions** — if files follow a pattern, state the pattern so future
   files can be validated against it

Template the spec will instruct CLI to write:

```markdown
# [Directory Name]

[One-sentence purpose statement.]

## Contents

### Files

| File | Type | Purpose |
|------|------|---------|
| `project_roadmap.md` | markdown | Feature roadmap and sprint sequencing |
| `lessons_learned.md` | markdown | Standing rules derived from past work |
| `Master.MEL.xlsx` | binary/xlsx | Monitoring, Evaluation & Learning tracker |
| ... | | |

### Subdirectories

| Directory | Purpose |
|-----------|---------|
| `archive/` | Superseded content preserved for reference |
| ... | |

## Naming Conventions

- Close-out reports: `CloseOut.<ID>.<YYYY-MM-DD>.md`
- [Other patterns observed in the directory]

## What Does NOT Belong Here

[Anything that should go elsewhere — e.g., "Source code belongs in the codebase.
One-off investigation notes should be archived after the work they support is
complete."]
```

When drafting a readme for a directory that already has files, populate the
hierarchy from the actual contents. Categorize every existing file — nothing
should be missing from the proposed readme.

### Step 3: Review existing readme.md files

For directories that already have a readme.md, compare the documented hierarchy
against the actual directory contents:

- **Files in directory but not in readme** — orphans. Spec adds them, or flags
  for absorption/archival.
- **Files in readme but not in directory** — missing. Spec records a `phantom_entry`
  finding for CLI to remove from the readme (or for human review if the file may
  have been lost).
- **Subdirectories that exist but aren't documented** — spec adds them or flags
  for cleanup.

### Step 4: Identify orphan files

An orphan is any file that exists in a document directory but is not listed in
that directory's readme.md and doesn't match a documented naming convention.
For each orphan, determine its proposed disposition:

| Disposition | Criteria | Spec action |
|-------------|----------|-------------|
| **Absorb** | Content is still relevant and logically belongs inside an existing parent document | `merge_then_delete`: source path, target doc + section, deletion |
| **Promote** | Content is still relevant and stands on its own — add it to the readme | `update_readme`: append entry |
| **Archive** | Content is outdated, superseded, or no longer actionable — but has historical value | `move_to_archive`: source path → archive path |
| **Delete** | Content is a temp file, duplicate, or artifact with no value | `delete`: source path |

Classify every orphan. If the disposition is ambiguous, route to human review
via AskUserQuestion (see "Flagging for Human Review" below).

### Structure output

```
## Structure Findings
- readme.md files to create: [N]
- readme.md files to update: [M]
- Orphan files: [N] — see disposition table

| File | Directory | Spec disposition | Target |
|------|-----------|------------------|--------|
| old_investigation.md | docs/ | move_to_archive | docs/archive/old_investigation.md |
| api_notes.md | docs/ | merge_then_delete | docs/project_spec.md §API |
| .tmp_draft.md | docs/ | delete | (temp artifact) |
| new_feature_spec.md | docs/ | update_readme | Add to docs/readme.md |
```

---

## Phase 3: Ground Truth

Before auditing document content, establish what's actually true right now. Ground
truth comes from the most authoritative source for each domain. **This phase
reads only.**

### Universal ground truth

Every project has some form of authoritative state. Identify it:

- **Project root docs** — CLAUDE.md, README.md, or equivalent. These define project
  conventions, and other docs should be consistent with them.
- **Directory readmes** — for directories that have one, this is the structural
  authority for that directory.
- **Current file state** — what files actually exist on disk right now (vs. what
  docs claim exists).

### Agent ground truth (optional — only if agent infrastructure exists)

If `.claude/agents/*.md` files exist with YAML frontmatter:

1. Read the `name:` field from each agent file's frontmatter
2. Check for `disabled: true` — these are deprecated stubs
3. Build the active agent roster and the deprecated-to-successor mapping
4. Check for `merged_into:` or `superseded_by:` fields on deprecated stubs

```
## Agent Ground Truth
Active agents: [list]
Deprecated stubs: [name] (→ [successor]), ...
```

### Cross-reference ground truth

If the same information appears in multiple documents (e.g., a list of team members,
a set of configuration values, a feature status), identify which source is
authoritative. Priority order defaults to:

1. Primary source files (code, config, agent definitions)
2. Root-level project docs (CLAUDE.md, README.md)
3. Operational docs (roadmaps, specs)
4. Historical records (close-outs, archives)

### Parity ground truth (optional — only if multi-location deployments exist)

If skills, agents, or shared docs are deployed to multiple project locations,
identify the canonical source and all deployment targets.

---

## Phase 4: Audit

Compare every discovered document against ground truth and the structural
authority assessed in Phase 2. For each document, enumerate every finding.
**This phase reads only.**

### Universal checks (always run)

**1. Structural violations**
Files classified as orphans in Phase 2 that need action. Files listed in readme.md
but missing from disk. Directories without documentation.

**2. Stale content**
References to things that no longer exist or have changed:
- File paths or links pointing to moved/deleted files
- Descriptions of processes or structures that no longer match reality
- Version numbers, dates, or status markers that are outdated
- References to people, tools, or systems that have changed

**3. Cross-document inconsistency**
The same fact stated differently in two or more documents:
- A feature described as "planned" in one doc and "shipped" in another
- Configuration values that differ between docs and actual config files
- Lists (team members, dependencies, file inventories) that have diverged

**4. Dead references**
Links or pointers to things that don't exist:
- Markdown links to files that aren't on disk
- References like "see X.md" where X.md doesn't exist
- Cross-references to sections or headers that have been removed

**5. Duplicate content**
Same logical document maintained in multiple locations with different content.
Common pattern: a working copy and an "official" copy that have drifted apart.

**6. Misplaced content**
Files that exist in the wrong directory based on their content type:
- Archive-era content (superseded close-outs, session logs, old investigation memos)
  sitting in active operational or governance directories instead of the archive
- Files at the wrong hierarchy level (e.g., a file at the root of the doc tree that
  belongs inside a numbered subdirectory)
- Agent infrastructure (`.claude/` directories, memory stores) nested inside
  reference or documentation directories where they don't belong

**7. Temp and junk artifacts**
Files with no governance or operational value that should be deleted outright:
- Temp files: `.tmp`, `.bak`, `testwrite`, `test_write_check.*`
- Unrecognizable filenames: hash-like strings with no extension (`zi6zfqMf`, `aB3xK9q2`)
- Editor swap files: `.swp`, `.swo`, `~` suffixed files
- Empty files with no content
- OS artifacts: `.DS_Store`, `Thumbs.db`, `desktop.ini`

**8. Version proliferation**
Multiple versions of the same logical file in the same directory:
- Pattern: `file.xlsx`, `file.v2.xlsx`, `file.v2.bak.xlsx`, `file_FINAL.xlsx`
- Audit action: identify the current version, propose archival/deletion of older
  versions, and ensure the readme spec references only the current version
- Also flag `_old`, `_backup`, `_copy`, `(1)`, `(2)` suffixed variants

**9. Naming convention violations**
Files in a directory that don't match the naming pattern documented in that
directory's readme.md:
- Compare each file's name against the conventions section of its directory's readme
- Flag files that deviate from the established pattern
- If no naming convention is documented in the readme, infer the dominant pattern
  from existing files and flag outliers — propose adding the convention to the
  readme via a spec action

**10. Volume and age-based archival triggers**
Directories with high file counts where older entries should rotate to archive:
- Close-out directories: if more than [configurable, default 20] close-outs exist,
  flag the oldest N for archival rotation. Close-outs older than N sprints or N months
  from the most recent close-out are candidates.
- Investigation memos, diagnostics, and one-off analysis files older than a project-
  defined threshold should be flagged for archive review.
- The threshold is advisory — always route to human review rather than proposing
  archive actions by age alone, since some old close-outs remain actively referenced.

**11. Stale temp packages**
Files or directories in designated temp locations (`temp/`, `3 temp/`, `scratch/`)
that have outlived their expected lifecycle:
- Any temp content older than 14 days (configurable) is flagged
- Temp directories with a stated purpose (e.g., "research package for X") — check
  whether X is complete; if so, flag the package for archival or deletion
- Temp content with no stated purpose is always flagged

**12. Stale tool infrastructure in unexpected locations**
Tool-specific directories (`.claude/`, `agent-memory/`, `__pycache__/`, `.pytest_cache/`,
`node_modules/`) found inside document directories where they don't belong:
- `.claude/agent-memory/` nested inside a reference or benchmark directory
- Python cache directories inside documentation trees
- These are either misplaced (spec proposes move to correct location) or
  orphaned (spec proposes delete)

**13. Binary file accounting**
Binary files (.xlsx, .docx, .pdf, .zip, .sqlite, .html, .png, .jpg) present in
document directories that may not be captured by text-centric readme templates:
- Ensure every binary file appears in its directory's readme.md with a purpose note
- Flag binary files with no clear relationship to surrounding documentation
- Flag large binary files (>10MB) that may be better stored outside the doc tree
- For .zip archives: note their contents in the readme (what's inside, why archived
  as a bundle) since the archive's purpose is invisible without documentation

### Agent-specific checks (only if agent infrastructure detected)

**14. Ghost agent references**
Agent names in documents that don't match any active agent definition file.
For each ghost, record file, line, ghost name, and the successor (from deprecated
stub mapping).

**15. Deprecated stub presence**
Agent files with `disabled: true` still in the agents directory. Flag each with
its merge target.

**16. Agent memory directory names**
Directories in `.claude/agent-memory/` that don't match active agent names.

### Multi-project checks (only if parity targets detected)

**17. Parity divergence**
Checksum mismatches between canonical and deployed copies of shared files.

### SRL-specific checks (only if SRL/lessons catalog detected)

**18. SRL/finding staleness**
Entries referencing agent names, code paths, or sprints that have changed.
Propose name reference updates; flag content staleness for human review.

### Audit output

Print findings grouped by check type with exact locations. Only include check
categories that produced findings — don't print empty tables.

---

## Phase 5: Spec Generation

Translate every Phase 4 finding into an ordered, CLI-executable action. The
spec is a single markdown document; CLI reads it top-to-bottom.

### Spec structure

The spec uses this skeleton (adapted to whatever findings exist):

```markdown
# Governance Sweep Spec — [project name] — [YYYY-MM-DD]

## Summary
- Findings: [N]
- Actions: [N]
- Files affected: [N]
- Estimated execution time: [low/medium/high]
- Human-review items deferred: [N]

## Pre-flight (CLI runs first)
1. Confirm working directory is the project root: `[absolute path]`
2. Create timestamped backup directory: `.governance-sweep-backup/YYYY-MM-DD/`
3. Copy every file listed in §"Files to be modified" into the backup directory,
   preserving relative paths.

## Action Group A — Junk Removal (run first; lowest risk)
[Ordered list of `delete` actions for temp files, OS artifacts, swap files, empties.]

## Action Group B — Misplaced Content Relocation
[Ordered list of `move` actions: source absolute path → target absolute path. Each
includes a one-line rationale.]

## Action Group C — Archival
[Ordered list of `move_to_archive` actions for orphans, version proliferation,
and human-approved rotation candidates.]

## Action Group D — Orphan Absorption
[Ordered list of `merge_then_delete` actions. Each contains:
  - Source file (absolute path)
  - Target document (absolute path) and target section heading
  - Exact content block to insert (the spec carries the merged content verbatim
    so CLI doesn't re-derive it)
  - Deletion of source after merge.]

## Action Group E — readme.md Synchronization
[Ordered list of `create_file` and `update_file` actions for readme.md files.
Each `create_file` action carries the full proposed readme content as a code
block. Each `update_file` action carries either a precise diff or a full
replacement, with rationale.]

## Action Group F — Content Repairs
[Ordered list of in-place edits for stale references, dead links, cross-doc
inconsistencies, and ghost agent references. Each carries:
  - File (absolute path)
  - Match string (verbatim, unique within file)
  - Replacement string
  - Rationale and source of authority.]

## Action Group G — Parity Sync (if applicable)
[Ordered list of file copies from canonical → deployment targets, with
checksum-verify steps.]

## Verification (CLI runs after all action groups)
1. For each directory whose readme.md was created or updated: list contents and
   confirm every file appears in the readme; confirm every readme entry exists
   on disk.
2. For each file referenced in Action Group F: confirm the match string is gone
   and the replacement is present.
3. For agent sweeps: grep for any retired agent name; expect zero hits.
4. For parity: re-checksum all canonical/target pairs; expect matches.
5. Print a completion report with action counts per group and any anomalies.

## Human-Review Items Deferred
[Items the user marked "skip" or that were too ambiguous to prompt. Each:
  - File / location
  - What's wrong
  - Why it remains open
  - Suggested next step.]

## Backup Manifest
[Plain list of every file CLI must back up before mutation. Generated from the
union of all sources/targets across action groups.]
```

### Action ordering principle

Action groups are ordered to minimize blast radius if CLI errors mid-run:

1. Junk removal first — irreversible but safe.
2. Misplaced content moves — reversible from backup.
3. Archival moves — reversible from backup.
4. Orphan absorption — content-bearing; runs after structural moves so absorption
   targets are in their final locations.
5. readme.md synchronization — runs after files have moved so the readmes reflect
   the final state.
6. Content repairs — last because they edit text inside files that are now in
   their final locations.
7. Parity sync — fully derivative; runs once all canonical content is settled.

### Action atomicity

Every action in the spec is **atomic, self-contained, and idempotent where
possible**:

- Absolute paths only. CLI shouldn't have to infer working directory.
- Match strings for content edits are verbatim and unique within the file.
- For ambiguous matches, the spec includes enough surrounding context to make
  the match unique, or splits into multiple narrower edits.
- For binary file actions (move/copy), the spec includes a checksum so CLI can
  verify the file is the one expected.

### Resolved vs deferred

Every finding resolved by AskUserQuestion during the sweep becomes an action in
the relevant group, tagged `[user-confirmed]`. Every finding the user deferred
or that couldn't be auto-prompted becomes a "Human-Review Items Deferred" entry.

---

## Phase 6: Spec Validation

Before handing off, verify the spec itself is well-formed. **This phase reads
the spec; it does not touch project files.**

### Validation checks

1. **Path correctness** — every source path in the spec exists on disk; every
   target path is well-formed (directory exists or is created earlier in the
   spec).
2. **Match-string uniqueness** — for each content edit, grep the match string
   in the target file and confirm exactly one occurrence.
3. **Action ordering** — confirm dependencies are respected (e.g., a move is
   ordered before a readme update that references the post-move state).
4. **Coverage** — every Phase 4 finding maps to either an action in the spec or
   a deferred-review entry. No finding is silently dropped.
5. **No phantom actions** — no action references a file that doesn't exist and
   isn't created earlier in the spec.

### Validation output

```
## Spec Validation
✓ All [N] source paths exist
✓ All [N] match strings are unique within their target files
✓ Action ordering: dependencies respected
✓ Coverage: [N] findings → [N] actions + [M] deferred items (no drops)
✓ No phantom actions
```

If any check fails, loop back to Phase 5 and rewrite the affected actions before
proceeding.

---

## Phase 7: Handoff

Save the spec and brief the user.

### Save location

Write the spec to:
```
<project root>/governance-sweep-spec.<YYYY-MM-DD>.md
```

Where `<project root>` is the top-level directory of the project being swept.
**This is the only file Cowork writes during the entire sweep**, and it lives
inside the project so CLI sees it without translation.

If a spec from a previous sweep already exists at that path, append a sequence
suffix (`-2`, `-3`) rather than overwriting.

### Brief

After saving, print this in chat:

```
## Governance Sweep — Ready for CLI

Spec saved: [absolute path to spec]

### Summary
- Directories scanned: [N]
- Files scanned: [N]
- Findings: [N]
- Actions queued for CLI: [N]
- Human-review items deferred: [N]
- Optional modules activated: [list, or "none — universal checks only"]

### Findings by category
| Category                    | Count |
|-----------------------------|-------|
| Structural violations       | [N]   |
| Stale content               | [N]   |
| Cross-doc inconsistencies   | [N]   |
| Dead references             | [N]   |
| Duplicate drift             | [N]   |
| Misplaced content           | [N]   |
| Temp/junk artifacts         | [N]   |
| Version proliferation       | [N]   |
| Naming convention violations| [N]   |
| Archival rotation candidates| [N]   |
| Stale temp packages         | [N]   |
| Stale tool infrastructure   | [N]   |
| Binary file gaps            | [N]   |
| [Agent-specific findings]   | [N]   | ← only if applicable
| [Parity divergence]         | [N]   | ← only if applicable
| **Total**                   | **[N]** |

### Spec validation
[Phase 6 verification block]

### Next step
Hand the spec to CLI:
  "Execute governance-sweep-spec.<date>.md from the project root."
CLI will create the backup, run the action groups in order, and print its own
completion report.
```

Cowork's job ends here. CLI takes over.

---

## Flagging for Human Review

Some findings require judgment. When a finding can't be classified
deterministically, present it to the user as an **AskUserQuestion** prompt — not
a list in the report. The user sees these as interactive questions with
selectable options, which is faster and more precise than reading a wall of
flagged items and typing responses.

The user's answers update **the spec being generated** — they do not trigger
file mutations.

### When to prompt

Pause and prompt the user at two points during the sweep:

1. **End of Phase 2 (Structure)** — after classifying orphan files. Batch all
   ambiguous orphans into questions before proceeding to Phase 3.
2. **End of Phase 4 (Audit)** — after enumerating all findings. Batch all
   ambiguous content findings into questions before proceeding to Phase 5.

Do NOT prompt one-at-a-time per file. Collect all ambiguous items within a phase,
group them by decision type, and present up to 4 questions per AskUserQuestion
call (the tool's limit). If more than 4 questions are needed, make multiple calls.

### How to structure each question

Each question must map to one of the flag types below. Use the `header` field as
a short category tag, the `question` field to name the specific file and what's
ambiguous, and the `options` to present the viable dispositions with descriptions
explaining consequences.

### Flag types and their question patterns

**Ambiguous orphan disposition**
A file that could plausibly be absorbed, archived, or promoted.
```
header: "Orphan"
question: "What should happen to `old_investigation.md` in docs/operational/?"
options:
  - label: "Absorb into [parent doc]"
    description: "Spec will merge relevant content into [target] §[section], then delete the file"
  - label: "Archive"
    description: "Spec will move to docs/archive/ — preserves history but removes from active view"
  - label: "Promote"
    description: "Spec will keep in place and add to the directory's readme.md as a standalone doc"
  - label: "Delete"
    description: "Spec will remove entirely — file has no lasting value"
```

**Absorption target unclear**
Content is relevant but no obvious parent document exists.
```
header: "Absorb into?"
question: "`api_notes.md` has relevant content but no clear parent doc. Where should it go?"
options:
  - label: "[Best-guess target]"
    description: "Spec will merge into [target] — closest topical match"
  - label: "Promote as standalone"
    description: "Spec will add to readme.md as its own entry — it doesn't belong inside another doc"
  - label: "Archive"
    description: "Not sure yet — spec will park in archive until a parent doc emerges"
```

**Large orphan absorption**
Files over 500 lines classified for absorption — merging may not be appropriate.
```
header: "Large file"
question: "`detailed_analysis.md` (847 lines) is flagged for absorption into [target]. Merge that much content?"
options:
  - label: "Absorb (full merge)"
    description: "Spec will merge all content into [target] — will significantly expand it"
  - label: "Absorb (summary only)"
    description: "Spec will write a summary section in [target] and link to the original as an appendix"
  - label: "Promote as standalone"
    description: "Spec will keep as its own document — too large to merge cleanly"
```

**Stale content with no clear update**
A reference is outdated but the correct current value isn't obvious.
```
header: "Stale ref"
question: "`roadmap.md` references '[old value]' which no longer exists. What replaced it?"
options:
  - label: "Replace with [best guess]"
    description: "Spec will update to '[guess]' — appears to be the successor based on [evidence]"
  - label: "Remove reference"
    description: "Spec will delete the reference — it's not load-bearing"
  - label: "Defer (manual)"
    description: "Leave as-is in spec deferred list — Evan will fix it with the correct value"
```

**Merge conflicts in duplicates**
Two copies of the same logical document both have unique content.
```
header: "Dup conflict"
question: "`spec.md` exists in both docs/ and docs/operational/ with different content. Which is authoritative?"
options:
  - label: "docs/ copy is primary"
    description: "Spec will sync docs/operational/ from docs/ — unique content in operational/ will be lost"
  - label: "docs/operational/ copy is primary"
    description: "Spec will sync docs/ from docs/operational/"
  - label: "Defer (manual merge)"
    description: "Add to deferred list — Evan will combine unique content from both manually"
```

**Archival rotation candidates**
Old close-outs or memos flagged by age/volume.
Use `multiSelect: true` — the user selects which ones to archive.
```
header: "Rotate?"
question: "These [N] close-outs are the oldest in operational/ ([date range]). Which should rotate to archive?"
multiSelect: true
options:
  - label: "Archive all [N]"
    description: "Spec will move all listed close-outs to archive/"
  - label: "Archive none"
    description: "Spec will leave all in operational/ — they're still actively referenced"
  - label: "Let me pick individually"
    description: "I'll specify which ones in a follow-up; spec will reflect the picks"
```

**Unclear version currency**
Multiple versions exist and it's not obvious which is current.
```
header: "Which version?"
question: "`Master.MEL.xlsx`, `Master.MEL.v2.xlsx`, and `Master.MEL.v2.bak.xlsx` all exist. Which is current?"
options:
  - label: "Master.MEL.v2.xlsx"
    description: "Spec will keep v2 as current, archive the others"
  - label: "Master.MEL.xlsx"
    description: "Spec will keep the original as current, archive v2 and bak"
  - label: "Defer (manual)"
    description: "Add to deferred list — leave all versions in place"
```

**Stale tool infrastructure**
`.claude/` or similar directories in unexpected locations.
```
header: "Tool infra"
question: "`.claude/agent-memory/calibration-tuner/` is nested inside `5 Reference/Benchmark References/`. What should happen to it?"
options:
  - label: "Relocate to project root .claude/"
    description: "Spec will move to the correct location in the project's .claude/ directory"
  - label: "Delete"
    description: "Spec will remove — orphaned infrastructure no longer needed"
  - label: "Leave in place"
    description: "It's there intentionally — spec will add it to the directory's readme"
```

**Binary files with unknown purpose**
Binary file has no clear relationship to surrounding documentation.
```
header: "Binary file"
question: "`data_export_2025.sqlite` in docs/reference/ — what is this for?"
options:
  - label: "[Best-guess purpose]"
    description: "Spec will document as '[guess]' in the readme — appears to be [evidence]"
  - label: "Archive"
    description: "Spec will move to archive — probably no longer needed but preserve just in case"
  - label: "Delete"
    description: "Spec will remove — no value"
```

**Temp packages tied to completed work**
Temp content whose parent task appears done.
```
header: "Stale temp"
question: "Research package in `3 temp/audit-prep/` is 23 days old and references sprint STG1A which is complete. Clean up?"
options:
  - label: "Delete"
    description: "Spec will remove — sprint is done; package served its purpose"
  - label: "Archive"
    description: "Spec will move to archive/ — may want to reference the research later"
  - label: "Keep"
    description: "Still needed — spec will leave untouched"
```

**SRL/finding content staleness**
The lesson itself (not just a name reference) may no longer apply.
```
header: "SRL stale?"
question: "SRL-[ID] references [outdated concept]. Is the lesson itself still valid?"
options:
  - label: "Still valid — update references only"
    description: "Spec will fix the names/paths it mentions; lesson body stays"
  - label: "Needs rewrite"
    description: "Add to deferred list — Evan will rewrite the entry"
  - label: "Retire"
    description: "Spec will mark as retired with reason"
```

### After the user answers

Apply the user's selections as actions in the spec being generated. Tag each
`[user-confirmed]` in the action description. If the user selects "Other" on any
question, read their free-text response and adapt the spec action accordingly.

### In the Phase 7 brief

The "Human-Review Items Deferred" section lists only items where the user
deferred a decision (selected "skip" or "defer") or where a question couldn't be
formed because the finding was too ambiguous to offer meaningful options. All
resolved review items are baked into action groups A–G.

---

## Scope Boundaries

This skill audits **documents and their organization** and produces a spec for
CLI to execute. It does NOT:

- Modify any project file. Ever. The only file written is the spec itself, at
  the project root.
- Modify source code (flags stale code references in the spec, doesn't fix code)
- Run tests, builds, or calibrations
- Make architectural or design decisions
- Auto-resolve ambiguous classifications — those always go through AskUserQuestion
  or land in the deferred list
- Modify files outside the project directory
- Create new operational content (it organizes existing content, not generates new)
- Run git operations (CLI handles version control after executing the spec)

---

## Adapting to Project Structure

The skill works on any project. A minimal project might have a single `docs/` folder
with five markdown files. A mature project might have agent definitions, roadmaps,
SRL catalogs, close-out archives, and multi-project deployments.

The universal checks (structure, orphans, staleness, cross-doc consistency, dead
references) run everywhere. The optional modules (agent roster, SRL, parity) activate
only when their infrastructure is detected. The skill tells you which modules are
active at the start so there are no surprises about scope.

The only hard requirement is that the project has at least one directory containing
documents. If the project root has no document files or directories, the skill has
nothing to audit — it reports that and exits without writing a spec.
