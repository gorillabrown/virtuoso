---
name: git-handoff
description: "MANUAL ONLY. Produces a copy/paste git hand-off packet for a session that cannot perform repository mutations itself — because the project's git policy withholds them, because the environment has no repository access, or because the user asked for one. Do NOT auto-trigger for close-out, branch creation, commits, merges, pushes, status checks, dirty worktrees, or dispatch gates: in an environment with repository access, do the git work directly, within whatever `policy.git` permits."
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

# Git Handoff

Produces a **hand-off packet**: a single copy/paste prompt that another actor — a
person, or an agent in an environment with repository access — runs to complete
repository work this session cannot perform itself.

This is not a general project rule. It applies in exactly three situations:

1. `policy.git.policy` is `read-only` or `prepare-no-stage`, so this ceremony may
   not mutate the repository;
2. `policy.git.separationOfDuties` is true and this actor authored the change, so a
   different actor must commit it;
3. the environment genuinely has no repository access, or the user explicitly asked
   for a packet.

In every other case, do the git work directly, within what `policy.git` permits.
See `references/git-policy.md`.

---

## Read-only git is always available

"Do not mutate" governs *state-changing* commands only. `git status`, `git log`,
`git diff`, `git show`, `git branch -vv`, and `git worktree list` remain available
in every environment and under every policy — run them lock-free
(`GIT_OPTIONAL_LOCKS=0 git --no-optional-locks …`). "No commits" never means "no
git at all". Verify from that primary evidence, never from a pasted summary.

---

## When NOT to activate

Do not activate merely because git is involved. Do not activate for close-out,
dispatch, branch creation, or a status check in an environment that can run git.
Activate on an explicit request ("give me a hand-off packet", "print the commands
for me"), or when one of the three situations above genuinely holds.

---

## What to do instead, when you can act

1. Inspect state: `git status --porcelain`, and the relevant `diff` / `log`.
2. Compute the expected dirty set for this change; report anything outside it and
   leave it alone.
3. Stage exact paths: `git add "<path>"`. Never `git add .` or `-A`.
4. Verify `git diff --cached --name-only` matches the expected set. Stop on anything
   unexpected.
5. Commit, merge, or push only as far as `policy.git.policy` permits, and subject to
   `policy.git.networkOperations` for anything that touches the network.
6. Never stash, reset, clean, destructively checkout, or force-push without explicit
   authorization. Never delete a lock file automatically — report it and check
   whether a git process is running.

---

## The packet — output contract

Exactly two parts, in this order. **The prompt block is the deliverable: it prints
last, and nothing follows it.**

### Part 1 — Diagnosis (brief, for the human)

One short paragraph: repository state, what already happened here, and why a
hand-off is needed — the policy that withholds the mutation, separation of duties,
or the absent repository access. Optionally a compact file list. **No command
fences here**; every command belongs inside the prompt block, so there is exactly
one thing to copy.

### Part 2 — The prompt (ONE fenced block, copy/paste-complete)

A single ```text fence containing a complete prompt addressed to **a fresh session
with zero context**, in an environment that can run git. The recipient pastes it
verbatim and must be able to act safely with nothing else. Never split it across
fences. Write commands as plain indented lines inside the fence.

The prompt MUST carry, in order:

1. **Role and repository** — one line: "You are completing a git hand-off in
   `<absolute repository path>`."
2. **What already happened** — the exact state this session left behind: which
   commits exist, on which branch, touching exactly which files. State plainly what
   is ALREADY DONE.
3. **What remains** — the precise state-changing steps left.
4. **Prohibitions, explicit** — whatever redoing would corrupt. Always include: no
   force-push; no reset, clean, or destructive restore; preserve unrelated dirty
   files; do not delete a lock file without checking for a running git process.
5. **Detection, not assumption** — the recipient resolves the remote and the default
   branch from the repository (`git remote`, `git symbolic-ref --quiet --short
   refs/remotes/<remote>/HEAD`, or `git remote show <remote>`). Never hardcode
   `origin` or `main` in the packet unless you detected them and say so.
6. **Ordered steps, each with its expected output** — verification reads first, then
   the state-changing command(s), then post-verification. Every expectation is
   concrete: a commit id, a file list, a count.
7. **Stop condition** — "If ANY expectation does not match, STOP before the next
   state-changing command and report the mismatch verbatim. Do not improvise a repair."
8. **Optional cleanup**, clearly marked optional, saying what each command removes.
9. **Report-back format** — the two or three lines to return, so this session can
   confirm the hand-off closed.

Skeleton (fill every `<…>` from the actual diagnosis; drop steps that do not apply):

```text
You are completing a git hand-off in <absolute repository path>.

ALREADY DONE (do not redo): <e.g. commit <id> (parent <id>) exists on local
<branch>, touching exactly: <file list>.>

REMAINING: <e.g. verify local state, push, verify the push.>

PROHIBITIONS: Do NOT re-stage or re-commit — that would duplicate <id>. No
force-push. No reset, clean, or destructive restore. Preserve unrelated dirty files.
If .git/index.lock exists, report it and check for a running git process before
touching it.

RESOLVE FIRST (do not assume):
1. cd "<absolute repository path>"
2. git remote
   expect: <the remote you detected, or: pick the single remote; if none, stop —
   this repository is local-only and the push step does not apply>
3. git symbolic-ref --quiet --short refs/remotes/<remote>/HEAD
   expect: <remote>/<default branch>

STEPS — run in order; each expectation must match before the next state-changing
command:
4. git log -1 --oneline
   expect: <short id> <subject>
5. git show --stat HEAD
   expect: exactly <N> files — <file list>; parent <parent short id>
6. git push <remote> <branch>
7. git log -1 --oneline <remote>/<branch>
   expect: same <short id>

IF ANY EXPECTATION MISMATCHES: stop before the next state-changing command and
report the mismatch verbatim. Do not improvise a repair.

OPTIONAL CLEANUP (safe to skip): <name each command and what it removes.>

WHEN DONE, REPORT BACK: the output of `git log -1 --oneline <remote>/<branch>` and a
one-line `git status` summary.
```

---

## After the packet

When the recipient reports back, **re-verify from primary evidence** — read the log
and the tree yourself. Do not accept "done" or "clean" as a claim. If a report
contradicts what the repository shows, state the contradiction plainly and say what
still has to happen.
