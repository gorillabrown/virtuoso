# Shared Agent Memory Guide

All agents in this project use a persistent, file-based memory system at:
`<project-root>/.claude/agent-memory/{agent-name}/`

## Where memory lives: one folder, spelled in lowercase

`{agent-name}` is the agent's name in **lowercase**: `Socrates` keeps its memory in
`.claude/agent-memory/socrates/`. Each agent's brief states its location exactly, on its
`Memory location:` line, and the plugin's validator holds every brief to that spelling.

**The brief is the one mechanism.** At the start of a dispatch, read `MEMORY.md` in your
memory folder if it exists; save as described below. Nothing else loads or places your
memory.

**Why the shipped agents declare no `memory:` field.** Some hosts support a `memory:` field
on an agent definition and keep that agent's memory in `.claude/agent-memory/<name-of-agent>/`,
named from the definition's `name:`. An agent loaded from a plugin has the field ignored. An
agent *copied* into a project's own agent folder has it honoured, so a copy named `Socrates`
gets `Socrates/` beside the documented `socrates/`. On Windows and on a default macOS
volume the two spellings are one folder, and nothing looks wrong. On Linux, and in git's
index, they are two, and each writer reads a memory the other never sees. Declaring no
`memory:` field leaves one writer and one spelling.

**For a project.** Carry project-specific instructions for an agent in an overlay, not in a
copy of its brief. A copy stops receiving the plugin's fixes and keeps names the plugin has
retired. If a project does keep a copy in its own agent folder, remove any `memory:` line
from it.

## Repairing a memory split by case

Symptoms: git tracks `.claude/agent-memory/socrates/` while the disk (or a new, untracked
note) shows `Socrates/`, or a Linux checkout has both.

1. **See both records.** `git ls-files .claude/agent-memory` lists the tracked spellings, and
   a directory listing shows the disk's. Only the lowercase spelling is correct.
2. **Fix the disk in two steps.** A case-only rename is invisible to a case-insensitive
   filesystem, so go through a temporary name: `Socrates` → `socrates.tmp` → `socrates`.
   Where both folders really exist (Linux), move the files from the capitalised folder
   into the lowercase one first. A file present in both is a conflict to resolve by hand,
   never by overwriting.
3. **Fix the index.** If git tracks a capitalised path, rename it with `git mv` rather
   than deleting and re-adding it. On a case-insensitive filesystem, go through a
   temporary name here too: `git mv <Name>/<file> <name>.tmp/<file>`, then
   `git mv <name>.tmp/<file> <name>/<file>`.
4. **Stage new notes where they live.** Add untracked notes from the checkout that holds
   them. Never commit a file from another worktree while an untracked copy of it sits in
   the checkout the commit will land in: git will refuse to overwrite the untracked copy
   when that checkout updates.
5. **Confirm.** `git ls-files .claude/agent-memory` shows only lowercase agent folders, and
   the disk agrees.

## The boundary — memory, lessons, findings

Stated once, here, for every agent:

| What it is | Where it goes | Read by |
|---|---|---|
| How *this agent* works in *this project* — preferences, workflow pointers, external references | agent memory, `.claude/agent-memory/{agent-name}/` — outside the registry | the agent |
| A discovery a future specification should apply | the registered `lessons` role, `<prefix>-NNN` (`policy.lessons.idPrefix`), appended by the ceremony that records it | every specification (rubric U9), every charter |
| Something wrong that is not dispositioned yet | the registered `findings` role, `F-NNN`, disposition by appended record | the roadmap review |

Nothing else: no feedback log, no memory YAML, no per-agent findings file, and no fixed
lesson prefix (`LL-`, `SRL-`) — the project's prefix is the one its policy declares.

## Memory Types

| Type | Purpose | Save When |
|------|---------|-----------|
| `user` | User's role, preferences, expertise | Learn about user's background or working style |
| `feedback` | Corrections to your approach | User says "don't...", "instead do...", "stop..." |
| `project` | Ongoing work, bugs, decisions not in code/git | Learn who/what/why/when about work in progress |
| `reference` | Pointers to external resources | Learn about tools, docs, or systems outside the repo |

## How to Save

**Step 1** — Write memory to its own file with frontmatter:
```markdown
---
name: {{memory name}}
description: {{one-line description}}
type: {{user|feedback|project|reference}}
---
{{memory content}}
```

**Step 2** — Add pointer to `MEMORY.md` index (keep under 200 lines).

## Rules
- Don't duplicate what's in code, git history, or CLAUDE.md
- **Don't duplicate what belongs in the project's knowledge system.** When a finding is about measured or inferred behaviour, store it in that system — through the roles the registry declares — not in agent memory. Memory should only retain workflow-specific pointers, stable user preferences, or external references.
- Don't save ephemeral task state — use tasks/plans for that
- Convert relative dates to absolute dates
- Update/remove outdated memories
- Check for existing memory before creating duplicates

## Knowledge-system reference
- **Governing spec** (project-supplied; not shipped with the plugin): resolve
  the project's knowledge-system specification document under the governance directory registered in the
  project's governance readme. If the project defines no such spec, the defaults below apply.
A project that keeps one declares its stores as registry roles (commonly an interaction
registry, a strategy guide, and a validation log). Resolve each through the registry; this
guide names no paths of its own.
- **Custodian**: MarcusAurelius (executes triage gate, maintains all 3 artifacts)

## Bash Execution Rule
**Never run multi-line Python as inline bash strings.** This triggers security prompts about `#`-prefixed lines hiding arguments. Instead:
1. Write a temp `.py` file (e.g., `/tmp/agent_query.py`)
2. Run it: `python /tmp/agent_query.py`
3. Clean up if needed

This applies to ALL agents running SQLite queries, data analysis, calibration scripts, or any Python longer than a single expression.

## Findings Output
All agents write findings to the project's registered `findings` role. Resolve it through
the registry; never assume a path.
One entry per finding, `### F-NNN — title (agent, YYYY-MM-DD)` with **Source**, **Severity**,
**Where**, **Finding** and **Disposition:** `open`; a disposition changes only by an appended
record under the same id.
