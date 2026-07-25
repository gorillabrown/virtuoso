---
name: git-handoff
description: "LEGACY / MANUAL ONLY. Use only when the user explicitly asks for the old Cowork browser-sandbox git handoff packet. This skill does not apply to Codex Desktop, Codex CLI, Claude Code CLI, local PowerShell, or any native/local execution environment with normal repository access. Do not auto-trigger this skill for sprint closeout, branch creation, commits, merges, pushes, status checks, dirty worktrees, or dispatch gates. In Codex/CLI contexts, run the needed git commands directly using the project's normal safety rules: inspect state, stage explicit files, avoid destructive commands unless explicitly requested, commit intentionally, merge/push when the sprint spec authorizes it."
---

<!-- virtuoso-shared-contract v1 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — the project-root governance readme's machine-readable block and `Virtuoso/workspace-layout.json` together form the registry. The manifest wins for any role it already carries a key for; the readme is the carrier for roles the manifest does not yet hold. Resolve every governance path through the registry — never hardcode one.
- **Workspace adopt** — bringing an established project under management is non-destructive: nothing is moved, nothing is duplicated, no parallel document is seeded beside a registered one, and user content is never overwritten.
- **Git ownership** — stage explicitly (`git add <path>`); never `git add .` or `git add -A`. Run a tripwire status check against the expected dirty set before any commit and stop on anything unexpected. No destructive flags, no force-push.
- **Effort levels** — low / medium / high / max. Model tier sets the default (haiku→low, sonnet→medium, opus→high); annotate a task only when overriding its default.
- **Issue contract** — any stop, hold, block, or elevation becomes the 7-field issue document, saved to the registered `issues` directory as `Issue.<SPRINT-ID>.<YYYY-MM-DD>.md`, then routed to `/mid-dispatch-decision` by path.
- **Governance staging** — a worktree-resident run never edits a main governance document directly; the change-intent goes to a staging file as fold-in instructions, applied at close-out.

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

**Even when the packet is requested, read-only git stays available.** "Do not run git" / "no commits" governs only *state-changing* commands — `git status`, `git log`, `git diff`, and `git show` remain fine for verification. It never means "no git at all, even reads."

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

## Legacy Handoff Packet — Output Contract

Use this only when the user explicitly requests a handoff. The packet has exactly two
parts, in this order, and **the CLI prompt block is the deliverable — it prints LAST and
nothing follows it.**

### Part 1 — Diagnosis (for the human, brief)

One short paragraph: repo state, what already happened in this sandbox, why the handoff is
needed (no network, mount limits, etc.). Optionally a compact files-to-sync list. No
command fences here — every command belongs inside the prompt block below, so there is
exactly one thing to copy.

### Part 2 — The CLI prompt (ONE fenced block, copy/paste-complete)

Print a single ```text fence containing a complete prompt addressed to a **fresh Claude
Code CLI session with zero context**. The user pastes it verbatim; the CLI agent must be
able to act safely with nothing else. Never split it across fences — one fence, one copy.
Write commands as plain indented lines inside the fence (no nested code fences — they
would break the block).

The prompt MUST carry, in order:

1. **Role + repo:** one line — "You are finishing a git handoff in <absolute repo path>."
2. **What already happened:** the exact state this sandbox left behind — e.g. "commit
   `<sha>` (parent `<sha>`) already exists on local `<branch>`, touching exactly:
   <files>." State plainly which steps are ALREADY DONE.
3. **What remains:** the precise state-changing steps left (usually verify-and-push only).
4. **Prohibitions, explicit:** whatever re-doing would corrupt — e.g. "Do NOT re-stage or
   re-commit (that duplicates the commit). No force-push, no reset/clean/restore; preserve
   unrelated dirty files." Tailor to the actual situation; never omit this section.
5. **Ordered steps, each with its expected output:** verification reads first (`git log -1
   --oneline` → "expect: <sha> <subject>"), then the state-changing command(s), then
   post-verification. Every expectation is concrete — a SHA, a file list, a count.
6. **Stop condition:** "If ANY expectation above does not match, STOP before the next
   state-changing command and report the mismatch verbatim — do not improvise a repair."
7. **Optional cleanup** clearly marked optional, with what each command removes.
8. **Report-back format:** the 2–3 lines the CLI agent should return to the user when done
   (final `git log -1 --oneline origin/<branch>`, `git status` summary), so the sandbox
   session can confirm the handoff closed.

Skeleton (fill every `<...>` from the actual diagnosis; drop steps that do not apply):

```text
You are finishing a git handoff in <absolute repo path>.

ALREADY DONE (do not redo): <e.g. commit <sha> (parent <sha>) exists on local <branch>,
touching exactly: <file list>. It was built and verified in a sandboxed session.>

REMAINING: <e.g. verify local state, push to origin, verify the push.>

PROHIBITIONS: Do NOT re-stage or re-commit — that would duplicate <sha>. No force-push.
No reset/clean/restore. Preserve unrelated dirty files in the working tree.

STEPS — run in order; each expectation must match before the next state-changing command:
1. cd "<absolute repo path>"
2. git log -1 --oneline
   expect: <shortsha> <subject line>
3. git show --stat HEAD
   expect: exactly <N> files — <file list>; parent <parent shortsha>
4. git push origin <branch>
5. git log -1 --oneline origin/<branch>
   expect: same <shortsha>

IF ANY EXPECTATION MISMATCHES: stop before the next state-changing command and report the
mismatch verbatim. Do not improvise a repair.

OPTIONAL CLEANUP (safe to skip): <e.g. git gc --prune=now — clears mount-orphaned
.git scratch: <names>.>

WHEN DONE, REPORT BACK: paste the output of `git log -1 --oneline origin/<branch>` and a
one-line `git status` summary.
```
