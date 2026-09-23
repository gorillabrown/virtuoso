---
name: pointer-closeout
description: |
  MANUAL INVOCATION ONLY. Closes a completed dispatch. Verifies completion
  evidence, drafts the close-out report and retrospective entries, and then
  performs a transactional crossing — create the close-out artifact, append the
  append-only terminal record, persist local governance changes, close the item
  in the live work register through its provider, and verify every result. Any
  partial failure leaves a recovery record naming exactly what remains. Triggered
  by "/pointer-closeout", "close out this sprint", or "run the close-out".
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
- **Effort levels** — low / medium / high / max. A property of the task's difficulty, never a ranking of whoever performs it.

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

# Pointer Close-Out

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check. It performs
discovery and validation with zero project writes.

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Add `--json` when you want the structured result (status, writes, findings, and the full
resolved role table). Read the `virtuoso-status:` line and branch:

- `ready` — the registry is valid. Continue.
- `warning` — usable; surface the findings to the user and continue. Warnings are not blockers.
- `repair-needed` — **STOP.** Run `--mode repair` to produce the preview, show the user the
  proposed paths, semantic changes, files affected, and backup location, and apply it only
  with `--apply` after they approve.
- `adoptable` — the project has governance documents but is not registered. Offer
  `--mode adopt`: it registers what exists, in place. Nothing is moved, duplicated, or rewritten.
- `none` — no registry and nothing to adopt. Route the user to `/virtuoso-init`.
- `failed` — report the error verbatim and stop.

If neither launcher resolves, report that the plugin could not be located and stop. Do not
guess a path.

**Governance authority.** Resolve every document you need through the registry
(`references/registry-contract.md`). Never create a parallel document for a registered role;
never write to a role whose `allowedWriters` does not name this ceremony; never treat a
`mirror`, `report`, `archive`, or `unknown` role as truth.

Read the `roadmap-integrity:` line the preflight printed (it follows the `deadlines:` line; `--json` carries it as `roadmapIntegrity`). On `fail` (missing, not text, or null bytes), STOP and report the corruption to the user; do not migrate or rewrite a corrupt roadmap. On `warn` (empty or unusually large), surface it and confirm with the user before proceeding. On `ok`, or `external` (a roadmap the preflight does not read), continue. Before rewriting the roadmap, re-check it: `virtuoso_preflight --check-document <path>` prints the same state for one file.

**Bookend with `/next-pointer`.** That skill opens a dispatch; this one closes it.

Two waves:

- **Wave 1 — Draft & Confirm** (writes nothing): the brief, findings,
  interpretation, proposed dispositions, governance updates, retrospective
  entries, and the proposed register and roadmap changes. The user confirms.
- **Wave 2 — The transactional crossing** (writes, in a fixed order, verifying
  each step): create the artifact, append the terminal record, persist local
  governance, close the item in the live register, verify everything.

This skill never prints a next dispatch pointer — that is `/next-pointer`.

## Resolve roles and capabilities before Wave 1

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor pointer-closeout provider
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . closeout --item "<ITEM-ID>" --date "<YYYY-MM-DD>"
    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open

The second command is **read-only**: it resolves paths and the next lesson
identifier (`nextLessonId`, prefixed per `policy.lessons.idPrefix`) without
creating anything. Pass `--prepare` only in Wave 2, when the user has approved
the crossing and the directory actually needs to exist. The third lists the live
lessons: the ones this item's specification applied, whose outcome the close-out
records, and the ones a new lesson may repeat — a second occurrence is what
promotes an observation to a rule.

It **fails loudly** rather than guessing: no registry, or a registry with
error-severity findings, is an error naming the fix — never a silent fallback to
a conventional close-out directory.

Confirm before drafting:

| Step | Requires |
|---|---|
| append the terminal record | `terminalLedger` registered, and `policy.terminalLedger.writers` names `pointer-closeout` |
| close the item in the live register | provider capability `record-completion` (or `write-status`), and `workRegister`'s `allowedWriters` names `pointer-closeout` |
| write the close-out artifact | `closeOuts` writable by this ceremony |
| append lessons | `lessons` writable by this ceremony |
| persist to version control | whatever `policy.git.policy` permits |

