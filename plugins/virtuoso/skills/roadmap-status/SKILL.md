---
name: roadmap-status
description: |
  MANUAL INVOCATION ONLY. Read-only status briefing (~5 min). ONLY runs
  when the user types "/roadmap-status", "roadmap status", or "status
  update". Reads the roadmap document and the project's configured
  work register through its provider, computes figures with provenance,
  and composes a plain-language briefing. It writes nothing to the
  project unless the user explicitly approves a bounded correction
  phase. DO NOT auto-trigger on conversational mentions of status,
  progress, or planning.
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

# Roadmap Status

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

Read the `roadmap-integrity:` line. On `fail` (null bytes, non-UTF-8, or missing — exit 3), STOP and report the corruption to the user; do not migrate or rewrite a corrupt roadmap. On `warn` (empty or unusually large — exit 2), surface it and confirm with the user before proceeding. On `ok`, continue.


Heavyweight, periodic recalibration of an entire project. The ceremony
you run when you need to know — with confidence — where the project
has been, where it's going, and what to dispatch next.
## Read-only by default

Phase 1 — the whole briefing — performs **zero project writes** (redesign item 36).
Archival, straggler migration, and status correction all live in Phase 2, which
runs only after the user explicitly approves specific, named changes.

If the user asked for a status update and nothing else, Phase 1 is the entire
skill. Ending after Phase 1 is a complete, correct run.

Phase 2 is additionally gated by the registry: a correction is attempted only when
the target role's `allowedWriters` names `roadmap-status` **and** the provider
reports the capability. When it does not, the correction is reported as a
recommendation for a ceremony that is permitted to make it.

## When to use

- Weekly or ad-hoc "where are we" check
- Before a stakeholder conversation
- Returning after a gap and wanting the short version

Do NOT use this for:
- Replanning or re-sequencing — `/roadmap-review`
- Finalizing a specification for dispatch — `/next-pointer`
- Closing out completed work — `/pointer-closeout`

## Invocation

Manual only: `/roadmap-status`, "roadmap status", "status update".

## Glossary

- **Work item** — a discrete unit of work with clear acceptance criteria.
- **Group / lane** — optional grouping levels, only if `policy.roadmap.hierarchy`
  and `policy.roadmap.lanes` declare them.
- **Stub / specification** — an item without / with its full card.
- **Straggler** — an item still in the roadmap's active section that has in fact
  shipped.

This skill **reads** the roadmap and the live work register. Its only write
actions are the small, individually approved corrections of Phase 2.

## Operating principles

1. **Read-only unless approved.** Phase 1 writes nothing. Phase 2 writes only what
   the user named.
2. **Descriptive names first.** Every bullet leads with the item's human title;
   the identifier follows in parentheses.
3. **Plain language, always.** Complete sentences, no fragments, no bare acronyms.
4. **Fast.** The whole briefing readable in under 60 seconds at the summary level.
5. **The provider is the register.** Figures come from the configured provider,
   never from a generated report or spreadsheet cache.
6. **Provenance on every figure.** Provider, source, snapshot time. A stale
   snapshot is labelled with its age.
7. **Never fabricate a figure.** A metric the data cannot support is reported as
   *not computable*, naming the missing inputs.
8. **Read, don't restructure.** This skill never re-sequences, authors
   specifications, or changes group boundaries.
9. **Two-phase hard ceiling.** Phase 2 executes only changes under five minutes
   each. Anything larger is handed to `/roadmap-review`.
10. **Bounded questions**, per `references/actors-and-interaction.md`.

## Writing rules for bullets

Apply these while writing, to every **Recently completed** and **Coming up** bullet.

### Rule 1 — Lead with the name, then bold the summary
```
- **[Item title]** — one- or two-sentence summary that says the news. *(ITEM-ID)*
  - Supporting detail (optional).
  - *Issue: [plain-language sentence, if any].*
```

### Rule 2 — The summary answers "what + why"
Pick the one or two angles most useful: what was supposed to happen, what
happened, why it matters, or zoom in/out.

### Rule 3 — Lead with news, not process

✗ "**Diagnostic review** — investigated a failing result and discovered the
original explanation was wrong; wrote up a protocol."

✓ "**Diagnostic review** — the earlier failure was misdiagnosed. The deeper
investigation produced a standing protocol now in force for every future failure
of this kind."

### Rule 4 — Complete sentences, never fragments

✗ "**Gate fix** — hybrid revert; secondary gate cleared at 20.90%."

