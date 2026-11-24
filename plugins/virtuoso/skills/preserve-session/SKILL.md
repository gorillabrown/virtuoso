---
name: preserve-session
description: >
  MANUAL INVOCATION ONLY. Preserve a settled session before it is cleared. Refuses while
  anything in this session still runs and offers compaction instead. Otherwise sorts
  everything the session holds into keep or drop, files every keeper in the registered
  home that owns its kind (a commit, findings, issues, the holding bay, host or agent
  memory, a project path), writes one dated session record listing each item, where it
  went and what was dropped, verifies every destination, and only then reports that the
  session is safe to clear. It never clears, stops, deletes or pushes anything, and never
  changes a session setting. Triggered by "/preserve-session", "preserve this session",
  or "save the session before I clear".
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

# Preserve Session

A long session ends in one of two bad ways: cleared without saving, and its temporary
work is lost; or kept running, and everything it carries, needed or not, rides into the
next piece of work. This skill makes clearing cost nothing. It secures every item the
session holds in a durable home a later session can find, proves each one landed, and
then tells the user it is safe to clear. The session itself, with its name and settings,
stays; only its context goes.

**Announce at start:** "Using preserve-session to save this session before it is cleared."

What it never does, in any step:

- clear the session, compact it, or change any of its settings;
- stop, cancel, delete or push anything, or commit beyond what `policy.git` allows;
- stage a file this session did not edit (another session's work in the same checkout);
- write a lesson, the terminal ledger, an epic packet or the work register;
- copy a credential, token or password into any document or memory file;
- report "safe to clear" before `session --record --apply` has verified every destination.

There is no promise that the next session resumes the last task. What it needs is in
the project's documentation, found through the session record or a repository search.

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check (zero project
writes).

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Read the `virtuoso-status:` line and branch:

- `ready` or `warning` — continue (surface any warnings).
- `repair-needed` — **STOP.** Nothing is saved into a registry that needs repair. Show the
  `--mode repair` preview and leave the decision to the user.
- `adoptable` or `none` — **STOP.** With no registry there is no registered home and no
  session record, and this skill never falls back to a conventional path. Offer
  `/virtuoso-init`.

The session record lives in the opt-in `sessionRecords` role. The skill writes as the
`preserve-session` actor, which a project's layout must name in the `allowedWriters` of
`sessionRecords`, `findings`, `issues` and `holdingBay`. A layout that registered those
roles before this skill existed refuses the actor: show the user the entry to add, which
the refusal prints, and stop until they add it.

## Step 1 — The gate: is anything still running?

Make a fresh marker with a command, never by hand, so no two sessions share one:

    python -c "import secrets; print('preserve-session:' + secrets.token_hex(4))"

Its output is printed into this session, which is how the gate finds this session's own
transcript. Below, `<hex>` stands for those 8 hex digits. Then run the gate with it:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . session --gate --marker preserve-session:<hex>

It reads this session's whole transcript, writes nothing, and exits:

| Exit | Means | Do |
|---|---|---|
| 0 | nothing in this session is still running | continue to Step 2 |
| 1 | something is still running; each holding is named | **refuse** (below) |
| 3 | it cannot tell (no transcript or more than one carries the marker, it cannot be read, or this host gives no way to see background work) | **refuse**: cannot tell counts as running |

**Refusing.** Write nothing. Name what is running, as the gate printed it, and offer
compaction instead: on a host that has `/compact`, offer `/compact`; on one that does
not, say to compact by the host's own means. Two holdings route elsewhere:

- **a dispatch whose work is finished but not closed out** → `/dispatch-closeout`, which
  owns the terminal record; this skill never writes it;
- **an open dispatch still mid-step** → finish the step, or compact, and run this skill
  once the session is settled;
- **a scheduled check-in or wakeup** → it stays a holding until it is cancelled in this
  session (delete the scheduled job, or stop the loop). Ask the user; never cancel one
  yourself.

`session --record` runs the gate again before it keeps the record, so anything started
during Steps 2–5 refuses "safe to clear" too.

Work running in *other* sessions is not this session's holding and does not refuse it.

## Step 2 — Inventory

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --json session --inventory --marker preserve-session:<hex>

It lists, read-only, the files this session's transcript edited, split into
**uncommitted**, **untracked** and **committed** since the session's base commit
(its subagents' edits included); **others**, dirty files this transcript never edited
(another session's, or changed here by a command), which are left alone and never
staged; **shared**, this session's files another recent session also names, never
staged whole here; **unpushed** commits; **leftovers** outside the tree; and **stage**,
the exact paths this session may stage. A figure the inventory cannot compute is named
*not computable*; never guess it.

Then take stock of what the inventory cannot see: decisions and conclusions reached
only in conversation, knowledge about the project, what was learned about the user and
how they work, a storyboard or plan stopped before alignment, scratch files outside the
tree, and anything blocked or waiting on someone.

## Step 3 — Sort every holding: keep or drop

Every holding goes into one of the two piles. **Keep** what a later session could need
and could not cheaply rebuild. **Drop** what is reproducible, superseded, or noise, and
say why in one line. File each keeper in the home that already owns its kind:

| Holding | Durable home |
|---|---|
| Code and documents this session changed | a commit of its exact paths, as `policy.git` allows (Step 4) |
| A decision, conclusion or piece of project knowledge that lives only in the conversation | a finding in the `findings` role (`F-NNN`); a lesson candidate is flagged there, never appended as a lesson |
| A stop, block or open question waiting on someone | an issue in the `issues` role |
| A storyboard or plan stopped before alignment | the holding bay, recorded `paused` with a `Not aligned — <the items still open>` verdict |
| What was learned about the user, or feedback on how to work | host or agent memory, per `references/agent-memory-guide.md`; project knowledge never goes there |
| A scratch file worth keeping | its registered role's directory, or a project path the repository already uses for its kind |
| Reproducible output, superseded drafts, probes, logs | dropped, listed under **Not kept** with the reason |

A credential, token or password is never kept in any document or memory file. Name that
one existed and where the user keeps it, and nothing more.

## Step 4 — File each keeper

File each keeper in its home, then note where it went: the exact path, the commit id,
the `F-NNN`, the held entry, the issue file, or the memory file's absolute path.

- **Commits.** Stage only paths from the inventory's **stage** list, each named exactly;
  never `git add -A` or `.`, and never a path under **others**. Commit as `policy.git`
  permits.
- **Under a git policy below "commit"** the files are saved on disk but not committed:
  list them under **Uncommitted** in the record, and recommend `/git-handoff` to the user
  so the repository operator can commit them. Do not invoke it; it is manual only.
- **Findings and issues** go through their roles as the registry contract describes.
- **A paused storyboard or plan** is recorded with
  `holding --record <entry> --state paused --note "<what is still open>"`, preview first,
  then `--apply`, as `--actor preserve-session`.

## Step 5 — Write the record, verify it, report

Write the session record as a draft file outside the project (a scratch folder):

    # Session record — <what this session was about>

    - **Date:** <yyyy-mm-dd>
    - **Session:** <this session's id>
    - **Host:** <the host's name>
    - **Marker:** preserve-session:<hex>

    ## Items

    | Item | Kind | Destination | Verified |
    |---|---|---|---|
    | <what was kept> | <code, finding, issue, held, memory, file> | `<destination>` |  |

    ## Not kept

    - <what was dropped> — <why>

    ## Uncommitted

    - <path saved on disk but not committed, or "none">

    Provenance: transcript <path>; git HEAD <sha>.

Each **Destination** is one of `path:<project path>`, `commit:<sha>`, `finding:F-NNN`,
`held:<entry>`, `issue:<file name>`, or `memory:<absolute path>`. Leave **Verified**
empty: the check fills it in.

Preview, then keep it:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor preserve-session session --record <draft>
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor preserve-session session --record <draft> --apply

`session --record` verifies every row where it says it went and refuses (exit 1) while
any row is unverified, the record lacks a header line, or it carries a credential; it
refuses (exit 3) while no `sessionRecords` role is registered, and prints the entry to
add. Fix what it names and run it again. Only with `--apply` and every row verified does
it keep the record in `sessionRecords` as `<yyyy-mm-dd>-<hhmm>-<slug>.md`, read it back,
drop this session's pending handoff note, and print `Safe to clear: run /clear`.

Report to the user in this order: what was kept and where, what was not kept, anything
saved but uncommitted (with the `/git-handoff` recommendation), and last the line the
check printed. The user runs `/clear` (on a host without it, they start a fresh
conversation by the host's own means). This skill never clears the session itself.
