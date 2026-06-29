---
name: git-handoff
description: "LEGACY / MANUAL ONLY. Use only when the user explicitly asks for the old Cowork browser-sandbox git handoff packet. This skill does not apply to Codex Desktop, Codex CLI, Claude Code CLI, local PowerShell, or any native/local execution environment with normal repository access. Do not auto-trigger this skill for sprint closeout, branch creation, commits, merges, pushes, status checks, dirty worktrees, or dispatch gates. In Codex/CLI contexts, run the needed git commands directly using the project's normal safety rules: inspect state, stage explicit files, avoid destructive commands unless explicitly requested, commit intentionally, merge/push when the sprint spec authorizes it."
---

# Git Handoff

Legacy fallback for the old Cowork browser sandbox only. It is no longer a general project rule.

Codex Desktop, Codex CLI, Claude Code CLI, and local PowerShell sessions are expected to run git directly when the sprint spec or user request calls for it.

---

## Current Rule

**Do not auto-activate this skill.**

If working in Codex Desktop, Codex CLI, Claude Code CLI, or a native/local shell:

- Run `git status`, `git branch`, `git diff`, `git log`, `git add`, `git commit`, `git merge`, and `git push` directly when needed.
- Prefer explicit staging (`git add <path>`) over broad staging.
- Avoid destructive commands such as `git reset --hard`, `git clean`, or broad checkout/restore unless the user explicitly requested that exact operation.
- Preserve unrelated dirty files.

If the user explicitly says "use git-handoff" or "give me the old handoff packet," use the packet template below. Otherwise, do not invoke this skill.

---

## Trigger Conditions

Activate this skill only when the user explicitly requests the legacy handoff packet, for example:

- "Use git-handoff."
- "Give me a handoff packet."
- "Do not run git; print commands for me."

Do not activate this skill merely because git is involved.

---

## What to Do Instead

For normal Codex/CLI sprint execution, do the git work directly:

1. Inspect state with `git status` and relevant `git diff` / `git log` commands.
2. Stage only intended files with explicit `git add <path>` commands.
3. Commit with a clear message.
4. Merge/push when the sprint spec authorizes it.
5. Leave unrelated dirty or generated files untouched.

---

## Legacy Handoff Packet Template

Use this only when the user explicitly requests a handoff.

### Diagnosis

One short paragraph explaining the repo state and why a handoff packet was requested.

### Files To Sync

- `path/to/file1` - what changed
- `path/to/file2` - what changed

### Stage And Commit

```powershell
git add "path/to/file1"
git add "path/to/file2"
git status
git commit -m "<message>"
```

### Push

```powershell
git push origin <branch>
```

### Verify

```powershell
git status
git log -1 --oneline
```