✓ "**Gate fix** — the broken secondary gate is fixed. Reverting to a clean
baseline cleared it at 20.9%, inside the target band, which unblocks the rest of
the cluster."

### Rule 5 — Expand or paraphrase acronyms

✗ "**Flash symmetry** — added Sec-INT flash mult; ref overshot at 70, retuned to 60."

✓ "**Flash symmetry** — secondary-channel specialists now receive a finish bonus
comparable to primary-channel specialists, evening out the two channels. An
initial multiplier overshot the target band and was tuned down."

### Rule 6 — Coming-up bullets follow the same format

✓ "**Attribute wiring** — wires the two relevant attributes into the
secondary-channel bonus calculation, so participants with high values in both are
rewarded for committed attempts. *(ITEM-ID)*"
  - *Adaptation: validation runs use two random seeds instead of one to reduce
    noise.*

### The stranger test
Before saving, ask of every summary: would a smart colleague who has never seen
this project understand the news from this line alone? If not, rewrite.

---

## Inputs

1. The registry — the authority for every path and permission.
2. The roadmap document, through its registered role.
3. The live work register, through its provider:

        "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . items --all --json
        "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . kpis --json

4. The terminal ledger — for what is already final.
5. The registered reviews directory — for the previous briefing and the pace read.
6. The registered close-outs directory — for completion evidence.

Never open a register file directly, and never read a generated report to obtain a
figure.

## Outputs

1. The briefing, in chat.
2. The briefing saved into the registered reviews directory (a checkins
   subdirectory when the project keeps one). **This is the one Phase 1 write, and
   it goes to a role this ceremony is registered to write.** If
   `roadmapReviews`'s `allowedWriters` does not name `roadmap-status`, print the
   briefing and say it was not saved, rather than writing anywhere else.
3. Nothing else, unless Phase 2 is approved.

---

## Phase 1 — READ & REPORT (read-only)

### 1.1 Determine the window
"Recent" = the longer of: time since the last briefing or review artifact, or the
last seven days.

### 1.2 Identify the current group
Only if `policy.roadmap.hierarchy` declares grouping. A flat project has no
"current phase" and the briefing simply omits that line — do not invent one.

### 1.3 Compute figures through the provider

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . kpis --json

The provider returns each metric with its provenance and marks anything it cannot
compute. Report them as returned:

| Figure | Notes |
|---|---|
| Total items | |
| Counts by canonical status | queued, in-flight, blocked, completed, dissolved, superseded, unknown |
| % complete by count | terminal ÷ total |
| Effort totals and % complete by effort | requires an effort value on every item and a scale entry for every value; otherwise **not computable**, with the offending items named |
| Items remaining | blocked + queued + in-flight |
| Dispatch-ready items | against `policy.roadmap.dispatchBuffer`; if the buffer is 0, report "eager specification disabled" |
| Group progress | only if the project uses grouping |

The status *words* in the register are the project's own; the canonical statuses
above come from `policy.workRegister.statusMappings`. Never assume a project
spells anything a particular way.

**There is no cache to refresh.** If a generated report exists and disagrees, the
report is stale by definition — note it if asked, regenerate it through its
registered generator if the user wants, and never read it as truth.

### 1.4 Read window signals
- Items whose completion date falls in the window → recently shipped
- Items added during the window → possible sideways scope
- Items at the head of the sequence that predate the window and are still active
  → potentially stuck
- Pace: completions in the window versus the recent average. If completion dates
  are absent from the register, pace is **not computable** — say so.

### 1.5 Straggler scan (read-only)
Walk the roadmap's active section and look for completion signals:
- a close-out artifact exists in the registered close-outs directory
- a terminal record exists in the terminal ledger
- the deliverable the item was to produce now exists

An item with completion signals but still active is a **straggler**. Record it as
a Phase 2 candidate. **Do not migrate it in Phase 1.**

### 1.6 Drift scan (read-only)
- In the roadmap's active section but absent from the register
- Active in the register but absent from the roadmap's active section
- Sequence order differs between the two
- A prerequisite that resolves to nothing

Each becomes a Phase 2 candidate, never a Phase 1 edit.

### 1.7 Compose the briefing

