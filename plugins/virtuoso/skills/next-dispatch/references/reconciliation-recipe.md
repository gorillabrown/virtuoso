# Repository Reconciliation Recipe

Serves next-dispatch's *Repository reconciliation* section: the detection steps, the recipe template, and how to print it inside the kickoff. Phase 3 (a missing recipe), pre-flight check 7, and §4.2 all fill it from here; write-plan and epic fill the same recipe.

The recipe below is a **template**. Fill it from `policy.git` and from the
repository's actual state. Never emit a placeholder, and never emit a step the
project's policy does not permit.

## First, detect — do not assume

```
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks rev-parse --is-inside-work-tree

# Remote: policy.git.remote if set; else the current branch's upstream remote;
# else the single remote if there is exactly one; else ASK. Never assume "origin".
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks remote

# Default branch: policy.git.defaultBranch if set; else
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks symbolic-ref --quiet --short refs/remotes/<remote>/HEAD
#   else `git remote show <remote>` → "HEAD branch"; else the current branch.
#   Never assume "main".

# Worktrees: distinguish the primary tree from a dedicated execution worktree.
GIT_OPTIONAL_LOCKS=0 git --no-optional-locks worktree list
```

**There may be no remote at all.** A local-only repository is fully supported.
Unless `policy.git.requireRemote` is true, record "no remote" as a fact and skip
every network step. Fetching and pushing are governed by
`policy.git.networkOperations` (`ask` by default): surface the operation and get
approval rather than running it silently, and treat offline as a normal state.

## The recipe

```
# ── Step 0: REPOSITORY RECONCILIATION — before any implementation ──

# 0a. Scope the working tree.
git status --porcelain
#   Compare against the EXPECTED dirty set for this item.
#   Paths inside it   → fine; they are this dispatch's own work.
#   Paths outside it  → REPORT them and leave them alone. An unrelated dirty
#                       path in the primary tree does NOT invalidate a separate,
#                       clean execution worktree (policy.git.worktreeAware).
#   Never stash, reset, clean, or destructively checkout to "tidy up".
#   If .git/index.lock exists: REPORT it and check whether a git process is
#   actually running. Never delete it automatically.

# 0b. Sync the default branch (only if a remote exists AND
#     policy.git.networkOperations permits it).
git fetch <remote> --prune
git switch <default>
git merge --ff-only <remote>/<default>
#   Diverged → STOP. No force, no reset --hard, no unauthorized rebase.
#   SANCTIONED FALLBACK (flag it; never silent): branch directly off the remote
#   tip and leave the local default branch for a human:
#       git switch -c <branch-name> <remote>/<default>
#   Then skip 0c. Report that the local default branch is still diverged.

# 0c. Create the work branch from the reconciled default branch.
git switch -c <branch-name> <default>
#   Already exists → confirm its base is current; if stale, STOP and report.

# 0d. Verify.
git status --porcelain                       # → only the expected set
git branch --show-current                    # → <branch-name>
git rev-list --count <default>..<remote>/<default>   # → 0  (skip if no remote)
```

## Print it ready to run, in the host's shell

The printed recipe is a script the executing session runs as-is, not notes to translate.
Write it for the shell the session runs in: **Windows → PowerShell**, anything else →
POSIX `sh`. The owner may ask for the other. It is carried inside the kickoff's one fence
(§4.2), under the `REPOSITORY RECONCILIATION` label that names the shell, every line
indented two spaces, so one paste carries the kickoff and its recipe. Because it is
indented inside that fence:

- No here-strings or heredocs: the indentation would break their terminators.
- No triple backticks anywhere in the fence.

In either shell:

- Every STOP is a real check that halts the script with the reason, not a comment.
- Every expectation the recipe states (an empty tree, the branch name, the
  specification on `HEAD`) is asserted, and a failed assertion halts with what was
  found.
- A network step runs only behind a switch at the top that is off by default, when
  `policy.git.networkOperations` is `ask`. With no remote, the step is left out.
- No tool the shell lacks: in PowerShell, `Select-String` and `Test-Path`, never
  `grep` or `2>/dev/null`. Paths with spaces are double-quoted.

The PowerShell form of the template:

```powershell
# Detected <date>: remote <remote> (<url>); default branch <default>; <worktrees>.
# policy.git: <policy, or "not declared -> defaults ...">.
$ErrorActionPreference = 'Stop'
$AllowNetwork = $false   # policy.git.networkOperations: ask. Set $true to fetch.
function Stop-Dispatch($why) { throw "STOP: $why" }
function Invoke-Git { git @args; if ($LASTEXITCODE) { Stop-Dispatch "git $args exited $LASTEXITCODE" } }

# 0a. Scope the working tree. Expected dirty set: <set, or "none">.
if (Test-Path .git/index.lock) { Stop-Dispatch ".git/index.lock exists. Check for a running git process; never delete it." }
$dirty = git status --porcelain
if ($dirty) { $dirty; Stop-Dispatch "unexpected dirty paths above. Report them; never stash, reset or clean." }

# 0b. Sync <default>.
if ($AllowNetwork) { Invoke-Git fetch <remote> --prune }
Invoke-Git switch <default>
git merge --ff-only <remote>/<default>
if ($LASTEXITCODE) { Stop-Dispatch "<default> diverged from <remote>/<default>. No force, no reset --hard." }

# 0c. Create the work branch.
if (git branch --list <branch-name>) {
    git merge-base --is-ancestor <spec-sha> <branch-name>
    if ($LASTEXITCODE) { Stop-Dispatch "<branch-name> exists but lacks <spec-sha>." }
    Invoke-Git switch <branch-name>
} else { Invoke-Git switch -c <branch-name> <default> }

# 0d. Verify.
if (git status --porcelain) { Stop-Dispatch "tree not clean after branching." }
if ((git branch --show-current) -ne '<branch-name>') { Stop-Dispatch "not on <branch-name>." }
if (-not (git show "HEAD:<spec path>" | Select-String -SimpleMatch '<distinctive token>')) { Stop-Dispatch "specification missing from HEAD." }
"Reconciled: on <branch-name> at $(git rev-parse --short HEAD)."
```

Keep the sanctioned fallback from the recipe as a commented alternative under 0b. It is
never run silently.

## Branch cleanup, and the work itself

**Branch cleanup is maintenance, not a prerequisite** (item 68). Report stale or
`[gone]` branches and unpruned worktrees as housekeeping. Do not gate this
dispatch on removing them, and never use `git branch -D` or `git worktree remove
--force` as part of a dispatch.

**During the work**, under whatever `policy.git.policy` permits: stage explicit
paths only (never `git add .` / `-A`); verify the cached set matches the expected
set before committing; no destructive flags; no force-push without explicit
authorization.

Return to SKILL.md *Repository reconciliation* (halt semantics), then to the step that sent you here.