Any of these that is unavailable changes the plan **before** Wave 1 drafts
anything. Say what will happen instead — a hand-off, or a manual step — rather
than discovering it mid-crossing.

## Wave 1 — Draft & Confirm

1. **Lead with the five-line brief** (below).
2. Findings table.
3. Interpret non-pass results; propose dispositions.
4. Draft the net-new governance updates still needed.
5. Draft the lessons (deliverable 2): what this dispatch taught, as entries ready
   to append — or the one line saying it taught nothing, and why — and how each
   lesson the specification applied turned out.
6. Propose the register and roadmap changes.
7. **Review every file the dispatch created.** Run, against the ref the
   specification's *Branch* field says the dispatch started from:

       "$HOME/.virtuoso/bin/virtuoso" sprint_guards created-files --root . --base "<base ref>"

   Draft the report's *Files Created* section from it: each **temporary** (scratch,
   backup, cache, log, anything under the registered `temp` role) proposed for
   removal — committed ones included; each **untracked** file proposed to commit,
   add to the ignore file, or name for the user's decision; each **uncommitted**
   change proposed to commit or revert. Nothing is left unreconciled by default: a
   close-out that leaves litter makes the next merge a forensic exercise.
8. State the **crossing plan**: the exact ordered steps Wave 2 will perform, the
   roles each touches, and what happens on a partial failure.
9. Ask the user to confirm dispositions, lessons, file dispositions, and the crossing plan.

Wave 1 writes nothing.

## The five-line brief

```
# [Item title] Close-Out  *(ITEM-ID)*

**Goal:** [What the dispatch set out to do — one sentence.]
**Result:** [What actually happened — name the things, no aggregates.]
**Learned:** [The durable lesson, by identifier: <prefix>-NNN — title. Or: No new lesson — reason.]
**Recommend:** [Recommended next direction — prose only, no pointer.]
**Bottom line:** [One-sentence takeaway.]
```

Optional one-line add-ons where they materially sharpen the story: **By the
numbers**, **Between the lines**, **Yes, but**, **What's at risk**. Past ~10
lines, cut.

**Substance rule:** name the actual things. "Shipped three fixes" hides the
conclusion — write which three, in one clause. Lead with the descriptive name;
the identifier is secondary.

## Deliverables

### 1. Close-out report

Interprets results, classifies findings, confirms dispositions, identifies
governance updates, and points at the next work.

One per completed item, named per the project's convention, written into the
registered `closeOuts` directory.

- Template: [assets/CloseOut.template.md](assets/CloseOut.template.md)
- Structure and the finding/disposition model:
  [references/closeout-report-format.md](references/closeout-report-format.md)

### 2. Lessons

What this dispatch taught, recorded where the next specification will read it: the
registered `lessons` role. This is not optional, and it is not prose in the report
alone — a lesson that exists only in a close-out is one no specification will ever
apply. Every close-out produces one of two things:

- **New lessons**, one entry each, appended to the registered `lessons` role under
  the identifier `closeout` resolved (`nextLessonId`), in the standard shape:
  [assets/SpecRetro.entry.template.md](assets/SpecRetro.entry.template.md).
  `Applies to` is the field the next author matches against new work — say *when*
  the lesson bears, not only what happened.
- Or the line **`No new lesson — <reason>`** in the report's Lessons section. The
  reason is evidence: "followed <prefix>-NNN exactly", "a routine change with no
  surprise". A close-out that names neither is not finished.

And in either case, **the outcome of every lesson the specification applied** (its
*Lessons applied* section): each held, or did not. A lesson that failed to prevent
the trap it names is the second occurrence that promotes it, or the evidence that
retires it — append a status record under its identifier; never edit the original.

The retrospective evaluates the specification too: effort calibration, sizing,
routing, dispatch precision, discovery yield.

- Entry shape, status records, and the append-only rule:
  [references/spec-retro-format.md](references/spec-retro-format.md)
