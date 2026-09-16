# Project Overlays — Design

**Status:** implemented in v1.7.0 · **Date:** 2026-09-16 · **Schema:** unchanged (v2)

## Problem Statement

A project that needs a shipped Virtuoso skill or agent to behave differently has exactly one
mechanism today: copy the whole file into its own tree and edit it. That fork then drifts
from the plugin in *both* directions — the plugin gains rules the fork never sees, the fork
gains rules the plugin never sees — and both files load in the same session, so the agent
reads two contradictory copies of one instruction and follows whichever it encounters first.
There is no signal that this has happened.

The one overlay mechanism that already exists covers a single skill (`virtuoso`) and works by
telling the caller to paste extra rules into a dispatch prompt. It saves nothing: the rules
still live outside the plugin, still have to be restated per dispatch, and still cannot be
audited.

## Goals

- Give every shipped skill and agent a project-owned extension point that does not involve
  copying the file.
- Make the extension point addressable without configuration — one convention, derivable
  from the shipped file's own path.
- Make its state observable at session start, including the state "there is none".
- Make it impossible for a newly added skill or agent to ship without the mechanism wired in.
- Keep it entirely optional and free for a project that does not use it.

## Non-Goals

- Not a templating or patching engine. An overlay is a document the agent reads, not a diff
  the plugin applies.
- Not a plugin write surface. Nothing in the plugin ever edits a project's overlays.
- No registry schema change. This is a new role in the existing v2 vocabulary.
- No change to the published two-line preflight status contract.

## Design

Four layers, one per failure mode the fork exhibited.

### 1. A registry role says where overlays live

```jsonc
"overlays": {
  "path": "Virtuoso/overlays",
  "provider": "directory",
  "authority": "reference",
  "mutability": "read-only",
  "allowedWriters": [],
  "validation": "exists",
  "classification": "active",
  "origin": "authored"
}
```

Two properties come from machinery the plugin already has, rather than from new code:

- **Read-only is already enforced.** `RoleSpec.writable_by` refuses any role whose mutability
  is in `NON_WRITABLE_MUTABILITIES`, before it ever consults `allowedWriters`. Registering
  the role `read-only` therefore makes every ceremony write to it impossible, including one
  that names a wildcard writer. No new refusal path was written, because the right one exists.
- **Opt-in comes from an omission.** `overlays` is deliberately absent from
  `CREATE_ROLE_ORDER`, so `create` neither registers the role nor scaffolds a directory. A
  project that never asked for overlays is never handed an empty folder. Leaving a role out
  of that tuple is how the plugin says "supported, not assumed".

`safepath.validate_path` already validates the registered path — root escape, absolute
paths, and a file registered where a directory is declared are all findings today.

### 2. One module finds and audits them

`tools/governance/overlays.py`. The addressing scheme is a **mirror path**: an overlay lives
at the shipped file's own relative path beneath the overlays root.

| shipped file | its overlay |
|---|---|
| `skills/<skill>/SKILL.md` | `<overlays>/skills/<skill>/SKILL.md` |
| `agents/<Agent>.md` | `<overlays>/agents/<Agent>.md` |

Only `skills/` and `agents/` are addressable; a file elsewhere under the root mirrors nothing
and is reported rather than quietly ignored.

**Case-exactness is the load-bearing detail.** `os.path.exists` inherits the filesystem's
case folding, so on Windows and on a default macOS volume it answers *yes* for a path whose
case is wrong. An overlay authored on one of those machines then works there and resolves to
nothing on Linux and in CI — with no error, because "no overlay" is a supported state.
`case_exact_join` walks the path one segment at a time and compares each against the names
`os.scandir` reports, so the answer is identical on every filesystem. The audit additionally
recognizes the case-folded near-miss and names the correct spelling.

The audit reports `overlays-absent`, `overlay-orphan`, `overlay-case-mismatch`,
`overlay-outside-mirror`, `overlays-external`, `overlays-writable`, and
`overlays-has-writers`. All of them are **informational or warnings, never errors**: an
overlay problem belongs to the project, and promoting it to an error would put a working
registry into `repair-needed`, promising a repair plan that cannot exist for a file the
plugin does not own.

`virtuoso_registry.py overlays [--for <mirror-path>]` exposes this. Both forms are queries;
neither creates the directory. "There is no overlay for this file" is an answer with exit 0.
An unusable `--for` argument — absolute, empty, or containing a traversal segment — is exit 3
with a message naming the expected form.