```
## Roadmap Status — YYYY-MM-DD

*Source: [register] via [provider], snapshot [timestamp][ — STALE: reason].*
*[Read through the legacy compatibility adapter — reads only.]*

### Health
- [Whether work is moving.]
- [Anything stuck.]
- [Anything sideways.]
- [Pace — or: pace is not computable because [missing inputs].]
- [Dispatch buffer: N of [policy target] — or: eager specification is disabled.]
- [If stragglers: N items look complete and need migration.]
- [If drift: the roadmap and the register disagree about N items.]

### Recently completed (since YYYY-MM-DD)
- **[Item title]** — summary. *(ITEM-ID)*
  - Supporting detail.

### Coming up (next 2–4 items)
- **[Item title]** — summary. *(ITEM-ID)*
  - *Adaptation: …*

### Where we stand
- **Current group ([name]):** X% of the group's work remains. *(omit for a flat project)*
- **Finish line:** Y% remains by effort; N items remain.
  *(or: not computable — [missing inputs])*

### Health read
- **[On track / Watch closely / Concerns]** — one plain-language sentence saying why.

### Recommended corrections
- **[Item title]** — one-sentence specific action, under five minutes. *(ITEM-ID)*
  *[permitted / needs a ceremony with write access to <role>]*
```

**Section rules**
- Recently completed: items that became terminal during the window.
- Coming up: the head of the active sequence, forward.
- Stragglers become recommendations: "Migrate to the completed summary and record
  the terminal record."
- Drift becomes recommendations naming the specific disagreement.
- Every recommendation is marked *permitted* or *needs a ceremony with write
  access*, based on the registry and the provider's capabilities.
- No recommendations → `- _No corrections needed — the roadmap and the register agree._`

**Escalation rule.** A recommendation that would require restructuring is not
listed as a correction. Instead:

```
### Larger changes detected
- **[Item title]** — one sentence explaining why /roadmap-review is the right
  ceremony for this. *(ITEM-ID)*
```

### 1.8 Save the briefing
Into the registered reviews directory (a `checkins` subdirectory if the project
keeps one), as `YYYY-MM-DD-status.md`, including the provenance line.

### 1.9 Present and pause

Show the briefing, then ask:
- (a) Approve all corrections — run Phase 2 *(recommended when corrections exist and are permitted)*
- (b) Approve some — pick which
- (c) Read only — stop here
- (d) The read is wrong — explain

With no corrections, close after (c). **Do not run Phase 2 without an explicit
approval of specific corrections.**

---

## Phase 2 — CORRECT (only with explicit approval)

This is the mutation phase. It runs only on named, approved corrections.

### 2.0 Confirm permission before touching anything

For each approved correction, confirm:
1. the target role's `allowedWriters` names `roadmap-status`;
2. the provider reports the capability the correction needs;
3. the role's authority and mutability permit a write at all — `archive`,
   `unknown`, `read-only`, and `immutable` never do.

If any of the three fails, **do not attempt the write**. Report the correction as
a hand-off to a ceremony that is permitted to make it, and say which check failed.

### 2.1 Execute the approved corrections

- **Straggler migration**
  1. Add the one-line entry to the roadmap's completed summary.
  2. Remove the full block from the active section.
  3. Update the item in the live register through the provider: status, clear the
     sequence, completion date, evidence link — passing the `revision` read in
     Phase 1 so a concurrent change is refused rather than clobbered.
  4. The terminal record belongs to the close-out ceremony. Append it here only if
     `policy.terminalLedger.correctionWriters` names `roadmap-status`; otherwise
     list it as a hand-off. Terminal records are append-only: a correction is a
     new record referencing the one it corrects, never an edit to history.

  All of this counts as one logical migration.

- **Drift reconciliation**
  - Item terminal in reality but active in the register → set its status.
  - Active in the roadmap but missing from the register → add it, if the provider
    supports it; otherwise report it.
  - Sequence mismatch → renumber only if the provider can write the sequence field.

- **Status notes** → edit the roadmap; mirror through the provider only where a
  field actually changes.

- **Risk flags** → append to the roadmap's notes section.

### 2.2 Regenerate derived artifacts (never hand-edit them)

If a generated report role exists and the register changed:

    "$HOME/.virtuoso/bin/virtuoso" build_register_report --root . --role sprintQueue

The generator refuses any role the project has not declared generated. Never edit
a generated artifact directly.

### 2.3 Confirm and close

Report:
- exactly which corrections were applied, and to which roles
- which were handed off, and why
- any recovery records created by a partial cross-system failure
  (`virtuoso_registry recovery`)
- the refreshed figures, with provenance

---

## Question protocol reminder

Every clarifying question follows `references/actors-and-interaction.md`: 2–4
concrete options, exactly one recommended, an escape hatch on consequential
decisions — structured when the host supports it, plain text when it does not.