- When an observation becomes a standing rule:
  [references/promotion-rules.md](references/promotion-rules.md)

---

## Wave 2 — The transactional crossing

Run the six steps **in this order**. Each step verifies before the next begins.
Local, reversible work happens before anything irreversible or external.

### Step 1 — Verify completion evidence

Before writing anything, confirm the work is actually done:

- the deliverables the specification named exist;
- its acceptance criteria are mechanically satisfied — run the commands the
  specification recorded and read their output, do not accept a summary;
- the repository state matches what was claimed (read-only inspection:
  `GIT_OPTIONAL_LOCKS=0 git --no-optional-locks status -sb`, `log --oneline -5`,
  `show <commit> --stat`);
- any mid-dispatch amendments are accounted for.

Evidence that does not hold **stops the crossing**. Report exactly which
criterion failed, with its output. A close-out is a claim about reality; do not
make one you have not checked.

### Step 2 — Create the close-out artifact

Write the close-out report into the registered `closeOuts` directory.

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . closeout --item "<ITEM-ID>" --date "<YYYY-MM-DD>" --prepare

**Idempotent:** if the artifact already exists for this item and date, do not
duplicate it. Update it in place, or stop and ask — never write a second one.

Also process a governance staging file if the project uses one (a worktree-
resident dispatch stages its governance changes rather than editing main
documents directly). Parse the fold-in instructions, apply them to the registered
targets, process amendment migrations before inline collapses, and delete the
staging file only after every fold-in lands. A fold-in that conflicts with current
state becomes a reconciliation question, not a silent overwrite.

Read the item's issue files in the registered `issues` role (`Issue.<ITEM-ID>.*`,
per `policy.issues.filenameTemplate`). Each carries the `## Decision` block
`mid-dispatch-decision` appended in its step 6d; summarize every block into the
report's *Mid-Dispatch Decisions* section. An issue file with no `## Decision`
block is an open decision, not a settled one: stop and route it to
`/mid-dispatch-decision` before the crossing continues.

### Step 3 — Append the terminal record

Append **one** record to the registered `terminalLedger`:

- Only if `policy.terminalLedger.writers` names `pointer-closeout`. If it does
  not, stop and hand the record to a permitted ceremony or to the user.
- **Append-only.** Never reorder, rewrite, or delete an existing record. A
  correction is a **new** record that names the record it corrects, appended
  under `policy.terminalLedger.correctionWriters`.
- **Idempotent.** A record whose content already appears in the ledger is a
  no-op. Re-running a close-out never duplicates history.

### Step 4 — Persist local governance changes

Apply the confirmed roadmap changes and append the lessons — new entries and
status records, each appended under the next or the existing identifier, none
edited — then persist per `policy.git`:

| `policy.git.policy` | What happens |
|---|---|
| `read-only` | Report the exact changed paths; someone else commits. |
| `prepare-no-stage` | Leave the changes in the working tree; report the paths. |
| `explicit-path-stage` | `git add "<exact paths>"`; verify the cached set; report. |
| `explicit-path-commit` | Stage the exact paths and commit. |
| `push` | As above, then push, subject to `policy.git.networkOperations`. |

Carry out the confirmed file dispositions first: delete each untracked temporary,
`git rm` each committed one (exact paths), add confirmed ignore patterns, and stage
the files confirmed for commit with everything else.

Stage **exact paths** — never `git add .` or `-A`. Verify
`git diff --cached --name-only` matches the expected set before committing, and
stop on anything unexpected. Unrelated dirty paths are reported and left alone.

If `policy.git.separationOfDuties` is true, hand the commit to another actor with
the exact file list. That is a project choice, not a rule of this plugin.

If the project declares no git policy and the default applies, say plainly which
files were written and whether they are committed. The close-out is not finished
while the changes are unpersisted.

### Step 5 — Close the item in the live register

Through the provider, not by editing a file:

- pass the `revision` read in Wave 1, so a concurrent change is refused rather
  than clobbered;
- set the terminal status using the project's own vocabulary
  (`policy.workRegister.statusMappings`);
- record the completion date and the evidence link (the close-out artifact).