### 3. An anchored clause in each skill and agent

All 15 skills and all 10 agents carry the same clause, marked
`<!-- virtuoso-overlay-clause v1 -->`. Its single home is `overlays.OVERLAY_CLAUSE`; CI
compares shipped bodies against that constant, so "the clause is present" and "the clause
still says the same thing" are one check rather than two documents that can drift.

CI enumerates both rosters **by scanning `skills/` and `agents/` on disk**, never from a list
kept in the validator. A list is precisely the thing a sixteenth skill gets added without
touching — and the clause it would then be missing is the one telling it to read its
project's overlay instead of being forked. The same principle is applied to hook files:
`check_session_hook` now validates every `hooks/*.json` it finds.

### 4. A status line that always states a result

Preflight prints a third parseable line beside the existing two, in every mode, surviving
`--quiet`:

```
overlays: not registered
overlays: registered but absent (<path>)
overlays: registered, none present (<path>)
overlays: 2 applied (<path>); 3 finding(s)
```

It is attached in exactly one place — after the mode dispatch in `preflight()`, including on
the error branch — so no branch can be the one that forgets. The observation is deliberately
total: a registry it cannot read reports `not registered` rather than raising, because
reporting overlays is a side observation and must not fail the operation the user asked for.

`not registered` exists as an explicit state because printing nothing would be
indistinguishable from an all-clear, and that is exactly how a project ends up believing its
overlays are in force while nothing reads them.

The published `contract_lines()` pair is unchanged, so every existing caller that parses the
two-line contract keeps working.

## The one narrowing

An overlay wins over the shipped file on conflict, **except** that it may not loosen a
shared-contract safety rule: registry resolution, read-only preflight, write permission, git
safety, provenance, or the issue contract. These are published as
`overlays.SAFETY_FLOOR` and printed by the CLI whenever overlays apply.

This is narrower than a plain "the overlay wins". It is deliberate: anyone who can write the
project folder can write an overlay, so without the floor, write access to a project folder
is also permission to switch off the plugin's git and write-permission guards.

## Release integrity (included because overlays land in a release)

- `.codex-plugin/plugin.json` is a shipped manifest again — it had been swept into
  `.gitignore` as local WIP — and is declared in `.version-bump.json`, so the Codex install
  surface is bumped with every release. `validate.py` fails when two install surfaces
  advertise different versions.
- `release.py` derived its dirty-tree tripwire from `.version-bump.json` but staged a
  hand-listed pair of files. A newly declared manifest would therefore be bumped and then
  left out of the release commit. Staging now uses the same derived set the tripwire checks.
- Agent memory directory names are audited against disk **and** git's index. A directory
  spelled with the wrong case reads back as correct on a case-insensitive filesystem and
  resolves to nothing elsewhere, where the agent silently starts every session with an empty
  memory. Git's index records the spelling it was given, so it catches a case-only rename the
  filesystem hides; the filesystem catches what was never added to the index. Neither record
  alone is sufficient.

## Success Metrics

| Gate | Result |
|---|---|
| `pytest` | 429 passed, 2 skipped (was 301 passed, 2 skipped) — 128 added, 0 broken |
| `validate.py` | `All checks passed.` |
| Overlay clause | 15/15 skills, 10/10 agents, verbatim |
| Install manifests | all three at 1.7.0 |
| Codex manifest | serves all 15 skills; hook target exists and runs a read-only mode |
| Project writes by the new code | 0 |

## Verification notes

Every claim above was executed, not read. Two errors in the first draft were found by running
it and are fixed in what shipped:

1. `check_agent_memory_names` assumed `AGENT_MEMORY_GUIDE.md` is always on disk, so it
   reported a false missing-from-index failure on any agents tree without it.
2. `release.py`'s staging/tripwire split (above) — found because adding the Codex manifest to
   `.version-bump.json` made the derived tripwire set grow and the hand-listed staging set
   not.

## Open Questions

- Should an overlay be able to address `references/` as well as `skills/` and `agents/`?
  Deferred: references are shared contracts, and a project-specific variant of one is a
  registry policy question rather than a document question.
- Should the audit's findings appear in `registry.validate()` rather than only in the overlay
  status? Deferred: the registry validates *registration*, the overlays module audits
  *content*, and merging them would require the registry to know the plugin root.
