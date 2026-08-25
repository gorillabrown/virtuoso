# Git Policy

Git behaviour is **project policy**, not a fixed rule of this plugin
(redesign items 64–73). It lives in `policy.git` in
`Virtuoso/workspace-layout.json`. Read it before touching a repository.

```jsonc
"git": {
  "policy": "explicit-path-commit",  // see the ladder below
  "separationOfDuties": false,       // optional; not tied to any product or vendor
  "independentReviewer": false,
  "defaultBranch": "",               // "" = DETECT it; never assume "main"
  "remote": "",                      // "" = DETECT it; never assume "origin"
  "requireRemote": false,            // local-only repositories are fully supported
  "networkOperations": "ask",        // ask | allow | deny
  "branchNameTemplate": "{item-id}",
  "branchCleanup": "maintenance",    // never a dispatch prerequisite
  "staleLock": "report",             // report | prompt — never automatic deletion
  "worktreeAware": true
}
```

## The policy ladder

| `policy` | The ceremony may … |
|---|---|
| `read-only` | inspect only. No `add`, no `commit`, no branch creation. |
| `prepare-no-stage` | write files. Never `git add`. |
| `explicit-path-stage` | `git add <exact paths>`. Never commit. |
| `explicit-path-commit` | stage exact paths and commit. Never push. |
| `push` | commit and push. |

`separationOfDuties: true` additionally means the actor that authored a change
does not commit it; `independentReviewer: true` means a commit waits on a
reviewer. Both are *optional project choices*. Neither is implied by which
product, host, or model is running the ceremony.

## Detection, not assumption

- **Default branch** — when `defaultBranch` is empty, detect it:
  `git symbolic-ref --quiet refs/remotes/<remote>/HEAD`, else the branch
  `git remote show <remote>` reports, else the current branch. Never hardcode `main`.
- **Remote** — when `remote` is empty, detect it: the current branch's upstream
  remote, else the sole remote if there is exactly one, else report the ambiguity
  and ask. Never hardcode `origin`.
- **No remote is fine.** A repository with no remote is fully supported. Unless
  `requireRemote` is true, the absence of a remote is a fact to report, not a blocker.

## Worktrees

When `worktreeAware` is true (the default), distinguish:

- the **primary tree**, which may be dirty with work unrelated to this item, and
- the **execution worktree** dedicated to this item.

A dirty primary tree does not invalidate a clean, isolated execution worktree.
Report unrelated dirty paths; do not treat them as a gate on work happening
somewhere else (item 72). Enumerate worktrees with `git worktree list`.

## Scoped vs unrelated changes

Before staging, compute the *expected dirty set* for this item. Then:

- paths inside the expected set → stage explicitly, by path;
- paths outside it → **report** them and leave them alone.

Unrelated dirty paths are never staged, stashed, reset, or cleaned.

## Locks

A `.git/index.lock` is *reported*, never deleted automatically (item 69). Verify
whether a git process is actually running first. With `staleLock: "prompt"` you
may ask the user to remove it; the plugin never removes it on its own.

## Network operations

`networkOperations` governs fetch, pull, and push:

- `ask` (default) — surface the operation and get approval before running it.
- `allow` — run it; still report what it did.
- `deny` — never run it; report what would have been needed.

Offline is a normal state, not a failure.

## Branch cleanup

Deleting merged branches and pruning worktrees is **maintenance** (item 68). It
is never a prerequisite for starting unrelated work. Report stale branches; do
not gate dispatch on removing them.

## Rules that hold under every policy

These are not configurable:

1. **Inspect before mutating.** `git status --porcelain` and `git diff --cached
   --name-only` before and after staging.
2. **Preserve unrelated work.** Never `git stash`, `git reset`, `git clean`, or a
   destructive `git checkout`/`git restore` over paths you did not author.
3. **Stage exact paths.** Never `git add .` or `git add -A`.
4. **Verify the cached set** matches the expected set before committing; stop on
   anything unexpected.
5. **No force-push, no history rewriting** on a branch you did not create,
   without explicit authorization.