**External registers are mutated by this ceremony, not by the plugin.** The
provider returns a structured instruction — operation, item, fields, expected
revision, idempotency key. Execute it with the host's connector, then confirm the
result. Re-running with the same idempotency key must not repeat the change.

**Two mandatory register outcomes** — the belt moves forward by exactly one:

- **Retire the closed item.** It leaves the active pipeline and no longer reads as
  in flight or pending.
- **Elevate the next item** into the vacated head position, so it becomes the
  active target. This is a sequence change, not a dispatch pointer.

### Step 6 — Verify every result

Re-read each thing you wrote, from its source:

- the close-out artifact exists at the resolved path and carries the expected content;
- the terminal ledger carries exactly one new record for this item, and prior
  records are byte-identical to before;
- the roadmap and lessons changes are present, and committed if policy required it;
- the report's Lessons section passes the lessons gate — every lesson it names is
  now in the registered role, or it says "No new lesson" with a reason:

      "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check "<close-out path>" --closeout --item "<ITEM-ID>"

- the item's status in the live register, re-read through the provider, is terminal;
- the next item is now at the head;
- `sprint_guards created-files --base "<base ref>"` exits 0 — or lists exactly the
  files `policy.git` leaves for someone else to commit and the ones the user chose
  to decide later, each named in the report's *Files Created* section.

### On partial failure

If a step succeeds and a later one fails — most commonly, local files commit but
the external register update does not — **write a recovery record** naming
precisely what completed and what remains:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . recovery

Report it to the user in the close-out summary. Never silently retry the whole
crossing: the completed steps are idempotent, so re-running is safe, but the user
must know the crossing is incomplete before it happens again.

---

## After the crossing

### Buffer check

Every close-out drains the dispatch buffer by one. Count the remaining
dispatch-ready active items and compare against `policy.roadmap.dispatchBuffer`.
If the count is below target, or the newly elevated head item is a stub,
recommend `/roadmap-review` plainly in the summary.

If `policy.roadmap.dispatchBuffer` is 0 or `policy.roadmap.eagerSpec` is false,
skip this check — the project has deliberately disabled eager specification. Do
not recommend replenishing a buffer the project does not keep.

Never author a specification here. Flagging depletion is this skill's whole job in
that loop.

### Governance gates

After the report is drafted, check whether any lesson belongs in a governance
document, and whether an audit, milestone review, or release gate should be
surfaced. Read [references/governance-gates.md](references/governance-gates.md).

### Optional adversarial pass

Before Wave 2 writes anything, offer `/adversarial-review` over the drafted
report and retrospective **when the close-out carries something the project will
inherit unexamined**: a lesson being promoted to a standing rule, an item declared
complete on partial evidence, or a change that retires scope. Skip the offer for
a routine close-out — a reflexive offer trains the user to decline it. If the pass
runs, fold its blocking concerns into the findings before the crossing begins.

### Next dispatch pointer — out of scope

This skill does not print one. Wave 1's *Recommend* line names a direction in
prose. Wave 2 ends at verification.

---

## Guardrails

- Propose dispositions; do not decide them unilaterally.
- Prefer net-new governance updates over ceremonial rewrites.
- Promote a lesson to a standing rule only after the same pattern appears twice.
- Change a lesson's status by appending a status record under its identifier; never
  edit an earlier entry. The role is append-only, and its history is how a second
  occurrence is recognized.
- A close-out without its Lessons section is not a close-out. "No new lesson" is an
  answer; silence is not.
- Never leave output only in conversation.
- Never write to a role whose `allowedWriters` does not name this ceremony.
- Never edit a generated artifact — regenerate it through its registered generator.
- Never treat a mirror, report, archive, or unclassified role as truth.

## Anti-patterns

- Declaring completion from a summary rather than from evidence.
- Appending a terminal record before the artifact exists, or before evidence holds.
- Editing existing terminal records instead of appending a correction.
- Closing the external register before local governance is persisted — that is the
  ordering that produces an unrecoverable split.
- Duplicating a terminal record by re-running the close-out.
- Silently creating directories while merely resolving paths.
